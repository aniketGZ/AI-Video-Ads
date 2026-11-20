"""
Batch Prompt Image Generation Engine

Enables uploading 1 or multiple Markdown/text files containing up to 100+ prompts,
intelligently parsing prompt blocks, and generating images in an automated queue
with rate-limit backoff handling, reference image bindings, live polling, and ZIP export.
"""

import os
import re
import json
import time
import uuid
import asyncio
import logging
import zipfile
import threading
from typing import List, Dict, Any, Optional

from fastapi import APIRouter, UploadFile, File, Form, Header, HTTPException
from fastapi.responses import FileResponse
from google import genai
from google.genai import types

from media_utils import (
    GENERATED_DIR,
    save_generated_media,
    IMAGE_EXTS,
    MAX_IMAGE_BYTES,
    GEMINI_IMAGE_ASPECTS,
    image_model,
    generate_gemini_image,
    sanitize_visual_prompt,
    mime_for_path,
)

logger = logging.getLogger(__name__)


def _get_genai_client(api_key: Optional[str] = None) -> Optional[genai.Client]:
    """Initializes and returns a Google GenAI client if an API key is provided or present in environment."""
    if api_key and str(api_key).strip().lower() in ("undefined", "null", "none"):
        api_key = None
    key = (api_key or os.environ.get("GEMINI_API_KEY") or "").strip()
    if not key:
        return None
    try:
        return genai.Client(api_key=key)
    except Exception as e:
        logger.warning(f"[batch_prompt] Could not initialize genai.Client: {e}")
        return None

batch_prompt_router = APIRouter(prefix="/api/batch-prompts", tags=["batch-prompts"])

BATCH_JOBS_FILE = "/tmp/batch_jobs.json" if os.environ.get("VERCEL") else os.path.join("data", "batch_jobs.json")
_jobs_lock = threading.Lock()
_batch_jobs: Dict[str, Dict[str, Any]] = {}
_job_controls: Dict[str, Dict[str, bool]] = {}  # {batch_id: {"paused": bool, "cancelled": bool}}


# ---------------------------------------------------------------------------
# Storage & Persistence
# ---------------------------------------------------------------------------
def _load_batch_jobs_cache() -> Dict[str, Dict[str, Any]]:
    if not os.path.exists(BATCH_JOBS_FILE):
        return {}
    try:
        with open(BATCH_JOBS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, dict) else {}
    except Exception as e:
        logger.warning(f"[batch_prompt] Could not load batch jobs cache: {e}")
        return {}


def _save_batch_job(batch_id: str, data: Dict[str, Any]) -> None:
    now = time.time()
    with _jobs_lock:
        cache = _load_batch_jobs_cache()
        data["updated_at"] = now
        data.setdefault("created_at", now)
        _batch_jobs[batch_id] = data
        cache[batch_id] = data

        # Keep last 50 jobs
        if len(cache) > 50:
            sorted_keys = sorted(cache.keys(), key=lambda k: cache[k].get("created_at", 0))
            for old_k in sorted_keys[:-50]:
                cache.pop(old_k, None)

        try:
            os.makedirs(os.path.dirname(BATCH_JOBS_FILE), exist_ok=True)
            tmp_path = BATCH_JOBS_FILE + ".tmp"
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(cache, f, ensure_ascii=False, indent=2)
            os.replace(tmp_path, BATCH_JOBS_FILE)
        except Exception as e:
            logger.warning(f"[batch_prompt] Failed to persist job {batch_id}: {e}")


def get_batch_job(batch_id: str) -> Optional[Dict[str, Any]]:
    with _jobs_lock:
        if batch_id in _batch_jobs:
            return _batch_jobs[batch_id]
        cache = _load_batch_jobs_cache()
        job = cache.get(batch_id)
        if job:
            _batch_jobs[batch_id] = job
        return job


# ---------------------------------------------------------------------------
# Intelligent Markdown Prompt Parser
# ---------------------------------------------------------------------------
def _clean_str(text: str) -> str:
    """Removes non-printable/control chars while keeping markdown structure."""
    if not text:
        return ""
    return re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text).strip()


