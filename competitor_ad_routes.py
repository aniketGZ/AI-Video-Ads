"""Competitor Ad Agent API Routes
Endpoints for managing background competitor ad intelligence runs,
streaming real-time agent execution logs & screenshots, and exploring deliverables.
"""

import os
import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional, List
import asyncio

from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Header, Request, BackgroundTasks
from fastapi.responses import FileResponse, JSONResponse

from competitor_ad_engine import (
    RUNS_DIR,
    STEPS,
    list_all_runs,
    get_or_create_run_state,
    run_competitor_agent_pipeline,
    analyze_and_build_input_from_url,
    discover_competitors_and_demographics,
    get_gemini_client,
    default_settings,
    RUN_TASKS,
)

router = APIRouter(prefix="/api/competitor-agent", tags=["Competitor Ad Agent"])


@router.post("/discover")
async def discover_brand_competitors(
    url: str = Form(...),
    x_api_key: Optional[str] = Header(None),
):
    """Fast discovery of brand profile, competitors, and demographic targeting."""
    clean_url = (url or "").strip()
    if not clean_url:
        raise HTTPException(status_code=400, detail="Please provide a valid brand website URL.")
    client = get_gemini_client(x_api_key)
    try:
        return await asyncio.to_thread(discover_competitors_and_demographics, clean_url, client)
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Discovery failed: {str(e)}")


@router.get("/runs")
async def get_runs():
    """List all competitor ad runs available on the server."""
    runs = list_all_runs()
    return {"runs": runs}


@router.get("/runs/{run_id}")
async def get_run_details(run_id: str):
    """Get complete run state, outputs, files, and intelligence deliverables."""
    run_dir = RUNS_DIR / run_id
    if not run_dir.exists():
        raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found.")

    state = get_or_create_run_state(run_id)

    # Load input.json
    input_data = {}
    input_file = run_dir / "input.json"
    if input_file.exists():
        try:
            input_data = json.loads(input_file.read_text(encoding="utf-8"))
        except Exception:
            pass

    # Load product lock
    product_lock = ""
    pl_file = run_dir / "brand" / "product_lock.md"
    if pl_file.exists():
        product_lock = pl_file.read_text(encoding="utf-8", errors="replace")

    # Load brand kit
    brand_kit = {}
    bk_file = run_dir / "brand" / "brand_kit.json"
    if bk_file.exists():
        try:
            brand_kit = json.loads(bk_file.read_text(encoding="utf-8"))
        except Exception:
            pass

    # Load captured ads from raw/<competitor>/ads.json
    captured_ads = []
    raw_dir = run_dir / "raw"
    if raw_dir.exists():
        for comp_folder in raw_dir.iterdir():
            if comp_folder.is_dir():
                ads_json = comp_folder / "ads.json"
                if ads_json.exists():
                    try:
                        c_data = json.loads(ads_json.read_text(encoding="utf-8"))
                        for card in c_data.get("cards", []):
                            card["competitor_slug"] = comp_folder.name
                            captured_ads.append(card)
                    except Exception:
                        pass

    # Load ad analysis
    ad_analyses = []
    jsonl_file = run_dir / "analysis" / "ads.jsonl"
    if jsonl_file.exists():
        for line in jsonl_file.read_text(encoding="utf-8", errors="replace").splitlines():
            line = line.strip()
            if line:
                try:
                    ad_analyses.append(json.loads(line))
                except Exception:
                    pass

    # Load insights
    insights = ""
    insights_file = run_dir / "analysis" / "insights.md"
    if insights_file.exists():
        insights = insights_file.read_text(encoding="utf-8", errors="replace")

    # Structured research handed to the campaign flow
    meta_refs = {}
    mr_file = run_dir / "analysis" / "meta_refs.json"
    if mr_file.exists():
        try:
            meta_refs = json.loads(mr_file.read_text(encoding="utf-8"))
        except Exception:
            pass

    # Load report
    report = ""
    rep_file = run_dir / "report.md"
    if rep_file.exists():
        report = rep_file.read_text(encoding="utf-8", errors="replace")

    # Load handoff
    handoff = {}
    ho_file = run_dir / "handoff.json"
    if ho_file.exists():
        try:
            handoff = json.loads(ho_file.read_text(encoding="utf-8"))
        except Exception:
            pass

    # Available product image path
    product_img_url = None
    uploads_dir = run_dir / "uploads"
    if uploads_dir.exists():
        for p in uploads_dir.glob("product.*"):
            product_img_url = f"/api/competitor-agent/runs/{run_id}/artifact/uploads/{p.name}"
            break

    # Available screenshots
    screenshots = []
    run_log_dir = run_dir / "run_log"
    if run_log_dir.exists():
        for s in run_log_dir.glob("*.png"):
            screenshots.append({
                "name": s.name,
                "url": f"/api/competitor-agent/runs/{run_id}/artifact/run_log/{s.name}"
            })

    return {
        "state": state.to_dict(),
        "input": input_data,
        "product_lock": product_lock,
        "brand_kit": brand_kit,
        "product_image_url": product_img_url,
        "captured_ads": captured_ads,
        "ad_analyses": ad_analyses,
        "insights": insights,
        "meta_refs": meta_refs,
        "report": report,
        "handoff": handoff,
        "screenshots": screenshots,
        "steps": STEPS,
    }


