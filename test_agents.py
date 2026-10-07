"""
Unit and integration test suite for Step 3 agents:
- A5 Creative Strategist (creative_strategist.py)
- A6 Static Prompt Writer & A7 Video Script Writer (prompt_writers.py)
- A8 Creative Director (creative_director.py)
"""

import asyncio
import json
from unittest.mock import MagicMock, AsyncMock

from creative_strategist import (
    CreativeStrategist,
    StaticBrief,
    StaticCopy,
    VideoBrief,
    VideoCopy,
    VideoBeatBrief,
    TestGroup,
    CampaignMatrix,
)
from prompt_writers import (
    StaticPromptWriter,
    VideoScriptWriter,
    build_omni_prompt,
)
from creative_director import (
    CreativeDirector,
    RubricReview,
    CriterionScore,
)


def test_models_serialization():
    """Verify all Pydantic models serialize and deserialize according to spec."""
    s_copy = StaticCopy(
        image_headline="Zero White Cast SPF 50",
        cta="Shop Now",
        primary_text="Tired of greasy sunscreen? Protect your skin effortlessly.",
        meta_headline="Zero White Cast SPF 50",
        description="Daily dewy glow",
    )
    s_brief = StaticBrief(
        id="S01",
        persona="P1",
        stage="problem_aware",
        angle="Tired of White Cast",
        framework="problem_solution",
        concept_source=["R1", "S1"],
        product_index=0,
        proof_ids=["P1"],
        market="US/en",
        scene_direction="Clean bathroom mirror morning light, holding product",
        copy=s_copy,
    )

    v_copy = VideoCopy(
        hook_line="Stop ruining your makeup with heavy SPF.",
        voiceover="This ultra-light sunscreen absorbs in seconds with zero white cast and no greasy residue. Try it today.",
        on_screen_text=["Zero White Cast", "Absorbs in 3s", "Shop Now"],
        primary_text="The viral sunscreen that doesn't ruin your foundation.",
        meta_headline="Zero White Cast SPF 50",
        cta="Shop Now",
    )
    v_beats = [
        VideoBeatBrief(time="0-3s", visual="Talent wipes white cream off face with frustration", on_screen_text="Stop ruining your makeup", audio="Sigh sound"),
        VideoBeatBrief(time="3-7s", visual="Applies Dot & Key sunscreen; absorbs invisibly", on_screen_text="Invisible in 3 seconds", audio="Satisfying whoosh"),
        VideoBeatBrief(time="7-10s", visual="Flawless finish smile with product bottle in hand", on_screen_text="Shop Now", audio="Upbeat jingle"),
    ]
    v_brief = VideoBrief(
        id="V01",
        persona="P1",
        stage="problem_aware",
        format="ugc",
        angle="Commuter Morning Rush",
        hook_mechanic_from="V1",
        product_indexes=[0],
        proof_ids=["P1"],
        market="US/en",
        beats=v_beats,
        copy=v_copy,
    )

    t_group = TestGroup(
        ad_set="AS1",
        variable="hook",
        creatives=["S01", "S02", "S03"],
        hypothesis="Tactile sensory hook beats frustration hook for problem-aware audience",
    )

    matrix = CampaignMatrix(
        statics=[s_brief],
        videos=[v_brief],
        test_plan=[t_group],
    )

    matrix_json = matrix.model_dump_json()
    parsed = json.loads(matrix_json)

    assert len(parsed["statics"]) == 1
    assert parsed["statics"][0]["id"] == "S01"
    assert parsed["statics"][0]["copy"]["image_headline"] == "Zero White Cast SPF 50"
    assert len(parsed["videos"]) == 1
    assert parsed["videos"][0]["id"] == "V01"
    assert len(parsed["test_plan"]) == 1
    assert parsed["test_plan"][0]["variable"] == "hook"
    print("[PASS] Model serialization and JSON validation passed.")


