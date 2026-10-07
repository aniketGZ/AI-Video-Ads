import os
import uuid
import asyncio
import logging
from typing import Optional, Dict, Any

from ad_templates import (
    TEMPLATES,
    detect_brand_mode,
    resolve_template_id,
    short_headline,
    build_template_prompt,
    build_reference_prompt,
)
from competitor_ad_engine import resolve_reference_media
from media_utils import (
    GENERATED_DIR,
    resolve_generated_path,
    mime_for_path,
    generate_gemini_image,
)

logger = logging.getLogger(__name__)

META_RATIO_DIMENSIONS = {
    "1:1": (1024, 1024),
    "4:5": (1024, 1280),
    "9:16": (1024, 1792),
    "16:9": (1792, 1024),
}

# Shared rule for every prompt that writes ad copy: generated claims end up printed in
# real ads, so nothing that needs evidence may be invented.
NO_FABRICATED_CLAIMS_RULE = (
    "COMPLIANCE RULE: Do NOT invent star ratings, review counts, customer counts, percentages, "
    "awards or rankings, named testimonials, expert endorsements, guarantees, free trials, discounts "
    "or shipping promises. Only use such claims if they appear verbatim in the brand data above. "
    "Otherwise write benefit-led copy without numbers or attributed quotes."
)


# Template-driven ad prompt (layout, product placement and a three-element text budget)
def build_native_in_image_ad_prompt(
    blueprint: Dict[str, Any],
    brand_name: str,
    product_name: str,
    product_category: str = "",
    target_audience_persona: str = "",
    aspect_ratio: str = "4:5",
    product_visual_description: str = "",
    color_palette: str = "",
    custom_directive: Optional[str] = None,
    *,
    business_type: str = "",
    has_product_ref: bool = False,
    setting: str = "",
    talent: str = "",
    brand_kit: Optional[Dict[str, Any]] = None,
    has_logo: bool = False,
    logo_tone: str = "dark",
    has_layout_ref: bool = False,
) -> str:
    """
    Builds the image prompt. With a competitor reference in the blueprint, the ad borrows that ad's concept
    and layout and applies our brand kit and logo; otherwise it uses the blueprint's layout template.
    Only the logo/wordmark, a short headline and the CTA are rendered in the image.
    """
    if blueprint.get("reference"):
        callouts = [c for c in (blueprint.get("callout_points") or []) if c]
        return build_reference_prompt(
            reference=blueprint["reference"],
            concept=blueprint.get("concept") or "",
            brand_name=brand_name,
            product_name=product_name,
            product_category=product_category,
            target_audience_persona=target_audience_persona,
            aspect_ratio=aspect_ratio,
            headline=blueprint.get("image_headline") or blueprint.get("headline") or "",
            cta=blueprint.get("cta") or "Shop Now",
            scene_hint=" ".join(x for x in [blueprint.get("visual_prompt") or "", f"Benefit shown: {callouts[0]}." if callouts else ""] if x),
            product_visual_description=product_visual_description,
            color_palette=color_palette,
            brand_kit=brand_kit,
            has_product_ref=has_product_ref,
            has_layout_ref=has_layout_ref,
            has_logo=has_logo,
            logo_tone=logo_tone,
            setting=setting,
            talent=talent,
            custom_directive=custom_directive,
        )
    mode = detect_brand_mode(business_type, product_category, has_product_ref)
    template_id = resolve_template_id(blueprint, mode)
    callouts = [c for c in (blueprint.get("callout_points") or []) if c]
    return build_template_prompt(
        template_id=template_id,
        mode=mode,
        brand_name=brand_name,
        product_name=product_name,
        product_category=product_category,
        target_audience_persona=target_audience_persona,
        aspect_ratio=aspect_ratio,
        headline=blueprint.get("image_headline") or blueprint.get("headline") or "",
        cta=blueprint.get("cta") or "Shop Now",
        scene_hint=blueprint.get("visual_prompt") or "",
        product_visual_description=product_visual_description,
        color_palette=color_palette,
        setting=setting,
        talent=talent,
        benefit=callouts[0] if callouts else "",
        contrast_before=blueprint.get("comparison_theirs") or "",
        business_type=business_type,
        has_product_ref=has_product_ref,
        custom_directive=custom_directive,
    )


