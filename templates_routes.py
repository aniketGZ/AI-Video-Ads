"""
Pinterest Creative Library & Recreate Template API Routes
Allows users to explore real Pinterest advertising references and recreate
custom commercial visuals by uploading their product, brand name, and custom edits.
"""

import asyncio
import json
import logging
import os
import random
import re
import uuid
from collections import Counter
from typing import Any, Dict, List, Optional
import httpx
from fastapi import APIRouter, Depends, File, Form, Header, HTTPException, Request, UploadFile
from google.genai import types

from access import current_user
import database
from media_utils import GENERATED_DIR, save_generated_media

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
        _normalise_industry_labels(_TEMPLATES_CACHE)
        _enrich_template_keywords(_TEMPLATES_CACHE)
    return _TEMPLATES_CACHE


# The dataset spells some industries two ways ("Fintech & Finance" / "Fintech Finance").
# Every template in an industry gets that industry's most used label, so the filter row
# shows one chip per industry.
OTHER_INDUSTRY = "uncategorized"


def _normalise_industry_labels(tpls: List[Dict[str, Any]]) -> None:
    counts: Dict[str, Dict[str, int]] = {}
    for t in tpls:
        slug = (t.get("industry") or OTHER_INDUSTRY).lower()
        label = t.get("industry_label") or ""
        counts.setdefault(slug, {})
        counts[slug][label] = counts[slug].get(label, 0) + 1
    best = {slug: max(labels, key=labels.get) for slug, labels in counts.items()}
    best[OTHER_INDUSTRY] = "Lifestyle & other"
    for t in tpls:
        slug = (t.get("industry") or OTHER_INDUSTRY).lower()
        t["industry"] = slug
        t["industry_label"] = best.get(slug) or slug.replace("-", " ").title()


