"""
Pinterest Creative Library & Recreate Template API Routes
Allows users to explore real Pinterest advertising references and recreate
custom commercial visuals by uploading their product, brand name, and custom edits.
"""

import asyncio
import json
import logging
import os
import uuid
from typing import Any, Dict, List, Optional
import httpx
from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from google.genai import types

from access import current_user
import database
from media_utils import GENERATED_DIR

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/templates", tags=["Pinterest Templates"])

TEMPLATES_JSON_PATH = os.path.join(os.path.dirname(__file__), "data", "explore_templates.json")

_TEMPLATES_CACHE: Optional[List[Dict[str, Any]]] = None


def load_templates() -> List[Dict[str, Any]]:
    global _TEMPLATES_CACHE
    if _TEMPLATES_CACHE is None:
        if os.path.exists(TEMPLATES_JSON_PATH):
            with open(TEMPLATES_JSON_PATH, "r", encoding="utf-8") as f:
                _TEMPLATES_CACHE = json.load(f)
        else:
            _TEMPLATES_CACHE = []
    return _TEMPLATES_CACHE


@router.get("/explore")
async def get_explore_templates(
    category: Optional[str] = None,
    industry: Optional[str] = None,
    media_type: Optional[str] = None,
    q: Optional[str] = None,
):
    """List and filter Pinterest ad creative templates."""
    all_tpls = load_templates()
    filtered = all_tpls

    if category and category.lower() != "all":
        cat_lower = category.lower()
        filtered = [t for t in filtered if t.get("category", "").lower() == cat_lower]

    if industry and industry.lower() != "all":
        ind_lower = industry.lower()
        filtered = [t for t in filtered if t.get("industry", "").lower() == ind_lower]

    if media_type and media_type.lower() != "all":
        med_lower = media_type.lower()
        filtered = [t for t in filtered if t.get("media_type", "image").lower() == med_lower]

    if q and q.strip():
        query = q.strip().lower()
        filtered = [
            t
            for t in filtered
            if query in t.get("title", "").lower()
            or query in t.get("movement", "").lower()
            or query in t.get("industry_label", "").lower()
            or query in t.get("category", "").lower()
            or query in t.get("description", "").lower()
        ]

    categories = [
        "All",
        "Product shot",
        "Motion",
        "UGC",
        "TikTok",
        "Ads",
        "Posters",
        "Marketplace",
    ]

    return {
        "status": "ok",
        "templates": filtered,
        "count": len(filtered),
        "total_templates": len(all_tpls),
        "categories": categories,
    }


@router.get("/detail/{template_id}")
async def get_template_detail(template_id: str):
    """Retrieve full detail for a single Pinterest reference template."""
    all_tpls = load_templates()
    for t in all_tpls:
        if str(t.get("id")) == str(template_id):
            return {"status": "ok", "template": t}
    raise HTTPException(status_code=404, detail="Template not found")