def test_omni_prompt_builder():
    """Verify Omni Flash prompt builder binds product locks, beats, and avoid rules."""
    prompt = build_omni_prompt(
        brand_name="Dot & Key",
        product_name="Watermelon Sunscreen SPF 50",
        featured_products=[{"name": "Watermelon SPF", "lock": "matte yellow pump bottle with watermelon decal"}],
        casting_description="Young female, natural skin, 20s",
        brand_kit={"primary_hex": "#FF6B81", "accent_hex": "#FFC107", "background_hex": "#FFFFFF", "visual_mood": "playful pastel"},
        beats=[{"time": "0-2s", "visual": "Applies pump on cheek", "on_screen_text": "Zero Cast", "audio": "Pop"}],
        voiceover="Never worry about white cast again. Absorbs invisibly.",
        direction="UGC style close-up selfie angle",
    )
    assert "10-second vertical 9:16 Meta Reels ad" in prompt
    assert "<IMAGE_REF_0> is matte yellow pump bottle" in prompt
    assert "CASTING: Young female" in prompt
    assert "BRAND LOOK: playful pastel" in prompt
    assert 'VOICEOVER (natural conversational tone, matches timeline): "Never worry about white cast again. Absorbs invisibly."' in prompt
    assert "AVOID:" in prompt
    print("[PASS] Omni Flash prompt builder correctly structures references and timelines.")


def test_creative_director_hard_checks():
    """Verify CreativeDirector catches prohibited words and unverified proof claims."""
    mock_client = MagicMock()
    director = CreativeDirector(mock_client)

    bad_image_ad = {
        "id": "img_01",
        "headline": "Cheap discount skincare",
        "image_headline": "Cheap deal",
        "cta": "Buy Now",
        "primary_text": "This is a cheap miracle cure.",
        "scene": "A model in bathroom",
        "product_name": "Moisturizer",
        "proof_ids": ["P99"],  # unverified proof id
    }

    initial_review = RubricReview(
        prompt_id="img_01",
        product_fidelity=CriterionScore(score=5, reasoning="Good"),
        url_grounding=CriterionScore(score=5, reasoning="Good"),
        brand_fit=CriterionScore(score=5, reasoning="Good"),
        persona_stage_fit=CriterionScore(score=5, reasoning="Good"),
        hook_strength=CriterionScore(score=5, reasoning="Good"),
        trend_fit=CriterionScore(score=5, reasoning="Good"),
        distinctness=CriterionScore(score=5, reasoning="Good"),
        executability=CriterionScore(score=5, reasoning="Good"),
        average_score=5.0,
        passed=True,
        rewrite_notes="",
    )

    avoid_words = ["cheap", "miracle"]
    verified_proof_ids = {"P1", "P2"}

    mock_response = MagicMock()
    mock_response.text = json.dumps({"reviews": [initial_review.model_dump()]})
    mock_client.models.generate_content.return_value = mock_response

    reviews = asyncio.run(director.review_prompts_batch(
        [bad_image_ad],
        context="Brand test context",
        avoid_words=avoid_words,
        proof_ids=verified_proof_ids,
    ))

    assert len(reviews) == 1
    rev = reviews[0]

    assert rev.brand_fit.score == 1
    assert "cheap" in rev.brand_fit.reasoning

    assert rev.url_grounding.score == 2
    assert "P99" in rev.url_grounding.reasoning

    assert rev.passed is False
    assert rev.brand_fit.score < 3
    assert rev.url_grounding.score < 3
    assert "Remove prohibited words" in rev.rewrite_notes
    assert "Remove unverified proof IDs" in rev.rewrite_notes
    print("[PASS] CreativeDirector hard checks successfully caught prohibited words and invalid proof IDs.")


