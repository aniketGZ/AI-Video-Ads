"""
A6 Static Prompt Writer & A7 Video Script Writer

A6: Static Prompt Writer
- Takes StaticBrief objects from A5 Creative Strategist.
- The copy (headline, CTA, primary text, meta headline) is used WORD FOR WORD.
- Writes one prompt per aspect ratio (1:1, 4:5, 9:16).
- Combines product lock v2 verbatim, brand kit, logo rules, and layout templates/references.
- Runs in parallel batches of 5 briefs.
- Implements rewrite_static() for A8 critic loops.

A7: Video Script Writer
- Takes VideoBrief objects from A5 Creative Strategist.
- The hook and voiceover are used WORD FOR WORD.
- Expands the brief into a beat-by-beat timeline script (hook -> demo/proof -> CTA).
- Writes the Omni Flash 1.1 prompt beat-by-beat using <IMAGE_REF_i> product locks.
- Runs in parallel batches of 5 briefs.
- Implements rewrite_video() for A8 critic loops.
"""

import os
import re
import json
import asyncio
import logging
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from google import genai
from google.genai import types

from ad_templates import (
    TEMPLATES,
    MAX_CTA_WORDS,
    detect_brand_mode,
    templates_for_mode,
    resolve_template_id,
    short_headline,
)
from meta_creative_engine import NO_FABRICATED_CLAIMS_RULE, build_native_in_image_ad_prompt
from creative_strategist import StaticBrief, VideoBrief

logger = logging.getLogger(__name__)

TEXT_MODEL = "gemini-3.6-flash"
VIDEO_DURATION_S = 10
MAX_VIDEO_PRODUCTS = 4


# ---------------------------------------------------------------------------
# Schemas for Model Calls
# ---------------------------------------------------------------------------
class StaticSceneDetail(BaseModel):
    brief_id: str
    scene_description: str = Field(description="Detailed art direction for the visual scene: props, setting, lighting, composition")
    template_id: str = Field(default="", description="Chosen layout template ID if no competitor reference used")
    layout_notes: str = Field(description="Specific placement instruction for wordmark, headline, product and CTA")


class StaticBatchArtDirection(BaseModel):
    scenes: List[StaticSceneDetail]


class VideoBeatExpanded(BaseModel):
    time: str = Field(description="Timestamp, e.g. '0-3s', '3-7s', '7-10s'")
    visual: str = Field(description="Camera action, subject movement, and product interaction")
    on_screen_text: str = Field(default="", description="Overlay text, <= 5 words")
    audio: str = Field(description="Sound effect, ambient track, or spoken VO segment")


class VideoScriptDetail(BaseModel):
    brief_id: str
    expanded_beats: List[VideoBeatExpanded] = Field(description="3-4 detailed beats covering 0-10 seconds")
    direction: str = Field(description="Cinematography and performance direction for Omni Flash (camera moves, lighting, pacing)")


class VideoBatchScripts(BaseModel):
    scripts: List[VideoScriptDetail]


