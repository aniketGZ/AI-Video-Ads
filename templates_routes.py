"""
Pinterest Creative Library & Recreate Template API Routes
Allows users to explore real Pinterest advertising references and recreate
custom commercial visuals by uploading their product, brand name, and custom edits.
"""

import asyncio
import json
import os
import uuid
from typing import Any, Dict, List, Optional
import httpx
from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from google.genai import types

from access import current_user
import database

router = APIRouter(prefix="/api/templates", tags=["Pinterest Templates"])

TEMPLATES_JSON_PATH = os.path.join(os.path.dirname(__file__), "data", "explore_templates.json")
GENERATED_DIR = os.path.join(os.path.dirname(__file__), "static", "generated")
os.makedirs(GENERATED_DIR, exist_ok=True)

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
    product_image: UploadFile = File(...),
    logo_image: Optional[UploadFile] = File(None),
    brand_name: Optional[str] = Form(""),
    product_name: Optional[str] = Form(""),
    user_edit: Optional[str] = Form(""),
    aspect_ratio: str = Form("4:5"),
    resolution: str = Form("2K"),
    folder_id: Optional[str] = Form(None),
    user: Optional[Dict[str, Any]] = Depends(current_user),
):
    """Recreate a Pinterest ad template with the user's product, branding, and custom edits."""
    from app import require_client, generate_gemini_image, read_upload, IMAGE_EXTS, MAX_IMAGE_BYTES

    # 1. Look up template
    all_tpls = load_templates()
    template = next((t for t in all_tpls if str(t.get("id")) == str(template_id)), None)
    if not template:
        raise HTTPException(status_code=404, detail="Template reference not found")

    # 2. Process product image
    if not product_image or not product_image.filename:
        raise HTTPException(status_code=400, detail="Product image is required")

    prod_bytes, prod_ext, prod_mime = await read_upload(product_image, IMAGE_EXTS, ".png", MAX_IMAGE_BYTES)
    prod_filename = f"ref_prod_{uuid.uuid4().hex}{prod_ext}"
    prod_path = os.path.join(GENERATED_DIR, prod_filename)
    with open(prod_path, "wb") as f:
        f.write(prod_bytes)
    prod_url = f"/static/generated/{prod_filename}"

    parts = [types.Part.from_bytes(data=prod_bytes, mime_type=prod_mime)]
    saved_ref_urls = [prod_url]

    # 3. Fetch template reference image to pass as visual reference
    tpl_img_url = template.get("image_url")
    if tpl_img_url:
        try:
            async with httpx.AsyncClient(timeout=8.0) as client_http:
                resp = await client_http.get(tpl_img_url)
                if resp.status_code == 200:
                    tpl_bytes = resp.content
                    tpl_mime = resp.headers.get("content-type", "image/jpeg")
                    parts.append(types.Part.from_bytes(data=tpl_bytes, mime_type=tpl_mime))
                    saved_ref_urls.append(tpl_img_url)
        except Exception as e:
            print("Could not fetch remote template image for Gemini:", e)

    # 4. Optional logo image
    if logo_image and logo_image.filename:
        try:
            logo_bytes, logo_ext, logo_mime = await read_upload(logo_image, IMAGE_EXTS, ".png", MAX_IMAGE_BYTES)
            logo_filename = f"ref_logo_{uuid.uuid4().hex}{logo_ext}"
            logo_path = os.path.join(GENERATED_DIR, logo_filename)
            with open(logo_path, "wb") as f:
                f.write(logo_bytes)
            saved_ref_urls.append(f"/static/generated/{logo_filename}")
            parts.append(types.Part.from_bytes(data=logo_bytes, mime_type=logo_mime))
        except Exception:
            pass

    # 5. Build prompt
    brand = brand_name.strip() if brand_name else "the featured brand"
    prod = product_name.strip() if product_name else "the featured product"

    ref_instructions = (
        "IMAGE 1 is the user's authentic product. Reproduce its exact packaging geometry, label typography, materials, and colors with photorealistic fidelity.\n"
        f"IMAGE 2 is the commercial advertising reference visual ({template.get('movement', 'High-end advertising aesthetic')}).\n\n"
        f"Goal: Create a high-converting, award-winning commercial ad photograph for {brand}'s {prod}. "
        "Place the exact product from IMAGE 1 into the center of the scene as the hero subject, completely recreating the composition, lighting, camera angle, and artistic aesthetic of the reference visual in IMAGE 2.\n"
        f"Lighting & Atmosphere: {template.get('lighting', 'Clean commercial studio lighting with soft diffused shadows and crisp highlights')}.\n"
    )

    if user_edit and user_edit.strip():
        ref_instructions += f"Artistic Edits & Custom Requests: {user_edit.strip()}.\n"

    if brand_name and brand_name.strip():
        ref_instructions += f"Typography & Branding: Integrate the brand name '{brand_name.strip()}' with elegant, immaculate typography.\n"

    ref_instructions += (
        "Composition: Clean commercial framing, balanced negative space, true-to-life shadows and physical contact on surfaces. "
        "Hyper-detailed 4K commercial advertising photography."
    )

    # 6. Generate via Gemini Nano Banana Pro
    client = require_client()
    contents = [*parts, ref_instructions]

    res_clean = (resolution or "2K").strip().upper()
    if res_clean not in ["1K", "2K", "4K"]:
        res_clean = "2K"

    image_bytes = await asyncio.to_thread(
        generate_gemini_image, client, contents, aspect_ratio, "nano-banana-pro", res_clean
    )

    out_filename = f"ad_recreate_{uuid.uuid4().hex}.png"
    out_path = os.path.join(GENERATED_DIR, out_filename)
    with open(out_path, "wb") as out_f:
        out_f.write(image_bytes)

    out_url = f"/static/generated/{out_filename}"

    # 7. Auto-save into user's library
    clean_title = f"{brand_name.strip() if brand_name else 'Commercial'} {product_name.strip() if product_name else 'Ad'} · {template.get('title', 'Template')}"
    creative_record = await database.save_creative(
        user,
        {
            "type": "image",
            "title": clean_title,
            "prompt": ref_instructions,
            "media_url": out_url,
            "aspect_ratio": aspect_ratio,
            "model_params": {
                "model": "nano-banana-pro",
                "resolution": res_clean,
                "recreated_from_template_id": template_id,
            },
            "tags": [template.get("category", "Ads"), template.get("industry", "general")],
            "reference_images": saved_ref_urls,
            "folder_id": folder_id,
        },
    )

    return {
        "status": "ok",
        "image_url": out_url,
        "creative_id": creative_record.get("id"),
        "title": clean_title,
        "prompt": ref_instructions,
        "aspect_ratio": aspect_ratio,
        "resolution": res_clean,
        "template": template,
        "reference_images": saved_ref_urls,
    }
