"""
A5 Creative Strategist Agent

Builds the campaign matrix: 25+ static briefs and 25+ video briefs,
grounded in the brand's verified assets, awareness stages, and competitor/trend references.

The Strategist OWNS ALL COPY:
- Static: image_headline (<=6 words), cta, primary_text, meta_headline (<=40 chars), description
- Video: hook_line, voiceover (~20 words / 8s), on_screen_text, primary_text, meta_headline, cta

Outputs:
- strategy/campaign_matrix.json
"""

import os
import json
import logging
import asyncio
import warnings
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from google import genai
from google.genai import types

warnings.filterwarnings("ignore", message=r'.*Field name "copy" in .* shadows an attribute in parent "BaseModel".*')

logger = logging.getLogger(__name__)

TEXT_MODEL = "gemini-3.6-flash"

AWARENESS_STAGES = [
    "unaware",
    "problem_aware",
    "solution_aware",
    "product_aware",
    "most_aware",
]

FRAMEWORK_KEYS = [
    "problem_solution",
    "feature_callout",
    "social_proof",
    "us_vs_them",
    "lifestyle_hero",
]

VIDEO_FORMATS = ["ugc", "demo", "motion_graphics"]


# ---------------------------------------------------------------------------
# Output Schemas
# ---------------------------------------------------------------------------
class StaticCopy(BaseModel):
    image_headline: str = Field(description="Headline to render directly on image, <= 6 words, punchy and on-brand")
    cta: str = Field(description="Call to action pill text, <= 3 words (e.g. Shop Now, Try Risk-Free)")
    primary_text: str = Field(description="Caption above the ad, 1-3 short sentences opening with a hook")
    meta_headline: str = Field(description="Ads Manager headline field, <= 40 characters")
    description: str = Field(default="", description="Ads Manager description field, optional")


class StaticBrief(BaseModel):
    id: str = Field(description="Unique brief ID, e.g. S01, S02")
    persona: str = Field(description="Target persona ID or name (e.g. P1 or bullseye persona)")
    stage: str = Field(description="Awareness stage: unaware, problem_aware, solution_aware, product_aware, or most_aware")
    angle: str = Field(description="Strategic creative angle name, e.g. 'Morning Routine Rush'")
    framework: str = Field(description="One of: problem_solution, feature_callout, social_proof, us_vs_them, lifestyle_hero")
    concept_source: List[str] = Field(default_factory=list, description="IDs of inspiration sources: Meta refs (e.g. R1), Pinterest tokens (e.g. S1), or pattern library IDs")
    product_index: int = Field(default=0, description="Index of the product from the uploaded products list")
    proof_ids: List[str] = Field(default_factory=list, description="IDs of claims from the proof bank used in copy (e.g. ['P1'])")
    market: str = Field(default="US/en", description="Target market code, e.g. US/en, IN/en")
    scene_direction: str = Field(description="Visual art direction for the scene: setting, props, mood, lighting")
    copy: StaticCopy


class VideoCopy(BaseModel):
    hook_line: str = Field(description="Opening hook spoken or shown in first 2-3 seconds")
    voiceover: str = Field(description="Continuous spoken script fitting 10 seconds, roughly 22-25 words, ~2.5 words/s")
    on_screen_text: List[str] = Field(default_factory=list, description="Text overlays on screen per beat, each <= 5 words")
    primary_text: str = Field(description="Caption above the ad, 1-3 sentences")
    meta_headline: str = Field(description="Ads Manager headline field, <= 40 characters")
    cta: str = Field(description="Closing call to action, <= 3 words")


class VideoBeatBrief(BaseModel):
    time: str = Field(description="Timestamp range, e.g. '0-3s', '3-7s', '7-10s'")
    visual: str = Field(description="What happens visually in this beat")
    on_screen_text: str = Field(default="", description="Text overlay for this beat, <= 5 words")
    audio: str = Field(description="Sound effect, ambient sound, or VO line for this beat")


