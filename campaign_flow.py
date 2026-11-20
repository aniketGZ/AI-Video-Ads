"""
Three-step campaign flow used by the Campaign tab:

  1. Brand URL + reference images from the user
  2. Brand intelligence: sentiment, audience, demographics and one bullseye target,
     grounded in the brand site, the reference images and (optionally) a competitor-agent run
  3. Ad prompts: full in-image Meta ads (layout template, headline, CTA, design) and
     Omni Flash video prompts

Rendering reuses the existing endpoints: images go through
/api/campaign/meta-creative-suite/render-one, videos through /api/studio/generate-video.
"""
import os
import re
import uuid
import json
import asyncio
import logging
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from urllib.parse import urlparse

from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Header
from pydantic import BaseModel
from google import genai
from google.genai import types

from media_utils import GENERATED_DIR, save_generated_media, IMAGE_EXTS, MAX_IMAGE_BYTES, read_upload, is_public_http_url
from ad_templates import (
    TEMPLATES,
    MAX_CTA_WORDS,
    detect_brand_mode,
    templates_for_mode,
    resolve_template_id,
    short_headline,
)
from meta_creative_engine import NO_FABRICATED_CLAIMS_RULE, build_native_in_image_ad_prompt
from competitor_ad_engine import load_competitor_run_summary, load_reference_ads, clean_market
from brand_research import crawl_brand_site, crawl_digest, check_proof_bank, appears_in, voice_flags
from brand_assets import find_brand_logo, save_uploaded_logo
from media_utils import resolve_generated_path, hex_to_color_name, sanitize_video_prompt, NO_END_SCREEN_LINE, NO_END_SCREEN_AVOID
from creative_strategist import CreativeStrategist, CampaignMatrix
from creative_director import CreativeDirector
from prompt_writers import StaticPromptWriter, VideoScriptWriter

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/flow", tags=["Campaign Flow"])

TEXT_MODEL = "gemini-3.6-flash"
MAX_REFERENCE_IMAGES = 4
FRAMEWORK_KEYS = ["problem_solution", "feature_callout", "social_proof", "us_vs_them", "lifestyle_hero"]
VIDEO_DURATION_S = 15
DEFAULT_IMAGE_PROMPTS = 25
DEFAULT_VIDEO_PROMPTS = 25
MAX_PROMPTS = 50
# Prompts are written in parallel batches; each batch owns one strategic focus so the 25 + 25 stay distinct
PROMPT_BATCH_SIZE = 5
BATCH_FOCUSES = [
    "the audience's core pain points: show the problem, then the relief",
    "desires and aspiration: the better day or result the bullseye target gets",
    "objections and doubts: answer each hesitation with a benefit or a stated proof point",
    "buying triggers and everyday moments: situational hooks tied to the trigger moment",
    "competitor white space: angles and visual styles competitors are not using",
]


# ---------------------------------------------------------------------------
# Step 2 schema: brand intelligence
# ---------------------------------------------------------------------------
class BrandSentiment(BaseModel):
    tone: str
    emotional_promise: str
    customer_perception: str
    voice_keywords: List[str]


class Demographics(BaseModel):
    age_range: str
    gender: str
    geography: str
    income_level: str
    lifestyle: str
    cultural_context: str


class AudienceInsight(BaseModel):
    segments: List[str]
    pain_points: List[str]
    desires: List[str]
    objections: List[str]
    buying_triggers: List[str]


class BullseyeTarget(BaseModel):
    persona_name: str
    snapshot: str
    age: str
    gender: str
    location: str
    occupation: str
    trigger_moment: str
    core_pain: str
    core_desire: str
    scroll_habits: str
    casting_description: str


class CompetitorTakeaways(BaseModel):
    winning_patterns: List[str]
    saturated_angles: List[str]
    whitespace: List[str]


class BrandKit(BaseModel):
    primary_hex: str
    accent_hex: str
    background_hex: str
    text_hex: str
    supporting_hexes: List[str]
    headline_type: str
    body_type: str
    visual_mood: str


class SurfaceColour(BaseModel):
    surface: str
    hex: str


class ProductLock(BaseModel):
    image_number: int
    product_name: str
    product_type: str
    shape_and_size: str
    proportions: str
    colours: str
    surface_colours: List[SurfaceColour]
    materials_and_finish: str
    closure_or_dispenser: str
    label_layout: str
    label_text: str
    distinctive_details: str
    visible_views: str
    never_do: List[str]


class ProductCatalog(BaseModel):
    products: List[ProductLock]


class BrandIntelligence(BaseModel):
    brand_name: str
    product_name: str
    product_category: str
    business_type: str
    product_visual_description: str
    key_benefits: List[str]
    color_palette: str
    brand_kit: BrandKit
    visual_style: str
    setting: str
    brand_sentiment: BrandSentiment
    demographics: Demographics
    audience: AudienceInsight
    bullseye_target: BullseyeTarget
    competitor_takeaways: CompetitorTakeaways


# Second structured pass of step 2: how the brand talks, what it can prove, what customers say
class BrandVoice(BaseModel):
    tone: str
    address_as: str
    reading_level: str
    sentence_style: str
    uses_emoji: bool
    use_words: List[str]
    avoid_words: List[str]
    sample_lines: List[str]


class ProofClaim(BaseModel):
    claim: str
    type: str
    source_url: str


class ReviewTheme(BaseModel):
    theme_type: str
    summary: str
    customer_phrases: List[str]
    mentions: int
    sources: List[str]


class MarketInfo(BaseModel):
    country_code: str
    country: str
    language: str
    currency: str
    evidence: str


class BrandVoiceProof(BaseModel):
    voice: BrandVoice
    proof_bank: List[ProofClaim]
    review_themes: List[ReviewTheme]
    review_rating: str
    markets: List[MarketInfo]
    aesthetic_keywords: List[str]


# ---------------------------------------------------------------------------
# Step 3 schema: ad prompts
# ---------------------------------------------------------------------------
class ImageAdPrompt(BaseModel):
    product_index: int
    reference_id: str
    concept: str
    angle_name: str
    framework_key: str
    template_id: str
    image_headline: str
    cta: str
    meta_headline: str
    primary_text: str
    scene: str
    benefit: str
    contrast_before: str
    proof_ids: List[str]
    rationale: str


class VideoBeat(BaseModel):
    time: str
    visual: str
    on_screen_text: str
    audio: str


class VideoAdPrompt(BaseModel):
    product_indexes: List[int]
    reference_id: str
    angle_name: str
    hook_line: str
    voiceover: str
    beats: List[VideoBeat]
    video_prompt: str
    proof_ids: List[str]
    rationale: str


class CampaignPrompts(BaseModel):
    image_ads: List[ImageAdPrompt]
    video_ads: List[VideoAdPrompt]


class PromptsRequest(BaseModel):
    intelligence: Dict[str, Any]
    has_reference_images: bool = False
    image_count: int = DEFAULT_IMAGE_PROMPTS
    video_count: int = DEFAULT_VIDEO_PROMPTS
    aspect_ratio: str = "4:5"
    video_duration_s: int = VIDEO_DURATION_S
    meta_refs: Optional[Dict[str, Any]] = None
    style_tokens: Optional[Dict[str, Any]] = None
    campaign_matrix: Optional[Dict[str, Any]] = None
    preset_id: Optional[str] = None