def _extract_aspect_ratio(text: str) -> Optional[str]:
    """Extracts aspect ratio if specified anywhere in the text (e.g. 1:1, 4:5, 9:16, 16:9)."""
    match = re.search(r"\b(1:1|4:5|9:16|16:9|21:9|3:4|4:3|2:3|3:2)\b", text)
    return match.group(1) if match else None


def _clean_title(title: str) -> str:
    if not title:
        return ""
    t = re.sub(r"^#{1,6}\s*", "", title)
    t = re.sub(r"^\d+[\.\)]\s*", "", t)
    t = re.sub(r"[\*\_]", "", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t[:80]


def parse_prompts_from_markdown(content: str, filename: str = "") -> List[Dict[str, Any]]:
    """
    Parses up to 100+ prompt definitions from a markdown or text file.
    Compares all viable parsing strategies (headings, explicit PROMPT tags, dividers,
    numbered lists, code fences, paragraphs) and selects the one extracting the
    greatest number of valid prompts.
    """
    content = _clean_str(content.replace("\r\n", "\n"))
    if not content:
        return []

    strategies_results = []

    # Strategy 1: Explicit PROMPT: or **PROMPT:** tags
    if re.search(r"\bPROMPT:\s*", content, re.IGNORECASE):
        strat1 = []
        sections = re.split(r"(?:\n|\A)(?=#{1,4}\s+|\*{0,2}PROMPT:?\*{0,2})", content)
        curr_title = ""
        for sec in sections:
            header_m = re.match(r"^#{1,4}\s+([^\n]+)", sec)
            if header_m:
                curr_title = _clean_title(header_m.group(1))

            p_match = re.search(r"\*{0,2}PROMPT:?\*{0,2}\s*\n(.*)", sec, re.DOTALL | re.IGNORECASE)
            if p_match:
                p_text = p_match.group(1).strip()
                p_text = re.split(r"\n---+\n|\n\*\*\*+\n", p_text)[0].strip()
                if len(p_text) >= 15:
                    strat1.append({
                        "id": len(strat1) + 1,
                        "title": curr_title or f"Prompt {len(strat1) + 1}",
                        "prompt": p_text,
                        "aspect_ratio": _extract_aspect_ratio(p_text),
                        "source_file": filename,
                        "word_count": len(p_text.split()),
                    })
        if strat1:
            strategies_results.append((len(strat1), 2, strat1))

    # Strategy 2: Headings (##, ###, #)
    headers = list(re.finditer(r"^(#{1,4}\s+[^\n]+)", content, re.MULTILINE))
    if len(headers) >= 2:
        strat2 = []
        for i, h in enumerate(headers):
            start = h.start()
            end = headers[i + 1].start() if i + 1 < len(headers) else len(content)
            sec = content[start:end].strip()
            lines = sec.split("\n")
            title = _clean_title(lines[0])
            body = "\n".join(lines[1:]).strip()

            clean_body = re.sub(r"^\*{0,2}PROMPT:?\*{0,2}\s*", "", body, flags=re.IGNORECASE).strip()
            codes = re.findall(r"```(?:[a-zA-Z0-9_\-]+)?\n(.*?)```", clean_body, re.DOTALL)
            p_text = "\n\n".join(c.strip() for c in codes) if codes else clean_body

            lines_body = [l.strip() for l in p_text.split("\n") if l.strip()]
            if lines_body and all(l.startswith("|") and l.endswith("|") for l in lines_body[:3]):
                continue

            low_title = title.lower()
            if len(p_text) >= 15 and not any(low_title.startswith(skip) for skip in ["table of contents", "overview", "introduction", "inputs", "role", "metadata"]):
                strat2.append({
                    "id": len(strat2) + 1,
                    "title": title or f"Prompt {len(strat2) + 1}",
                    "prompt": p_text,
                    "aspect_ratio": _extract_aspect_ratio(p_text),
                    "source_file": filename,
                    "word_count": len(p_text.split()),
                })
        if strat2:
            strategies_results.append((len(strat2), 3, strat2))

    # Strategy 3: Horizontal rule dividers (--- or ***)
    div_parts = [p.strip() for p in re.split(r"\n---+\n|\n\*\*\*+\n", content) if p.strip()]
    if len(div_parts) >= 2:
        strat3 = []
        for idx, part in enumerate(div_parts, 1):
            p_text = part
            title = f"Prompt {idx}"
            m_first = re.match(r"^(?:#{1,4}\s+|\*\*)([^\n\*]+)(?:\*\*|\n)", part)
            if m_first:
                title = _clean_title(m_first.group(1))
                p_text = part[m_first.end():].strip()
            p_text = re.sub(r"^\*{0,2}PROMPT:?\*{0,2}\s*", "", p_text, flags=re.IGNORECASE).strip()
            if len(p_text) >= 15:
                strat3.append({
                    "id": len(strat3) + 1,
                    "title": title,
                    "prompt": p_text,
                    "aspect_ratio": _extract_aspect_ratio(p_text),
                    "source_file": filename,
                    "word_count": len(p_text.split()),
                })
        if strat3:
            strategies_results.append((len(strat3), 1, strat3))

    # Strategy 4: Numbered list items
    num_matches = list(re.finditer(r"(?:^|\n)(\d+)[\.\)]\s+([^\n]+(?:\n(?!\d+[\.\)]\s+)[^\n]+)*)", content))
    if len(num_matches) >= 2:
        strat4 = []
        for m in num_matches:
            num = m.group(1)
            p_text = m.group(2).strip()
            p_text = re.sub(r"^\*{0,2}PROMPT:?\*{0,2}\s*", "", p_text, flags=re.IGNORECASE).strip()
            if len(p_text) >= 15:
                strat4.append({
                    "id": len(strat4) + 1,
                    "title": f"Prompt {num}",
                    "prompt": p_text,
                    "aspect_ratio": _extract_aspect_ratio(p_text),
                    "source_file": filename,
                    "word_count": len(p_text.split()),
                })
        if strat4:
            strategies_results.append((len(strat4), 0, strat4))

    # Strategy 5: Standalone code blocks
    code_blocks = re.findall(r"```(?:[a-zA-Z0-9_\-]+)?\n(.*?)```", content, re.DOTALL)
    if len(code_blocks) >= 2:
        strat5 = []
        for idx, cb in enumerate(code_blocks, 1):
            p_text = cb.strip()
            if len(p_text) >= 15:
                strat5.append({
                    "id": len(strat5) + 1,
                    "title": f"Prompt {idx}",
                    "prompt": p_text,
                    "aspect_ratio": _extract_aspect_ratio(p_text),
                    "source_file": filename,
                    "word_count": len(p_text.split()),
                })
        if strat5:
            strategies_results.append((len(strat5), -1, strat5))

    if strategies_results:
        # Sort by count descending, then strategy priority
        strategies_results.sort(key=lambda x: (x[0], x[1]), reverse=True)
        chosen = strategies_results[0][2]
        for i, item in enumerate(chosen, 1):
            item["id"] = i
        return chosen

    # Fallback: Double newline paragraphs or full document
    paras = [p.strip() for p in re.split(r"\n\s*\n", content) if len(p.strip()) >= 20]
    if len(paras) > 1:
        prompts = []
        for idx, p in enumerate(paras, 1):
            clean_p = re.sub(r"^\*{0,2}PROMPT:?\*{0,2}\s*", "", p, flags=re.IGNORECASE).strip()
            if len(clean_p) >= 15:
                prompts.append({
                    "id": len(prompts) + 1,
                    "title": f"Prompt {idx}",
                    "prompt": clean_p,
                    "aspect_ratio": _extract_aspect_ratio(clean_p),
                    "source_file": filename,
                    "word_count": len(clean_p.split()),
                })
        if prompts:
            return prompts

    if len(content) >= 15:
        return [{
            "id": 1,
            "title": filename or "Prompt 1",
            "prompt": content,
            "aspect_ratio": _extract_aspect_ratio(content),
            "source_file": filename,
            "word_count": len(content.split()),
        }]

    return []


# ---------------------------------------------------------------------------
# Background Queue Worker with Rate Limit & 429 Backoff
# ---------------------------------------------------------------------------
def _create_batch_zip(batch_id: str, job: Dict[str, Any]) -> Optional[str]:
    """Bundles all successfully generated images into a single ZIP file."""
    try:
        zip_filename = f"batch_{batch_id}_all.zip"
        zip_path = os.path.join(GENERATED_DIR, zip_filename)

        with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            # Manifest
            manifest = {
                "batch_id": batch_id,
                "created_at": job.get("created_at"),
                "total_prompts": job.get("total_count"),
                "completed": job.get("completed_count"),
                "failed": job.get("failed_count"),
                "prompts": job.get("prompts", []),
            }
            zf.writestr("manifest.json", json.dumps(manifest, indent=2, ensure_ascii=False))

            # Images
            for item in job.get("prompts", []):
                if item.get("status") == "success" and item.get("filename"):
                    img_file = os.path.join(GENERATED_DIR, item["filename"])
                    if os.path.exists(img_file):
                        item_id_num = int(item.get("id") or 1)
                        clean_name = re.sub(r"[^\w\-\.]", "_", item.get("title", f"prompt_{item_id_num}"))
                        arcname = f"{item_id_num:03d}_{clean_name}.png"
                        zf.write(img_file, arcname=arcname)

        return f"/static/generated/{zip_filename}"
    except Exception as e:
        logger.warning(f"[batch_prompt] Could not create zip for {batch_id}: {e}")
        return None


async def run_batch_worker(batch_id: str, api_key: Optional[str]) -> None:
    """Processes prompts in order with automatic rate limit backoff and reference image binding."""
    job = get_batch_job(batch_id)
    if not job:
        return

    _job_controls[batch_id] = {"paused": False, "cancelled": False}

    try:
        client = _get_genai_client(api_key)
        if not client:
            try:
                from media_utils import get_client as mu_get_client
                client = mu_get_client(api_key)
            except Exception:
                pass

        if not client:
            job["status"] = "failed"
            job["error"] = "Gemini API key is required. Please set your API key in the top navigation bar or in .env."
            _save_batch_job(batch_id, job)
            return

        model_key = job.get("model", "nano-banana-pro")
        default_aspect = job.get("default_aspect_ratio", "1:1")
        delay_s = max(0.5, float(job.get("rate_limit_delay_s", 2.5)))

        # Load reference images if supplied
        ref_parts: List[Any] = []
        ref_paths = job.get("reference_image_paths", [])
        for rp in ref_paths:
            full_p = os.path.join(GENERATED_DIR, os.path.basename(rp)) if not os.path.isabs(rp) else rp
            if os.path.exists(full_p):
                with open(full_p, "rb") as f:
                    mime = mime_for_path(full_p, default="image/png")
                    ref_parts.append(types.Part.from_bytes(data=f.read(), mime_type=mime))

        ref_prefix = ""
        if len(ref_parts) == 1:
            ref_prefix = (
                "IMAGE 1 is the reference product/subject. Reproduce it accurately with high fidelity "
                "(exact shape, branding, colors, and label layout) as the hero in the scene.\n\n"
            )
        elif len(ref_parts) > 1:
            ref_tags = ", ".join(f"IMAGE {i+1}" for i in range(len(ref_parts)))
            ref_prefix = (
                f"The attached images ({ref_tags}) are reference images. Maintain exact visual fidelity "
                "to the product packaging, branding, materials, and styling shown.\n\n"
            )

        prompts = job.get("prompts", [])
        total = len(prompts)

        for idx, item in enumerate(prompts):
            # 1. Check if cancelled
            if _job_controls[batch_id]["cancelled"]:
                item["status"] = "cancelled"
                continue

            # 2. Check if paused
            while _job_controls[batch_id]["paused"]:
                if _job_controls[batch_id]["cancelled"]:
                    break
                job["status"] = "paused"
                job["rate_limit_notice"] = "Batch queue is paused by user."
                _save_batch_job(batch_id, job)
                await asyncio.sleep(1.0)

            if _job_controls[batch_id]["cancelled"]:
                item["status"] = "cancelled"
                continue

            job["status"] = "running"
            job["current_index"] = idx
            item["status"] = "processing"
            job["rate_limit_notice"] = f"Processing #{item['id']} of {total}: '{item['title']}'..."
            _save_batch_job(batch_id, job)

            # Format prompt text
            raw_prompt = item.get("prompt", "")
            # Sanitize proper names if any
            clean_prompt = sanitize_visual_prompt(raw_prompt)

            # Append reference prefix if needed and not already present
            if ref_prefix and not ("IMAGE 1" in clean_prompt.upper() or "<IMAGE_REF" in clean_prompt.upper()):
                final_text = f"{ref_prefix}{clean_prompt}"
            else:
                final_text = clean_prompt

            # Append anti-celebrity guardrail if not already in prompt
            if "avoid:" not in final_text.lower():
                final_text = f"{final_text} (AVOID: celebrity likeness, famous actors, public figures, retouched glamour aesthetics, distorted hands)"

            item_aspect = item.get("aspect_ratio") or default_aspect
            if item_aspect not in GEMINI_IMAGE_ASPECTS:
                item_aspect = default_aspect

            # Generation loop with rate-limit exponential backoff
            max_retries = 5
            backoff_s = 14.0
            item_success = False

            for attempt in range(max_retries):
                if _job_controls[batch_id]["cancelled"]:
                    item["status"] = "cancelled"
                    break

                try:
                    contents = [*ref_parts, final_text]
                    image_bytes = await asyncio.to_thread(
                        generate_gemini_image, client, contents, item_aspect, model_key
                    )
                    if not image_bytes:
                        raise RuntimeError("Model returned no image data.")

                    item_id_num = int(item.get("id") or (idx + 1))
                    filename = f"batch_{batch_id}_{item_id_num:03d}_{uuid.uuid4().hex[:6]}.png"
                    item_url = save_generated_media(filename, image_bytes, "image/png")

                    item["status"] = "success"
                    item["image_url"] = item_url
                    item["filename"] = filename
                    item["error"] = None
                    job["completed_count"] += 1
                    job["rate_limit_notice"] = ""
                    item_success = True
                    break

                except Exception as e:
                    err_msg = str(e)
                    err_lower = err_msg.lower()
                    is_rate_limit = any(
                        term in err_lower
                        for term in ["429", "resource_exhausted", "quota", "rate limit", "too many requests", "rate_limit"]
                    )
                    item["attempts"] = attempt + 1

                    if is_rate_limit and attempt < max_retries - 1:
                        item["status"] = "retrying"
                        wait_time = int(backoff_s)
                        job["rate_limit_notice"] = (
                            f"⏳ Rate limit reached on prompt #{item['id']} ('{item['title']}'). "
                            f"Cooling down for {wait_time}s before automatic retry ({attempt + 1}/{max_retries})..."
                        )
                        _save_batch_job(batch_id, job)
                        await asyncio.sleep(wait_time)
                        backoff_s = min(backoff_s * 1.8, 90.0)
                    else:
                        item["status"] = "failed"
                        item["error"] = err_msg
                        job["failed_count"] += 1
                        job["rate_limit_notice"] = ""
                        logger.warning(f"[batch_prompt] Prompt #{item['id']} failed: {err_msg}")
                        break

            _save_batch_job(batch_id, job)

            # Delay between prompts to avoid hitting requests-per-minute bursts
            if item_success and delay_s > 0 and idx + 1 < total and not _job_controls[batch_id]["cancelled"]:
                job["rate_limit_notice"] = f"Queue delay: waiting {delay_s:.1f}s before next prompt..."
                _save_batch_job(batch_id, job)
                await asyncio.sleep(delay_s)

        # Mark final status
        if _job_controls[batch_id]["cancelled"]:
            job["status"] = "cancelled"
            job["rate_limit_notice"] = "Batch run was cancelled."
        else:
            job["status"] = "completed"
            job["rate_limit_notice"] = "All prompts processed."

        # Bundle ZIP
        zip_url = _create_batch_zip(batch_id, job)
        if zip_url:
            job["zip_url"] = zip_url

        _save_batch_job(batch_id, job)

    except Exception as e:
        logger.error(f"[batch_prompt] Batch runner crashed for {batch_id}: {e}", exc_info=True)
        job["status"] = "failed"
        job["error"] = str(e)
        _save_batch_job(batch_id, job)
    finally:
        _job_controls.pop(batch_id, None)


# ---------------------------------------------------------------------------
# API Routes
# ---------------------------------------------------------------------------
@batch_prompt_router.post("/parse")
async def parse_batch_markdown_files(files: List[UploadFile] = File(...)):
    """
    Accepts 1 or multiple Markdown or text files and returns the extracted prompts list.
    Supports up to 100+ prompts.
    """
    if not files:
        raise HTTPException(status_code=400, detail="Please upload at least 1 Markdown (.md) or text (.txt) file.")

    all_prompts: List[Dict[str, Any]] = []

    for f in files:
        if not f.filename:
            continue
        try:
            content_bytes = await f.read()
            text = content_bytes.decode("utf-8", errors="replace")
            parsed = parse_prompts_from_markdown(text, filename=f.filename)
            all_prompts.extend(parsed)
        except Exception as e:
            logger.warning(f"[batch_prompt] Could not parse file {f.filename}: {e}")

    # Re-number prompts sequentially
    for idx, p in enumerate(all_prompts, start=1):
        p["id"] = idx

    return {
        "status": "success",
        "total": len(all_prompts),
        "prompts": all_prompts,
        "files_parsed": len(files),
    }


@batch_prompt_router.post("/start")
async def start_batch_generation(
    prompts: str = Form(...),
    model: str = Form("nano-banana-pro"),
    aspect_ratio: str = Form("1:1"),
    rate_limit_delay_s: float = Form(2.5),
    reference_images: Optional[List[UploadFile]] = File(None),
    x_api_key: Optional[str] = Header(None),
):
    """
    Starts a background batch generation queue for up to 100 prompts.
    """
    try:
        parsed_prompts = json.loads(prompts)
        if not isinstance(parsed_prompts, list) or not parsed_prompts:
            raise HTTPException(status_code=400, detail="Prompts list is empty.")
    except (ValueError, TypeError):
        raise HTTPException(status_code=400, detail="Invalid JSON for prompts.")

    if len(parsed_prompts) > 120:
        raise HTTPException(status_code=400, detail="Maximum 100 prompts allowed per batch.")

    # Save reference images if provided
    ref_paths: List[str] = []
    if reference_images:
        os.makedirs(GENERATED_DIR, exist_ok=True)
        max_refs = image_model(model).get("max_refs", 14)
        for upload in reference_images[:max_refs]:
            if not upload or not upload.filename:
                continue
            ext = os.path.splitext(upload.filename)[1].lower()
            if ext not in IMAGE_EXTS:
                continue
            content = await upload.read()
            if len(content) > MAX_IMAGE_BYTES:
                continue
            fname = f"batch_ref_{uuid.uuid4().hex[:8]}{ext}"
            fpath = os.path.join(GENERATED_DIR, fname)
            with open(fpath, "wb") as f_out:
                f_out.write(content)
            ref_paths.append(f"/static/generated/{fname}")

    batch_id = f"batch_{int(time.time())}_{uuid.uuid4().hex[:6]}"

    # Prepare prompt records
    clean_items = []
    for idx, p in enumerate(parsed_prompts, start=1):
        clean_items.append({
            "id": idx,
            "title": p.get("title") or f"Prompt {idx}",
            "prompt": p.get("prompt", "").strip(),
            "aspect_ratio": p.get("aspect_ratio") or aspect_ratio,
            "source_file": p.get("source_file", ""),
            "status": "pending",
            "image_url": None,
            "filename": None,
            "error": None,
            "attempts": 0,
        })

    job = {
        "batch_id": batch_id,
        "status": "queued",
        "created_at": time.time(),
        "updated_at": time.time(),
        "model": model,
        "default_aspect_ratio": aspect_ratio,
        "rate_limit_delay_s": max(0.5, float(rate_limit_delay_s)),
        "reference_image_paths": ref_paths,
        "total_count": len(clean_items),
        "completed_count": 0,
        "failed_count": 0,
        "current_index": 0,
        "rate_limit_notice": "Queue starting...",
        "prompts": clean_items,
        "zip_url": None,
    }

    _save_batch_job(batch_id, job)
    asyncio.create_task(run_batch_worker(batch_id, x_api_key))

    return {
        "status": "queued",
        "batch_id": batch_id,
        "total": len(clean_items),
    }


@batch_prompt_router.get("/status/{batch_id}")
async def get_batch_status(batch_id: str):
    """Returns live progress and results of a batch job."""
    job = get_batch_job(batch_id)
    if not job:
        raise HTTPException(status_code=404, detail="Batch job not found.")
    return job


@batch_prompt_router.post("/pause/{batch_id}")
async def pause_batch(batch_id: str):
    job = get_batch_job(batch_id)
    if not job:
        raise HTTPException(status_code=404, detail="Batch job not found.")
    if batch_id in _job_controls:
        _job_controls[batch_id]["paused"] = True
    job["status"] = "paused"
    job["rate_limit_notice"] = "Batch queue paused by user."
    _save_batch_job(batch_id, job)
    return {"status": "paused", "batch_id": batch_id}


@batch_prompt_router.post("/resume/{batch_id}")
async def resume_batch(batch_id: str):
    job = get_batch_job(batch_id)
    if not job:
        raise HTTPException(status_code=404, detail="Batch job not found.")
    if batch_id in _job_controls:
        _job_controls[batch_id]["paused"] = False
    job["status"] = "running"
    job["rate_limit_notice"] = "Resuming queue..."
    _save_batch_job(batch_id, job)
    return {"status": "running", "batch_id": batch_id}


@batch_prompt_router.post("/cancel/{batch_id}")
async def cancel_batch(batch_id: str):
    job = get_batch_job(batch_id)
    if not job:
        raise HTTPException(status_code=404, detail="Batch job not found.")
    if batch_id in _job_controls:
        _job_controls[batch_id]["cancelled"] = True
    job["status"] = "cancelled"
    job["rate_limit_notice"] = "Batch queue cancelled."
    _save_batch_job(batch_id, job)
    return {"status": "cancelled", "batch_id": batch_id}


@batch_prompt_router.get("/download-zip/{batch_id}")
async def download_batch_zip(batch_id: str):
    job = get_batch_job(batch_id)
    if not job:
        raise HTTPException(status_code=404, detail="Batch job not found.")

    zip_path = os.path.join(GENERATED_DIR, f"batch_{batch_id}_all.zip")
    if not os.path.exists(zip_path):
        # Generate on the fly if needed
        zip_url = _create_batch_zip(batch_id, job)
        if not zip_url:
            raise HTTPException(status_code=404, detail="No images available to download.")

    return FileResponse(zip_path, filename=f"batch_images_{batch_id}.zip", media_type="application/zip")


@batch_prompt_router.get("/history")
async def get_batch_history():
    """Returns the most recent batch runs."""
    cache = _load_batch_jobs_cache()
    summary = []
    for bid, data in sorted(cache.items(), key=lambda kv: kv[1].get("created_at", 0), reverse=True)[:10]:
        summary.append({
            "batch_id": bid,
            "status": data.get("status"),
            "total_count": data.get("total_count", 0),
            "completed_count": data.get("completed_count", 0),
            "failed_count": data.get("failed_count", 0),
            "created_at": data.get("created_at"),
            "model": data.get("model", "nano-banana-pro"),
            "zip_url": data.get("zip_url"),
        })
    return {"batches": summary}