@router.post("/recreate")
async def recreate_template_visual(
    request: Request,
    template_id: str = Form(...),
    product_image: Optional[UploadFile] = File(None),
    logo_image: Optional[UploadFile] = File(None),
    brand_name: Optional[str] = Form(""),
    product_name: Optional[str] = Form(""),
    user_edit: Optional[str] = Form(""),
    aspect_ratio: str = Form("4:5"),
    resolution: str = Form("2K"),
    folder_id: Optional[str] = Form(None),
    user: Optional[Dict[str, Any]] = Depends(current_user),
):
    """
    Recreate a Pinterest ad template with custom prompt and/or uploaded product & branding.
    Flow:
      1. Gemini Multimodal Analysis: Analyzes template visual + optional product photo + user prompt.
      2. Prompt Synthesis: Synthesizes a high-converting commercial prompt tailored for Nano Banana 2.1.
      3. Render via Nano Banana 2.1: Executes photorealistic rendering with nano-banana-2.1.
      4. Auto-save to user library and project folder.
    """
    from app import require_client, generate_gemini_image, read_upload, IMAGE_EXTS, MAX_IMAGE_BYTES

    # 1. Look up template
    all_tpls = load_templates()
    template = next((t for t in all_tpls if str(t.get("id")) == str(template_id)), None)
    if not template:
        raise HTTPException(status_code=404, detail="Template reference not found")

    # 2. Process product image (OPTIONAL - user can generate via prompt alone)
    prod_bytes: Optional[bytes] = None
    prod_mime: Optional[str] = None
    saved_ref_urls = []

    if product_image and product_image.filename:
        try:
            prod_bytes, prod_ext, prod_mime = await read_upload(product_image, IMAGE_EXTS, ".png", MAX_IMAGE_BYTES)
            prod_filename = f"ref_prod_{uuid.uuid4().hex}{prod_ext}"
            prod_path = os.path.join(GENERATED_DIR, prod_filename)
            with open(prod_path, "wb") as f:
                f.write(prod_bytes)
            prod_url = f"/static/generated/{prod_filename}"
            saved_ref_urls.append(prod_url)
        except Exception as e:
            logger.warning(f"Could not read uploaded product image: {e}")

    # 3. Fetch template visual reference (local file or remote URL)
    tpl_bytes: Optional[bytes] = None
    tpl_mime: Optional[str] = None
    tpl_img_url = template.get("image_url")
    if tpl_img_url:
        if tpl_img_url.startswith("/static/"):
            local_rel = tpl_img_url.lstrip("/")
            local_path = os.path.join(os.path.dirname(__file__), local_rel)
            if os.path.exists(local_path):
                try:
                    with open(local_path, "rb") as f_local:
                        tpl_bytes = f_local.read()
                    tpl_mime = "image/png" if local_path.endswith(".png") else "image/jpeg"
                    saved_ref_urls.append(tpl_img_url)
                except Exception as e:
                    logger.warning(f"Could not read local template visual {local_path}: {e}")
        elif tpl_img_url.startswith("http://") or tpl_img_url.startswith("https://"):
            try:
                async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client_http:
                    resp = await client_http.get(tpl_img_url)
                    if resp.status_code == 200:
                        tpl_bytes = resp.content
                        tpl_mime = resp.headers.get("content-type", "image/jpeg").split(";")[0]
                        saved_ref_urls.append(tpl_img_url)
            except Exception as e:
                logger.warning(f"Could not fetch remote template visual for Gemini analysis: {e}")

    # 4. Optional logo image
    logo_bytes: Optional[bytes] = None
    logo_mime: Optional[str] = None
    if logo_image and logo_image.filename:
        try:
            logo_bytes, logo_ext, logo_mime = await read_upload(logo_image, IMAGE_EXTS, ".png", MAX_IMAGE_BYTES)
            logo_filename = f"ref_logo_{uuid.uuid4().hex}{logo_ext}"
            logo_path = os.path.join(GENERATED_DIR, logo_filename)
            with open(logo_path, "wb") as f:
                f.write(logo_bytes)
            saved_ref_urls.append(f"/static/generated/{logo_filename}")
        except Exception as e:
            logger.warning(f"Could not process logo image: {e}")

    # 5. STEP 1: Gemini Multimodal Analysis -> Synthesizes prompt based on images & instructions
    client = require_client()

    analysis_parts = []
    has_product = prod_bytes is not None and prod_mime is not None

    if has_product:
        analysis_parts.append(types.Part.from_bytes(data=prod_bytes, mime_type=prod_mime))

    tpl_context = []
    if tpl_bytes and tpl_mime:
        analysis_parts.append(types.Part.from_bytes(data=tpl_bytes, mime_type=tpl_mime))
        tpl_context.append("IMAGE REFERENCE: The commercial advertising visual selected by the user from Pinterest.")
    else:
        tpl_context.append("Template composition and lighting metadata is described below.")

    if logo_bytes and logo_mime:
        analysis_parts.append(types.Part.from_bytes(data=logo_bytes, mime_type=logo_mime))

    brand = brand_name.strip() if brand_name else "the featured brand"
    prod = product_name.strip() if product_name else "the hero product"
    edits = user_edit.strip() if user_edit else "Faithfully recreate the template composition, studio lighting, and aesthetic."

    if has_product:
        product_instruction = (
            "1. VISUAL AUDIT: Examine the packaging geometry, materials, cap/closure, typography, and palette of the authentic product in IMAGE 1.\n"
            "2. SCENE RECREATION: Examine the composition, camera angle, focal depth, surface materials, and lighting in the template visual.\n"
            "3. WRITE THE PROMPT: Feature the authentic product from IMAGE 1 as the central hero subject, situated within the lighting and composition of the reference template, applying user directives."
        )
    else:
        product_instruction = (
            "1. SCENE RECREATION: Examine the composition, camera angle, lighting setup, surface textures, reflections, and mood of the reference template visual.\n"
            f"2. HERO CONCEPT: Feature {brand}'s {prod} as the hero subject based on user prompt/directives: '{edits}'.\n"
            "3. WRITE THE PROMPT: Write a photorealistic commercial advertising photograph prompt for Nano Banana 2.1 that places this hero concept into the exact studio lighting, environment surfaces, and aesthetic of the reference template."
        )

    palette_list = template.get("colors") or template.get("color_palette") or []

    analysis_prompt = (
        "You are an elite commercial advertising art director and generative vision prompt engineer.\n\n"
        "You are synthesizing an exact generation prompt tailored specifically for the Nano Banana 2.1 image model.\n\n"
        "TEMPLATE CREATIVE ATTRIBUTES:\n"
        f"- Title: {template.get('title', 'Advertising Template')}\n"
        f"- Category: {template.get('category', 'Product shot')}\n"
        f"- Industry: {template.get('industry_label', template.get('industry', 'Commercial'))}\n"
        f"- Movement / Style: {template.get('movement', 'High-end commercial aesthetic')}\n"
        f"- Studio Lighting: {template.get('lighting', 'Clean studio lighting with soft diffused shadows and crisp highlights')}\n"
        f"- Color Palette: {', '.join(palette_list[:5])}\n"
        f"- Scene Atmosphere: {template.get('description', '')}\n\n"
        "USER DIRECTIVES & PROMPT:\n"
        f"- Brand Name: {brand}\n"
        f"- Product / Subject: {prod}\n"
        f"- User Custom Prompt / Instructions: {edits}\n\n"
        f"SYNTHESIS PROTOCOL:\n"
        f"{product_instruction}\n"
        "- Direct camera optics, physical surface contact shadows, realistic reflections, and balanced commercial negative space.\n\n"
        "Output ONLY the final synthesized prompt string. Do not include markdown quotes, preambles, or conversational commentary."
    )
    analysis_parts.append(analysis_prompt)

    # Perform analysis with Gemini multimodal models
    synthesized_prompt: Optional[str] = None
    analysis_model_used: str = "algorithmic_fallback"
    analysis_candidates = [
        os.environ.get("GEMINI_ANALYSIS_MODEL", "gemini-3.6-flash"),
        "gemini-3.8-flash",
        "gemini-2.5-flash",
    ]
    seen_models = set()
    candidate_list = [m for m in analysis_candidates if m and not (m in seen_models or seen_models.add(m))]

    for model_name in candidate_list:
        try:
            resp = await asyncio.to_thread(
                client.models.generate_content,
                model=model_name,
                contents=analysis_parts,
            )
            txt = (resp.text or "").strip()
            if txt:
                synthesized_prompt = txt
                analysis_model_used = model_name
                break
        except Exception as e:
            logger.warning(f"Gemini analysis on {model_name} failed: {e}")

    # Algorithmic fallback if vision API call was unavailable
    if not synthesized_prompt:
        if has_product:
            product_clause = "The authentic product from Image 1 is featured as the hero subject with exact packaging geometry, materials, and label typography. "
        else:
            product_clause = f"Featuring {brand}'s {prod} as the hero subject based on user concept: {edits}. "

        synthesized_prompt = (
            f"Award-winning commercial advertising photograph for {brand}'s {prod}. "
            f"{product_clause}"
            f"Recreating the signature aesthetic of {template.get('title', 'Template')}: {template.get('movement', 'Commercial advertising')}. "
            f"Studio Lighting: {template.get('lighting', 'clean diffused commercial lighting with crisp specular highlights and soft contact shadows')}. "
            f"Environment and surfaces: {template.get('description', 'Balanced commercial set with authentic textures')}. "
            f"User directives: {edits}. "
            "Pristine optical clarity, physical contact shadows on surfaces, hyper-detailed commercial ad photography."
        )

    # 6. STEP 2: Render using Nano Banana 2.1
    render_contents = []
    if has_product:
        render_contents.append(types.Part.from_bytes(data=prod_bytes, mime_type=prod_mime))
    if logo_bytes and logo_mime:
        render_contents.append(types.Part.from_bytes(data=logo_bytes, mime_type=logo_mime))

    render_contents.append(synthesized_prompt)

    res_clean = (resolution or "2K").strip().upper()
    if res_clean not in ["1K", "2K", "4K"]:
        res_clean = "2K"

    image_bytes = await asyncio.to_thread(
        generate_gemini_image, client, render_contents, aspect_ratio, "nano-banana-2.1", res_clean
    )

    out_filename = f"ad_recreate_{uuid.uuid4().hex}.png"
    out_path = os.path.join(GENERATED_DIR, out_filename)
    with open(out_path, "wb") as out_f:
        out_f.write(image_bytes)

    out_url = f"/static/generated/{out_filename}"

    # 7. STEP 3: Auto-save into user's creative library & project folder
    clean_title = f"{brand_name.strip() if brand_name else 'Commercial'} {product_name.strip() if product_name else 'Ad'} · {template.get('title', 'Template')}"
    creative_record = await database.save_creative(
        user,
        {
            "type": "image",
            "title": clean_title,
            "prompt": synthesized_prompt,
            "media_url": out_url,
            "aspect_ratio": aspect_ratio,
            "model_params": {
                "model": "nano-banana-2.1",
                "resolution": res_clean,
                "recreated_from_template_id": template_id,
                "template_title": template.get("title"),
                "analysis_model": analysis_model_used,
                "user_edit": user_edit,
                "has_product_reference": has_product,
            },
            "tags": [template.get("category", "Ads"), template.get("industry", "general"), "recreation"],
            "reference_images": saved_ref_urls,
            "folder_id": folder_id,
        },
    )

    return {
        "status": "ok",
        "image_url": out_url,
        "creative_id": creative_record.get("id"),
        "title": clean_title,
        "prompt": synthesized_prompt,
        "aspect_ratio": aspect_ratio,
        "resolution": res_clean,
        "model": "nano-banana-2.1",
        "analysis_model": analysis_model_used,
        "template": template,
        "reference_images": saved_ref_urls,
        "has_product_reference": has_product,
    }