class StrategyRequest(BaseModel):
    intelligence: Dict[str, Any]
    meta_refs: Optional[Dict[str, Any]] = None
    style_tokens: Optional[Dict[str, Any]] = None
    target_statics: int = DEFAULT_IMAGE_PROMPTS
    target_videos: int = DEFAULT_VIDEO_PROMPTS
    video_duration_s: int = VIDEO_DURATION_S


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _require_client(api_key: Optional[str]) -> genai.Client:
    key = (api_key or os.environ.get("GEMINI_API_KEY") or "").strip()
    if not key:
        raise HTTPException(status_code=400, detail="A Gemini API key is required. Add it under API Keys.")
    return genai.Client(api_key=key)


def _normalize_url(url: str) -> str:
    url = (url or "").strip()
    if not url:
        raise HTTPException(status_code=400, detail="Please enter a brand or product URL.")
    if not url.lower().startswith(("http://", "https://")):
        url = "https://" + url
    if not is_public_http_url(url):
        raise HTTPException(status_code=400, detail="The URL must be a public http(s) web address.")
    return url


def _bullets(items: Any, limit: int = 8) -> str:
    return "\n".join(f"- {x}" for x in (items or [])[:limit] if x) or "- (none)"


def _competitor_brief(comp: Optional[dict]) -> str:
    if not comp:
        return "No competitor research is available. Leave competitor_takeaways lists empty."
    demo = comp.get("demographics") or {}
    market = comp.get("market") or {}
    head = (
        f"Competitors analysed: {', '.join(comp.get('competitors') or [])}\n"
        f"Live competitor ads captured from the Meta Ad Library: {comp.get('total_ads', 0)} "
        f"(signal: {comp.get('signal')}; ranked by days running)\n"
        + (f"Brand's main market (read from its site): {market.get('country')} · {market.get('language')} · "
           f"{market.get('currency')}\n" if market.get("country") else "")
        + f"Competitor headlines and hooks currently running:\n{_bullets(comp.get('winning_hooks'))}\n"
        f"Competitor-agent demographic read: {json.dumps(demo, ensure_ascii=False)}\n"
    )
    syn = comp.get("synthesis") or {}
    if not syn:
        # Runs from before meta_refs.json only have the markdown insights
        return head + f"Agent insights (patterns, saturated territory, white space):\n{comp.get('insights_text') or '(none)'}"
    patterns = [f"[{w.get('kind')}] {w.get('pattern')} — {w.get('why')} (evidence: {', '.join(w.get('evidence') or [])})"
                for w in syn.get("winning_patterns") or [] if isinstance(w, dict)]
    per_comp = [f"{c.get('competitor')}: {', '.join(c.get('dominant_angles') or [])}; formats {', '.join(c.get('formats') or [])}; "
                f"{c.get('visual_signature') or ''}" for c in syn.get("per_competitor") or [] if isinstance(c, dict)]
    return (
        head
        + f"Per competitor:\n{_bullets(per_comp, 10)}\n"
        f"Winning patterns (weighted by days running):\n{_bullets(patterns, 15)}\n"
        f"Saturated territory:\n{_bullets(syn.get('saturated'), 10)}\n"
        f"White space:\n{_bullets(syn.get('whitespace'), 10)}"
    )


PRODUCT_LOCK_DIR = os.path.join("data", "product_locks")
MAX_VIDEO_PRODUCTS = MAX_REFERENCE_IMAGES  # a video may feature every uploaded product


def _lock_text(p: Dict[str, Any]) -> str:
    """One-paragraph product lock used verbatim in image and video prompts."""
    fields = [
        ("shape and size", "shape_and_size"),
        ("proportions", "proportions"),
        ("colours", "colours"),
        ("materials and finish", "materials_and_finish"),
        ("closure or dispenser", "closure_or_dispenser"),
        ("label layout", "label_layout"),
        ("label text exactly as printed", "label_text"),
        ("distinctive details", "distinctive_details"),
    ]
    parts = [f"{p.get('product_name')} ({p.get('product_type')})"]
    for label, key in fields:
        value = (p.get(key) or "").strip()
        if value:
            parts.append(f'{label}: "{value}"' if key == "label_text" else f"{label}: {value}")
    surfaces = [f"{c.get('surface')} {c.get('hex')}" for c in p.get("surface_colours") or [] if isinstance(c, dict) and c.get("hex")]
    if surfaces:
        parts.append(f"exact colours: {', '.join(surfaces)}")
    never = [n for n in p.get("never_do") or [] if n]
    if never:
        parts.append(f"never: {'; '.join(never)}")
    return "; ".join(parts) + "."


async def _describe_products(client: genai.Client, image_parts: List[Any]) -> List[Dict[str, Any]]:
    """One focused vision pass over the uploads: a separate product lock per image, in upload order."""
    if not image_parts:
        return []
    contents: List[Any] = []
    for i, part in enumerate(image_parts, start=1):
        contents += [f"Image {i}:", part]
    contents.append(
        f"You are a packaging analyst. For each of the {len(image_parts)} images above, describe the product it shows "
        "so an image or video model can reproduce it exactly without seeing the photo. Return one entry per image, "
        "image_number matching the image label. If one image shows several products (a kit), describe them together "
        "as one entry.\n"
        "- label_text: every word printed on the pack, copied exactly with the same spelling, capitalisation and line "
        "breaks as ' / '.\n"
        "- proportions: width to height ratio of the pack as seen (e.g. 'about 1:3, tall and slim') and how big each "
        "label element is relative to the pack.\n"
        "- surface_colours: one entry per visible surface (body, cap, label background, logo, main text, accent) with "
        "its hex code sampled from the photo.\n"
        "- visible_views: which sides are visible (e.g. 'front only', 'front and left side').\n"
        "- never_do: 2-5 specific mistakes a generator is likely to make with this pack and must not "
        "(e.g. 'cap is matte black, never glossy', 'no second label on the back', 'logo is not centred').\n"
        "Describe only what is visible; never guess hidden sides or invent text. If you cannot see an image, set its "
        "product_name to UNREADABLE and leave the other fields empty."
    )
    response = await asyncio.to_thread(
        client.models.generate_content,
        model=TEXT_MODEL,
        contents=contents,
        config=types.GenerateContentConfig(response_mime_type="application/json", response_schema=ProductCatalog),
    )
    found = {p.get("image_number"): p for p in (json.loads(response.text).get("products") or [])}
    return [found.get(i) for i in range(1, len(image_parts) + 1)]


def _save_product_lock(image_path: str, product: Dict[str, Any]) -> None:
    """Persist the lock next to its image name so a render can always be traced to the analysis it used."""
    try:
        os.makedirs(PRODUCT_LOCK_DIR, exist_ok=True)
        stem = os.path.splitext(os.path.basename(image_path))[0]
        with open(os.path.join(PRODUCT_LOCK_DIR, f"{stem}.json"), "w", encoding="utf-8") as f:
            json.dump(product, f, ensure_ascii=False, indent=2)
    except OSError as e:
        logger.warning(f"[flow/analyze] could not save product lock for {image_path}: {e}")


def _products(intel: Dict[str, Any]) -> List[Dict[str, Any]]:
    return [p for p in (intel.get("products") or []) if isinstance(p, dict)]


def _pick_products(raw: Any, n_products: int, fallback: int, limit: int) -> List[int]:
    """Valid, unique product indexes chosen by the writer; spreads ads across products when it chose none."""
    if not n_products:
        return []
    picked: List[int] = []
    for i in raw if isinstance(raw, list) else [raw]:
        if isinstance(i, int) and 0 <= i < n_products and i not in picked:
            picked.append(i)
    return picked[:limit] or [fallback % n_products]


def _references(intel: Dict[str, Any]) -> Dict[str, Dict[str, Dict[str, Any]]]:
    """Competitor reference ads keyed by the short ids the prompt writer uses (R1.. images, V1.. videos)."""
    refs = intel.get("references") or {}
    return {
        "image": {f"R{i}": r for i, r in enumerate(refs.get("image") or [], start=1)},
        "video": {f"V{i}": r for i, r in enumerate(refs.get("video") or [], start=1)},
    }