class VideoBrief(BaseModel):
    id: str = Field(description="Unique brief ID, e.g. V01, V02")
    persona: str = Field(description="Target persona ID or name")
    stage: str = Field(description="Awareness stage: unaware, problem_aware, solution_aware, product_aware, or most_aware")
    format: str = Field(description="One of: ugc, demo, motion_graphics")
    angle: str = Field(description="Creative angle name")
    hook_mechanic_from: str = Field(default="", description="Reference ad ID (e.g. V1) or pattern ID that inspired the hook mechanic")
    product_indexes: List[int] = Field(default_factory=lambda: [0], description="List of product indices featured")
    proof_ids: List[str] = Field(default_factory=list, description="IDs of claims from proof bank used in VO or on-screen text")
    market: str = Field(default="US/en", description="Target market code")
    duration_s: int = Field(default=10, description="Video duration in seconds")
    beats: List[VideoBeatBrief] = Field(description="3-4 structured timeline beats covering 0-10 seconds")
    copy: VideoCopy


class TestGroup(BaseModel):
    ad_set: str = Field(description="Ad set name, e.g. AS1, AS2")
    variable: str = Field(description="Single variable being tested: hook, angle, format, stage, or product")
    creatives: List[str] = Field(description="List of brief IDs in this test set, e.g. ['S01', 'S02', 'S03']")
    hypothesis: str = Field(description="Hypothesis for this test set")


class CampaignMatrix(BaseModel):
    statics: List[StaticBrief]
    videos: List[VideoBrief]
    test_plan: List[TestGroup]


# Smaller schemas for batched generation
class StaticsBatch(BaseModel):
    statics: List[StaticBrief]


class VideosBatch(BaseModel):
    videos: List[VideoBrief]


class TestPlanBatch(BaseModel):
    test_plan: List[TestGroup]


