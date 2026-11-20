import os
import json
import re
import time
import uuid
import base64
import asyncio
import logging
from contextlib import asynccontextmanager
from typing import List, Optional

from fastapi import Depends, FastAPI, HTTPException, UploadFile, File, Form, Header, Request
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from google import genai
from google.genai import types

from media_utils import (
    load_dotenv,
    sanitize_video_prompt,
    GENERATED_DIR,
    IMAGE_EXTS,
    VIDEO_EXTS,
    MAX_IMAGE_BYTES,
    MAX_VIDEO_BYTES,
    read_upload,
    mime_for_path,
    generate_gemini_image,
    IMAGE_MODELS,
    DEFAULT_IMAGE_MODEL,
    image_model,
    GEMINI_IMAGE_RESOLUTIONS,
    DEFAULT_IMAGE_RESOLUTION,
    OMNI_VIDEO_RESOLUTIONS,
    DEFAULT_VIDEO_RESOLUTION,
    get_video_dimensions,
    ensure_video_resolution,
    resolve_generated_path,
)

# Load .env before the routers below read API keys from the environment
load_dotenv()

from job_store import persist_job_update, load_job  # noqa: E402
from meta_creative_engine import generate_single_meta_creative  # noqa: E402
from competitor_ad_routes import router as competitor_ad_router  # noqa: E402
from campaign_flow import router as campaign_flow_router  # noqa: E402
from batch_prompt_engine import batch_prompt_router  # noqa: E402
from demo_session_routes import router as demo_session_router  # noqa: E402
from access import current_plan, plan_summary, require_feature  # noqa: E402
from upgrade_routes import router as upgrade_router  # noqa: E402
from auth import router as auth_router  # noqa: E402
from saved_routes import router as saved_router  # noqa: E402
from templates_routes import router as templates_router  # noqa: E402

# Pro and Studio only (see pricing.PLANS)
CAMPAIGN_ACCESS = [Depends(require_feature("campaign_manager"))]


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# A processing job that has not reported progress for this long is marked failed.
STALE_JOB_SECONDS = 3600
OMNI_MODEL = os.environ.get("OMNI_MODEL", "gemini-omni-1.2-flash")
MAX_VIDEO_REF_IMAGES = 7  # Omni Flash reference images per video
MAX_PROMPTS_PER_REQUEST = 10  # Prompts started together, each its own render
_video_tasks: set = set()  # keeps running render tasks referenced until they finish

os.makedirs(GENERATED_DIR, exist_ok=True)


def cleanup_generated_files() -> None:
    """Delete generated files older than GENERATED_MAX_AGE_DAYS (opt-in; unset = keep everything)."""
    days = os.environ.get("GENERATED_MAX_AGE_DAYS", "").strip()
    if not days:
        return
    try:
        cutoff = time.time() - float(days) * 86400
    except ValueError:
        logger.warning(f"Ignoring invalid GENERATED_MAX_AGE_DAYS={days!r}")
        return
    removed = 0
    for name in os.listdir(GENERATED_DIR):
        path = os.path.join(GENERATED_DIR, name)
        if name == ".gitkeep" or not os.path.isfile(path):
            continue
        try:
            if os.path.getmtime(path) < cutoff:
                os.remove(path)
                removed += 1
        except OSError:
            pass
    if removed:
        logger.info(f"Removed {removed} generated files older than {days} days.")


async def _cleanup_loop():
    while True:
        await asyncio.to_thread(cleanup_generated_files)
        await asyncio.sleep(6 * 3600)


@asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(_cleanup_loop())
    yield
    task.cancel()


app = FastAPI(title="AI Ad Studio", lifespan=lifespan)

# CORS is only needed when another origin calls this API. The bundled UI is same-origin,
# so it stays off unless CORS_ORIGINS lists explicit origins.
_cors_origins = [o.strip() for o in os.environ.get("CORS_ORIGINS", "").split(",") if o.strip()]
if _cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=_cors_origins,
        allow_methods=["*"],
        allow_headers=["*"],
    )


def get_client(api_key: Optional[str] = None) -> Optional[genai.Client]:
    key = api_key or os.environ.get("GEMINI_API_KEY")
    if not key or not str(key).strip():
        return None
    try:
        return genai.Client(api_key=str(key).strip())
    except Exception as e:
        logger.warning(f"Could not initialize GenAI client: {e}")
        return None


def require_client(api_key: Optional[str] = None) -> genai.Client:
    client = get_client(api_key)
    if not client:
        raise HTTPException(status_code=400, detail="A Gemini API key is required. Add it under API Keys.")
    return client


def safe_b64decode(data) -> bytes:
    if isinstance(data, bytes):
        if b"ftyp" in data[:20]:
            return data
        try:
            return base64.b64decode(data)
        except Exception:
            return data
    if isinstance(data, str):
        if data.startswith("data:") and "," in data:
            data = data.split(",", 1)[1]
        try:
            return base64.b64decode(data)
        except Exception:
            return data.encode("latin1")
    raise TypeError(f"Unsupported video data type: {type(data)}")


def _b64(data: bytes) -> str:
    return base64.b64encode(data).decode("utf-8")


# In-memory job dictionary (mirrored to disk by persist_job_update)
video_jobs = {}


def _save_video_bytes(prefix: str, video_bytes: bytes) -> str:
    filename = f"{prefix}_{uuid.uuid4().hex}.mp4"
    with open(os.path.join(GENERATED_DIR, filename), "wb") as f:
        f.write(video_bytes)
    return f"/static/generated/{filename}"