def _reference_brief(intel: Dict[str, Any]) -> str:
    refs = _references(intel)
    lines = []
    if refs["image"]:
        lines.append("IMAGE REFERENCE ADS (live competitor ads from the Meta Ad Library, best performers first):")
        for rid, r in refs["image"].items():
            lines.append(
                f"[{rid}] {r['competitor']} · {r['performance_signal']}, {r['days_running']} days live · angle: {r['angle']} · "
                f"composition: {r['composition']} · product: {r['product_presence']} · people: {r['people']} · "
                f"setting: {r['setting']} · lighting: {r['lighting']} · text on image: {r['text_overlay_density']} "
                f"({r['typography_feel']}) · hook: {r['hook']} · why it works: {r['why_it_works']}"
            )
    if refs["video"]:
        lines.append("VIDEO REFERENCE ADS:")
        for rid, r in refs["video"].items():
            beats = "; ".join(f"{b.get('t')} {b.get('beat')}: {b.get('shot')}" for b in r.get("structure") or [] if isinstance(b, dict))
            lines.append(f"[{rid}] {r['competitor']} · {r['performance_signal']}, {r['days_running']} days · angle: {r['angle']} · "
                         f"hook: {r['hook']} · beats: {beats} · why it works: {r['why_it_works']}")
    return "\n".join(lines)


def _brand_kit_line(intel: Dict[str, Any]) -> str:
    kit = intel.get("brand_kit") or {}
    if not kit:
        return ""
    return (
        f"BRAND KIT: primary {kit.get('primary_hex')}, CTA accent {kit.get('accent_hex')}, background {kit.get('background_hex')}, "
        f"text {kit.get('text_hex')}, supporting {', '.join(kit.get('supporting_hexes') or [])}; headline type: {kit.get('headline_type')}; "
        f"body type: {kit.get('body_type')}; mood: {kit.get('visual_mood')}\n"
    )


def _primary_language(intel: Dict[str, Any]) -> str:
    markets = intel.get("markets") or []
    return (markets[0].get("language") if markets and isinstance(markets[0], dict) else "") or ""


def _proof_lines(intel: Dict[str, Any]) -> str:
    bank = [c for c in intel.get("proof_bank") or [] if isinstance(c, dict) and c.get("id")]
    if bank:
        return "\n".join(f"[{c['id']}] ({c.get('type')}) {c['claim']}" for c in bank)
    # Campaigns analysed before the proof bank existed only carry plain proof points
    return _bullets(intel.get("proof_points"))


def _voice_brief(intel: Dict[str, Any]) -> str:
    v = intel.get("voice") or {}
    markets = intel.get("markets") or []
    lines = []
    if markets:
        m = markets[0]
        others = ", ".join(x.get("country", "") for x in markets[1:4] if isinstance(x, dict))
        lines.append(f"MARKET: {m.get('country')} ({m.get('country_code')}), language {m.get('language') or 'unknown'}, "
                     f"currency {m.get('currency') or 'unknown'}" + (f"; also sells in {others}" if others else ""))
    if v:
        lines += [
            f"VOICE RULES: tone {v.get('tone')}; addresses the reader as {v.get('address_as')}; {v.get('reading_level')}; "
            f"{v.get('sentence_style')}; emoji: {'yes, sparingly' if v.get('uses_emoji') else 'never'}",
            f"Words and phrases the brand uses: {', '.join(v.get('use_words') or []) or '(none recorded)'}",
            f"NEVER use these words or phrases: {', '.join(v.get('avoid_words') or []) or '(none recorded)'}",
            "Lines from the site that show the voice:\n" + _bullets(v.get("sample_lines"), 6),
        ]
    themes = [t for t in intel.get("review_themes") or [] if isinstance(t, dict)]
    if themes:
        lines.append("CUSTOMER LANGUAGE (real review phrases, best material for hooks and on-screen text):")
        for t in sorted(themes, key=lambda t: -(t.get("mentions") or 0))[:8]:
            quotes = " / ".join(f'"{q}"' for q in (t.get("customer_phrases") or [])[:4])
            lines.append(f"- {t.get('theme_type')}: {t.get('summary')} ({t.get('mentions')} mentions) {quotes}")
    if intel.get("review_rating"):
        lines.append(f"Overall rating as shown: {intel['review_rating']} (only usable in copy if it is also in the proof bank)")
    return "\n".join(lines) + ("\n\n" if lines else "")


def _intel_brief(intel: Dict[str, Any]) -> str:
    """Compact text version of the step 2 intelligence for the step 3 prompt writer."""
    products = _products(intel)
    catalog = (
        "PRODUCTS (from the user's photos; every ad features products from this list by index):\n"
        + "\n".join(f"[{i}] {p.get('name')}: {p.get('lock')}" for i, p in enumerate(products))
        + "\n"
        if products else ""
    )
    bs = intel.get("bullseye_target") or {}
    snt = intel.get("brand_sentiment") or {}
    aud = intel.get("audience") or {}
    demo = intel.get("demographics") or {}
    comp = intel.get("competitor_takeaways") or {}
    look = catalog or f"Product look: {intel.get('product_visual_description', '')[:600]}\n"
    return (
        f"Brand: {intel.get('brand_name')} | Product: {intel.get('product_name')} | Category: {intel.get('product_category')} "
        f"| Business type: {intel.get('business_type')}\n"
        f"{look}"
        f"Key benefits:\n{_bullets(intel.get('key_benefits'))}\n"
        f"PROOF BANK (claims found on the brand's own site; the ONLY factual claims you may use, cite their ids):\n{_proof_lines(intel)}\n"
        f"Brand palette: {intel.get('color_palette')} | Visual style: {intel.get('visual_style')} | Typical setting: {intel.get('setting')}\n"
        f"{_brand_kit_line(intel)}\n"
        f"{_voice_brief(intel)}"
        f"BRAND SENTIMENT: tone={snt.get('tone')}; emotional promise={snt.get('emotional_promise')}; "
        f"customer perception={snt.get('customer_perception')}; voice={', '.join(snt.get('voice_keywords') or [])}\n\n"
        f"DEMOGRAPHICS: {json.dumps(demo, ensure_ascii=False)}\n\n"
        f"AUDIENCE\nPain points:\n{_bullets(aud.get('pain_points'))}\nDesires:\n{_bullets(aud.get('desires'))}\n"
        f"Objections:\n{_bullets(aud.get('objections'))}\nBuying triggers:\n{_bullets(aud.get('buying_triggers'))}\n\n"
        f"BULLSEYE TARGET (write every ad for this one person): {bs.get('persona_name')}, {bs.get('age')}, {bs.get('gender')}, "
        f"{bs.get('occupation')} in {bs.get('location')}. {bs.get('snapshot')}\n"
        f"Trigger moment: {bs.get('trigger_moment')}\nCore pain: {bs.get('core_pain')}\nCore desire: {bs.get('core_desire')}\n"
        f"Scroll habits: {bs.get('scroll_habits')}\nOn-camera casting: {bs.get('casting_description')}\n\n"
        f"COMPETITOR TAKEAWAYS\nWinning patterns:\n{_bullets(comp.get('winning_patterns'))}\n"
        f"Saturated (avoid copying):\n{_bullets(comp.get('saturated_angles'))}\n"
        f"White space (own these):\n{_bullets(comp.get('whitespace'))}"
    )


