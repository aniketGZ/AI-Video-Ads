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
    assert "15-second vertical 9:16 Meta Reels ad" in prompt
    assert "<IMAGE_REF_0> is matte yellow pump bottle" in prompt
    assert "CASTING: Young female" in prompt
    assert "BRAND LOOK: playful pastel" in prompt
    assert "hot pink" in prompt
    assert "#FF6B81" not in prompt
    assert "#" not in prompt
    assert 'VOICEOVER (natural conversational tone, matches timeline): "Never worry about white cast again. Absorbs invisibly."' in prompt
    assert "AVOID:" in prompt
    assert "raw hex codes" in prompt
    print("[PASS] Omni Flash prompt builder correctly structures references and eliminates hex codes.")


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


def test_anti_celebrity_and_persona_sanitization():
    """Verify that proper persona names are sanitized out of prompts and anti-celebrity guardrails are active."""
    from media_utils import sanitize_visual_prompt
    from ad_templates import build_template_prompt, build_reference_prompt

    # 1. Test name sanitization
    raw_scene = "Ananya stepping off a crowded Delhi Metro platform into bright daylight. Ananya's tote bag is visible."
    cleaned = sanitize_visual_prompt(raw_scene, ["Ananya Sharma", "Ananya"])
    assert "Ananya" not in cleaned
    assert "relatable customer" in cleaned.lower()
    assert "the customer's tote bag" in cleaned.lower()

    # 2. Test Omni prompt AVOID guardrails
    omni_prompt = build_omni_prompt(
        brand_name="Test Brand",
        product_name="Sunscreen",
        featured_products=[],
        casting_description="20s commuter",
        brand_kit={},
        beats=[],
        voiceover="",
        direction="UGC selfie",
    )
    assert "celebrity likeness" in omni_prompt
    assert "famous actors" in omni_prompt

    # 3. Test template prompt TALENT guardrails
    template_prompt = build_template_prompt(
        template_id="model_lifestyle",
        mode="product_mode",
        brand_name="Test Brand",
        product_name="Lotion",
        target_audience_persona="Working professional",
        headline="Morning Glow",
        cta="Shop Now",
    )
    assert "Not a celebrity, actor, or glamorous influencer" in template_prompt

    # 4. Test reference prompt LAYOUT-REF guardrails
    ref_prompt = build_reference_prompt(
        reference={"composition": "split", "product_presence": "handheld"},
        concept="Test concept",
        brand_name="Test Brand",
        product_name="Lotion",
        target_audience_persona="Commuter",
        headline="Stay Fresh",
        cta="Try Now",
        has_layout_ref=True,
    )
    assert "NOT a celebrity, model, or influencer" in ref_prompt
    print("[PASS] Anti-celebrity guardrails and persona name sanitization verified.")


