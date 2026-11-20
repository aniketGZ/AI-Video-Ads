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
    save_generated_media,
    resolve_generated_path,
    mime_for_path,
    generate_gemini_image,
    image_model,
    DEFAULT_IMAGE_MODEL,
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
    preset_id: Optional[str] = None,
) -> str:
    """
    Builds the image prompt. With a competitor reference in the blueprint, the ad borrows that ad's concept
    and layout and applies our brand kit and logo; otherwise it uses the creative reference preset or layout template.
    Only the logo/wordmark, a short headline and the CTA are rendered in the image.
    """
    # 1. Competitor reference layout takes absolute precedence if present
    if blueprint.get("reference"):
        concept_text = blueprint.get("concept") or (f"Layout inspired by {blueprint['reference'].get('competitor')}" if blueprint.get("reference", {}).get("competitor") else "")
        callouts = [c for c in (blueprint.get("callout_points") or []) if c]
        return build_reference_prompt(
            reference=blueprint["reference"],
            concept=concept_text,
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

    # 2. Check if a specific single creative preset is selected (and not "diverse")
    active_preset_id = preset_id or blueprint.get("preset_id")
    preset = None
    if active_preset_id and active_preset_id != "diverse":
        try:
            from creative_library_presets import get_preset_by_id
            preset = get_preset_by_id(active_preset_id)
        except Exception:
            preset = None

    if preset and preset.get("id") != "diverse":
        from creative_library_presets import build_preset_creative_prompt
        callouts = [c for c in (blueprint.get("callout_points") or []) if c]
        scene_hint = blueprint.get("visual_prompt") or ""
        if callouts and not scene_hint:
            scene_hint = f"Highlight key benefit: {callouts[0]}."
        return build_preset_creative_prompt(
            preset["id"],
            brand_name=brand_name,
            product_name=product_name,
            headline=short_headline(blueprint.get("image_headline") or blueprint.get("headline") or ""),
            cta=blueprint.get("cta") or "Shop Now",
            aspect_ratio=aspect_ratio,
            product_visual_description=product_visual_description,
            color_palette=color_palette,
            custom_directive=custom_directive,
            has_product_ref=has_product_ref,
            has_logo=has_logo,
            setting=setting,
            talent=talent,
            scene_hint=scene_hint,
            brand_kit=brand_kit,
        )

    # 3. Dynamic layout template resolution (split_contrast, macro_texture, model_lifestyle, etc.)
    mode = detect_brand_mode(business_type, product_category, has_product_ref)
    template_id = resolve_template_id(blueprint, mode, product_category)
    callouts = [c for c in (blueprint.get("callout_points") or []) if c]
    effective_palette = color_palette
    if not effective_palette and brand_kit:
        effective_palette = f"Primary {brand_kit.get('primary_hex', '')}, Accent {brand_kit.get('accent_hex', '')}, Mood: {brand_kit.get('visual_mood', '')}"

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
        color_palette=effective_palette,
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
    model: str = DEFAULT_IMAGE_MODEL,
) -> Dict[str, Any]:
    """
    Renders one finished Meta ad (in-image wordmark, headline and CTA) with Gemini Nano Banana 2.1
    and saves it to static/generated.
    """
    from google.genai import types

    chosen_model = (model or DEFAULT_IMAGE_MODEL).strip()
    model_meta = image_model(chosen_model)

    if not client:
        raise RuntimeError(f"A Gemini API key is required for {model_meta['label']}. Add it under API Keys.")

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

    preset_id = blueprint.get("preset_id")
    preset_info = None
    if preset_id:
        try:
            from creative_library_presets import get_preset_by_id
            preset_info = get_preset_by_id(preset_id)
        except Exception:
            preset_info = None

    mode = detect_brand_mode(business_type, product_category, bool(product_bytes))
    template_id = resolve_template_id(blueprint, mode, product_category)
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
        preset_id=preset_id,
    )

    logger.info(f"[Meta Creative #{cid}] Generating with Gemini {model_meta['label']} ({model_meta['id']})...")
    contents = []
    # Order must match the IMAGE numbers in the prompt: product, layout reference, logo
    if product_bytes:
        contents.append(types.Part.from_bytes(data=product_bytes, mime_type=mime_type))
    if layout_bytes:
        contents.append(types.Part.from_bytes(data=layout_bytes, mime_type="image/jpeg"))
    if logo_bytes:
        contents.append(types.Part.from_bytes(data=logo_bytes, mime_type="image/png"))
    contents.append(visual_prompt)
    image_bytes = await asyncio.to_thread(generate_gemini_image, client, contents, aspect_ratio, model=chosen_model)
    if not image_bytes:
        raise RuntimeError(f"{model_meta['label']} did not return an image.")

    filename = f"meta_suite_{cid}_{uuid.uuid4().hex}.png"
    image_url = save_generated_media(filename, image_bytes, "image/png")

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
        "template_name": preset_info["name"] if preset_info else (f"Layout from a {ref.get('competitor')} ad" if layout_bytes else (TEMPLATES.get(template_id, {}).get("name") or "Meta Creative")),
        "preset_id": preset_id,
        "preset_name": preset_info["name"] if preset_info else blueprint.get("preset_name"),
        "preset_movement": preset_info["movement"] if preset_info else blueprint.get("preset_movement"),
        "brand_mode": mode,
        "brand_name": brand_name,
        "image_url": image_url,
        "filename": filename,
        "aspect_ratio": aspect_ratio,
        "width": target_w,
        "height": target_h,
        "model_used": model_meta["id"],
        "model_label": model_meta["label"],
        "visual_prompt": visual_prompt,
        "has_product_reference": bool(product_bytes),
    }