def _omni_prompt(intel: Dict[str, Any], ad: Dict[str, Any], has_refs: bool, featured: List[Dict[str, Any]]) -> str:
    """Final Omni Flash prompt: product lock + casting + beat-by-beat timeline + the writer's direction.

    `featured` are the products this ad uses; the render attaches their photos in this order,
    so the i-th one is <IMAGE_REF_i>."""
    bs = intel.get("bullseye_target") or {}
    brand = intel.get("brand_name") or "the brand"
    product = " and ".join(p["name"] for p in featured) if featured else (intel.get("product_name") or "the product")
    lines = [
        f"{VIDEO_DURATION_S}-second vertical 9:16 Meta Reels ad for {product} by {brand}. Photoreal, shot on a phone-grade or cinema camera as fits the beats, natural motion.",
    ]
    if featured:
        lines.append(
            "PRODUCT LOCK: every product on screen is one of these real products, reproduced exactly as in its "
            "reference image (same shape, colours, materials, cap or pump, label artwork and label text). Never "
            "redesign them, swap in a generic product, add other products or invent label text."
        )
        lines += [f"- <IMAGE_REF_{i}> is {sanitize_video_prompt(p['lock'])}" for i, p in enumerate(featured)]
    elif has_refs:
        look = sanitize_video_prompt(intel.get("product_visual_description") or "")
        lines.append(
            f"PRODUCT LOCK: the reference images (<IMAGE_REF_0> onward) show the real {product}. The product on screen "
            "must be the referenced product, reproduced exactly: same shape, colours, materials and label layout. "
            "Never redesign it, swap it for a generic product or invent label text."
            + (f" It looks like this: {look}" if look else "")
        )
    if bs.get("casting_description"):
        lines.append(f"CASTING: {bs['casting_description']}")
    kit = intel.get("brand_kit") or {}
    if kit:
        primary_name = hex_to_color_name(kit.get("primary_hex", "")) if kit.get("primary_hex") else ""
        accent_name = hex_to_color_name(kit.get("accent_hex", "")) if kit.get("accent_hex") else ""
        bg_name = hex_to_color_name(kit.get("background_hex", "")) if kit.get("background_hex") else ""
        palette_names = [c for c in dict.fromkeys([primary_name, accent_name, bg_name]) if c]
        if len(palette_names) > 1:
            palette_desc = ", ".join(palette_names[:-1]) + " and " + palette_names[-1]
        elif palette_names:
            palette_desc = palette_names[0]
        else:
            palette_desc = "brand accent tones"
        lines.append(
            f"BRAND LOOK: {kit.get('visual_mood')}; colour accents in the brand palette {palette_desc} "
            "(props, wardrobe, set), never overpowering the product."
        )
    lines.append("TIMELINE:")
    for b in ad.get("beats") or []:
        on_screen = sanitize_video_prompt(b.get("on_screen_text") or "")
        text = f' On-screen text: "{on_screen}".' if on_screen else ""
        vis = sanitize_video_prompt(b.get("visual") or "")
        lines.append(f"- {b.get('time')}: {vis}{text} Audio: {b.get('audio')}")
    if ad.get("voiceover"):
        language = _primary_language(intel)
        spoken = f"spoken in {language}, " if language and language.lower() not in ("english", "en") else ""
        lines.append(f'VOICEOVER ({spoken}natural, matches the timeline): "{ad["voiceover"]}"')
    lines.append(f"DIRECTION: {sanitize_video_prompt(ad.get('video_prompt', ''))}")
    lines.append(NO_END_SCREEN_LINE)
    lines.append(
        "DEVICE ORIENTATION & SCREEN INTEGRITY: Every laptop, smartphone, tablet, and computer monitor must appear strictly upright in its natural, physically correct orientation. Laptops sit flat on desks with keyboards at the bottom and screens upright. Phones are held vertically upright with front cameras at the top. All UI, dashboards, software screens, and text must be horizontal and right-side up, NEVER inverted, upside-down, or mirrored."
    )
    lines.append(
        "AVOID: hex color codes, raw hex codes, hash codes, color code labels, printed hex strings, "
        "inverted laptop screens, upside-down laptops, backward laptops, laptops held upside-down or flipped, "
        "inverted phones, upside-down phone screens, mirrored screens, reverse UI, backwards display, "
        "floating distorted keyboards, impossible hinge angles, backward screens, celebrity likeness, "
        "famous actors or public figures, glamorous airbrushed influencer aesthetic, competitor brands or logos, "
        "star ratings, prices, discounts, fake reviews, extra products, warped hands, garbled or misspelled on-screen text, "
        "more than six words of on-screen text at once, " + NO_END_SCREEN_AVOID + "."
    )
    return sanitize_video_prompt("\n".join(lines))


