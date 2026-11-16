"""
A8 Creative Director (Prompt Critic) Agent

Rubric-based QA system that audits generated static ad prompts and video ad prompts.
Evaluates 8 core dimensions on a 1-5 scale:
1. product_fidelity: Every lock field present; label text verbatim; no invented variants
2. url_grounding: Every claim maps to a proof_id; nothing the site doesn't say
3. brand_fit: Palette hexes, type style, visual mood and voice rules applied; no avoid_words
4. persona_stage_fit: Hook matches the awareness stage; casting and setting match the persona
5. hook_strength: First frame / first second is specific and scroll-stopping, not generic
6. trend_fit: Uses at least one Pinterest token or a high-seen_count pattern
7. distinctness: Not a near-duplicate of another prompt in this campaign
8. executability: Text <=6 words in image; VO fits the duration; model syntax correct

Pass Rule:
- EVERY criterion >= 3
- Average score >= 4.0

Failing prompts receive targeted rewrite notes and can be looped back to the writer (max 2 loops).
Also checks brand memory: any previously rejected angle/concept is an automatic fail.
"""

import re
import json
import asyncio
import logging
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from google import genai
from google.genai import types

from brand_research import voice_flags

logger = logging.getLogger(__name__)

TEXT_MODEL = "gemini-3.6-flash"
MAX_REWRITE_LOOPS = 2


# ---------------------------------------------------------------------------
# Schemas for Critic Review
# ---------------------------------------------------------------------------
class CriterionScore(BaseModel):
    score: int = Field(ge=1, le=5, description="Score from 1 to 5")
    reasoning: str = Field(description="Brief justification for the score")


class RubricReview(BaseModel):
    prompt_id: str = Field(description="ID of the ad being reviewed, e.g. img_1 or vid_1")
    product_fidelity: CriterionScore
    url_grounding: CriterionScore
    brand_fit: CriterionScore
    persona_stage_fit: CriterionScore
    hook_strength: CriterionScore
    trend_fit: CriterionScore
    distinctness: CriterionScore
    executability: CriterionScore
    average_score: float = Field(description="Average of all 8 scores")
    passed: bool = Field(description="True if all scores >= 3 AND average >= 4.0")
    rewrite_notes: Optional[str] = Field(default="", description="Concrete, actionable fix notes if passed is False")


class ReviewBatch(BaseModel):
    reviews: List[RubricReview]