# ---------------------------------------------------------------------------
# Helper: Build Omni Flash Prompt
# ---------------------------------------------------------------------------
def build_omni_prompt(
    brand_name: str,
    product_name: str,
    featured_products: List[Dict[str, Any]],
    casting_description: str,
    brand_kit: Dict[str, Any],
    beats: List[Dict[str, Any]],
    voiceover: str,
    direction: str,
    language: str = "en",
    has_uploaded_images: bool = True,
    duration_s: int = VIDEO_DURATION_S,
) -> str:
    """Produces the exact Omni Flash 1.1 prompt with <IMAGE_REF_i> bindings."""
    prod_label = " and ".join(p["name"] for p in featured_products) if featured_products else product_name
    lines = [
        f"{duration_s}-second vertical 9:16 Meta Reels ad for {prod_label} by {brand_name}. Photoreal, shot on high-end camera, natural physical motion.",
    ]

    if featured_products:
        lines.append(
            "PRODUCT LOCK: Every product on screen is one of these real products, reproduced exactly as in its "
            "reference image (same packaging silhouette, typography, surface finishes, colors, and pump/cap). "
            "Never invent variants or swap with generic containers."
        )
        for i, p in enumerate(featured_products):
            lines.append(f"- <IMAGE_REF_{i}> is {p.get('lock', p.get('name'))}")
    elif has_uploaded_images:
        lines.append(
            f"PRODUCT LOCK: Reference images show the real {product_name}. Reproduce it exactly with the same shape, "
            "materials and label artwork."
        )

    if casting_description:
        lines.append(f"CASTING: {casting_description}")

    if brand_kit:
        mood = brand_kit.get("visual_mood", "")
        primary = brand_kit.get("primary_hex", "")
        accent = brand_kit.get("accent_hex", "")
        bg = brand_kit.get("background_hex", "")
        lines.append(
            f"BRAND LOOK: {mood}; color accents in brand palette {primary}, {accent}, {bg} (props, wardrobe, set), "
            "never overpowering the product."
        )

    lines.append("TIMELINE:")
    for b in beats or []:
        text = f' On-screen text: "{b.get("on_screen_text")}".' if b.get("on_screen_text") else ""
        lines.append(f"- {b.get('time')}: {b.get('visual')}{text} Audio: {b.get('audio')}")

    if voiceover:
        spoken = f"spoken in {language}, " if language and language.lower() not in ("english", "en") else ""
        lines.append(f'VOICEOVER ({spoken}natural conversational tone, matches timeline): "{voiceover}"')

    if direction:
        lines.append(f"DIRECTION: {direction}")

    lines.append(
        "AVOID: competitor logos, hallucinated pack text, illegible on-screen text, distorted hands, generic 3D renders."
    )
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# [A6] Static Prompt Writer
# ---------------------------------------------------------------------------
class StaticPromptWriter:
    """Takes StaticBriefs from A5, keeps copy verbatim, and crafts multi-aspect prompts."""

    def __init__(self, client: genai.Client):
        self.client = client

    async def write_batch(
        self,
        briefs: List[StaticBrief],
        brand_profile: Dict[str, Any],
        references: Dict[str, Any],
        style_tokens: Optional[Dict[str, Any]] = None,
        default_aspect: str = "4:5",
    ) -> List[Dict[str, Any]]:
        """Processes a batch of up to 5 static briefs in one model call."""
        if not briefs:
            return []

        products = brand_profile.get("products", [])
        brand_name = brand_profile.get("brand_name", "")
        category = brand_profile.get("product_category", "")
        business_type = brand_profile.get("business_type", "physical_product")
        brand_kit = brand_profile.get("brand_kit", {})
        logo = brand_profile.get("logo", {})
        has_product_ref = bool(products) and business_type == "physical_product"
        mode = detect_brand_mode(business_type, category, has_product_ref)
        templates = templates_for_mode(mode)
        template_menu = "\n".join(f"- {t['id']}: {t['name']} ({', '.join(t['frameworks'])})" for t in templates)

        # Build prompt for LLM art direction
        brief_summaries = []
        for b in briefs:
            prod_name = products[b.product_index]["name"] if 0 <= b.product_index < len(products) else brand_profile.get("product_name", "")
            brief_summaries.append(
                f"[{b.id}] Framework: {b.framework} | Angle: {b.angle} | Product: {prod_name}\n"
                f"  Headline: \"{b.copy.image_headline}\" | CTA: \"{b.copy.cta}\"\n"
                f"  Scene Direction from Strategist: {b.scene_direction}\n"
                f"  Concept Sources: {', '.join(b.concept_source) or 'None'}"
            )

        instructions = (
            f"You are the Lead Art Director for {brand_name} ({category}).\n"
            "For each of the following static ad briefs, write precise visual scene art direction.\n"
            "THE COPY IS FINAL AND MUST NOT BE CHANGED.\n\n"
            f"BRAND KIT: Primary {brand_kit.get('primary_hex')}, Accent {brand_kit.get('accent_hex')}, Mood {brand_kit.get('visual_mood')}\n"
            f"AVAILABLE TEMPLATES:\n{template_menu}\n\n"
            f"BRIEFS TO ART DIRECT:\n" + "\n\n".join(brief_summaries) + "\n\n"
            "Return a scene_description and layout_notes for each brief."
        )

        try:
            response = await asyncio.to_thread(
                self.client.models.generate_content,
                model=TEXT_MODEL,
                contents=instructions,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=StaticBatchArtDirection,
                ),
            )
            data = json.loads(response.text)
            art_map = {item["brief_id"]: item for item in data.get("scenes", [])}
        except Exception as e:
            logger.warning(f"[A6/Writer] Art direction call failed, fallback to brief direction: {e}")
            art_map = {}

        results: List[Dict[str, Any]] = []
        for idx, brief in enumerate(briefs, start=1):
            art = art_map.get(brief.id, {})
            scene_desc = art.get("scene_description") or brief.scene_direction
            chosen_tmpl = art.get("template_id") or ""

            # Resolve product
            prod = products[brief.product_index] if 0 <= brief.product_index < len(products) else None
            prod_name = prod["name"] if prod else (brand_profile.get("product_name") or "")
            prod_lock = prod["lock"] if prod else (brand_profile.get("product_visual_description") or "")
            prod_img_idx = prod["index"] if prod else 0

            # Resolve competitor reference if cited in concept_source
            ref_match = None
            image_refs = references.get("image", {})
            for src in brief.concept_source:
                clean_src = src.strip("[] ").upper()
                if clean_src in image_refs:
                    ref_match = image_refs[clean_src]
                    break

            # Build blueprint
            headline_clean = short_headline(brief.copy.image_headline)
            cta_clean = short_headline(brief.copy.cta, MAX_CTA_WORDS) or "Shop Now"
            meta_headline_clean = brief.copy.meta_headline or headline_clean

            blueprint = {
                "creative_id": brief.id,
                "framework_key": brief.framework,
                "framework_name": brief.angle,
                "template_id": chosen_tmpl,
                "headline": meta_headline_clean,
                "image_headline": headline_clean,
                "cta": cta_clean,
                "primary_text": brief.copy.primary_text,
                "visual_prompt": scene_desc,
                "callout_points": [],
                "comparison_theirs": "",
                "target_audience_resonance": brief.angle,
            }
            blueprint["template_id"] = resolve_template_id(blueprint, mode)

            if ref_match:
                blueprint["reference"] = {k: ref_match.get(k) for k in (
                    "ref_id", "run_id", "media_path", "image_url", "competitor", "angle", "composition",
                    "product_presence", "people", "setting", "lighting", "text_overlay_density", "typography_feel",
                )}
                blueprint["concept"] = f"Layout inspired by {ref_match.get('competitor')}"

            # Generate prompts for multiple aspect ratios
            aspect_prompts = {}
            for asp in ("1:1", "4:5", "9:16"):
                aspect_prompts[asp] = build_native_in_image_ad_prompt(
                    blueprint=blueprint,
                    brand_name=brand_name,
                    product_name=prod_name,
                    product_category=category,
                    target_audience_persona=(brand_profile.get("bullseye_target") or {}).get("snapshot", ""),
                    aspect_ratio=asp,
                    product_visual_description=prod_lock,
                    color_palette=brand_profile.get("color_palette") or "",
                    business_type=business_type,
                    has_product_ref=has_product_ref,
                    setting=brand_profile.get("setting") or "",
                    talent=(brand_profile.get("bullseye_target") or {}).get("casting_description", ""),
                    brand_kit=brand_kit,
                    has_logo=bool(logo.get("path")),
                    logo_tone=logo.get("tone") or "dark",
                    has_layout_ref=bool(ref_match),
                )

            results.append({
                "id": brief.id,
                "brief_id": brief.id,
                "angle_name": brief.angle,
                "stage": brief.stage,
                "framework": brief.framework,
                "concept_source": brief.concept_source,
                "product_name": prod_name,
                "product_lock": prod_lock,
                "product_image_index": prod_img_idx,
                "proof_ids": brief.proof_ids,
                "template_name": f"Layout from {ref_match['competitor']}" if ref_match else TEMPLATES[blueprint["template_id"]]["name"],
                "reference": {"competitor": ref_match["competitor"], "image_url": ref_match["image_url"]} if ref_match else None,
                "blueprint": blueprint,
                "prompt_preview": aspect_prompts.get(default_aspect, aspect_prompts["4:5"]),
                "prompts_by_aspect": aspect_prompts,
                "checks": {
                    "proof_ids": brief.proof_ids,
                    "unknown_proof_ids": [],
                    "avoid_words": [],
                },
            })

        return results

    async def rewrite_static(
        self,
        brief: StaticBrief,
        current_ad: Dict[str, Any],
        critic_notes: str,
        brand_profile: Dict[str, Any],
        references: Dict[str, Any],
        aspect: str = "4:5",
    ) -> Dict[str, Any]:
        """Rewrites a single static ad that failed critic check based on critic notes."""
        prompt = (
            f"You are the Art Director fixing an image ad prompt that failed review.\n"
            f"Ad ID: {current_ad.get('id')}\n"
            f"Current Visual Prompt: {current_ad.get('blueprint', {}).get('visual_prompt')}\n"
            f"CRITIC'S REWRITE NOTE: {critic_notes}\n\n"
            "Rewrite the visual scene description to fix every issue mentioned by the critic.\n"
            "Keep the scene realistic, brand-aligned, and suitable for commercial Meta advertising.\n"
            "Return only the updated scene description text."
        )

        try:
            resp = await asyncio.to_thread(
                self.client.models.generate_content,
                model=TEXT_MODEL,
                contents=prompt,
            )
            new_scene = resp.text.strip()
        except Exception as e:
            logger.warning(f"[A6/Writer] Rewrite call failed: {e}")
            new_scene = current_ad.get("blueprint", {}).get("visual_prompt", "") + " " + critic_notes

        updated = dict(current_ad)
        updated["blueprint"]["visual_prompt"] = new_scene

        # Rebuild prompt preview
        prod_lock = current_ad.get("product_lock", "")
        prod_name = current_ad.get("product_name", "")
        brand_kit = brand_profile.get("brand_kit", {})
        logo = brand_profile.get("logo", {})

        aspect_prompts = {}
        for asp in ("1:1", "4:5", "9:16"):
            aspect_prompts[asp] = build_native_in_image_ad_prompt(
                blueprint=updated["blueprint"],
                brand_name=brand_profile.get("brand_name", ""),
                product_name=prod_name,
                product_category=brand_profile.get("product_category", ""),
                target_audience_persona=(brand_profile.get("bullseye_target") or {}).get("snapshot", ""),
                aspect_ratio=asp,
                product_visual_description=prod_lock,
                color_palette=brand_profile.get("color_palette") or "",
                business_type=brand_profile.get("business_type", "physical_product"),
                has_product_ref=bool(prod_lock),
                setting=brand_profile.get("setting") or "",
                talent=(brand_profile.get("bullseye_target") or {}).get("casting_description", ""),
                brand_kit=brand_kit,
                has_logo=bool(logo.get("path")),
                logo_tone=logo.get("tone") or "dark",
                has_layout_ref=bool(current_ad.get("reference")),
            )

        updated["prompts_by_aspect"] = aspect_prompts
        updated["prompt_preview"] = aspect_prompts.get(aspect, aspect_prompts["4:5"])
        return updated