@router.get("/runs/{run_id}/stream")
async def get_run_stream(run_id: str, last_index: int = 0):
    """Polling/streaming endpoint for real-time agent logs and state updates."""
    state = get_or_create_run_state(run_id)
    events = state.logger.events if state.logger else []
    new_events = events[last_index:] if last_index < len(events) else []

    return {
        "run_id": run_id,
        "status": state.status,
        "current_step": state.current_step,
        "step_name": state.step_name,
        "progress": round(state.progress, 2),
        "stats": state.stats,
        "latest_screenshot": state.latest_screenshot,
        "error": state.error,
        "next_index": len(events),
        "events": new_events,
    }


@router.post("/start")
async def start_new_run(
    url: Optional[str] = Form(None),
    brand_url: Optional[str] = Form(None),
    brand_name: Optional[str] = Form(None),
    product_image: Optional[UploadFile] = File(None),
    logo_image: Optional[UploadFile] = File(None),
    brand_category: Optional[str] = Form(None),
    brand_product: Optional[str] = Form(None),
    brand_usp: Optional[str] = Form(None),
    brand_audience: Optional[str] = Form(None),
    brand_tone: Optional[str] = Form(None),
    brand_colors: Optional[str] = Form(None),
    competitors: Optional[str] = Form(None),
    demographics: Optional[str] = Form(None),
    market: Optional[str] = Form(None),
    settings_json: Optional[str] = Form(None),
    x_api_key: Optional[str] = Header(None),
):
    """Start competitor ad agent. Accepts just a URL and optional image, or full manual parameters."""
    target_url = (url or brand_url or "").strip()
    if not target_url and not brand_name:
        raise HTTPException(status_code=400, detail="Please provide a brand or product URL.")

    # Parse custom competitors if provided
    custom_comps = None
    if competitors and competitors.strip():
        try:
            parsed_c = json.loads(competitors)
            if isinstance(parsed_c, list):
                custom_comps = []
                for item in parsed_c:
                    if isinstance(item, dict) and item.get("name"):
                        custom_comps.append({"name": item["name"].strip()})
                    elif isinstance(item, str) and item.strip():
                        custom_comps.append({"name": item.strip()})
        except Exception:
            custom_comps = [{"name": c.strip()} for c in competitors.split(",") if c.strip()]

    # Parse custom demographics if provided
    custom_demos = None
    if demographics and demographics.strip():
        try:
            custom_demos = json.loads(demographics)
        except Exception:
            pass

    # Market confirmed at discovery (sets the Ad Library country)
    custom_market = None
    if market and market.strip():
        try:
            custom_market = json.loads(market)
        except Exception:
            pass

    # Read product image bytes if uploaded
    p_bytes = None
    p_ext = ".png"
    if product_image and product_image.filename:
        p_bytes = await product_image.read()
        p_ext = os.path.splitext(product_image.filename)[1].lower() or ".png"

    # Generate unique run ID
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    clean_slug = "run"
    if target_url:
        from urllib.parse import urlparse
        domain = urlparse(target_url).netloc.replace("www.", "").split(".")[0]
        clean_slug = "".join(c for c in domain.lower() if c.isalnum() or c == "_")[:12] or "run"
    elif brand_name:
        clean_slug = "".join(c for c in brand_name.lower() if c.isalnum() or c == "_")[:12] or "run"

    run_id = f"run_{clean_slug}_{ts}"
    run_dir = RUNS_DIR / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    uploads_dir = run_dir / "uploads"
    uploads_dir.mkdir(parents=True, exist_ok=True)

    client = get_gemini_client(x_api_key)

    # 1. Autonomous URL-first mode
    if target_url and not (brand_name and brand_product and brand_category):
        try:
            input_payload = await asyncio.to_thread(
                analyze_and_build_input_from_url,
                url=target_url,
                client=client,
                run_dir=run_dir,
                uploaded_product_bytes=p_bytes,
                uploaded_product_ext=p_ext,
                custom_competitors=custom_comps,
                custom_demographics=custom_demos,
                custom_market=custom_market,
            )
        except RuntimeError as e:
            shutil.rmtree(run_dir, ignore_errors=True)
            raise HTTPException(status_code=502, detail=str(e))
        detected_brand = input_payload.get("brand", {}).get("name", clean_slug.capitalize())
        detected_cat = input_payload.get("brand", {}).get("category", "")
        detected_prod = input_payload.get("brand", {}).get("product", "")
    else:
        # 2. Manual / override mode
        if p_bytes:
            (uploads_dir / f"product{p_ext}").write_bytes(p_bytes)

        detected_brand = brand_name or clean_slug.capitalize()
        detected_cat = brand_category
        detected_prod = brand_product

        competitors_list = []
        if competitors and competitors.strip():
            try:
                competitors_list = json.loads(competitors)
            except Exception:
                for item in competitors.split(","):
                    item = item.strip()
                    if item:
                        competitors_list.append({"name": item})

        settings = default_settings(custom_market)
        if settings_json and settings_json.strip():
            try:
                settings.update(json.loads(settings_json))
            except Exception:
                pass

        input_payload = {
            "brand": {
                "name": detected_brand,
                "url": target_url,
                "category": detected_cat,
                "product": detected_prod,
                "usp": [u.strip() for u in (brand_usp or "").split(",") if u.strip()],
                "audience": brand_audience or "",
                "tone": brand_tone or "",
                "brand_colors": [c.strip() for c in (brand_colors or "").split(",") if c.strip()],
            },
            "market": custom_market or {},
            "demographics": custom_demos or {},
            "competitors": competitors_list,
            "settings": settings,
        }
        (run_dir / "input.json").write_text(json.dumps(input_payload, indent=2, ensure_ascii=False), encoding="utf-8")

    # Save optional logo if supplied
    if logo_image and logo_image.filename:
        l_ext = os.path.splitext(logo_image.filename)[1].lower() or ".png"
        (uploads_dir / f"logo{l_ext}").write_bytes(await logo_image.read())

    # Initialize run_log.md
    log_content = f"""# Run log — competitor_ad_agent — run `{run_id}`

Brand: **{detected_brand}** — {detected_prod} ({detected_cat}).
Target URL: {target_url}
Started: {datetime.now().strftime('%Y-%m-%d %H:%M')}.

## Steps
- [ ] Step 0 — Validate inputs, read product, write brand files
- [ ] Step 1 — Resolve competitors in Ad Library
- [ ] Step 2 — Capture ads
- [ ] Step 3 — Download creatives
- [ ] Step 4 — Analyse ads
- [ ] Step 5 — Insights (meta_refs.json)
- [ ] Step 6 — Report + handoff
"""
    (run_dir / "run_log.md").write_text(log_content, encoding="utf-8")

    # Start background execution
    task = asyncio.create_task(run_competitor_agent_pipeline(run_id, api_key=x_api_key, from_step=0))
    RUN_TASKS[run_id] = task

    return {
        "run_id": run_id,
        "brand_name": detected_brand,
        "status": "started",
        "message": f"Autonomous agent launched for {detected_brand} ({target_url})."
    }