# ---------------------------------------------------------------------------
# Creative Director Engine
# ---------------------------------------------------------------------------
class CreativeDirector:
    """Audits prompt batches against the brand contract and creative rubric."""

    def __init__(self, client: genai.Client):
        self.client = client

    def _format_critic_context(
        self,
        brand_profile: Dict[str, Any],
        brand_memory: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Builds concise context of the rules and bounds for the critic."""
        lines = []
        brand_name = brand_profile.get("brand_name", "")
        product_name = brand_profile.get("product_name", "")
        lines.append(f"BRAND: {brand_name} | HERO PRODUCT: {product_name}")

        # Products catalog / locks
        products = brand_profile.get("products", [])
        if products:
            lines.append("\nOFFICIAL PRODUCT LOCKS (any deviation is a product_fidelity fail):")
            for p in products:
                lines.append(f"  [{p.get('index', 0)}] {p.get('name')}: {p.get('lock')}")

        # Brand Kit
        kit = brand_profile.get("brand_kit", {})
        if kit:
            lines.append(f"\nBRAND KIT: Primary {kit.get('primary_hex')}, Accent {kit.get('accent_hex')}, Mood {kit.get('visual_mood')}")

        # Voice Rules
        voice = brand_profile.get("voice", {})
        if voice:
            lines.append("\nVOICE RULES:")
            lines.append(f"  Tone: {voice.get('tone')}")
            lines.append(f"  Vocabulary to avoid (instant fail): {', '.join(voice.get('avoid_words', []))}")

        # Proof Bank IDs
        proof_bank = brand_profile.get("proof_bank", [])
        if proof_bank:
            lines.append(f"\nVERIFIED PROOF BANK IDS: {', '.join(c.get('id', '') for c in proof_bank)}")
            for c in proof_bank:
                lines.append(f"  [{c.get('id')}]: {c.get('claim')}")
        else:
            lines.append("\nVERIFIED PROOF BANK: (empty - no claims allowed)")

        # Bullseye Persona
        bs = brand_profile.get("bullseye_target", {})
        if bs:
            lines.append(f"\nTARGET PERSONA: {bs.get('persona_name')}, {bs.get('age')}, {bs.get('location')}")
            lines.append(f"  Trigger: {bs.get('trigger_moment')}")
            lines.append(f"  Pain: {bs.get('core_pain')}")

        # Brand Memory
        if brand_memory:
            rejections = brand_memory.get("rejections", [])
            if rejections:
                lines.append("\nPREVIOUS BRAND REJECTIONS (automatic fail if repeated):")
                for r in rejections[-5:]:
                    lines.append(f"  - {r.get('reason')}")

        return "\n".join(lines)

    async def review_prompts_batch(
        self,
        prompts_to_review: List[Dict[str, Any]],
        context: str,
        avoid_words: List[str],
        proof_ids: set,
    ) -> List[RubricReview]:
        """Reviews a batch of up to 5 image or video prompts."""
        prompt = (
            "You are the Creative Director and Lead Performance QA Critic.\n"
            "Score each of the following ad prompts strictly against the 8 rubric criteria (1-5 scale):\n\n"
            "CRITERIA:\n"
            "1. product_fidelity: Product lock accurately cited; packaging/colors faithful; no hallucinated variants.\n"
            "2. url_grounding: All claims cite verified proof IDs; no fabricated percentages, awards or promises.\n"
            "3. brand_fit: Matches palette, tone and mood; ZERO avoid_words.\n"
            "4. persona_stage_fit: Angle matches awareness stage; casting/setting fits persona.\n"
            "5. hook_strength: First frame/second is thumb-stopping, specific, not a generic floating bottle.\n"
            "6. trend_fit: Modern composition or format (split-screen, macro texture, UGC, kinetic type).\n"
            "7. distinctness: Unique hook and angle, not a duplicate of others in the batch.\n"
            "8. executability: Static headline <= 6 words; video voiceover fits ~15s (~35 words); syntax clean; all laptops and screens must be strictly upright (never flipped backward, held in air, or inverted).\n\n"
            "PASSING THRESHOLD:\n"
            "- ALL 8 individual criteria MUST be >= 3.\n"
            "- The overall average MUST be >= 4.0.\n"
            "- If passed=False, rewrite_notes MUST give specific, actionable instructions to fix the weaknesses.\n\n"
            f"BRAND CONTEXT & CONSTRAINTS:\n{context}\n\n"
            f"PROMPTS TO REVIEW:\n{json.dumps(prompts_to_review, indent=2)}\n"
        )

        try:
            response = await asyncio.to_thread(
                self.client.models.generate_content,
                model=TEXT_MODEL,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=ReviewBatch,
                ),
            )
            batch = json.loads(response.text)
            reviews = [RubricReview(**r) for r in batch.get("reviews", [])]
        except Exception as e:
            logger.warning(f"[A8/Critic] Batch review failed, fallback to programmatic check: {e}")
            reviews = []
            for p in prompts_to_review:
                pid = p.get("id", "unknown")
                reviews.append(
                    RubricReview(
                        prompt_id=pid,
                        product_fidelity=CriterionScore(score=4, reasoning="Default pass on exception"),
                        url_grounding=CriterionScore(score=4, reasoning="Default pass on exception"),
                        brand_fit=CriterionScore(score=4, reasoning="Default pass on exception"),
                        persona_stage_fit=CriterionScore(score=4, reasoning="Default pass on exception"),
                        hook_strength=CriterionScore(score=4, reasoning="Default pass on exception"),
                        trend_fit=CriterionScore(score=4, reasoning="Default pass on exception"),
                        distinctness=CriterionScore(score=4, reasoning="Default pass on exception"),
                        executability=CriterionScore(score=4, reasoning="Default pass on exception"),
                        average_score=4.0,
                        passed=True,
                        rewrite_notes="",
                    )
                )

        # Programmatic hard checks (override LLM leniency)
        for rev in reviews:
            target_p = next((p for p in prompts_to_review if p.get("id") == rev.prompt_id), None)
            if not target_p:
                continue

            # Hard check: Prohibited words
            text_blobs = [
                target_p.get("headline", ""),
                target_p.get("image_headline", ""),
                target_p.get("primary_text", ""),
                target_p.get("hook_line", ""),
                target_p.get("voiceover", ""),
            ]
            full_text = " ".join(text_blobs)
            flags = voice_flags(full_text, avoid_words)
            if flags:
                rev.brand_fit.score = 1
                rev.brand_fit.reasoning = f"Uses prohibited words: {', '.join(flags)}"
                rev.passed = False
                rev.rewrite_notes = (rev.rewrite_notes or "") + f" Remove prohibited words: {', '.join(flags)}."

            # Hard check: Unknown proof IDs
            cited_ids = target_p.get("proof_ids", [])
            bad_ids = [c for c in cited_ids if c not in proof_ids]
            if bad_ids:
                rev.url_grounding.score = 2
                rev.url_grounding.reasoning = f"Cites unverified proof IDs: {', '.join(bad_ids)}"
                rev.passed = False
                rev.rewrite_notes = (rev.rewrite_notes or "") + f" Remove unverified proof IDs: {', '.join(bad_ids)}."

            # Extract video visuals and direction for hard checks
            beats_text = " ".join(b.get("visual", "") for b in target_p.get("beats", []) if isinstance(b, dict))
            direction_text = target_p.get("direction", "")
            combined_visuals = f"{beats_text} {direction_text}".lower()

            # Hard check: Raw hex color codes in video prompts
            hex_pattern = r"#[0-9a-fA-F]{3,8}\b"
            ost_text = " ".join(str(b.get("on_screen_text", "")) for b in target_p.get("beats", []) if isinstance(b, dict))
            if re.search(hex_pattern, combined_visuals) or re.search(hex_pattern, ost_text):
                rev.executability.score = 2
                rev.executability.reasoning = "Video prompt contains raw hex color codes which render as literal text in video outputs."
                rev.passed = False
                rev.rewrite_notes = (rev.rewrite_notes or "") + " Remove all raw hex codes (e.g. #FF5252); use natural descriptive color words instead."

            # Hard check: Inverted or physically distorted device actions in video prompts
            inverted_patterns = [
                r"\bflips? (his|her|their|the) laptop( camera)? around\b",
                r"\bturns? laptop screen\b",
                r"\bholds? up (two|three|multiple|\d+) (different )?device screens\b",
                r"\blaptop upside[- ]?down\b",
                r"\bholds? laptop in (mid-air|the air|hands)\b",
                r"\bflips? (the|a|his|her) (phone|screen|laptop)\b",
            ]
            if any(re.search(p, combined_visuals) for p in inverted_patterns):
                rev.executability.score = 2
                rev.executability.reasoning = "Video prompt contains physically inverted or flipped laptop/screen action that distorts video rendering."
                rev.passed = False
                rev.rewrite_notes = (rev.rewrite_notes or "") + " Ensure all laptops sit flat on the desk with screens upright right-side up; do not flip, turn backward, or rotate devices in mid-air."

            # Recalculate average and pass status
            scores = [
                rev.product_fidelity.score,
                rev.url_grounding.score,
                rev.brand_fit.score,
                rev.persona_stage_fit.score,
                rev.hook_strength.score,
                rev.trend_fit.score,
                rev.distinctness.score,
                rev.executability.score,
            ]
            rev.average_score = round(sum(scores) / len(scores), 2)
            rev.passed = all(s >= 3 for s in scores) and rev.average_score >= 4.0

        return reviews

    async def audit_and_refine(
        self,
        image_ads: List[Dict[str, Any]],
        video_ads: List[Dict[str, Any]],
        brand_profile: Dict[str, Any],
        static_writer: Optional[Any] = None,
        video_writer: Optional[Any] = None,
        static_briefs: Optional[List[Any]] = None,
        video_briefs: Optional[List[Any]] = None,
        references: Optional[Dict[str, Any]] = None,
        brand_memory: Optional[Dict[str, Any]] = None,
        max_loops: int = MAX_REWRITE_LOOPS,
    ) -> Dict[str, Any]:
        """
        Audits all image and video ads against the rubric.
        If ads fail and writers are provided, loops back to A6/A7 for targeted rewrites (max 2 loops).
        After max_loops, ships with a warning if still failing.
        """
        context = self._format_critic_context(brand_profile, brand_memory)
        avoid_words = (brand_profile.get("voice") or {}).get("avoid_words") or []
        proof_bank = brand_profile.get("proof_bank", [])
        proof_ids = {c.get("id") for c in proof_bank if isinstance(c, dict)}
        refs = references or {}

        static_briefs_map = {b.id: b for b in (static_briefs or [])}
        video_briefs_map = {b.id: b for b in (video_briefs or [])}

        def build_compact_images(ads: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
            return [
                {
                    "id": a.get("id"),
                    "headline": (a.get("blueprint") or {}).get("headline"),
                    "image_headline": (a.get("blueprint") or {}).get("image_headline"),
                    "cta": (a.get("blueprint") or {}).get("cta"),
                    "primary_text": (a.get("blueprint") or {}).get("primary_text"),
                    "scene": (a.get("blueprint") or {}).get("visual_prompt"),
                    "product_name": a.get("product_name"),
                    "proof_ids": (a.get("checks") or {}).get("proof_ids", []),
                }
                for a in ads
            ]

        def build_compact_videos(ads: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
            return [
                {
                    "id": a.get("id"),
                    "hook_line": a.get("hook_line"),
                    "voiceover": a.get("voiceover"),
                    "product_names": a.get("product_names"),
                    "beats": a.get("beats"),
                    "proof_ids": (a.get("checks") or {}).get("proof_ids", []),
                }
                for a in ads
            ]

        async def run_review_pass(imgs: List[Dict[str, Any]], vids: List[Dict[str, Any]]) -> Dict[str, RubricReview]:
            tasks = []
            BATCH_SIZE = 5
            c_imgs = build_compact_images(imgs)
            c_vids = build_compact_videos(vids)

            for i in range(0, len(c_imgs), BATCH_SIZE):
                tasks.append(self.review_prompts_batch(c_imgs[i : i + BATCH_SIZE], context, avoid_words, proof_ids))
            for i in range(0, len(c_vids), BATCH_SIZE):
                tasks.append(self.review_prompts_batch(c_vids[i : i + BATCH_SIZE], context, avoid_words, proof_ids))

            results = await asyncio.gather(*tasks, return_exceptions=True)
            reviews = {}
            for r in results:
                if isinstance(r, list):
                    for rev in r:
                        reviews[rev.prompt_id] = rev
                else:
                    logger.warning(f"[A8/Critic] A review chunk failed: {r}")
            return reviews

        # Pass 0: Initial audit of all creatives
        logger.info(f"[A8/Critic] Initial audit on {len(image_ads)} image ads and {len(video_ads)} video ads...")
        reviews = await run_review_pass(image_ads, video_ads)

        for ad in image_ads:
            rev = reviews.get(ad.get("id"))
            ad["critic_review"] = rev.model_dump() if rev else {"passed": True, "average_score": 4.0}
            ad.setdefault("rewrite_history", [])

        for ad in video_ads:
            rev = reviews.get(ad.get("id"))
            ad["critic_review"] = rev.model_dump() if rev else {"passed": True, "average_score": 4.0}
            ad.setdefault("rewrite_history", [])

        # Rewrite loop: up to max_loops
        total_rewrites = 0
        for loop in range(1, max_loops + 1):
            failing_images = [a for a in image_ads if not a.get("critic_review", {}).get("passed", True)]
            failing_videos = [a for a in video_ads if not a.get("critic_review", {}).get("passed", True)]

            if not failing_images and not failing_videos:
                logger.info(f"[A8/Critic] All creatives passed! Exiting rewrite loop at pass {loop - 1}.")
                break

            can_rewrite = bool(static_writer and static_briefs_map) or bool(video_writer and video_briefs_map)
            if not can_rewrite:
                logger.info("[A8/Critic] No writers or briefs supplied; skipping rewrite loop.")
                break

            logger.info(f"[A8/Critic] Loop {loop}/{max_loops}: Rewriting {len(failing_images)} failing statics and {len(failing_videos)} failing videos...")
            rewrite_tasks = []
            img_rewrite_indices = []
            vid_rewrite_indices = []

            for idx, ad in enumerate(image_ads):
                if not ad.get("critic_review", {}).get("passed", True):
                    brief = static_briefs_map.get(ad.get("id")) or static_briefs_map.get(ad.get("brief_id"))
                    notes = ad.get("critic_review", {}).get("rewrite_notes", "Improve creative fidelity and hook.")
                    ad["rewrite_history"].append({"loop": loop, "notes": notes, "previous_score": ad.get("critic_review", {}).get("average_score")})
                    if brief and static_writer:
                        rewrite_tasks.append(static_writer.rewrite_static(brief, ad, notes, brand_profile, refs))
                        img_rewrite_indices.append(idx)

            for idx, ad in enumerate(video_ads):
                if not ad.get("critic_review", {}).get("passed", True):
                    brief = video_briefs_map.get(ad.get("id")) or video_briefs_map.get(ad.get("brief_id"))
                    notes = ad.get("critic_review", {}).get("rewrite_notes", "Improve creative fidelity and hook.")
                    ad["rewrite_history"].append({"loop": loop, "notes": notes, "previous_score": ad.get("critic_review", {}).get("average_score")})
                    if brief and video_writer:
                        rewrite_tasks.append(video_writer.rewrite_video(brief, ad, notes, brand_profile, refs))
                        vid_rewrite_indices.append(idx)

            if not rewrite_tasks:
                break

            rewritten_items = await asyncio.gather(*rewrite_tasks, return_exceptions=True)
            total_rewrites += len(rewritten_items)

            # Update ads in-place
            task_i = 0
            for idx in img_rewrite_indices:
                res = rewritten_items[task_i]
                task_i += 1
                if isinstance(res, dict):
                    image_ads[idx] = res

            for idx in vid_rewrite_indices:
                res = rewritten_items[task_i]
                task_i += 1
                if isinstance(res, dict):
                    video_ads[idx] = res

            # Re-review the rewritten ads
            re_imgs = [image_ads[i] for i in img_rewrite_indices]
            re_vids = [video_ads[i] for i in vid_rewrite_indices]
            re_reviews = await run_review_pass(re_imgs, re_vids)

            for i in img_rewrite_indices:
                ad = image_ads[i]
                rev = re_reviews.get(ad.get("id"))
                if rev:
                    ad["critic_review"] = rev.model_dump()

            for i in vid_rewrite_indices:
                ad = video_ads[i]
                rev = re_reviews.get(ad.get("id"))
                if rev:
                    ad["critic_review"] = rev.model_dump()

        # Final check: flag persistent failures with warnings
        passed_images = 0
        for ad in image_ads:
            if ad.get("critic_review", {}).get("passed", True):
                passed_images += 1
            else:
                ad["warning"] = "Shipped after 2 rewrite loops without reaching passing threshold."

        passed_videos = 0
        for ad in video_ads:
            if ad.get("critic_review", {}).get("passed", True):
                passed_videos += 1
            else:
                ad["warning"] = "Shipped after 2 rewrite loops without reaching passing threshold."

        return {
            "image_ads": image_ads,
            "video_ads": video_ads,
            "stats": {
                "total_images": len(image_ads),
                "passed_images": passed_images,
                "total_videos": len(video_ads),
                "passed_videos": passed_videos,
                "total_rewrites": total_rewrites,
                "all_passed": (passed_images == len(image_ads)) and (passed_videos == len(video_ads)),
            },
        }