# ---------------------------------------------------------------------------
# Strategist Engine
# ---------------------------------------------------------------------------
class CreativeStrategist:
    """Builds campaign matrices with strict grounding, copy ownership, and test plans."""

    def __init__(self, client: genai.Client):
        self.client = client

    def _format_context(
        self,
        brand_profile: Dict[str, Any],
        meta_refs: Optional[Dict[str, Any]] = None,
        style_tokens: Optional[Dict[str, Any]] = None,
        brand_memory: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Assembles rich context string from all upstream inputs."""
        lines = []

        brand_name = brand_profile.get("brand_name", "")
        product_name = brand_profile.get("product_name", "")
        category = brand_profile.get("product_category", "")
        lines.append(f"BRAND: {brand_name} | PRODUCT: {product_name} | CATEGORY: {category}")

        # Products catalog
        products = brand_profile.get("products", [])
        if products:
            lines.append("\nAVAILABLE PRODUCTS:")
            for p in products:
                lines.append(f"  [{p.get('index', 0)}] {p.get('name', 'Product')}: {p.get('lock', '')[:200]}")

        # Market
        markets = brand_profile.get("markets", [])
        if markets and isinstance(markets, list) and len(markets) > 0:
            m = markets[0]
            lines.append(f"\nMARKET: {m.get('country')} ({m.get('country_code')}) | Language: {m.get('language')} | Currency: {m.get('currency')}")

        # Brand Voice Rules
        voice = brand_profile.get("voice", {})
        if voice:
            lines.append("\nBRAND VOICE RULES:")
            lines.append(f"  Tone: {voice.get('tone')}")
            lines.append(f"  Address as: {voice.get('address_as')}")
            lines.append(f"  Reading level: {voice.get('reading_level')}")
            lines.append(f"  Uses emoji: {'Yes' if voice.get('uses_emoji') else 'No'}")
            use_words = voice.get("use_words", [])
            if use_words:
                lines.append(f"  Vocabulary to USE: {', '.join(use_words)}")
            avoid_words = voice.get("avoid_words", [])
            if avoid_words:
                lines.append(f"  NEVER USE (instant fail): {', '.join(avoid_words)}")
            samples = voice.get("sample_lines", [])
            if samples:
                lines.append("  Sample lines from site:")
                for s in samples[:4]:
                    lines.append(f'    - "{s}"')

        # Proof Bank (Strict: only these claims may be made)
        proof_bank = brand_profile.get("proof_bank", [])
        if proof_bank:
            lines.append("\nPROOF BANK (Strict: only cite claims from this list; use proof_ids):")
            for c in proof_bank:
                lines.append(f"  [{c.get('id', '')}] ({c.get('type', 'claim')}) {c.get('claim', '')}")
        else:
            lines.append("\nPROOF BANK: (none recorded - no factual claims permitted)")

        # Customer Language / Review Themes
        themes = brand_profile.get("review_themes", [])
        if themes:
            lines.append("\nCUSTOMER LANGUAGE (verbatim review quotes for hooks):")
            for t in themes[:6]:
                quotes = ' / '.join(f'"{q}"' for q in (t.get('customer_phrases') or [])[:3])
                lines.append(f"  - [{t.get('theme_type')}]: {t.get('summary')} -> {quotes}")

        # Bullseye Persona
        bs = brand_profile.get("bullseye_target", {})
        if bs:
            lines.append(f"\nPRIMARY PERSONA: {bs.get('persona_name')}, {bs.get('age')}, {bs.get('occupation')} in {bs.get('location')}")
            lines.append(f"  Snapshot: {bs.get('snapshot')}")
            lines.append(f"  Trigger moment: {bs.get('trigger_moment')}")
            lines.append(f"  Core pain: {bs.get('core_pain')}")
            lines.append(f"  Core desire: {bs.get('core_desire')}")
            lines.append(f"  Casting: {bs.get('casting_description')}")

        # Meta References (A3)
        if meta_refs:
            signal = meta_refs.get("signal", "none")
            lines.append(f"\nMETA AD REFS (Competitor Signal: {signal}):")
            for r in (meta_refs.get("image_refs") or [])[:8]:
                lines.append(f"  [{r.get('id')}] {r.get('competitor')}: {r.get('angle')} | Hook: {r.get('hook')} | Days running: {r.get('days_running')}")
            for v in (meta_refs.get("video_refs") or [])[:6]:
                lines.append(f"  [{v.get('id')}] {v.get('competitor')}: {v.get('format', 'video')} | Hook: {v.get('hook')} | Days running: {v.get('days_running')}")

            syn = meta_refs.get("synthesis", {})
            if syn:
                sat = syn.get("saturated", [])
                if sat:
                    lines.append(f"  Saturated territory to AVOID: {', '.join(sat[:4])}")
                ws = syn.get("whitespace", [])
                if ws:
                    lines.append(f"  White space to OWN: {', '.join(ws[:4])}")

        # Pinterest Style Tokens (A4)
        if style_tokens:
            tokens = style_tokens.get("tokens", [])
            if tokens:
                lines.append("\nPINTEREST STYLE TOKENS:")
                for t in tokens[:6]:
                    lines.append(f"  [{t.get('id')}] {t.get('trend_tag')}: {t.get('composition')} | Light: {t.get('lighting')}")

        # Brand Memory (Rejections & Preferences)
        if brand_memory:
            rejections = brand_memory.get("rejections", [])
            if rejections:
                lines.append("\nBRAND MEMORY (Previously rejected - NEVER repeat):")
                for r in rejections[-5:]:
                    lines.append(f"  - Avoid: {r.get('reason')} ({r.get('angle', '')})")

        return "\n".join(lines)

    async def generate_statics_batch(
        self,
        context: str,
        start_id: int,
        count: int,
        awareness_stage: str,
        market: str = "US/en",
    ) -> List[StaticBrief]:
        """Generates a batch of StaticBriefs focused on one awareness stage."""
        prompt = (
            "You are the Creative Strategist for a launch-ready ad campaign.\n"
            "Generate high-converting STATIC AD BRIEFS for the following brand.\n"
            "YOU OWN ALL COPY: Write final, polished copy for each brief.\n\n"
            f"{context}\n\n"
            f"REQUIREMENTS FOR THIS BATCH:\n"
            f"- Generate exactly {count} StaticBrief objects starting with ID S{start_id:02d}.\n"
            f"- Target awareness stage: '{awareness_stage}'\n"
            f"- Market: {market}\n"
            "- Spread across different frameworks: problem_solution, feature_callout, social_proof, us_vs_them, lifestyle_hero.\n"
            "- Concept source: cite Meta refs (e.g. R1, R2), Pinterest tokens, or patterns if available.\n"
            "- Proof IDs: every claim in copy MUST reference an ID from the PROOF BANK (e.g. ['P1']). If no claim made, use empty list [].\n"
            "- Copy constraints:\n"
            "  * image_headline: <= 6 words, punchy, in brand voice. No fluff.\n"
            "  * cta: <= 3 words (e.g. 'Shop Now', 'Claim Yours').\n"
            "  * primary_text: 1-3 short punchy sentences.\n"
            "  * meta_headline: <= 40 characters.\n"
            "  * NEVER use words from the avoid_words list.\n"
            "  * Never invent statistics, awards, or medical claims.\n"
            "- CRITICAL CASTING & PROMPT RULE: In scene_direction, NEVER use proper personal names (e.g. do NOT use 'Ananya', 'Sarah', etc.). Always describe talent anonymously using demographic and situational descriptors (e.g. 'A 24-year-old South Asian woman in smart-casual office wear', 'A young commuter'). NEVER request, imply, or describe celebrity likeness, famous actors, or glamorous influencers. Keep talent looking like relatable everyday real customers with natural skin texture.\n"
            "- PERSONA DIVERSITY: Do not assign the exact same persona name to every single brief. Vary the persona name and customer sub-segment (e.g., college commuter, corporate professional, outdoor traveler, young parent, weekend athlete) across angles and awareness stages to represent real audience segments.\n"
        )

        response = await asyncio.to_thread(
            self.client.models.generate_content,
            model=TEXT_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=StaticsBatch,
                temperature=0.7,
            ),
        )
        batch = json.loads(response.text)
        return [StaticBrief(**s) for s in batch.get("statics", [])]

    async def generate_videos_batch(
        self,
        context: str,
        start_id: int,
        count: int,
        awareness_stage: str,
        video_format: str,
        market: str = "US/en",
    ) -> List[VideoBrief]:
        """Generates a batch of VideoBriefs focused on one stage and format."""
        prompt = (
            "You are the Creative Strategist for a launch-ready Meta Reels / TikTok ad campaign.\n"
            "Generate 10-SECOND VERTICAL VIDEO BRIEFS.\n"
            "YOU OWN ALL COPY: Write final, polished voiceover and on-screen text.\n\n"
            f"{context}\n\n"
            f"REQUIREMENTS FOR THIS BATCH:\n"
            f"- Generate exactly {count} VideoBrief objects starting with ID V{start_id:02d}.\n"
            f"- Target awareness stage: '{awareness_stage}'\n"
            f"- Video format: '{video_format}' (ugc, demo, or motion_graphics)\n"
            f"- Market: {market}\n"
            "- Beats: 3 to 4 timeline beats covering 0-10 seconds (e.g. 0-3s hook, 3-7s demo/benefit, 7-10s CTA).\n"
            "- Copy constraints:\n"
            "  * hook_line: the first 2-3 seconds hook line.\n"
            "  * voiceover: ~22-25 words total (fits 10 seconds, roughly 2.5 words/second). Natural spoken tone.\n"
            "  * on_screen_text: <= 5 words per beat overlay.\n"
            "  * meta_headline: <= 40 characters.\n"
            "  * cta: <= 3 words.\n"
            "  * Proof IDs: cited from PROOF BANK only.\n"
            "  * NEVER use avoid_words.\n"
            "- CRITICAL CASTING & PROMPT RULE: In beats (the visual field) and copy, NEVER use proper character names (e.g. do NOT write 'Ananya steps off...', 'Sarah in the office...'). Always describe people anonymously (e.g. 'A 25-year-old woman in casual office wear', 'A young commuter'). NEVER request, imply, or describe celebrity likeness, famous actors, or glamorous influencers. Keep talent relatable with natural unretouched skin.\n"
            "- PERSONA DIVERSITY: Vary persona names and sub-segments across briefs to match the angle and awareness stage.\n"
        )

        response = await asyncio.to_thread(
            self.client.models.generate_content,
            model=TEXT_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=VideosBatch,
                temperature=0.7,
            ),
        )
        batch = json.loads(response.text)
        return [VideoBrief(**v) for v in batch.get("videos", [])]

    async def generate_test_plan(
        self,
        context: str,
        statics: List[StaticBrief],
        videos: List[VideoBrief],
    ) -> List[TestGroup]:
        """Groups briefs into rigorous A/B test ad sets changing ONE variable at a time."""
        static_ids = [s.id for s in statics]
        video_ids = [v.id for v in videos]

        prompt = (
            "You are a Senior Performance Marketing Media Buyer.\n"
            "Create a structured META ADS TEST PLAN grouping the generated briefs into ad sets.\n"
            "Core principle: Change ONE variable at a time per ad set (e.g., Hook test, Angle test, Format test, Stage test).\n\n"
            f"Available Static Creative IDs: {', '.join(static_ids)}\n"
            f"Available Video Creative IDs: {', '.join(video_ids)}\n\n"
            "REQUIREMENTS:\n"
            "- Create 6 to 10 TestGroup objects.\n"
            "- Group 3 to 5 creatives per ad set.\n"
            "- Name the variable being tested: 'hook', 'angle', 'format', 'stage', or 'product'.\n"
            "- State a clear testing hypothesis for each group.\n"
        )

        response = await asyncio.to_thread(
            self.client.models.generate_content,
            model=TEXT_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=TestPlanBatch,
                temperature=0.7,
            ),
        )
        batch = json.loads(response.text)
        return [TestGroup(**t) for t in batch.get("test_plan", [])]

    async def build_campaign_matrix(
        self,
        brand_profile: Dict[str, Any],
        meta_refs: Optional[Dict[str, Any]] = None,
        style_tokens: Optional[Dict[str, Any]] = None,
        brand_memory: Optional[Dict[str, Any]] = None,
        target_statics: int = 25,
        target_videos: int = 25,
    ) -> CampaignMatrix:
        """
        Orchestrates full matrix generation across stages and formats.
        Runs batches concurrently to produce >=25 statics and >=25 videos + test plan.
        """
        context = self._format_context(brand_profile, meta_refs, style_tokens, brand_memory)
        market_code = "US/en"
        markets = brand_profile.get("markets", [])
        if markets and isinstance(markets, list) and len(markets) > 0:
            m = markets[0]
            market_code = f"{m.get('country_code', 'US')}/{m.get('language', 'en')}"

        # Stage distribution for statics (5 stages × 5 = 25)
        static_tasks = []
        static_batch_size = max(1, target_statics // len(AWARENESS_STAGES))
        for i, stage in enumerate(AWARENESS_STAGES):
            count = static_batch_size if i < len(AWARENESS_STAGES) - 1 else (target_statics - static_batch_size * (len(AWARENESS_STAGES) - 1))
            start_id = i * static_batch_size + 1
            static_tasks.append(
                self.generate_statics_batch(context, start_id, count, stage, market_code)
            )

        # Video format distribution (e.g. 10 UGC, 9 Demo, 6 Motion Graphics = 25)
        video_configs = [
            ("problem_aware", "ugc", 5),
            ("solution_aware", "ugc", 5),
            ("product_aware", "demo", 5),
            ("most_aware", "demo", 5),
            ("unaware", "motion_graphics", 5),
        ]
        # Adjust last batch count to match target_videos
        total_vid_configured = sum(c[2] for c in video_configs)
        if total_vid_configured != target_videos and video_configs:
            diff = target_videos - total_vid_configured
            stage, fmt, c = video_configs[-1]
            video_configs[-1] = (stage, fmt, max(1, c + diff))

        video_tasks = []
        curr_vid_id = 1
        for stage, fmt, count in video_configs:
            video_tasks.append(
                self.generate_videos_batch(context, curr_vid_id, count, stage, fmt, market_code)
            )
            curr_vid_id += count

        logger.info(f"[A5/Strategist] Generating {target_statics} statics and {target_videos} videos concurrently...")
        static_results, video_results = await asyncio.gather(
            asyncio.gather(*static_tasks, return_exceptions=True),
            asyncio.gather(*video_tasks, return_exceptions=True),
        )

        all_statics: List[StaticBrief] = []
        for r in static_results:
            if isinstance(r, list):
                all_statics.extend(r)
            else:
                logger.warning(f"[A5/Strategist] A statics batch failed: {r}")

        all_videos: List[VideoBrief] = []
        for r in video_results:
            if isinstance(r, list):
                all_videos.extend(r)
            else:
                logger.warning(f"[A5/Strategist] A videos batch failed: {r}")

        # Renumber to ensure strictly sequential IDs
        for idx, s in enumerate(all_statics, start=1):
            s.id = f"S{idx:02d}"
        for idx, v in enumerate(all_videos, start=1):
            v.id = f"V{idx:02d}"

        logger.info(f"[A5/Strategist] Assembling test plan for {len(all_statics)} statics and {len(all_videos)} videos...")
        test_plan = await self.generate_test_plan(context, all_statics, all_videos)

        return CampaignMatrix(
            statics=all_statics,
            videos=all_videos,
            test_plan=test_plan,
        )