async def generate_single_meta_creative(
    blueprint: Dict[str, Any],
    brand_name: str,
    product_name: str,
    product_category: str = "",
    target_audience_persona: str = "",
    aspect_ratio: str = "4:5",
    product_image_path: Optional[str] = None,
    product_bytes: Optional[bytes] = None,
    mime_type: str = "image/png",
    custom_directive: Optional[str] = None,
    client: Any = None,
    product_visual_description: str = "",
    color_palette: str = "",
    business_type: str = "",
    setting: str = "",
    talent: str = "",
    brand_kit: Optional[Dict[str, Any]] = None,
    logo_path: Optional[str] = None,
    logo_tone: str = "dark",
) -> Dict[str, Any]:
    """
    Renders one finished Meta ad (in-image wordmark, headline and CTA) with Nano Banana Pro
    and saves it to static/generated.
    """
    from google.genai import types

    if not client:
        raise RuntimeError("A Gemini API key is required for Nano Banana Pro. Add it under API Keys.")

    cid = blueprint.get("creative_id", 1)
    target_w, target_h = META_RATIO_DIMENSIONS.get(aspect_ratio, (1024, 1280))

    # Product reference resolution (only files inside static/generated are allowed)
    if not product_bytes and product_image_path:
        local_path = resolve_generated_path(product_image_path)
        if local_path:
            with open(local_path, "rb") as f:
                product_bytes = f.read()
            mime_type = mime_for_path(local_path, "image/png")

    # Competitor layout reference and brand logo (both optional; only files inside known folders are read)
    layout_bytes = None
    ref = blueprint.get("reference") or {}
    if ref:
        layout_path = resolve_reference_media(ref.get("run_id") or "", ref.get("media_path") or "")
        if layout_path:
            layout_bytes = layout_path.read_bytes()
        else:
            logger.warning(f"[Meta Creative #{cid}] layout reference not found: {ref.get('media_path')}")
    logo_bytes = None
    logo_local = resolve_generated_path(logo_path) if logo_path else None
    if logo_local:
        with open(logo_local, "rb") as f:
            logo_bytes = f.read()

    mode = detect_brand_mode(business_type, product_category, bool(product_bytes))
    template_id = resolve_template_id(blueprint, mode)
    blueprint = {**blueprint, "template_id": template_id}

    visual_prompt = build_native_in_image_ad_prompt(
        blueprint=blueprint,
        brand_name=brand_name,
        product_name=product_name,
        product_category=product_category,
        target_audience_persona=target_audience_persona,
        aspect_ratio=aspect_ratio,
        product_visual_description=product_visual_description,
        color_palette=color_palette,
        custom_directive=custom_directive,
        business_type=business_type,
        has_product_ref=bool(product_bytes),
        setting=setting,
        talent=talent,
        brand_kit=brand_kit,
        has_logo=bool(logo_bytes),
        logo_tone=logo_tone,
        has_layout_ref=bool(layout_bytes),
    )

    logger.info(f"[Meta Creative #{cid}] Generating with Gemini Nano Banana Pro...")
    contents = []
    # Order must match the IMAGE numbers in the prompt: product, layout reference, logo
    if product_bytes:
        contents.append(types.Part.from_bytes(data=product_bytes, mime_type=mime_type))
    if layout_bytes:
        contents.append(types.Part.from_bytes(data=layout_bytes, mime_type="image/jpeg"))
    if logo_bytes:
        contents.append(types.Part.from_bytes(data=logo_bytes, mime_type="image/png"))
    contents.append(visual_prompt)
    image_bytes = await asyncio.to_thread(generate_gemini_image, client, contents, aspect_ratio)
    if not image_bytes:
        raise RuntimeError("Nano Banana Pro did not return an image.")

    filename = f"meta_suite_{cid}_{uuid.uuid4().hex}.png"
    with open(os.path.join(GENERATED_DIR, filename), "wb") as f:
        f.write(image_bytes)
    image_url = f"/static/generated/{filename}"

    return {
        "status": "success",
        "creative_id": cid,
        "framework_key": blueprint.get("framework_key", "general"),
        "framework_name": blueprint.get("framework_name", "Meta Creative"),
        "headline": blueprint.get("headline", ""),
        "primary_text": blueprint.get("primary_text", ""),
        "cta": blueprint.get("cta", "Shop Now"),
        "image_headline": short_headline(blueprint.get("image_headline") or blueprint.get("headline")),
        "template_id": template_id,
        "template_name": f"Layout from a {ref.get('competitor')} ad" if layout_bytes else TEMPLATES[template_id]["name"],
        "brand_mode": mode,
        "brand_name": brand_name,
        "image_url": image_url,
        "filename": filename,
        "aspect_ratio": aspect_ratio,
        "width": target_w,
        "height": target_h,
        "model_used": "nano-banana-pro-preview",
        "visual_prompt": visual_prompt,
        "has_product_reference": bool(product_bytes),
    }