def _paste_block(prompt: str) -> str:
    """When a prompt document wraps the prompt in a ``` block (with notes, file paths and
    'do not paste' sections around it), send only the block, as a user would paste into Flow."""
    blocks = re.findall(r"```[^\n]*\n(.*?)```", prompt or "", re.S)
    return max(blocks, key=len).strip() if blocks else (prompt or "").strip()


def _is_client_error(err: Exception) -> bool:
    """True for 4xx API errors (quota/spend cap, blocked input, invalid request)."""
    code = getattr(err, "status_code", None) or getattr(err, "code", None)
    if isinstance(code, int):
        return 400 <= code < 500
    return str(err).startswith("Error code: 4")


def _extract_interaction_video(interaction) -> Optional[str]:
    if getattr(interaction, "output_video", None):
        return interaction.output_video.data
    for step in getattr(interaction, "steps", None) or []:
        if isinstance(step, dict) and step.get("type") == "model_output" and step.get("content"):
            for part in step["content"]:
                if part.get("type") == "video":
                    return part.get("data")
    return None


# ---------------------------------------------------------------------------
# Creative Library Presets (Pinterest Reference Design Atlas)
# ---------------------------------------------------------------------------
@app.get("/api/campaign/presets")
async def list_creative_presets(industry: Optional[str] = None, q: Optional[str] = None):
    """Returns curated creative presets from Pinterest design reference library."""
    from creative_library_presets import get_all_presets, get_presets_for_industry
    presets = get_presets_for_industry(industry) if industry else get_all_presets()
    if q:
        query = q.lower().strip()
        presets = [
            p for p in presets
            if query in p["name"].lower()
            or query in p["movement"].lower()
            or query in p["industry_label"].lower()
            or query in p["summary"].lower()
        ]
    return {"status": "success", "total": len(presets), "presets": presets}


@app.get("/api/campaign/presets/{preset_id}")
async def get_creative_preset(preset_id: str):
    """Returns detail for a specific creative library preset."""
    from creative_library_presets import get_preset_by_id
    preset = get_preset_by_id(preset_id)
    if not preset:
        raise HTTPException(status_code=404, detail="Preset not found")
    return {"status": "success", "preset": preset}


@app.get("/api/campaign/presets/{preset_id}/template")
async def get_preset_template_detail(preset_id: str):
    """Returns prompt template, defaults, Pinterest reference pins, and sample preview for a preset."""
    from creative_library_presets import get_preset_prompt_template
    template_info = get_preset_prompt_template(preset_id)
    if not template_info:
        raise HTTPException(status_code=404, detail="Preset template not found")
    return {"status": "success", "template": template_info}


@app.get("/api/campaign/preset-templates")
async def list_all_preset_templates(industry: Optional[str] = None):
    """Returns all industry preset prompt templates from the Pinterest Design Atlas."""
    from creative_library_presets import list_preset_templates
    templates = list_preset_templates(industry)
    return {"status": "success", "total": len(templates), "templates": templates}


@app.post("/api/campaign/presets/render-template")
async def render_preset_template_endpoint(
    preset_id: str = Form(...),
    brand_name: str = Form(""),
    product_name: str = Form(""),
    idea: str = Form(""),
    headline: str = Form(""),
    cta: str = Form(""),
    aspect_ratio: str = Form("4:5"),
    has_product_ref: bool = Form(False),
    has_logo: bool = Form(False),
    custom_directive: Optional[str] = Form(None),
):
    """Compiles an exact commercial visual prompt from an industry preset with user inputs and image locks."""
    from creative_library_presets import get_preset_by_id, render_preset_prompt_template
    preset = get_preset_by_id(preset_id)
    if not preset:
        raise HTTPException(status_code=404, detail=f"Preset '{preset_id}' not found")

    prompt = render_preset_prompt_template(
        preset_id,
        brand_name=brand_name,
        product_name=product_name,
        idea=idea,
        headline=headline,
        cta=cta,
        aspect_ratio=aspect_ratio,
        has_product_ref=has_product_ref,
        has_logo=has_logo,
        custom_directive=custom_directive or "",
    )
    return {
        "status": "success",
        "preset_id": preset_id,
        "rendered_prompt": prompt,
        "preset": {
            "id": preset["id"],
            "name": preset["name"],
            "industry_label": preset.get("industry_label"),
            "movement": preset.get("movement"),
            "reference_pins": preset.get("reference_pins", []),
        },
    }