def _industry_facets(tpls: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Industries present in `tpls`, most templates first, with 'other' last."""
    seen: Dict[str, Dict[str, Any]] = {}
    for t in tpls:
        slug = t.get("industry") or OTHER_INDUSTRY
        f = seen.setdefault(slug, {"id": slug, "label": t.get("industry_label") or slug, "count": 0})
        f["count"] += 1
    return sorted(seen.values(), key=lambda f: (f["id"] == OTHER_INDUSTRY, -f["count"], f["label"]))


# Curated design, mood, layout, and subject keywords used to arrange templates
_CURATED_KEYWORDS = [
    ("minimalist", ("minimalist", "minimal", "clean", "negative space")),
    ("luxury", ("luxury", "premium", "high-end", "gold", "travertine", "marble")),
    ("editorial", ("editorial", "magazine", "didone", "serif", "vogue")),
    ("ugc", ("ugc", "selfie", "handheld", "candid", "creator", "authentic")),
    ("studio", ("studio", "plinth", "pedestal", "backdrop", "spotlight")),
    ("lifestyle", ("lifestyle", "everyday", "morning", "outdoor", "home")),
    ("dark mode", ("dark", "noir", "black", "moody", "neon", "cyber")),
    ("botanical", ("botanical", "organic", "leaves", "nature", "herbal", "eco")),
    ("typography", ("typography", "headline", "bold type", "swiss", "poster")),
    ("3d & bento", ("3d", "bento", "ui", "saas", "dashboard", "glassmorphism")),
    ("macro", ("macro", "texture", "swatch", "droplet", "splash", "close-up")),
    ("pastel & warm", ("pastel", "warm", "beige", "sand", "soft light", "dewy")),
    ("monochrome", ("monochrome", "black and white", "grayscale")),
    ("split layout", ("split", "before", "after", "comparison", "grid")),
    ("skincare", ("skincare", "serum", "cream", "cleanser", "glow", "spf")),
    ("fintech", ("fintech", "card", "banking", "finance", "wallet", "crypto")),
    ("food & drink", ("coffee", "cafe", "drink", "beverage", "food", "snack", "bottle")),
    ("fashion", ("fashion", "apparel", "sneaker", "streetwear", "outfit")),
    ("jewelry", ("jewelry", "jewellery", "watch", "ring", "diamond")),
    ("fitness", ("fitness", "gym", "sport", "athletic", "workout")),
]


def _enrich_template_keywords(tpls: List[Dict[str, Any]]) -> None:
    """Assign clean, searchable keywords to each template from its visual & industry metadata."""
    for t in tpls:
        existing = [str(k).strip().lower() for k in (t.get("keywords") or []) if str(k).strip()]
        blob = " ".join([
            t.get("title") or "",
            t.get("category") or "",
            t.get("industry_label") or "",
            t.get("movement") or "",
            t.get("preset_name") or "",
            t.get("lighting") or "",
            t.get("composition") or "",
            t.get("description") or "",
        ]).lower()

        kws: List[str] = []
        seen = set()

        def add_kw(val: str) -> None:
            v = val.strip().lower()
            if v and v not in seen:
                seen.add(v)
                kws.append(v)

        for k in existing:
            add_kw(k)
        for label, triggers in _CURATED_KEYWORDS:
            if any(re.search(rf"\b{re.escape(tr)}\b", blob) for tr in triggers):
                add_kw(label)

        # Fallback: include category / industry token if very few matched
        if len(kws) < 2:
            cat = (t.get("category") or "").strip().lower()
            if cat:
                add_kw(cat)
            ind_lbl = (t.get("industry_label") or "").split("&")[0].strip().lower()
            if ind_lbl and ind_lbl != "lifestyle":
                add_kw(ind_lbl)

        t["keywords"] = kws


def _keyword_facets(tpls: List[Dict[str, Any]], limit: int = 20) -> List[Dict[str, Any]]:
    """Most common keywords across `tpls`, sorted by frequency."""
    counts: Counter = Counter()
    for t in tpls:
        for kw in t.get("keywords") or []:
            counts[kw] += 1
    return [
        {"id": kw, "label": kw.title() if kw != "ugc" else "UGC", "count": cnt}
        for kw, cnt in counts.most_common(limit)
    ]


def _matches_query(t: Dict[str, Any], query: str) -> bool:
    tokens = [tok for tok in query.lower().split() if tok]
    if not tokens:
        return True
    haystack = " ".join([
        t.get("title") or "",
        t.get("movement") or "",
        t.get("industry_label") or "",
        t.get("category") or "",
        t.get("preset_name") or "",
        t.get("composition") or "",
        t.get("lighting") or "",
        t.get("description") or "",
        " ".join(t.get("keywords") or []),
    ]).lower()
    return all(tok in haystack for tok in tokens)


@router.get("/explore")
async def get_explore_templates(
    category: Optional[str] = None,
    industry: Optional[str] = None,
    keyword: Optional[str] = None,
    media_type: Optional[str] = None,
    q: Optional[str] = None,
    shuffle: bool = True,
):
    """List, filter by category/industry/keyword, and randomize Pinterest ad creative templates."""
    all_tpls = load_templates()
    filtered = list(all_tpls)

    if category and category.lower() != "all":
        cat_lower = category.lower()
        filtered = [t for t in filtered if t.get("category", "").lower() == cat_lower]

    if media_type and media_type.lower() != "all":
        med_lower = media_type.lower()
        filtered = [t for t in filtered if t.get("media_type", "image").lower() == med_lower]

    if q and q.strip():
        filtered = [t for t in filtered if _matches_query(t, q.strip())]

    # Industry and keyword facets reflect the active format/search filters
    industries = _industry_facets(filtered)

    if industry and industry.lower() != "all":
        ind_lower = industry.lower()
        filtered = [t for t in filtered if t.get("industry", "").lower() == ind_lower]

    keywords = _keyword_facets(filtered)

    if keyword and keyword.lower() != "all":
        kw_lower = keyword.strip().lower()
        filtered = [t for t in filtered if kw_lower in (t.get("keywords") or [])]

    if shuffle:
        random.shuffle(filtered)

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
        "industries": industries,
        "keywords": keywords,
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
    x_api_key: Optional[str] = Header(None),
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
    client = require_client(x_api_key)

    analysis_parts = []
    has_product = prod_bytes is not None and prod_mime is not None
    has_tpl = tpl_bytes is not None and tpl_mime is not None
    has_logo = logo_bytes is not None and logo_mime is not None

    img_idx = 0
    prod_idx = tpl_idx = logo_idx = None

    if has_product:
        img_idx += 1
        prod_idx = img_idx
        analysis_parts.append(f"IMAGE {prod_idx} (USER PRODUCT — preserve exact packaging, shape, colors, and label):")
        analysis_parts.append(types.Part.from_bytes(data=prod_bytes, mime_type=prod_mime))

    tpl_context = []
    if has_tpl:
        img_idx += 1
        tpl_idx = img_idx
        analysis_parts.append(f"IMAGE {tpl_idx} (TEMPLATE CREATIVE REFERENCE — recreate its layout, lighting, and visual hierarchy):")
        analysis_parts.append(types.Part.from_bytes(data=tpl_bytes, mime_type=tpl_mime))
        tpl_context.append(f"IMAGE {tpl_idx} is the commercial advertising template selected by the user.")
    else:
        tpl_context.append("No template image could be fetched; rely on the template composition and lighting metadata below.")

    if has_logo:
        img_idx += 1
        logo_idx = img_idx
        analysis_parts.append(f"IMAGE {logo_idx} (USER BRAND LOGO):")
        analysis_parts.append(types.Part.from_bytes(data=logo_bytes, mime_type=logo_mime))

    brand = brand_name.strip() if brand_name else "the featured brand"
    prod = product_name.strip() if product_name else "the hero product"
    edits = user_edit.strip() if user_edit else "Faithfully recreate the template composition, studio lighting, and aesthetic."

    if has_product:
        product_instruction = (
            f"1. VISUAL AUDIT: Examine the packaging geometry, materials, cap/closure, typography, and palette of the authentic product in IMAGE {prod_idx}.\n"
            + (
                f"2. SCENE RECREATION: Examine the exact composition, camera angle, focal depth, surface materials, typography placement, and lighting in IMAGE {tpl_idx} (the template creative).\n"
                if has_tpl else
                "2. SCENE RECREATION: Use the template metadata below for composition, camera angle, surface materials, and lighting.\n"
            )
            + f"3. WRITE THE PROMPT: Feature the authentic product from IMAGE {prod_idx} as the central hero subject, placed into the exact layout, lighting, and visual hierarchy of "
            + (f"IMAGE {tpl_idx}, " if has_tpl else "the reference template, ")
            + "replacing any original brand/product/text from the template with the user's brand and directives."
        )
    else:
        product_instruction = (
            (
                f"1. SCENE RECREATION: Examine the exact composition, camera angle, lighting setup, surface textures, typography placement, and mood of IMAGE {tpl_idx} (the template creative).\n"
                if has_tpl else
                "1. SCENE RECREATION: Use the template metadata below for composition, camera angle, lighting setup, surface textures, and mood.\n"
            )
            + f"2. HERO CONCEPT: Feature {brand}'s {prod} as the hero subject based on user prompt/directives: '{edits}'.\n"
            + "3. WRITE THE PROMPT: Write a photorealistic commercial advertising photograph prompt for Nano Banana 2.1 that places this hero concept into the exact layout, studio lighting, environment surfaces, and aesthetic of "
            + (f"IMAGE {tpl_idx}, replacing any original brand/product/text from the template." if has_tpl else "the reference template.")
        )

    palette_list = template.get("colors") or template.get("color_palette") or []

    analysis_prompt = (
        "You are an elite commercial advertising art director and generative vision prompt engineer.\n\n"
        "You are synthesizing an exact generation prompt tailored specifically for the Nano Banana 2.1 image model. "
        "Nano Banana 2.1 will receive the exact same numbered reference images listed above.\n\n"
        "TEMPLATE CREATIVE ATTRIBUTES:\n"
        f"- Reference Status: {' '.join(tpl_context)}\n"
        f"- Title: {template.get('title', 'Advertising Template')}\n"
        f"- Category: {template.get('category', 'Product shot')}\n"
        f"- Industry: {template.get('industry_label', template.get('industry', 'Commercial'))}\n"
        f"- Movement / Style: {template.get('movement', 'High-end commercial aesthetic')}\n"
        f"- Composition: {template.get('composition', '')}\n"
        f"- Studio Lighting: {template.get('lighting', 'Clean studio lighting with soft diffused shadows and crisp highlights')}\n"
        f"- Color Palette: {', '.join(palette_list[:5])}\n"
        f"- Scene Atmosphere: {template.get('description', '')}\n\n"
        "USER DIRECTIVES & PROMPT:\n"
        f"- Brand Name: {brand}\n"
        f"- Product / Subject: {prod}\n"
        f"- Aspect Ratio: {aspect_ratio}\n"
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

    # 6. STEP 2: Render using Nano Banana 2.1 (order matches IMAGE 1, 2, 3 roles)
    render_contents = []
    role_lines = ["REFERENCE ROLES (follow strictly):"]
    if has_product:
        render_contents.append(types.Part.from_bytes(data=prod_bytes, mime_type=prod_mime))
        role_lines.append(
            f"- IMAGE {prod_idx} = PRODUCT-REF: the real {prod} by {brand}. Reproduce it as the hero with exact shape, proportions, materials, and label typography."
        )
    if has_tpl:
        render_contents.append(types.Part.from_bytes(data=tpl_bytes, mime_type=tpl_mime))
        role_lines.append(
            f"- IMAGE {tpl_idx} = TEMPLATE LAYOUT-REF: copy ONLY its compositional architecture, framing, camera angle, lighting, and visual hierarchy. "
            f"Do NOT copy the template's original brand name, logo, product, or unrelated text; replace them with {brand}'s {prod}."
        )
    if has_logo:
        render_contents.append(types.Part.from_bytes(data=logo_bytes, mime_type=logo_mime))
        role_lines.append(
            f"- IMAGE {logo_idx} = BRAND LOGO: place the authentic {brand} logo cleanly without redrawing or distorting it."
        )

    final_render_prompt = (
        "\n".join(role_lines) + "\n\n" + synthesized_prompt
        if len(role_lines) > 1
        else synthesized_prompt
    )
    render_contents.append(final_render_prompt)

    res_clean = (resolution or "2K").strip().upper()
    if res_clean not in ["1K", "2K", "4K"]:
        res_clean = "2K"

    image_bytes = await asyncio.to_thread(
        generate_gemini_image, client, render_contents, aspect_ratio, "nano-banana-2.1", res_clean
    )
    if not image_bytes:
        raise HTTPException(status_code=502, detail="Nano Banana 2.1 did not return an image. Please try again.")

    out_filename = f"ad_recreate_{uuid.uuid4().hex}.png"
    out_url = save_generated_media(out_filename, image_bytes, "image/png")

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