# ---------------------------------------------------------------------------
# [A7] Video Script Writer
# ---------------------------------------------------------------------------
class VideoScriptWriter:
    """Takes VideoBriefs from A5, expands into beat scripts, and builds Omni Flash prompts."""

    def __init__(self, client: genai.Client):
        self.client = client

    async def write_batch(
        self,
        briefs: List[VideoBrief],
        brand_profile: Dict[str, Any],
        references: Dict[str, Any],
        style_tokens: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Processes a batch of up to 5 video briefs in one model call."""
        if not briefs:
            return []

        products = brand_profile.get("products", [])
        brand_name = brand_profile.get("brand_name", "")
        brand_kit = brand_profile.get("brand_kit", {})
        bs = brand_profile.get("bullseye_target", {})
        casting = bs.get("casting_description", "")
        markets = brand_profile.get("markets", [])
        lang = markets[0].get("language", "en") if markets and isinstance(markets, list) else "en"

        brief_summaries = []
        for b in briefs:
            featured = [products[p]["name"] for p in b.product_indexes if 0 <= p < len(products)]
            brief_summaries.append(
                f"[{b.id}] Format: {b.format} | Angle: {b.angle} | Products: {', '.join(featured) or 'Hero Product'}\n"
                f"  Hook Line (verbatim): \"{b.copy.hook_line}\"\n"
                f"  Voiceover (verbatim): \"{b.copy.voiceover}\"\n"
                f"  Input Beats: {'; '.join(f'{beat.time}: {beat.visual}' for beat in b.beats)}"
            )

        instructions = (
            f"You are the Commercial Video Director for {brand_name}.\n"
            "For each 10-second vertical video brief below, expand the beats into a full cinematography production script.\n"
            "THE HOOK LINE AND VOICEOVER ARE FINAL AND MUST BE USED VERBATIM.\n\n"
            f"CASTING: {casting}\n"
            f"BRIEFS TO EXPAND:\n" + "\n\n".join(brief_summaries) + "\n\n"
            "Format: 3-4 beats covering 0-10 seconds (e.g. 0-3s, 3-7s, 7-10s). Provide detailed visual action and camera motion."
        )

        try:
            response = await asyncio.to_thread(
                self.client.models.generate_content,
                model=TEXT_MODEL,
                contents=instructions,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=VideoBatchScripts,
                ),
            )
            data = json.loads(response.text)
            scripts_map = {item["brief_id"]: item for item in data.get("scripts", [])}
        except Exception as e:
            logger.warning(f"[A7/Writer] Video script batch failed, using brief beats: {e}")
            scripts_map = {}

        results: List[Dict[str, Any]] = []
        for brief in briefs:
            script_detail = scripts_map.get(brief.id, {})
            expanded_beats_data = script_detail.get("expanded_beats", [])

            if expanded_beats_data:
                beats = [b if isinstance(b, dict) else b.model_dump() for b in expanded_beats_data]
            else:
                beats = [b.model_dump() for b in brief.beats]

            direction = script_detail.get("direction", f"{brief.format.upper()} video ad with natural phone/cinema camera motion.")

            # Featured products
            featured = [products[p] for p in brief.product_indexes if 0 <= p < len(products)]
            ref_image_indexes = [p["index"] for p in featured]

            # Video reference if any
            vref_match = None
            if brief.hook_mechanic_from:
                clean_src = brief.hook_mechanic_from.strip("[] ").upper()
                vref_match = references.get("video", {}).get(clean_src)

            omni_prompt_text = build_omni_prompt(
                brand_name=brand_name,
                product_name=brand_profile.get("product_name", ""),
                featured_products=featured,
                casting_description=casting,
                brand_kit=brand_kit,
                beats=beats,
                voiceover=brief.copy.voiceover,
                direction=direction,
                language=lang,
                has_uploaded_images=bool(products),
                duration_s=VIDEO_DURATION_S,
            )

            results.append({
                "id": brief.id,
                "brief_id": brief.id,
                "angle_name": brief.angle,
                "stage": brief.stage,
                "format": brief.format,
                "hook_line": brief.copy.hook_line,
                "voiceover": brief.copy.voiceover,
                "product_names": [p["name"] for p in featured],
                "ref_image_indexes": ref_image_indexes,
                "proof_ids": brief.proof_ids,
                "duration_s": VIDEO_DURATION_S,
                "aspect_ratio": "9:16",
                "beats": beats,
                "direction": direction,
                "omni_prompt": omni_prompt_text,
                "reference": {"competitor": vref_match["competitor"], "hook": vref_match["hook"]} if vref_match else None,
                "checks": {
                    "proof_ids": brief.proof_ids,
                    "unknown_proof_ids": [],
                    "avoid_words": [],
                },
            })

        return results

    async def rewrite_video(
        self,
        brief: VideoBrief,
        current_ad: Dict[str, Any],
        critic_notes: str,
        brand_profile: Dict[str, Any],
        references: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Rewrites a single video ad that failed critic check based on critic notes."""
        prompt = (
            f"You are the Commercial Video Director revising a 10s video ad.\n"
            f"Ad ID: {current_ad.get('id')}\n"
            f"Voiceover: \"{current_ad.get('voiceover')}\"\n"
            f"Current Direction: {current_ad.get('direction')}\n"
            f"CRITIC'S REWRITE NOTE: {critic_notes}\n\n"
            "Revise the timeline beats and direction to resolve the critic's concerns.\n"
            "Ensure the hook is visually arresting, pacing fits 10 seconds, and product interaction is realistic."
        )

        try:
            resp = await asyncio.to_thread(
                self.client.models.generate_content,
                model=TEXT_MODEL,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=VideoScriptDetail,
                ),
            )
            data = json.loads(resp.text)
            beats = data.get("expanded_beats", current_ad.get("beats", []))
            direction = data.get("direction", current_ad.get("direction", ""))
        except Exception as e:
            logger.warning(f"[A7/Writer] Video rewrite call failed: {e}")
            beats = current_ad.get("beats", [])
            direction = current_ad.get("direction", "") + " " + critic_notes

        updated = dict(current_ad)
        updated["beats"] = beats
        updated["direction"] = direction

        # Rebuild omni prompt
        products = brand_profile.get("products", [])
        featured = [products[p] for p in brief.product_indexes if 0 <= p < len(products)]
        brand_name = brand_profile.get("brand_name", "")
        brand_kit = brand_profile.get("brand_kit", {})
        casting = (brand_profile.get("bullseye_target") or {}).get("casting_description", "")
        markets = brand_profile.get("markets", [])
        lang = markets[0].get("language", "en") if markets and isinstance(markets, list) else "en"

        updated["omni_prompt"] = build_omni_prompt(
            brand_name=brand_name,
            product_name=brand_profile.get("product_name", ""),
            featured_products=featured,
            casting_description=casting,
            brand_kit=brand_kit,
            beats=beats,
            voiceover=current_ad.get("voiceover", ""),
            direction=direction,
            language=lang,
            has_uploaded_images=bool(products),
            duration_s=VIDEO_DURATION_S,
        )
        return updated