def test_hex_code_sanitization_in_video_prompts():
    """Verify that hex codes are stripped/converted from video prompts and flagged by CreativeDirector."""
    from media_utils import sanitize_video_prompt, hex_to_color_name
    from creative_director import CreativeDirector
    from unittest.mock import MagicMock

    # 1. Test hex_to_color_name
    assert hex_to_color_name("#FF5252") == "coral red"
    assert hex_to_color_name("#FFFFFF") == "white"
    assert hex_to_color_name("#000000") == "black"
    assert hex_to_color_name("#D3E935") == "chartreuse"
    assert hex_to_color_name("#152B36") == "dark navy"

    # 2. Test sanitize_video_prompt across various prompt patterns
    raw_prompt = (
        "10-second vertical 9:16 Meta Reels ad for Kulfi. "
        "BRAND LOOK: playful, intimate; color accents in brand palette #FF5252, #FFFFFF, #FF5252 (props, wardrobe, set). "
        "Talent holding neon chartreuse (#D3E935) bottle with dark navy lettering (#152B36). "
        "Bottom right CTA pill in dark navy #152B36 with crisp white text. "
        "Salad Container; exact colours: base #1E2022, lid #939A9D, sleeve #F3F3F5, text #111113. "
        "On-screen text: \"#FF5252 Save Now\". "
        "accent button in #FF5252."
    )
    cleaned = sanitize_video_prompt(raw_prompt)
    assert "#" not in cleaned
    assert "#FF5252" not in cleaned
    assert "#D3E935" not in cleaned
    assert "#152B36" not in cleaned
    assert "#1E2022" not in cleaned
    assert "coral red and white" in cleaned
    assert "neon chartreuse bottle" in cleaned
    assert "dark navy lettering" in cleaned
    assert "dark navy with crisp white text" in cleaned
    assert "base dark charcoal" in cleaned
    assert "accent button in coral red" in cleaned

    # 3. Test CreativeDirector flags raw hex codes in video prompts
    mock_client = MagicMock()
    director = CreativeDirector(mock_client)
    bad_video_ad = {
        "id": "vid_hex_01",
        "format": "ugc",
        "voiceover": "Tired of dull skin? Try this glow serum today for instant hydration.",
        "direction": "Talent wearing #FF5252 hoodie holding product",
        "beats": [
            {"time": "0-3s", "visual": "Holds bottle with #D3E935 cap", "on_screen_text": "Glow Now", "audio": "Whoosh"}
        ],
        "proof_ids": [],
    }
    from creative_director import RubricReview, CriterionScore
    initial_review = RubricReview(
        prompt_id="vid_hex_01",
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
    mock_response = MagicMock()
    mock_response.text = json.dumps({"reviews": [initial_review.model_dump()]})
    mock_client.models.generate_content.return_value = mock_response

    reviews = asyncio.run(director.review_prompts_batch(
        [bad_video_ad],
        context="Hyphen brand",
        avoid_words=[],
        proof_ids=set(),
    ))
    review = reviews[0]
    assert review.passed is False
    assert review.executability.score <= 2
    assert "raw hex color codes" in review.executability.reasoning.lower()
    assert "Remove all raw hex codes" in review.rewrite_notes
    print("[PASS] Hex code sanitization and CreativeDirector QA audit verified.")


def test_static_creative_themes_diversity():
    """Verify static creative theme variety, distinct Pinterest pins, and prompt routing."""
    import creative_library_presets as clp
    from meta_creative_engine import build_native_in_image_ad_prompt
    from ad_templates import resolve_template_id

    # 1. Diverse theme assignment across multiple marketing frameworks
    frameworks = ["problem_solution", "feature_callout", "lifestyle_hero", "social_proof", "sensory_immersion", "bento_features"]
    assigned_themes = []
    assigned_pins = []
    for idx, fw in enumerate(frameworks):
        theme = clp.get_diverse_theme_for_brief(fw, category="skincare", business_type="physical", index=idx)
        assigned_themes.append(theme["id"])
        pins = theme.get("reference_pins", [])
        assert len(pins) > 0, f"Theme {theme['id']} missing Pinterest reference pins"
        assigned_pins.append(pins[0]["image_url"])

    # Verify high theme variety (not all identical presets)
    unique_themes = set(assigned_themes)
    assert len(unique_themes) >= 5, f"Expected at least 5 distinct themes across 6 frameworks, got {len(unique_themes)}: {assigned_themes}"
    # Verify Pinterest pins are diverse
    unique_pins = set(assigned_pins)
    assert len(unique_pins) >= 4, f"Expected diverse Pinterest reference pins, got: {assigned_pins}"

    # 2. Template resolution honors blueprint template_id
    bp_split = {"framework_key": "problem_solution", "template_id": "split_contrast", "preset_id": "diverse"}
    tid = resolve_template_id(bp_split, mode="product", category="skincare")
    assert tid == "split_contrast", f"Expected split_contrast, got {tid}"

    # 3. meta_creative_engine routing
    # Case A: Competitor reference takes priority
    bp_ref = {
        "framework_key": "problem_solution",
        "template_id": "split_contrast",
        "preset_id": "diverse",
        "reference": {
            "ref_id": "R01",
            "competitor": "CompetitorX",
            "image_url": "https://example.com/ref.jpg",
            "composition": "Split screen comparison with red X and green checkmark",
        },
        "image_headline": "Stop Wasting Time",
        "cta": "Get Started",
    }
    prompt_ref = build_native_in_image_ad_prompt(
        blueprint=bp_ref,
        brand_name="BrandAlpha",
        product_name="ProductOmega",
        product_category="skincare",
        preset_id="diverse",
    )
    assert "CompetitorX" in prompt_ref

    # Case B: Diverse mix uses layout template without being intercepted by detect_best_preset_for_brand
    bp_macro = {
        "framework_key": "feature_callout",
        "template_id": "macro_texture",
        "preset_id": "diverse",
        "image_headline": "Pure Hyaluronic Texture",
        "cta": "Shop Now",
        "visual_prompt": "Extreme macro close-up of glistening clear gel drop resting on honeysuckle petal.",
    }
    prompt_macro = build_native_in_image_ad_prompt(
        blueprint=bp_macro,
        brand_name="BrandAlpha",
        product_name="ProductOmega",
        product_category="skincare",
        preset_id="diverse",
    )
    assert "Macro Texture" in prompt_macro or "macro" in prompt_macro.lower()
    # Confirm it was NOT intercepted by an unconditional preset override
    assert "travertine stone pedestal" not in prompt_macro.lower()

    # Case C: Explicit single preset choice respected with brand_kit
    bp_preset = {
        "framework_key": "problem_solution",
        "template_id": "beauty_editorial_rhode",
        "preset_id": "beauty_editorial_rhode",
        "image_headline": "Dewy Radiance",
        "cta": "Shop Now",
        "visual_prompt": "Morning sunbeams lighting amber serum bottle.",
    }
    prompt_rhode = build_native_in_image_ad_prompt(
        blueprint=bp_preset,
        brand_name="BrandAlpha",
        product_name="ProductOmega",
        product_category="skincare",
        preset_id="beauty_editorial_rhode",
        brand_kit={"primary_hex": "#112233", "accent_hex": "#EE5522", "visual_mood": "warm organic"},
    )
    assert "Rhode Editorial" in prompt_rhode or "Rhode" in prompt_rhode
    assert "#EE5522" in prompt_rhode

    # 4. Batch generation with StaticPromptWriter distributes diverse themes
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = json.dumps({
        "scenes": [
            {"brief_id": "S01", "template_id": "split_contrast", "scene_description": "Split screen comparison"},
            {"brief_id": "S02", "template_id": "macro_texture", "scene_description": "Macro dew drop texture"},
            {"brief_id": "S03", "template_id": "model_lifestyle", "scene_description": "Model applying cream in morning sun"},
        ]
    })
    mock_client.models.generate_content.return_value = mock_response

    writer = StaticPromptWriter(mock_client)
    briefs = [
        StaticBrief(
            id="S01", persona="P1", stage="problem_aware", angle="Angle 1", framework="problem_solution",
            concept_source=[], product_index=0, proof_ids=[], market="US/en", scene_direction="Split screen",
            copy=StaticCopy(image_headline="Before vs After", meta_headline="Before vs After", cta="Try Now", primary_text="Text 1"),
        ),
        StaticBrief(
            id="S02", persona="P1", stage="solution_aware", angle="Angle 2", framework="feature_callout",
            concept_source=[], product_index=0, proof_ids=[], market="US/en", scene_direction="Macro shot",
            copy=StaticCopy(image_headline="Hydration Detail", meta_headline="Hydration Detail", cta="Explore", primary_text="Text 2"),
        ),
        StaticBrief(
            id="S03", persona="P1", stage="unaware", angle="Angle 3", framework="lifestyle_hero",
            concept_source=[], product_index=0, proof_ids=[], market="US/en", scene_direction="Lifestyle moment",
            copy=StaticCopy(image_headline="Everyday Ritual", meta_headline="Everyday Ritual", cta="Shop Now", primary_text="Text 3"),
        ),
    ]
    brand_profile = {
        "brand_name": "GlowCo",
        "product_name": "Dew Serum",
        "product_category": "skincare",
        "business_type": "physical",
        "featured_products": [{"name": "Dew Serum", "lock": "frosted glass bottle"}],
        "brand_kit": {"primary_hex": "#000000", "accent_hex": "#FF0000", "visual_mood": "modern"},
    }
    results = asyncio.run(writer.write_batch(briefs, brand_profile, {}, "", default_aspect="4:5", preset_id="diverse"))
    assert len(results) == 3
    themes_in_batch = [r["preset_name"] for r in results]
    assert len(set(themes_in_batch)) == 3, f"Expected 3 distinct theme names in batch, got: {themes_in_batch}"
    pins_in_batch = [r["preset_references"][0]["image_url"] for r in results if r["preset_references"]]
    assert len(set(pins_in_batch)) >= 2, f"Expected distinct Pinterest pin references in batch, got: {pins_in_batch}"
    print("[PASS] Static creative theme diversity and multi-theme Pinterest utilization verified.")


if __name__ == "__main__":
    test_models_serialization()
    test_omni_prompt_builder()
    test_creative_director_hard_checks()
    test_creative_director_rewrite_loop()
    test_anti_celebrity_and_persona_sanitization()
    test_hex_code_sanitization_in_video_prompts()
    test_static_creative_themes_diversity()
    print("\nALL STEP 3 TESTS PASSED PERFECTLY!")