def _prompt_batch_instructions(
    brief: str, template_menu: str, n_img: int, n_vid: int, focus: str, has_products: bool,
    ref_brief: str = "", has_image_refs: bool = False, has_video_refs: bool = False, language: str = "",
) -> str:
    image_source = (
        "- reference_id: the [R..] image reference ad this ad is built on. Use every reference before reusing one. "
        "The ad keeps that reference's concept and layout (composition, framing, camera distance, where the text "
        "sits and how much text there is) and swaps in everything of ours: our product, palette, logo and copy.\n"
        "- concept: one sentence: what the reference ad does and how this ad does the same for our brand.\n"
        "- template_id: empty string.\n"
        if has_image_refs else
        "- reference_id: empty string.\n"
        "- concept: one sentence on the visual idea.\n"
        f"- template_id: the layout that best fits the angle, from this list only:\n{template_menu}\n"
    )
    video_source = (
        "- reference_id: the [V..] video reference ad this video is built on; adapt its hook mechanic and beat "
        "structure to our product (never its brand, people or words). Use every reference before reusing one.\n"
        if has_video_refs else
        "- reference_id: empty string.\n"
    )
    refs_block = f"{ref_brief}\n\nConcepts and layouts come ONLY from these reference ads.\n\n" if ref_brief else ""
    return (
        "You are a creative director writing a Meta ad campaign. Every ad must speak to the bullseye target, "
        "use the brand's voice, and win against the competitor patterns by owning the white space.\n\n"
        f"{brief}\n\n"
        f"{refs_block}"
        f"Write exactly {n_img} IMAGE ADS and exactly {n_vid} VIDEO ADS. This batch focuses on {focus}. "
        "Every ad in the batch takes a different angle within that focus, with a different hook and headline.\n\n"
        + (
            "PRODUCT CHOICE: each ad is about specific products from the PRODUCTS list. Spread the ads across all "
            "listed products, and write the copy, benefit and scene for the product(s) the ad features, not for the "
            "range in general. Mention products by their exact names.\n\n"
            if has_products else
            "PRODUCT CHOICE: no product photos were given; set product_index to 0 and product_indexes to [].\n\n"
        )
        + "IMAGE ADS (rendered as finished ads with text in the image):\n"
        "- product_index: the index of the ONE product from the PRODUCTS list this ad shows.\n"
        f"- framework_key: one of {', '.join(FRAMEWORK_KEYS)}. Use a mix.\n"
        f"{image_source}"
        "- image_headline: at most 6 words, the only headline printed in the image. Specific, punchy, in the brand voice.\n"
        f"- cta: at most {MAX_CTA_WORDS} words for the CTA pill (e.g. Shop Now, Try It Free).\n"
        "- meta_headline: the Ads Manager headline field, at most 40 characters.\n"
        "- primary_text: the caption above the ad, 1-3 short sentences opening with a hook for the bullseye target.\n"
        "- scene: one or two sentences of art direction for this ad (props, environment, moment), consistent with the "
        "reference or template and the bullseye target's world. No text instructions here.\n"
        "- benefit: the single benefit this ad sells.\n"
        "- contrast_before: for problem_solution or us_vs_them, the 'before' state or generic alternative (never a "
        "competitor name); otherwise an empty string.\n"
        "- proof_ids: ids of the PROOF BANK claims this ad's copy relies on (e.g. [\"P2\"]); empty when it makes no "
        "factual claim.\n"
        "- rationale: one sentence on why this works for the bullseye target and which competitor gap it uses.\n\n"
        f"VIDEO ADS ({VIDEO_DURATION_S}s vertical 9:16, rendered with Gemini Omni Flash from the product reference images):\n"
        f"- product_indexes: 1 to {MAX_VIDEO_PRODUCTS} indexes from the PRODUCTS list shown in this video (usually 1; "
        "more only for a routine or kit story).\n"
        f"{video_source}"
        "- hook_line: the first-second hook.\n"
        f"- voiceover: one continuous spoken line that fits {VIDEO_DURATION_S} seconds (about 30-35 words).\n"
        "- beats: 3 or 4 beats covering 0s to 15s (e.g. 0-3s, 3-8s, 8-12s, 12-15s), each with visual, on_screen_text (at most 5 "
        "words, may be empty) and audio. Start with a scroll-stopping hook, show the product in use, and end on a payoff "
        "moment inside the live scene. NO END SCREEN: never write an end screen, end card, logo slate, title card, CTA card "
        "or button, packshot on a plain background, or a fade to a brand-colour screen; the CTA is the Meta button outside "
        "the video.\n"
        "- video_prompt: a single paragraph of direction for the whole clip in ONE of these formats: UGC (a real person "
        "talking to a phone camera), product demo, or motion graphics with kinetic type. Never a cinematic brand film. "
        "Cover casting, setting, camera moves, lighting, pacing and how the product is handled.\n"
        "- DEVICE ORIENTATION & SCREEN INTEGRITY: When laptops, monitors, or smartphones appear, they MUST be strictly upright in normal gravity. Laptops sit flat with screen open upright; phones held vertically upright. Never describe laptops flipped, turned backward, or upside down. All UI and dashboards must be horizontal and right-side up.\n"
        "- NO HEX CODES OR RAW COLOR VALUES: Never include hex codes (e.g. #FF5252, #FFFFFF) or color hashes in visual beats, on-screen text, voiceover, or video_prompt. Always describe colors using natural descriptive words (e.g. 'vibrant coral red', 'warm cream', 'dark navy').\n"
        "- proof_ids: ids of the PROOF BANK claims the voiceover or on-screen text relies on; empty if none.\n"
        "- rationale: one sentence on why this hook works for the bullseye target.\n\n"
        "VOICE AND CLAIMS: all copy (headlines, CTA, primary text, hook, voiceover, on-screen text) follows the VOICE "
        "RULES and never uses a word from the NEVER list. "
        + (f"Write all copy in {language}, the language of the brand's market. " if language else "")
        + "Prefer real customer phrases from CUSTOMER LANGUAGE for hooks. Any factual claim (number, rating, ingredient "
        "effect, guarantee, award, offer) must come from the PROOF BANK and be listed in proof_ids.\n"
        "Never name or show competitors. "
        "CASTING & PROMPT RULE: In scene, beats (visual action), and video_prompt, NEVER use proper personal names "
        "(e.g. do NOT write 'Ananya', 'Sarah', etc.). Always describe talent anonymously using realistic demographic and situational "
        "descriptors (e.g. 'A 24-year-old female commuter', 'A young professional'). NEVER request, imply, or describe celebrity likeness, "
        "famous actors, or glamorous influencers. All talent should look like everyday relatable real people with natural unretouched skin.\n"
        f"{NO_FABRICATED_CLAIMS_RULE}"
    )


# ---------------------------------------------------------------------------
# Step 2 helpers: voice rules, proof bank, customer language, market
# ---------------------------------------------------------------------------
BRAND_PROFILE_DIR = "/tmp/data/brands" if os.environ.get("VERCEL") else os.path.join("data", "brands")


def _grounding_sources(response: Any) -> List[str]:
    """Sites Google Search grounding used for the research (titles are usually the domain)."""
    out: List[str] = []
    try:
        for cand in response.candidates or []:
            meta = getattr(cand, "grounding_metadata", None)
            for chunk in getattr(meta, "grounding_chunks", None) or []:
                web = getattr(chunk, "web", None)
                label = getattr(web, "title", None) or getattr(web, "uri", None)
                if label and label not in out:
                    out.append(label)
    except Exception as e:
        logger.debug(f"[flow/analyze] no grounding metadata: {e}")
    return out[:30]


def _voice_proof_prompt(site_text: str, research_text: str, sources: List[str], discovered_market: Optional[dict]) -> str:
    market_note = (
        f"Market already detected from the site at discovery: {json.dumps(discovered_market, ensure_ascii=False)}\n"
        if discovered_market and discovered_market.get("country") else ""
    )
    return (
        "You are a brand copy chief. From the brand's own site and the research below, write the brand's voice rules, "
        "its proof bank, what its customers say, and where it sells.\n\n"
        f"SITE (crawled pages, each labelled with its URL):\n{site_text or '(the site could not be read)'}\n\n"
        f"RESEARCH (includes review snippets found by search):\n{research_text}\n\n"
        f"Sites the research used: {', '.join(sources) or '(not reported)'}\n{market_note}\n"
        "Rules:\n"
        "- voice.tone: 3-6 words. address_as: how the brand addresses the reader (e.g. 'you, first person plural for the "
        "brand'). reading_level: e.g. 'plain, short words'. sentence_style: length, rhythm and punctuation habits. "
        "uses_emoji: true only if the site itself uses emoji. use_words: 8-15 words or short phrases the brand actually "
        "uses on the site. avoid_words: 5-12 words or phrases that would sound wrong for this brand (e.g. clinical jargon "
        "for a playful brand, slang for a premium one, hype words a calm brand never uses). sample_lines: 3-6 lines "
        "copied word for word from the site that best show the voice.\n"
        "- proof_bank: every factual claim the brand makes on its own site, copied word for word as one short sentence "
        "or phrase each: statistics, ratings, review counts, awards, certifications, guarantees, ingredients or "
        "materials and what they do, offers, shipping and returns promises. type is one of stat, rating, award, "
        "certification, guarantee, ingredient, feature, offer. source_url is the URL of the PAGE block it was copied "
        "from. Only the brand's own site: never review sites, search results or your own knowledge.\n"
        "- review_themes: group what customers say into themes. theme_type is one of pain, desire, objection, praise. "
        "customer_phrases are short phrases copied word for word from real reviews in the site's review data or the "
        "research (never paraphrased, never invented). mentions is how many separate reviews you saw expressing it. "
        "sources are the sites they came from. Empty list if no reviews were found.\n"
        "- review_rating: the overall rating exactly as shown (e.g. '4.7/5 from 1,203 reviews on Trustpilot'), or empty.\n"
        "- markets: the countries the brand sells in, main market first, with ISO country_code, country, language, "
        "currency and the evidence. Use ALL as country_code only when it clearly sells worldwide with no main market.\n"
        "- aesthetic_keywords: 6-10 visual style keywords a creative director would search on Pinterest for this brand "
        "(e.g. 'warm minimalism', 'retro sport poster', 'clean studio flatlay'), based on the site's photography, "
        "colours and type."
    )