# ---------------------------------------------------------------------------
# Campaign image ads (Nano Banana Pro)
# ---------------------------------------------------------------------------
@app.post("/api/campaign/meta-creative-suite/render-one", dependencies=CAMPAIGN_ACCESS)
async def render_meta_creative_suite_one(
    request: Request,
    blueprint_json: str = Form(...),
    brand_name: str = Form(...),
    product_name: str = Form(...),
    product_category: str = Form(""),
    target_audience_persona: str = Form(""),
    product_visual_description: str = Form(""),
    color_palette: str = Form(""),
    business_type: str = Form(""),
    setting: str = Form(""),
    on_screen_talent: str = Form(""),
    aspect_ratio: str = Form("4:5"),
    product_image_path: Optional[str] = Form(None),
    product_image: Optional[UploadFile] = File(None),
    custom_directive: Optional[str] = Form(None),
    brand_kit_json: Optional[str] = Form(None),
    logo_path: Optional[str] = Form(None),
    logo_tone: str = Form("dark"),
    preset_id: Optional[str] = Form(None),
    model: str = Form("nano-banana-2.1"),
    x_api_key: Optional[str] = Header(None),
):
    try:
        blueprint = json.loads(blueprint_json)
        if preset_id:
            blueprint["preset_id"] = preset_id
        try:
            brand_kit = json.loads(brand_kit_json) if brand_kit_json else None
        except ValueError:
            brand_kit = None

        product_bytes = None
        mime_type = "image/png"
        if product_image and product_image.filename:
            product_bytes, _, mime_type = await read_upload(product_image, IMAGE_EXTS, ".png", MAX_IMAGE_BYTES)

        result = await generate_single_meta_creative(
            blueprint=blueprint,
            brand_name=brand_name,
            product_name=product_name,
            product_category=product_category,
            target_audience_persona=target_audience_persona,
            aspect_ratio=aspect_ratio,
            product_image_path=product_image_path,
            product_bytes=product_bytes,
            mime_type=mime_type,
            custom_directive=custom_directive,
            client=require_client(x_api_key),
            product_visual_description=product_visual_description,
            color_palette=color_palette,
            business_type=business_type,
            setting=setting,
            talent=on_screen_talent,
            brand_kit=brand_kit if isinstance(brand_kit, dict) else None,
            logo_path=logo_path,
            logo_tone=logo_tone if logo_tone in ("dark", "light") else "dark",
            model=model,
        )

        # Auto-save campaign ad generation to user library & project storage
        if result and result.get("status") == "success":
            try:
                from access import current_user
                import database
                cur_user = await current_user(request)
                ref_images = []
                if product_image_path:
                    ref_images.append(product_image_path)

                saved_rec = await database.save_creative(
                    user=cur_user,
                    data={
                        "type": "image",
                        "title": f"{brand_name} · {result.get('headline') or result.get('template_name') or 'Campaign Ad'}",
                        "prompt": result.get("visual_prompt", ""),
                        "media_url": result.get("image_url", ""),
                        "aspect_ratio": aspect_ratio,
                        "model_params": {
                            "model": result.get("model_used", "nano-banana-2.1"),
                            "framework": result.get("framework_name"),
                            "headline": result.get("headline"),
                            "primary_text": result.get("primary_text"),
                            "cta": result.get("cta"),
                            "template_name": result.get("template_name"),
                            "preset_name": result.get("preset_name"),
                            "preset_movement": result.get("preset_movement"),
                        },
                        "tags": ["Campaign", "Meta Creative", result.get("framework_key", "ad")],
                        "reference_images": ref_images,
                        "folder_id": "",
                    }
                )
                result["saved_id"] = saved_rec.get("id")
            except Exception as save_err:
                logger.warning(f"Failed to auto-save campaign creative: {save_err}")

        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Render one meta creative failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# Image studio (Nano Banana Pro)
# ---------------------------------------------------------------------------
STYLE_PRESETS = {
    "luxury_podium": "High-end luxury commercial advertisement, product displayed on an elegant white marble pedestal with brass accents, dramatic soft rim lighting, subtle volumetric atmosphere, crisp studio reflections, ultra-sharp editorial quality.",
    "ugc_lifestyle": "Authentic UGC creator ad photo, held naturally in hands or placed on a warm wooden cafe table, soft natural golden morning window light, realistic smartphone depth of field, relatable candid lifestyle aesthetic.",
    "nature_botanical": "Organic botanical product advertisement, resting on earthy moss and natural river stones, lush green leaves, gentle sun rays filtering through foliage, clean eco-friendly aesthetic.",
    "dramatic_splash": "High-speed dynamic splash advertisement, liquid splashes and droplets frozen in mid-air around the product, dramatic studio strobe lighting, vibrant energetic commercial composition.",
    "minimal_dtc": "Minimalist modern direct-to-consumer advertisement, seamless pastel studio backdrop, soft diffused light, floating product hero angle, clean negative space, ultra crisp presentation.",
}


@app.get("/api/image-studio/models")
async def get_image_studio_models():
    """Available image generation models, resolutions, and default selection."""
    return {
        "models": [
            {
                "key": k,
                "label": v["label"],
                "max_refs": v["max_refs"],
                "id": image_model(k)["id"],
            }
            for k, v in IMAGE_MODELS.items()
        ],
        "default": DEFAULT_IMAGE_MODEL,
        "resolutions": sorted(list(GEMINI_IMAGE_RESOLUTIONS)),
        "default_resolution": DEFAULT_IMAGE_RESOLUTION,
    }