def test_creative_director_rewrite_loop():
    """Verify CreativeDirector runs rewrite loop when a creative initially fails."""
    mock_client = MagicMock()
    director = CreativeDirector(mock_client)

    bad_ad = {
        "id": "S01",
        "brief_id": "S01",
        "headline": "Morning Hydration",
        "image_headline": "Dewy Skin",
        "cta": "Shop Now",
        "primary_text": "Get glow today.",
        "blueprint": {
            "headline": "Morning Hydration",
            "image_headline": "Dewy Skin",
            "cta": "Shop Now",
            "primary_text": "Get glow today.",
            "visual_prompt": "Bottle on white table.",
        },
        "product_name": "Moisturizer",
        "proof_ids": [],
    }

    # Pass 1: fails
    fail_review = RubricReview(
        prompt_id="S01",
        product_fidelity=CriterionScore(score=4, reasoning="Ok"),
        url_grounding=CriterionScore(score=4, reasoning="Ok"),
        brand_fit=CriterionScore(score=4, reasoning="Ok"),
        persona_stage_fit=CriterionScore(score=4, reasoning="Ok"),
        hook_strength=CriterionScore(score=2, reasoning="Too generic, white table is boring"),
        trend_fit=CriterionScore(score=2, reasoning="No styling"),
        distinctness=CriterionScore(score=4, reasoning="Ok"),
        executability=CriterionScore(score=4, reasoning="Ok"),
        average_score=3.5,
        passed=False,
        rewrite_notes="Change setting to morning sunlit bathroom with macro water droplets.",
    )

    # Pass 2: passes
    pass_review = RubricReview(
        prompt_id="S01",
        product_fidelity=CriterionScore(score=5, reasoning="Great"),
        url_grounding=CriterionScore(score=5, reasoning="Great"),
        brand_fit=CriterionScore(score=5, reasoning="Great"),
        persona_stage_fit=CriterionScore(score=4, reasoning="Great"),
        hook_strength=CriterionScore(score=5, reasoning="Scroll-stopping macro drops"),
        trend_fit=CriterionScore(score=4, reasoning="Modern aesthetic"),
        distinctness=CriterionScore(score=4, reasoning="Distinct"),
        executability=CriterionScore(score=5, reasoning="Valid"),
        average_score=4.62,
        passed=True,
        rewrite_notes="",
    )

    mock_client.models.generate_content.side_effect = [
        MagicMock(text=json.dumps({"reviews": [fail_review.model_dump()]})),
        MagicMock(text=json.dumps({"reviews": [pass_review.model_dump()]})),
    ]

    mock_writer = MagicMock()
    async def mock_rewrite(brief, ad, notes, brand, refs):
        new_ad = dict(ad)
        new_ad["blueprint"] = dict(ad["blueprint"])
        new_ad["blueprint"]["visual_prompt"] = "Morning sunlit bathroom with macro water droplets."
        return new_ad

    mock_writer.rewrite_static = AsyncMock(side_effect=mock_rewrite)

    mock_brief = StaticBrief(
        id="S01",
        persona="P1",
        stage="problem_aware",
        angle="Dry Skin",
        framework="problem_solution",
        concept_source=[],
        product_index=0,
        proof_ids=[],
        market="US/en",
        scene_direction="Bottle on table",
        copy=StaticCopy(
            image_headline="Dewy Skin",
            cta="Shop Now",
            primary_text="Get glow today.",
            meta_headline="Morning Hydration",
        ),
    )

    result = asyncio.run(director.audit_and_refine(
        image_ads=[bad_ad],
        video_ads=[],
        brand_profile={"brand_name": "Test Brand", "voice": {}, "proof_bank": []},
        static_writer=mock_writer,
        static_briefs=[mock_brief],
        max_loops=2,
    ))

    # Assert rewrite happened
    assert mock_writer.rewrite_static.called
    assert result["stats"]["total_rewrites"] == 1
    assert result["stats"]["passed_images"] == 1
    assert result["image_ads"][0]["critic_review"]["passed"] is True
    assert len(result["image_ads"][0]["rewrite_history"]) == 1
    print("[PASS] CreativeDirector successfully executed rewrite loop and recovered failing ad to passing score.")


if __name__ == "__main__":
    test_models_serialization()
    test_omni_prompt_builder()
    test_creative_director_hard_checks()
    test_creative_director_rewrite_loop()
    print("\nALL STEP 3 TESTS PASSED PERFECTLY!")