def _apply_voice_proof(intel: Dict[str, Any], vp: Dict[str, Any], crawl: Dict[str, Any], research_text: str,
                       research_sources: List[str], discovered_market: Optional[dict]) -> None:
    """Adds the checked voice/proof/customer-language/market data to the intelligence.
    Claims, sample lines and customer phrases that can't be found in the source text are dropped."""
    site_corpus = " ".join(p["text"] for p in crawl.get("pages", []))
    review_corpus = " ".join(crawl.get("reviews", [])) + " " + research_text

    verified, unverified = check_proof_bank(vp.get("proof_bank") or [], crawl)
    voice = dict(vp.get("voice") or {})
    voice["sample_lines"] = [l for l in voice.get("sample_lines") or [] if appears_in(l, site_corpus)]
    themes = []
    for t in vp.get("review_themes") or []:
        phrases = [ph for ph in t.get("customer_phrases") or [] if appears_in(ph, review_corpus)]
        if phrases:
            themes.append({**t, "customer_phrases": phrases})

    markets = [clean_market(m) for m in vp.get("markets") or [] if isinstance(m, dict) and (m.get("country") or m.get("country_code"))]
    if not markets and discovered_market:
        markets = [clean_market(discovered_market)]

    intel.update({
        "voice": voice,
        "proof_bank": verified,
        "unverified_claims": unverified,
        # Older prompt code and saved campaigns read proof_points as plain strings
        "proof_points": [c["claim"] for c in verified],
        "review_themes": themes,
        "review_rating": vp.get("review_rating") or "",
        "markets": markets,
        "aesthetic_keywords": vp.get("aesthetic_keywords") or [],
        "research_sources": research_sources,
        "site_pages": [{"kind": p["kind"], "url": p["url"]} for p in crawl.get("pages", [])],
    })


def _save_brand_profile(url: str, intel: Dict[str, Any]) -> None:
    """data/brands/<domain>/brand_profile.json: the checked brand facts later agents build on."""
    try:
        site = urlparse(url).netloc.lower().removeprefix("www.")
        folder = os.path.join(BRAND_PROFILE_DIR, re.sub(r"[^a-z0-9.\-]", "_", site))
        os.makedirs(folder, exist_ok=True)
        profile = {k: intel.get(k) for k in (
            "brand_name", "product_category", "business_type", "brand_kit", "voice", "proof_bank", "unverified_claims",
            "review_themes", "review_rating", "markets", "aesthetic_keywords", "research_sources", "site_pages",
        )}
        profile["url"] = url
        profile["products"] = [{"index": p["index"], "image_path": p["image_path"], "name": p["name"], "lock": p["details"]}
                               for p in intel.get("products") or []]
        profile["saved_at"] = datetime.now(timezone.utc).isoformat()
        with open(os.path.join(folder, "brand_profile.json"), "w", encoding="utf-8") as f:
            json.dump(profile, f, ensure_ascii=False, indent=2)
    except OSError as e:
        logger.warning(f"[flow/analyze] could not save brand profile for {url}: {e}")