@router.post("/resume/{run_id}")
async def resume_run(
    run_id: str,
    from_step: Optional[int] = None,
    x_api_key: Optional[str] = Header(None),
):
    """Resume or run an existing run (e.g. _example or incomplete run)."""
    run_dir = RUNS_DIR / run_id
    if not run_dir.exists():
        raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found.")

    state = get_or_create_run_state(run_id)
    if state.status == "running":
        return {"run_id": run_id, "status": "already_running", "message": "Run is already actively executing."}

    # Auto-detect starting step if not specified
    if from_step is None:
        # Check files to see where we left off
        if (run_dir / "analysis" / "meta_refs.json").exists():
            from_step = 6
        elif (run_dir / "analysis" / "ads.jsonl").exists() and (run_dir / "analysis" / "ads.jsonl").stat().st_size > 50:
            from_step = 5
        elif any((run_dir / "frames").iterdir()) if (run_dir / "frames").exists() else False:
            from_step = 4
        elif (run_dir / "raw").exists() and any((run_dir / "raw").glob("*/ads.json")):
            from_step = 3
        else:
            from_step = 0

    task = asyncio.create_task(run_competitor_agent_pipeline(run_id, api_key=x_api_key, from_step=from_step))
    RUN_TASKS[run_id] = task

    return {
        "run_id": run_id,
        "status": "resumed",
        "from_step": from_step,
        "step_name": STEPS[from_step]["name"],
        "message": f"Resuming agent execution from Step {from_step} ({STEPS[from_step]['name']})."
    }