@app.post("/api/image-studio/generate")
async def generate_studio_image(
    request: Request,
    prompt: Optional[str] = Form(None),
    prompts: Optional[str] = Form(None),
    model: str = Form("nano-banana-pro"),
    aspect_ratio: str = Form("1:1"),
    resolution: str = Form("1K"),
    style_preset: Optional[str] = Form(None),
    negative_prompt: Optional[str] = Form(None),
    folder_id: Optional[str] = Form(None),
    product_image: Optional[UploadFile] = File(None),
    reference_images: Optional[List[UploadFile]] = File(None),
    x_api_key: Optional[str] = Header(None),
):
    """Generate image ad(s) from prompt(s) with selectable Nano Banana models, resolutions, and reference images."""
    client = require_client(x_api_key)
    try:
        # Parse prompts
        prompt_list: List[str] = []
        if prompts:
            try:
                parsed = json.loads(prompts)
            except ValueError:
                raise HTTPException(status_code=400, detail="prompts must be a JSON list of strings.")
            if not isinstance(parsed, list):
                raise HTTPException(status_code=400, detail="prompts must be a JSON list of strings.")
            prompt_list = [p.strip() for p in parsed if isinstance(p, str) and p.strip()]
        elif prompt and prompt.strip():
            prompt_list = [prompt.strip()]

        if not prompt_list:
            raise HTTPException(status_code=400, detail="Write a prompt first.")
        if len(prompt_list) > MAX_PROMPTS_PER_REQUEST:
            raise HTTPException(status_code=400, detail=f"Send at most {MAX_PROMPTS_PER_REQUEST} prompts at once.")

        # Resolve model
        model_info = image_model(model)
        model_key = model_info["key"]
        max_refs = model_info.get("max_refs", 6)

        # Resolve resolution
        res_clean = (resolution or DEFAULT_IMAGE_RESOLUTION).strip().upper()
        if res_clean not in GEMINI_IMAGE_RESOLUTIONS:
            res_clean = DEFAULT_IMAGE_RESOLUTION

        # Collect reference images (supports both reference_images list and legacy product_image)
        upload_files: List[UploadFile] = [f for f in (reference_images or []) if f and f.filename]
        if not upload_files and product_image and product_image.filename:
            upload_files = [product_image]

        parts = []
        saved_ref_urls = []
        for upload in upload_files[:max_refs]:
            if not upload or not upload.filename:
                continue
            img_bytes, ext, mime_type = await read_upload(upload, IMAGE_EXTS, ".png", MAX_IMAGE_BYTES)
            parts.append(types.Part.from_bytes(data=img_bytes, mime_type=mime_type))

            # Persist reference image to disk so user can retrieve it at any time
            ref_filename = f"ref_{uuid.uuid4().hex}{ext}"
            ref_path = os.path.join(GENERATED_DIR, ref_filename)
            try:
                with open(ref_path, "wb") as rf:
                    rf.write(img_bytes)
                saved_ref_urls.append(f"/static/generated/{ref_filename}")
            except Exception:
                pass

        # Format reference directive
        ref_prefix = ""
        if len(parts) == 1:
            ref_prefix = (
                "IMAGE 1 is the reference product/subject. Reproduce it accurately with high fidelity "
                "(exact shape, branding, colors, and label layout) as the hero in the scene.\n\n"
            )
        elif len(parts) > 1:
            ref_tags = ", ".join(f"IMAGE {i+1}" for i in range(len(parts)))
            ref_prefix = (
                f"The attached images ({ref_tags}) are reference images. Maintain exact visual fidelity "
                "to the product, branding, materials, and styling shown in these references.\n\n"
            )

        async def render_one(text: str, idx: int) -> dict:
            try:
                clean_p = _paste_block(text)
                enriched = clean_p
                if STYLE_PRESETS.get(style_preset or ""):
                    enriched = f"{enriched}. Style: {STYLE_PRESETS[style_preset]}"
                if negative_prompt and negative_prompt.strip():
                    enriched = f"{enriched} (Avoid: {negative_prompt.strip()})"
                final_text = f"{ref_prefix}{enriched}" if ref_prefix else enriched
                contents = [*parts, final_text]

                image_bytes = await asyncio.to_thread(
                    generate_gemini_image, client, contents, aspect_ratio, model_key, res_clean
                )
                if not image_bytes:
                    return {
                        "index": idx,
                        "prompt": text,
                        "status": "failed",
                        "error": f"{model_info['label']} did not return an image."
                    }

                actual_width, actual_height = None, None
                try:
                    import io
                    from PIL import Image
                    with Image.open(io.BytesIO(image_bytes)) as img_obj:
                        actual_width, actual_height = img_obj.size
                except Exception:
                    pass

                filename = f"banana_ad_{uuid.uuid4().hex}.png"
                with open(os.path.join(GENERATED_DIR, filename), "wb") as f:
                    f.write(image_bytes)

                return {
                    "index": idx,
                    "prompt": text,
                    "status": "success",
                    "filename": filename,
                    "image_url": f"/static/generated/{filename}",
                    "aspect_ratio": aspect_ratio,
                    "resolution": res_clean,
                    "width": actual_width,
                    "height": actual_height,
                    "model": model_key,
                }
            except Exception as e:
                logger.error(f"[Image Studio] Prompt #{idx+1} failed: {e}", exc_info=True)
                return {
                    "index": idx,
                    "prompt": text,
                    "status": "failed",
                    "error": str(e)
                }

        results = await asyncio.gather(*(render_one(p, i) for i, p in enumerate(prompt_list)))
        successful = [r for r in results if r.get("status") == "success"]
        if not successful:
            first_err = next((r.get("error") for r in results if r.get("error")), "Image generation failed.")
            raise HTTPException(status_code=502, detail=first_err)

        # Automatically store any generations from users for them to access anytime with prompts & uploaded references
        try:
            from access import current_user
            import database
            cur_user = await current_user(request)
            for s in successful:
                saved_rec = await database.save_creative(
                    user=cur_user,
                    data={
                        "type": "image",
                        "title": f"Image Ad ({aspect_ratio})",
                        "prompt": s["prompt"],
                        "media_url": s["image_url"],
                        "aspect_ratio": aspect_ratio,
                        "model_params": {
                            "model": model_key,
                            "resolution": res_clean,
                            "style": style_preset,
                            "width": s.get("width"),
                            "height": s.get("height"),
                        },
                        "reference_images": saved_ref_urls,
                        "folder_id": folder_id or "",
                    }
                )
                s["saved_id"] = saved_rec["id"]
        except Exception as db_err:
            logger.warning(f"Auto-saving image creative to library failed: {db_err}")

        first_url = successful[0]["image_url"]
        return {
            "status": "success",
            "image_url": first_url,
            "filename": successful[0]["filename"],
            "aspect_ratio": aspect_ratio,
            "resolution": res_clean,
            "width": successful[0].get("width"),
            "height": successful[0].get("height"),
            "prompt": successful[0]["prompt"],
            "model": model_key,
            "has_product_reference": bool(parts),
            "images": [
                {
                    "prompt": r["prompt"],
                    "image_url": r.get("image_url"),
                    "filename": r.get("filename"),
                    "aspect_ratio": r.get("aspect_ratio"),
                    "resolution": r.get("resolution"),
                    "width": r.get("width"),
                    "height": r.get("height"),
                    "status": r.get("status"),
                    "error": r.get("error"),
                }
                for r in results
            ],
            "results": results,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[Image Studio] Generation failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/image-studio/history")
async def get_image_studio_history():
    """Most recent image-studio renders."""
    files = [f for f in os.listdir(GENERATED_DIR) if f.startswith("banana_ad_") and f.endswith(".png")]
    files.sort(key=lambda x: os.path.getmtime(os.path.join(GENERATED_DIR, x)), reverse=True)
    return {"images": [
        {"filename": f, "url": f"/static/generated/{f}", "created_at": os.path.getmtime(os.path.join(GENERATED_DIR, f))}
        for f in files[:24]
    ]}


THUMB_DIR = os.path.join(GENERATED_DIR, "thumbs")
THUMB_WIDTH = 640


@app.get("/api/thumb/{filename}")
def get_generated_thumbnail(filename: str):
    """A small WebP of a studio render for gallery tiles; the renders themselves run to several MB each."""
    if os.path.basename(filename) != filename or not (filename.startswith("banana_ad_") and filename.endswith(".png")):
        raise HTTPException(status_code=404, detail="Not found")
    source = os.path.join(GENERATED_DIR, filename)
    if not os.path.isfile(source):
        raise HTTPException(status_code=404, detail="Not found")
    thumb = os.path.join(THUMB_DIR, f"{filename[:-4]}_{THUMB_WIDTH}.webp")
    if not os.path.isfile(thumb):
        from PIL import Image

        os.makedirs(THUMB_DIR, exist_ok=True)
        partial = f"{thumb}.{uuid.uuid4().hex}.tmp"
        with Image.open(source) as image:
            image.thumbnail((THUMB_WIDTH, THUMB_WIDTH * 4))
            image.convert("RGB").save(partial, "WEBP", quality=80)
        os.replace(partial, thumb)
    return FileResponse(thumb, media_type="image/webp", headers={"Cache-Control": "public, max-age=31536000, immutable"})


# ---------------------------------------------------------------------------
# Video studio + campaign video ads (Gemini Omni Flash)
# ---------------------------------------------------------------------------
DEVICE_INTEGRITY_NEGATIVE_PROMPT = (
    "inverted laptop screens, upside-down laptops, backward laptops, laptops held upside-down or flipped, "
    "inverted phones, upside-down phone screens, mirrored screens, reverse UI, backwards display, "
    "floating distorted keyboards, impossible hinge angles, backward screens, warped hands, extra fingers, "
    "hex codes, color codes, hash codes, hexadecimal text, raw hex values, color hashes, printed hex codes, "
    "color labels on screen, floating hex values"
)

async def generate_omni_video_background(
    job_id: str,
    mode: str,
    prompt: str,
    negative_prompt: Optional[str],
    aspect_ratio: str,
    resolution: str,
    duration: int,
    reference_image_paths: List[str],
    first_frame_path: Optional[str],
    last_frame_path: Optional[str],
    source_video_path: Optional[str],
    api_key: Optional[str],
    user_id: str = "",
    user_email: str = "",
    folder_id: str = "",
):
    try:
        prompt = sanitize_video_prompt(prompt)
        client = get_client(api_key)
        if not client:
            persist_job_update(job_id, {"status": "failed", "error": "A Gemini API key is required for Omni Flash. Add it under API Keys."}, video_jobs)
            return

        res_clean = (resolution or DEFAULT_VIDEO_RESOLUTION).strip().lower()
        if res_clean in ("4k", "2160p", "uhd"):
            res_clean = "4k"
        elif res_clean in ("1080p", "fhd"):
            res_clean = "1080p"
        else:
            res_clean = "720p"

        orientation = {"16:9": "horizontal landscape (16:9)", "9:16": "vertical portrait (9:16)"}.get(aspect_ratio, "square (1:1)")
        header = (
            f"Generate an ultra-high quality video in {orientation}, target resolution: {res_clean}, duration: {duration} seconds.\n"
            "PHYSICAL DEVICE ORIENTATION: All laptops, computer screens, smartphones, and tablets must appear strictly right-side up in physically authentic orientation. Laptops sit flat with keyboards below screens. Screens and UI text must be horizontal and right-side up, never inverted, mirrored, or upside-down.\n"
            "NO HEX CODES: Never render hex color codes, color values, hash symbols, or alphanumeric color codes anywhere in the video scene, overlays, props, or labels.\n\n"
        )

        if mode == "first_last_frame":
            if first_frame_path and last_frame_path:
                omni_prompt = (
                    f"{header}MODE: FIRST FRAME & LAST FRAME INTERPOLATION.\n"
                    "The first attached image is the EXACT START FRAME (t=0.0s).\n"
                    f"The second attached image is the EXACT LAST FRAME (t={duration}.0s).\n"
                    "Render a fluid, continuous sequence transitioning from the start frame to the end frame.\n"
                    f"Action and motion directions: {_paste_block(prompt)}\n"
                )
            else:
                omni_prompt = (
                    f"{header}MODE: START FRAME ANIMATION.\n"
                    "The attached image is the EXACT START FRAME (t=0.0s).\n"
                    "Render a fluid, continuous sequence animating forward starting exactly from this start frame.\n"
                    f"Action and motion directions: {_paste_block(prompt)}\n"
                )
        elif mode == "edit_video":
            omni_prompt = (
                f"{header}MODE: VIDEO-TO-VIDEO EDITING.\n"
                "The attached video is the source. Transform it following these instructions while preserving camera "
                "motion, core composition and subject timing:\n"
                f"Edit instructions: {prompt}\n"
            )
        else:  # prompt_images
            # Send the user's prompt as written (as Google Flow does): extra all-caps directives around it
            # tripped Omni's input filter. Images are bound through numbered <IMAGE_REF_n> tags.
            ref_line = ""
            if reference_image_paths:
                tags = " ".join(f"<IMAGE_REF_{i}>" for i in range(len(reference_image_paths)))
                ref_line = (
                    f"Use the given images ({tags}) as references for video generation, not as literal initial frames. "
                    "Keep the product exactly as it looks in them.\n\n"
                )
            omni_prompt = f"{ref_line}{_paste_block(prompt)}\n\nThe video is {duration} seconds long."

        combined_negative = DEVICE_INTEGRITY_NEGATIVE_PROMPT
        if negative_prompt and negative_prompt.strip():
            combined_negative = f"{negative_prompt.strip()}, {DEVICE_INTEGRITY_NEGATIVE_PROMPT}"
        omni_prompt += f"NEGATIVE PROMPT (strictly avoid): {combined_negative}\n"
        omni_prompt = sanitize_video_prompt(omni_prompt)

        def encode(path: str, kind: str) -> dict:
            with open(path, "rb") as f:
                return {"type": kind, "data": _b64(f.read()), "mime_type": mime_for_path(path)}

        inputs = []
        if mode == "first_last_frame":
            inputs += [encode(p, "image") for p in (first_frame_path, last_frame_path) if p and os.path.exists(p)]
        elif mode == "edit_video" and source_video_path and os.path.exists(source_video_path):
            inputs.append(encode(source_video_path, "video"))
        else:
            inputs += [encode(p, "image") for p in reference_image_paths if p and os.path.exists(p)]
        inputs.append({"type": "text", "text": omni_prompt})

        logger.info(f"Dispatching Omni Flash video job {job_id} (mode={mode}, res={res_clean}, ratio={aspect_ratio}, dur={duration}s)...")
        persist_job_update(job_id, {"status": "processing", "progress_msg": "Omni Flash is rendering the video..."}, video_jobs)

        video_b64 = None
        try:
            resp_fmt = {"type": "video"}
            if aspect_ratio in ("9:16", "16:9"):
                resp_fmt["aspect_ratio"] = aspect_ratio
            if res_clean in ("1080p", "4k"):
                resp_fmt["resolution"] = res_clean
            request = {"model": OMNI_MODEL, "input": inputs, "response_format": resp_fmt}
            try:
                interaction = await asyncio.to_thread(client.interactions.create, **request)
            except Exception as fmt_err:
                if "response_format" in str(fmt_err).lower() or "resolution" in str(fmt_err).lower():
                    resp_fmt.pop("resolution", None)
                    request["response_format"] = resp_fmt
                    interaction = await asyncio.to_thread(client.interactions.create, **request)
                else:
                    raise
            video_b64 = _extract_interaction_video(interaction)
        except Exception as api_err:
            # Client errors (spend cap, blocked input, bad request) fail the same way on the fallback,
            # so retrying would only add a second billable call
            if _is_client_error(api_err):
                raise
            logger.warning(f"Interactions API attempt failed: {api_err}. Trying generate_videos fallback...")
            try:
                config_args = {"aspect_ratio": aspect_ratio, "resolution": res_clean, "duration_seconds": duration}
                config_args["negative_prompt"] = combined_negative

                first_path = first_frame_path if mode == "first_last_frame" else (reference_image_paths[0] if reference_image_paths else None)
                first_img = None
                if first_path and os.path.exists(first_path):
                    with open(first_path, "rb") as f:
                        first_img = types.Image(image_bytes=f.read())
                if mode == "first_last_frame" and last_frame_path and os.path.exists(last_frame_path):
                    with open(last_frame_path, "rb") as f:
                        config_args["last_frame"] = types.Image(image_bytes=f.read())

                try:
                    op = await asyncio.to_thread(
                        client.models.generate_videos,
                        model=OMNI_MODEL,
                        prompt=sanitize_video_prompt(prompt),
                        image=first_img,
                        config=types.GenerateVideosConfig(**config_args),
                    )
                except Exception as gen_cfg_err:
                    if "resolution" in str(gen_cfg_err).lower() and res_clean == "4k":
                        config_args["resolution"] = "1080p"
                        op = await asyncio.to_thread(
                            client.models.generate_videos,
                            model=OMNI_MODEL,
                            prompt=prompt,
                            image=first_img,
                            config=types.GenerateVideosConfig(**config_args),
                        )
                    else:
                        raise

                deadline = time.time() + 1200
                while not op.done:
                    if time.time() > deadline:
                        raise TimeoutError("Omni Flash generate_videos timed out after 20 minutes")
                    await asyncio.sleep(5)
                    op = await asyncio.to_thread(client.operations.get, op)
                if op.response and op.response.generated_videos:
                    video_b64 = _b64(op.response.generated_videos[0].video.video_bytes)
            except Exception as gen_err:
                logger.error(f"Fallback generate_videos also failed: {gen_err}")
                raise api_err

        if not video_b64:
            persist_job_update(job_id, {"status": "failed", "error": "Omni Flash did not return any video output"}, video_jobs)
            return

        video_url = _save_video_bytes("studio_video", safe_b64decode(video_b64))
        video_disk_path = resolve_generated_path(video_url)
        final_w, final_h = None, None
        if video_disk_path and os.path.isfile(video_disk_path):
            video_disk_path = await asyncio.to_thread(
                ensure_video_resolution, video_disk_path, res_clean, aspect_ratio
            )
            final_w, final_h = get_video_dimensions(video_disk_path)

        logger.info(f"Omni Flash video saved to {video_url} ({final_w}x{final_h}, target={res_clean})")
        persist_job_update(job_id, {
            "status": "success",
            "video_url": video_url,
            "mode": mode,
            "resolution": res_clean,
            "width": final_w,
            "height": final_h,
            "aspect_ratio": aspect_ratio,
            "duration": duration,
            "prompt": prompt,
            "engine": "Omni Flash",
        }, video_jobs)

        # Automatically persist video generation with prompt & reference frames to library
        try:
            import database
            ref_urls = [f"/static/generated/{os.path.basename(p)}" for p in (reference_image_paths or []) if p]
            if first_frame_path:
                ref_urls.insert(0, f"/static/generated/{os.path.basename(first_frame_path)}")
            await database.save_creative(
                user={"id": user_id, "email": user_email} if user_id else None,
                data={
                    "type": "video",
                    "title": f"Video Ad ({aspect_ratio})",
                    "prompt": prompt,
                    "media_url": video_url,
                    "aspect_ratio": aspect_ratio,
                    "model_params": {
                        "model": "omni-flash",
                        "resolution": res_clean,
                        "duration": duration,
                        "width": final_w,
                        "height": final_h,
                    },
                    "reference_images": ref_urls,
                    "folder_id": folder_id or "",
                }
            )
        except Exception as db_err:
            logger.warning(f"Failed to auto-save video creative to library: {db_err}")
    except Exception as e:
        if "content_blocked" in str(e):
            # Keep what was sent so the blocked wording can be found and fixed
            logger.warning(f"Omni Flash blocked job {job_id} ({len(reference_image_paths)} refs). Prompt sent:\n{omni_prompt}")
            persist_job_update(job_id, {
                "status": "failed",
                "error": "Google's safety filter blocked this prompt, so no video was made. "
                         "Reword the prompt and render again.",
                "blocked_prompt": omni_prompt,
            }, video_jobs)
            return
        logger.error(f"Omni Flash background generation failed: {e}", exc_info=True)
        persist_job_update(job_id, {"status": "failed", "error": str(e), "prompt": prompt}, video_jobs)


async def _save_upload(upload: Optional[UploadFile], prefix: str, allowed: set, default_ext: str, max_bytes: int) -> Optional[str]:
    if not upload or not upload.filename:
        return None
    content, ext, _ = await read_upload(upload, allowed, default_ext, max_bytes)
    path = os.path.join(GENERATED_DIR, f"{prefix}_{uuid.uuid4().hex}{ext}")
    with open(path, "wb") as f:
        f.write(content)
    return path


@app.post("/api/studio/generate-video")
async def studio_generate_video(
    request: Request,
    mode: str = Form("prompt_images"),
    prompt: Optional[str] = Form(None),
    prompts: Optional[str] = Form(None),
    negative_prompt: Optional[str] = Form(None),
    aspect_ratio: str = Form("9:16"),
    resolution: str = Form("1080p"),
    duration: int = Form(8),
    folder_id: Optional[str] = Form(None),
    reference_images: Optional[List[UploadFile]] = File(None),
    first_frame: Optional[UploadFile] = File(None),
    last_frame: Optional[UploadFile] = File(None),
    source_video: Optional[UploadFile] = File(None),
    x_api_key: Optional[str] = Header(None),
):
    """Start Omni Flash video jobs; poll /api/video-status/{job_id} for each result.

    Send one `prompt`, or `prompts` as a JSON list of up to MAX_PROMPTS_PER_REQUEST prompts that share the
    same reference images, frames and format. Each prompt is its own render (and its own billed video)."""
    try:
        prompt_list: List[str] = []
        if prompts:
            try:
                parsed = json.loads(prompts)
            except ValueError:
                raise HTTPException(status_code=400, detail="prompts must be a JSON list of strings.")
            if not isinstance(parsed, list):
                raise HTTPException(status_code=400, detail="prompts must be a JSON list of strings.")
            prompt_list = [p.strip() for p in parsed if isinstance(p, str) and p.strip()]
        elif prompt and prompt.strip():
            prompt_list = [prompt]
        if not prompt_list:
            raise HTTPException(status_code=400, detail="Write a prompt first.")
        if len(prompt_list) > MAX_PROMPTS_PER_REQUEST:
            raise HTTPException(status_code=400, detail=f"Send at most {MAX_PROMPTS_PER_REQUEST} prompts at once.")

        saved_refs = []
        for img in (reference_images or [])[:MAX_VIDEO_REF_IMAGES]:
            path = await _save_upload(img, "ref", IMAGE_EXTS, ".jpg", MAX_IMAGE_BYTES)
            if path:
                saved_refs.append(path)
        first_path = await _save_upload(first_frame, "frame_start", IMAGE_EXTS, ".jpg", MAX_IMAGE_BYTES)
        last_path = await _save_upload(last_frame, "frame_end", IMAGE_EXTS, ".jpg", MAX_IMAGE_BYTES)
        source_path = await _save_upload(source_video, "source_vid", VIDEO_EXTS, ".mp4", MAX_VIDEO_BYTES)

        if mode == "first_last_frame" and not first_path:
            raise HTTPException(status_code=400, detail="Please upload at least a start frame.")
        if mode == "edit_video" and not source_path:
            raise HTTPException(status_code=400, detail="Please upload a source video to edit.")

        res_clean = (resolution or DEFAULT_VIDEO_RESOLUTION).strip().lower()
        if res_clean in ("4k", "2160p", "uhd"):
            res_clean = "4k"
        elif res_clean in ("1080p", "fhd"):
            res_clean = "1080p"
        else:
            res_clean = "720p"

        from access import current_user
        cur_user = await current_user(request)
        u_id = cur_user.get("id") if cur_user else ""
        u_email = cur_user.get("email") if cur_user else ""

        job_ids = []
        for text in prompt_list:
            job_id = f"job_studio_{uuid.uuid4().hex}"
            persist_job_update(job_id, {
                "status": "processing",
                "created_at": time.time(),
                "resolution": res_clean,
                "aspect_ratio": aspect_ratio,
            }, video_jobs)
            # Plain tasks, not BackgroundTasks: those run one after another, these render in parallel
            task = asyncio.create_task(generate_omni_video_background(
                job_id=job_id,
                mode=mode,
                prompt=text,
                negative_prompt=negative_prompt,
                aspect_ratio=aspect_ratio,
                resolution=res_clean,
                duration=max(4, min(15, duration)),
                reference_image_paths=saved_refs,
                first_frame_path=first_path,
                last_frame_path=last_path,
                source_video_path=source_path,
                api_key=x_api_key,
                user_id=u_id,
                user_email=u_email,
                folder_id=folder_id or "",
            ))
            _video_tasks.add(task)
            task.add_done_callback(_video_tasks.discard)
            job_ids.append(job_id)
        return {"status": "processing", "job_id": job_ids[0], "job_ids": job_ids}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Video dispatch failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/video-status/{job_id}")
async def get_video_status(job_id: str):
    job = video_jobs.get(job_id)
    if not job:
        job = await asyncio.to_thread(load_job, job_id)
        if job:
            video_jobs[job_id] = job
    if not job:
        raise HTTPException(status_code=404, detail="Job not found. The server may have restarted. Please render again.")

    # Fail jobs that stopped reporting progress (e.g. the worker died during a restart)
    last_seen = job.get("updated_at") or job.get("created_at")
    if job.get("status") == "processing" and last_seen and (time.time() - last_seen > STALE_JOB_SECONDS):
        job = persist_job_update(job_id, {
            "status": "failed",
            "error": "This job stopped responding for over an hour. Please try again.",
        }, video_jobs)
    return job


app.include_router(competitor_ad_router, dependencies=CAMPAIGN_ACCESS)
app.include_router(campaign_flow_router, dependencies=CAMPAIGN_ACCESS)
app.include_router(upgrade_router)
app.include_router(batch_prompt_router)
app.include_router(demo_session_router)
app.include_router(auth_router)
app.include_router(saved_router)
app.include_router(templates_router)


app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/css", StaticFiles(directory="static/css"), name="css")
app.mount("/js", StaticFiles(directory="static/js"), name="js")


# Serve product landing page at root (Higgsfield-style showcase)
@app.api_route("/", methods=["GET", "HEAD"])
async def read_landing(request: Request):
    if request.method == "HEAD":
        return Response(status_code=200)
    return FileResponse("static/landing/index.html", headers={"Cache-Control": "no-cache"})


# Serve the Ad Studio workspace at /app and /studio
@app.get("/app", include_in_schema=False)
@app.get("/studio", include_in_schema=False)
async def read_studio_app(request: Request):
    return FileResponse("static/index.html", headers={"Cache-Control": "no-cache"})


@app.api_route("/healthz", methods=["GET", "HEAD"])
@app.api_route("/health", methods=["GET", "HEAD"])
async def health_check():
    return {"status": "ok"}


@app.get("/api/plan")
async def get_plan(plan: str = Depends(current_plan)):
    """The caller's plan and which gated features it includes (the UI locks the rest)."""
    return plan_summary(plan)


@app.get("/favicon.ico")
async def favicon():
    return Response(status_code=204)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=True)