# ---------------------------------------------------------------------------
# Step 2: brand intelligence
# ---------------------------------------------------------------------------
@router.post("/analyze")
async def analyze_brand(
    url: str = Form(...),
    images: Optional[List[UploadFile]] = File(None),
    logo: Optional[UploadFile] = File(None),
    competitor_run_id: Optional[str] = Form(None),
    x_api_key: Optional[str] = Header(None),
):
    url = _normalize_url(url)
    client = _require_client(x_api_key)

    # Brand logo: the user's upload, otherwise found on the brand site (runs alongside the research)
    logo_info = None
    logo_task = None
    if logo and logo.filename:
        logo_bytes, _, _ = await read_upload(logo, IMAGE_EXTS, ".png", MAX_IMAGE_BYTES)
        logo_info = save_uploaded_logo(logo_bytes)
        if not logo_info:
            raise HTTPException(status_code=400, detail="The logo file could not be read as an image.")
    else:
        logo_task = asyncio.create_task(asyncio.to_thread(find_brand_logo, url))

    # Reference images: saved for rendering, sent to the analyst for the product description
    image_paths: List[str] = []
    image_parts: List[Any] = []
    for img in (images or [])[:MAX_REFERENCE_IMAGES]:
        if not img or not img.filename:
            continue
        content, ext, mime = await read_upload(img, IMAGE_EXTS, ".jpg", MAX_IMAGE_BYTES)
        filename = f"product_{uuid.uuid4().hex}{ext}"
        image_url = save_generated_media(filename, content, mime)
        image_paths.append(image_url)
        image_parts.append(types.Part.from_bytes(data=content, mime_type=mime))

    comp = load_competitor_run_summary(competitor_run_id) if competitor_run_id else None
    competitor_note = None
    if competitor_run_id and not comp:
        competitor_note = "The competitor run could not be found, so this analysis uses the brand site only."
    elif comp and not comp.get("reliable"):
        competitor_note = "The competitor agent found no live ads for these competitors, so its findings were left out."
        comp = None
    # The analysed competitor creatives become the concept and layout references for our ads
    references = load_reference_ads(competitor_run_id) if comp else {"image": [], "video": []}

    # Per-image product locks run alongside the research so they add no wait
    products_task = asyncio.create_task(_describe_products(client, image_parts)) if image_parts else None

    try:
        crawl = await asyncio.to_thread(crawl_brand_site, url)
        site_text = crawl_digest(crawl)
        if not crawl["pages"]:
            logger.warning(f"[flow/analyze] could not read any page of {url}; relying on search")

        # Research pass with Google Search grounding (tools and response_schema cannot be combined)
        research_prompt = (
            f"You are a brand strategist researching {url}.\n"
            f"The brand's own site (pages crawled just now):\n{site_text or '(the site could not be read; rely on search)'}\n\n"
            "Using the site and Google Search, report: brand and hero product; category; what is sold; price positioning; "
            "the main country or countries it sells in and the evidence; how the brand talks (tone, vocabulary); the feeling "
            "it promises; who buys it (age, gender, location, income, lifestyle, culture); their pains, desires, objections "
            "and buying triggers; visual identity (colours, photography style).\n"
            "CUSTOMER REVIEWS: search for reviews of this brand and its products on Amazon, Trustpilot, Google reviews, "
            "Reddit and retailers in its market. Quote up to 25 short review snippets word for word, each with the site it "
            "came from, and the overall ratings shown there. If you find none, say so plainly; never paraphrase a review as "
            "a quote or invent one.\n"
            "List every guarantee, rating, statistic, ingredient claim, certification or offer exactly as the site states it."
        )
        try:
            research = await asyncio.to_thread(
                client.models.generate_content,
                model=TEXT_MODEL,
                contents=research_prompt,
                config=types.GenerateContentConfig(tools=[types.Tool(google_search=types.GoogleSearch())]),
            )
        except Exception as ground_err:
            logger.warning(f"[flow/analyze] search grounding unavailable, using page text only: {ground_err}")
            research = await asyncio.to_thread(client.models.generate_content, model=TEXT_MODEL, contents=research_prompt)
        research_text = research.text or ""
        research_sources = _grounding_sources(research)

        if logo_task:
            try:
                logo_info = await logo_task
            except Exception as e:
                logger.warning(f"[flow/analyze] logo lookup failed: {e}")
            logo_task = None
        logo_parts: List[Any] = []
        logo_local = resolve_generated_path(logo_info["path"]) if logo_info else None
        if logo_local:
            with open(logo_local, "rb") as f:
                logo_parts = ["The brand's logo:", types.Part.from_bytes(data=f.read(), mime_type="image/png")]

        analysis_prompt = (
            "You are a senior performance-marketing strategist. Turn the research below into a brand intelligence brief.\n\n"
            f"BRAND RESEARCH:\n{research_text}\n\n"
            f"COMPETITOR RESEARCH (Meta Ad Library):\n{_competitor_brief(comp)}\n\n"
            + (
                f"{len(image_parts)} reference image(s) from the user are attached. Describe the product in "
                "product_visual_description precisely enough to keep it identical across ads: shape, materials, colours, "
                "cap or closure, label layout and the words printed on it. If the images show an app or website rather than "
                "a physical product, describe the interface and visual style instead.\n\n"
                if image_parts else
                "No reference images were supplied; describe the product from the research.\n\n"
            )
            + "Rules:\n"
            "- business_type: exactly one of physical_product, fintech, saas_app, service.\n"
            "- brand_sentiment: how the brand feels and is perceived. customer_perception must reflect real reviews from the "
            "research; if there are none, say that customer sentiment is not public.\n"
            "- demographics and bullseye_target live in the brand's main market from the research (never assume a country "
            "the research does not support).\n"
            "- bullseye_target: ONE specific person who is the single most valuable buyer (not an average of segments). "
            "persona_name should be realistic and authentic to the culture/market (do not default to common repetitive AI cliché names like 'Ananya Sharma', 'Priya Sharma', 'Sarah Miller', 'Alex', etc.). "
            "trigger_moment is the everyday moment they feel the problem. casting_description is a concrete on-camera look "
            "(age, ethnicity, styling, wardrobe, setting, natural unretouched skin) for image and video models, true to that market. "
            "NEVER reference or resemble celebrities, famous actors, or public figures.\n"
            "- competitor_takeaways: derived from the competitor research only; empty lists when there is none.\n"
            "- color_palette: 3-5 colour names or hex codes from the brand identity.\n"
            "- brand_kit: the brand's real visual identity from its logo and site (hex codes like #1F1F1F): primary_hex is "
            "the main brand colour, accent_hex the colour for CTA buttons, background_hex and text_hex the usual ad "
            "background and text colours, supporting_hexes up to 3 more; headline_type and body_type describe the "
            "typefaces (e.g. 'heavy rounded geometric sans, tight tracking'); visual_mood is 3-6 words.\n"
            "- visual_style: one of UGC_REALISTIC, CINEMATIC_PREMIUM, CLEAN_STUDIO, PIXAR_3D_STYLIZED, FOOD_APPETITE.\n"
            f"{NO_FABRICATED_CLAIMS_RULE}"
        )
        intel_call = asyncio.to_thread(
            client.models.generate_content,
            model=TEXT_MODEL,
            contents=[*image_parts, *logo_parts, analysis_prompt],
            config=types.GenerateContentConfig(response_mime_type="application/json", response_schema=BrandIntelligence, temperature=0.7),
        )
        voice_call = asyncio.to_thread(
            client.models.generate_content,
            model=TEXT_MODEL,
            contents=_voice_proof_prompt(site_text, research_text, research_sources, (comp or {}).get("market")),
            config=types.GenerateContentConfig(response_mime_type="application/json", response_schema=BrandVoiceProof, temperature=0.7),
        )
        response, voice_response = await asyncio.gather(intel_call, voice_call, return_exceptions=True)
        if isinstance(response, Exception):
            raise response
        intelligence = json.loads(response.text)
        if isinstance(voice_response, Exception):
            logger.warning(f"[flow/analyze] voice/proof pass failed; ads will run without voice rules or claims: {voice_response}")
            voice_proof: Dict[str, Any] = {}
        else:
            voice_proof = json.loads(voice_response.text)
    except HTTPException:
        for task in (products_task, logo_task):
            if task:
                task.cancel()
        raise
    except Exception as e:
        for task in (products_task, logo_task):
            if task:
                task.cancel()
        logger.error(f"[flow/analyze] failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Brand analysis failed: {e}")

    # One product entry per uploaded image, in upload order (index = position in product_image_paths)
    products: List[Dict[str, Any]] = []
    if products_task:
        try:
            locks = await products_task
        except Exception as e:
            logger.warning(f"[flow/analyze] per-image product analysis failed, using the combined description: {e}")
            locks = []
        for i, path in enumerate(image_paths):
            lock = locks[i] if i < len(locks) and locks[i] else None
            if not lock or (lock.get("product_name") or "").strip().upper() == "UNREADABLE":
                continue
            entry = {
                "index": i,
                "image_path": path,
                "name": lock.get("product_name") or f"Product {i + 1}",
                "lock": _lock_text(lock),
                "details": lock,
            }
            _save_product_lock(path, entry)
            products.append(entry)
        # Ads pick products by position in this list; each entry's "index" is its image's upload position
        if len(products) != len(image_paths):
            logger.warning(f"[flow/analyze] product locks for {len(products)} of {len(image_paths)} images")
    intelligence["products"] = products
    intelligence["logo"] = logo_info
    intelligence["references"] = references
    _apply_voice_proof(intelligence, voice_proof, crawl, research_text, research_sources, (comp or {}).get("market"))

    # Auto-detect best matching creative library preset from Pinterest reference atlas
    try:
        from creative_library_presets import detect_best_preset_for_brand, get_presets_for_industry, DIVERSE_PRESET
        detected = detect_best_preset_for_brand(
            brand_category=intelligence.get("product_category", ""),
            business_type=intelligence.get("business_type", ""),
            product_name=intelligence.get("product_name", ""),
            brand_name=intelligence.get("brand_name", "")
        )
        intelligence["detected_preset"] = DIVERSE_PRESET
        intelligence["industry_preset"] = detected
        ind_presets = get_presets_for_industry(intelligence.get("product_category", ""))
        intelligence["available_presets"] = [DIVERSE_PRESET] + [p for p in ind_presets if p["id"] != "diverse"]
    except Exception as e:
        logger.warning(f"[flow/analyze] could not detect creative preset: {e}")

    _save_brand_profile(url, intelligence)

    return {
        "url": url,
        "intelligence": intelligence,
        "product_image_paths": image_paths,
        "competitor": {
            "run_id": competitor_run_id,
            "used": bool(comp),
            "competitors": (comp or {}).get("competitors", []),
            "total_ads": (comp or {}).get("total_ads", 0),
            "report_url": (comp or {}).get("report_url"),
            "note": competitor_note,
        },
    }


# ---------------------------------------------------------------------------
# Step 2.5 (A5): Campaign Strategy Matrix
# ---------------------------------------------------------------------------
STRATEGY_DIR = os.path.join("data", "strategy")


def _save_campaign_matrix(url: str, matrix_dict: Dict[str, Any]) -> None:
    """Save strategy/campaign_matrix.json both globally and per-brand."""
    try:
        os.makedirs(STRATEGY_DIR, exist_ok=True)
        with open(os.path.join(STRATEGY_DIR, "campaign_matrix.json"), "w", encoding="utf-8") as f:
            json.dump(matrix_dict, f, ensure_ascii=False, indent=2)

        if url:
            site = urlparse(url).netloc.lower().removeprefix("www.")
            folder = os.path.join(BRAND_PROFILE_DIR, re.sub(r"[^a-z0-9.\-]", "_", site))
            os.makedirs(folder, exist_ok=True)
            with open(os.path.join(folder, "campaign_matrix.json"), "w", encoding="utf-8") as f:
                json.dump(matrix_dict, f, ensure_ascii=False, indent=2)
    except OSError as e:
        logger.warning(f"[flow/strategy] could not save campaign matrix: {e}")


@router.post("/strategy")
async def generate_campaign_strategy(req: StrategyRequest, x_api_key: Optional[str] = Header(None)):
    """A5 Creative Strategist: Builds the campaign matrix (25+ statics and 25+ videos + test plan)."""
    client = _require_client(x_api_key)
    intel = req.intelligence or {}
    url = intel.get("url") or ""

    strategist = CreativeStrategist(client)
    try:
        matrix = await strategist.build_campaign_matrix(
            brand_profile=intel,
            meta_refs=req.meta_refs,
            style_tokens=req.style_tokens,
            target_statics=req.target_statics,
            target_videos=req.target_videos,
        )
        matrix_dict = matrix.model_dump()
        _save_campaign_matrix(url, matrix_dict)
        return {
            "status": "success",
            "campaign_matrix": matrix_dict,
            "counts": {
                "statics": len(matrix.statics),
                "videos": len(matrix.videos),
                "test_ad_sets": len(matrix.test_plan),
            },
        }
    except Exception as e:
        logger.error(f"[flow/strategy] Strategy matrix generation failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Campaign strategy generation failed: {e}")