@router.post("/stop/{run_id}")
async def stop_run(run_id: str):
    """Request cancellation of an active run."""
    state = get_or_create_run_state(run_id)
    state.cancel_requested = True
    if run_id in RUN_TASKS and not RUN_TASKS[run_id].done():
        RUN_TASKS[run_id].cancel()
    state.status = "stopped"
    if state.logger:
        state.logger.log(state.current_step, "warning", "Run cancellation requested by user.")
    return {"run_id": run_id, "status": "stopping"}


@router.get("/runs/{run_id}/artifact/{file_path:path}")
async def get_artifact_file(run_id: str, file_path: str):
    """Safely serve media, frame, screenshot or deliverable files from runs/<run_id>/."""
    run_dir = (RUNS_DIR / run_id).resolve()
    target_file = (run_dir / file_path).resolve()

    # Prevent directory traversal attacks
    if not str(target_file).startswith(str(run_dir)):
        raise HTTPException(status_code=403, detail="Forbidden file path.")

    if not target_file.exists() or not target_file.is_file():
        raise HTTPException(status_code=404, detail="Artifact file not found.")

    ext = target_file.suffix.lower()
    media_types = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".webp": "image/webp",
        ".mp4": "video/mp4",
        ".json": "application/json",
        ".jsonl": "application/x-ndjson",
        ".md": "text/markdown",
        ".txt": "text/plain",
    }
    media_type = media_types.get(ext, "application/octet-stream")
    return FileResponse(str(target_file), media_type=media_type)