# ---------------------------------------------------------------------------
# Step 3: image ad prompts + Omni Flash video prompts (A6/A7 writers + A8 critic)
# ---------------------------------------------------------------------------
@router.post("/prompts")
async def write_ad_prompts(req: PromptsRequest, x_api_key: Optional[str] = Header(None)):
    client = _require_client(x_api_key)
    intel = req.intelligence or {}
    image_count = max(1, min(req.image_count, MAX_PROMPTS))
    video_count = max(0, min(req.video_count, MAX_PROMPTS))
    aspect = req.aspect_ratio if req.aspect_ratio in ("1:1", "4:5", "9:16", "16:9") else "4:5"

    business_type = intel.get("business_type") or ""
    category = intel.get("product_category") or ""
    # Reference photos only lock the product for physical products; for apps/services they are style references
    has_product_ref = req.has_reference_images and business_type == "physical_product"
    mode = detect_brand_mode(business_type, category, has_product_ref)
    templates = templates_for_mode(mode)
    template_menu = "\n".join(
        f"- {t['id']}: {t['name']} — {t['summary']} (suits: {', '.join(t['frameworks'])})" for t in templates
    )
    brief = _intel_brief(intel)
    products = _products(intel)
    refs = _references(intel)
    ref_brief = _reference_brief(intel)
    image_refs = list(refs["image"].items())
    video_refs = list(refs["video"].items())
    logo = intel.get("logo") or {}
    brand_kit = intel.get("brand_kit") or {}

    # -----------------------------------------------------------------------
    # Step 3.1: Creative Strategist (A5) -> campaign_matrix.json
    # -----------------------------------------------------------------------
    matrix = None
    if req.campaign_matrix:
        try:
            matrix = CampaignMatrix(**req.campaign_matrix)
        except Exception as e:
            logger.warning(f"[flow/prompts] could not parse supplied campaign matrix: {e}")

    if not matrix:
        logger.info(f"[flow/prompts] Generating campaign matrix via A5 Creative Strategist ({image_count} statics, {video_count} videos)...")
        strategist = CreativeStrategist(client)
        effective_meta_refs = req.meta_refs
        if not effective_meta_refs and intel.get("references"):
            raw_refs = intel.get("references", {})
            img_list = raw_refs.get("image") or []
            vid_list = raw_refs.get("video") or []
            if img_list or vid_list:
                effective_meta_refs = {
                    "signal": "strong" if img_list else "moderate",
                    "image_refs": [
                        {
                            "id": f"R{i}",
                            "competitor": r.get("competitor", "Competitor"),
                            "angle": r.get("angle", ""),
                            "hook": r.get("hook", ""),
                            "days_running": r.get("days_running", 14),
                        }
                        for i, r in enumerate(img_list, start=1)
                    ],
                    "video_refs": [
                        {
                            "id": f"V{i}",
                            "competitor": v.get("competitor", "Competitor"),
                            "format": v.get("format", "video"),
                            "hook": v.get("hook", ""),
                            "days_running": v.get("days_running", 14),
                        }
                        for i, v in enumerate(vid_list, start=1)
                    ],
                    "synthesis": {
                        "saturated": (intel.get("competitor_takeaways") or {}).get("saturated_angles", []),
                        "whitespace": (intel.get("competitor_takeaways") or {}).get("whitespace", []),
                    },
                }

        matrix = await strategist.build_campaign_matrix(
            brand_profile=intel,
            meta_refs=effective_meta_refs,
            style_tokens=req.style_tokens,
            target_statics=image_count,
            target_videos=video_count,
        )
        _save_campaign_matrix(intel.get("url", ""), matrix.model_dump())

    # Limit briefs to requested counts
    static_briefs = matrix.statics[:image_count]
    video_briefs = matrix.videos[:video_count]

    # Creative Library Preset resolution (defaults to Diverse Creative Mix for maximum campaign theme variety)
    preset_id = req.preset_id or intel.get("selected_preset_id") or "diverse"
    if not preset_id:
        preset_id = "diverse" 

    # -----------------------------------------------------------------------
    # Step 3.2: Parallel Batched Prompt Writing (A6 Static Writer & A7 Video Writer)
    # Batches of 5 briefs per model call as specified in architecture doc
    # -----------------------------------------------------------------------
    static_writer = StaticPromptWriter(client)
    video_writer = VideoScriptWriter(client)

    BATCH_SIZE = 5
    static_tasks = []
    for i in range(0, len(static_briefs), BATCH_SIZE):
        chunk = static_briefs[i : i + BATCH_SIZE]
        static_tasks.append(
            static_writer.write_batch(chunk, intel, refs, req.style_tokens, default_aspect=aspect, preset_id=preset_id)
        )

    video_tasks = []
    for i in range(0, len(video_briefs), BATCH_SIZE):
        chunk = video_briefs[i : i + BATCH_SIZE]
        video_tasks.append(
            video_writer.write_batch(chunk, intel, refs, req.style_tokens)
        )

    logger.info(f"[flow/prompts] Writing prompts for {len(static_briefs)} statics and {len(video_briefs)} videos...")
    s_results, v_results = await asyncio.gather(
        asyncio.gather(*static_tasks, return_exceptions=True),
        asyncio.gather(*video_tasks, return_exceptions=True),
    )

    image_ads = []
    for r in s_results:
        if isinstance(r, list):
            image_ads.extend(r)
        else:
            logger.warning(f"[flow/prompts] A static writer batch failed: {r}")

    video_ads = []
    for r in v_results:
        if isinstance(r, list):
            video_ads.extend(r)
        else:
            logger.warning(f"[flow/prompts] A video writer batch failed: {r}")

    # -----------------------------------------------------------------------
    # Step 3.3: Creative Director Critic (A8) with Rewrite Loop (max 2 loops)
    # -----------------------------------------------------------------------
    critic = CreativeDirector(client)
    audit = await critic.audit_and_refine(
        image_ads=image_ads,
        video_ads=video_ads,
        brand_profile=intel,
        static_writer=static_writer,
        video_writer=video_writer,
        static_briefs=static_briefs,
        video_briefs=video_briefs,
        references=refs,
    )
    audited_images = audit["image_ads"]
    audited_videos = audit["video_ads"]
    audit_stats = audit["stats"]

    from creative_library_presets import get_preset_by_id
    preset_info = get_preset_by_id(preset_id) if preset_id else None

    return {
        "brand_mode": mode,
        "uses_product_lock": has_product_ref,
        "aspect_ratio": aspect,
        "preset_id": preset_id,
        "preset_info": preset_info,
        "test_plan": [t.model_dump() for t in matrix.test_plan],
        "image_ads": audited_images,
        "video_ads": audited_videos,
        "requested": {"image_ads": image_count, "video_ads": video_count},
        "failed_batches": sum(1 for r in s_results + v_results if isinstance(r, Exception)),
        "critic_summary": audit_stats,
        "flagged": {
            "image_ads": sum(1 for a in audited_images if not a.get("critic_review", {}).get("passed", True)),
            "video_ads": sum(1 for a in audited_videos if not a.get("critic_review", {}).get("passed", True)),
        },
    }
