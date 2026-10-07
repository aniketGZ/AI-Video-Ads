# Agent architecture: campaign builder

Goal: from **a brand URL + product photos**, produce a launch-ready campaign of **≥25 statics and ≥25 videos**.
Each creative comes with copy, placements and targeting. Everything is grounded in the user's own website.
The app is self-serve first: agents run end to end with no questions. Optional checkpoints are for power users.

## Decisions this design is built on (2026-10-07)

| Topic | Decision |
|---|---|
| Users | Mostly self-serve founders, plus agency use. Runs must finish without human input. |
| "Ready to launch" | Creative + primary text + headline + description + CTA + 1:1 / 4:5 / 9:16 + targeting + test plan. |
| "On brand" | Every claim, colour, word and visual is traceable to the user's URL (website only for now). |
| Winning-ad signal | `days_running` only (performance data comes later). |
| Competitors | Top 3. If they aren't running ads → adjacent-category brands on Meta + Pinterest becomes the primary concept source. |
| Pinterest's job | Design compositions, layouts and concepts, plus what looks current. Meta's job: what is actually running as ads. |
| Pinterest access | Logged-in Playwright, using **the user's own Pinterest account** (they're asked to log in). Output is **style tokens**, not images. |
| Copy | **The Strategist owns all copy.** There is no upstream copy step with locked headlines. |
| Market | **Global.** Market, language and currency come from the website. Nothing defaults to one country. |
| Video | UGC, product demo, motion graphics. **No cinematic brand films.** Scripted on its own (not animated from statics). Voiceover baked in by Omni Flash 1.1. |
| QA | Critic judges **prompts** always. Checking **rendered images and videos** runs only when the user asks for it. No ad-policy checks. |
| Learning | Cross-run pattern library + per-brand memory of rejections and edits. |
| Runtime | Python pipeline steps and Claude subagents, mixed. Independent research runs in parallel. |

## Flow

```
URL + product photos (+ logo)
        │
        ▼
[A1] Brand & Product Analyser ─────────────► brand_profile.json
        │
        ├──────────────────┬──────────────────────┐        (parallel)
        ▼                  ▼                      ▼
[A2] Audience Builder  [A3] Meta Ads Analyser  [A4] Pinterest Creative Researcher
 audience.json          meta_refs.json          style_tokens.json
                        (+ pattern library)
        └──────────────────┴──────────────────────┘
                           ▼
              [A5] Creative Strategist ─────► campaign_matrix.json  (50+ briefs + test plan)
                           │
              ┌────────────┴────────────┐               (parallel, batched)
              ▼                         ▼
   [A6] Static Prompt Writer   [A7] Video Script Writer
              └────────────┬────────────┘
                           ▼
              [A8] Creative Director (critic) ── fail → rewrite (max 2 loops)
                           │ pass
                           ▼
                     render (Nano Banana Pro / Qwen, Omni Flash 1.1)
                           │
                           ├── only if the user asks: [A8b] rendered image + video check → re-render failures
                           ▼
              [A9] Launch Packager ──────────► launch_pack.json + Ads Manager sheet
                           │
                user approves / rejects / edits ──► brand_memory (feeds A5–A8 next run)
```

---

## [A1] Brand & Product Analyser (upgrade of `campaign_flow.analyze_brand`)

**Inputs:** URL, product photos, optional logo.
**Does:**
- Crawls the homepage, the product pages for the uploaded products, About, and FAQ. Pulls on-site reviews. Then searches for the brand on Amazon / Trustpilot / Google and pulls review snippets.
- **Product lock v2:** one lock per photo. Keeps the existing `ProductLock` fields, plus: dominant hex per surface, label text read verbatim (OCR-style, with line breaks), aspect ratio of the pack, which views are visible, and "never do" notes (e.g. "cap is matte, not glossy"). Product fidelity is the #1 rejection reason today, so this lock is the contract every downstream prompt and the critic check against.
- **Voice rules:** words and phrases the brand uses, words to avoid, reading level, emoji yes/no, sentence length, how it addresses the customer.
- **Proof bank:** every claim the site makes, each with its source URL. Downstream agents may only use claims from this bank.
- **Review language:** customer phrases grouped by pain, desire and objection, with counts.

**Output: `brand/brand_profile.json`**
```json
{
  "brand": {"name": "", "url": "", "category": "", "business_type": "",
            "markets": [{"country": "", "language": "", "currency": "", "evidence": "shipping page / currency / hreflang"}]},
  "brand_kit": {"primary_hex": "", "accent_hex": "", "background_hex": "", "text_hex": "",
                "headline_type": "", "body_type": "", "visual_mood": "", "logo_path": ""},
  "voice": {"tone": "", "use_words": [], "avoid_words": [], "reading_level": "",
            "emoji": false, "address_as": "you", "sample_lines": []},
  "products": [{"index": 0, "image": "uploads/p0.png", "lock": {"...": "ProductLock v2"}}],
  "proof_bank": [{"claim": "", "source_url": "", "type": "stat|ingredient|award|guarantee|review"}],
  "review_language": {"pains": [{"phrase": "", "count": 0}], "desires": [], "objections": []},
  "aesthetic_keywords": ["used by A4 to search Pinterest"]
}
```

## [A2] Audience Builder

**Inputs:** `brand_profile.json`. **Model:** Gemini (as now).
**Does:** builds 3–4 personas (keeps today's `BullseyeTarget` shape). Maps each persona across **awareness stages**: unaware → problem-aware → solution-aware → product-aware → most-aware. Each cell gets its hook style and its best formats. Also outputs a **targeting block** for Ads Manager. Personas and targeting are built per market from `brand.markets`. Casting, settings and language follow that market; nothing defaults to one country.

**Output: `audience/audience.json`**
```json
{
  "personas": [{"id": "P1", "...": "BullseyeTarget fields", "review_phrases": []}],
  "stage_map": [{"persona": "P1", "stage": "problem_aware", "hook_style": "", "message": "",
                 "best_formats": ["ugc", "problem_solution_static"]}],
  "targeting": {"geo": [], "age_min": 0, "age_max": 0, "genders": [], "languages": [],
                "interests": [], "advantage_plus_audience": true,
                "lookalike_seeds": ["site purchasers", "IG engagers"], "exclusions": []}
}
```

## [A3] Meta Ads Library Analyser (`competitor_ad_engine.py` steps 1–5 + `competitor-ad-agent`)

**Inputs:** `brand_profile.json` (category, competitors from discovery).
**Does:**
1. Takes the **top 3 competitors** and captures their active ads. Ranks them by `days_running` (tie-break: `versions_count`).
2. **Thin-signal routing:** if fewer than **9 ads** across the 3 have run for **14 days or more**, it searches **2–3 adjacent-category brands** that sell to the same persona with strong creative craft, and sets `signal: "thin"`. A5 then makes Pinterest the primary concept source.
3. Breaks every selected ad into reusable **patterns**: hook type, layout, text density, offer framing, pacing (video), first-frame composition, VO style.
4. Writes the patterns to the cross-run **pattern library**, so a hook seen in 6 categories is worth more than one seen once.

**Output: `analysis/meta_refs.json`**
```json
{
  "signal": "strong|thin",
  "sources": [{"brand": "", "relation": "competitor|adjacent", "ads_found": 0, "ads_14d_plus": 0}],
  "image_refs": [{"id": "R1", "brand": "", "days_running": 0, "layout": "", "hook_type": "",
                  "text_density": "low|med|high", "offer_frame": "", "why_it_works": "", "media": ""}],
  "video_refs": [{"id": "V1", "brand": "", "days_running": 0, "format": "ugc|demo|motion_graphics",
                  "hook_mechanic": "", "beat_structure": [], "vo_style": "", "pacing_s_per_cut": 0}],
  "saturated": [], "whitespace": []
}
```

**Pattern library** (`library/patterns.jsonl`, one row per pattern, shared across runs):
`{pattern_id, kind: hook|layout|beat_structure, description, categories[], seen_count, max_days_running, example_refs[]}`

## [A4] Pinterest Creative Researcher (new; Claude subagent + Playwright, logged in)

**Inputs:** `brand_profile.json` (aesthetic keywords, category, palette, product type), `audience.json` (persona lifestyle).
**Thinks like a creative director building a mood board.** It does not search for "deodorant ad". It builds about 8–12 queries across four lanes:
- **Category craft:** "minimal skincare product poster", "supplement ad layout typography"
- **Aesthetic:** the brand's mood keywords × format ("quiet luxury product flatlay", "Y2K chrome poster")
- **Persona world:** where the persona lives ("gen z commute aesthetic", "home gym morning routine")
- **Technique:** "split screen product comparison design", "bold typography poster grid", "UGC style story ad"

For each query it opens the top pins, then follows "More like this" one level deep. It favours pins with high save counts and recent pins. It keeps **30–50 references**.

**Output: `research/style_tokens.json`**. Each reference is reduced to tokens the prompt writers can use directly:
```json
{
  "tokens": [{
    "id": "S1", "source_pin": "", "lane": "aesthetic",
    "composition": "product hero bottom-third, 60% negative space top",
    "layout": "headline top-left, CTA pill bottom-right",
    "lighting": "hard side light, long shadows",
    "palette_role": "brand primary as background block, accent on CTA",
    "props_set": "travertine plinth, dried pampas",
    "camera": "eye-level, 50mm, shallow DOF",
    "typography_style": "condensed grotesk, all caps, tight tracking",
    "motion_idea": "for motion graphics: kinetic type slam-in on beat",
    "trend_tag": "warm minimalism", "fits_personas": ["P1"]
  }],
  "trend_summary": ["3–5 visual trends seen this run"]
}
```

**Account: the user's own.**
- The first time a user runs a campaign, the app asks them to connect Pinterest. A headed Playwright window opens and they log in themselves; the app never sees their password.
- The session is saved in a per-user persistent browser profile (`profiles/<user_id>/pinterest/`). Later runs reuse it, and if the session expires the app asks the user to log in again.
- If the user skips this step, A4 is skipped and A5 builds concepts from the Meta refs and the pattern library alone. The run report says so.
- Pinterest's terms restrict automated access. Tell the user that before they connect, keep browsing slow and human-paced, and run one session per account at a time.
- Only tokens and pin URLs are stored, never the pin images in any output. This keeps the creatives original.

## [A5] Creative Strategist (new; replaces the "focus batches" in `campaign_flow`)

**Inputs:** A1–A4 outputs, the pattern library, and `brand_memory` for this brand.
**Does:** builds the **campaign matrix**: 25+ static briefs and 25+ video briefs. Each brief is one cell of `persona × awareness stage × angle × format`. Each brief names exactly where its idea came from:
- `concept_source`: a Meta ref (`R3` / `V2`), a pattern-library id, or a Pinterest token (`S7`). When `signal == "thin"`, at least 60% of statics must come from Pinterest tokens.
- `proof_ids`: claims from the proof bank only.
- Format spread for videos: e.g. 10 UGC / 9 demo / 6 motion graphics (adjusted to what the Meta refs show working).

**The Strategist owns all copy.** Each brief carries its final copy (headline, CTA, primary text, Meta headline, description; for videos also the hook line, VO and on-screen text), written in the brand's voice rules and the market's language. The prompt writers use it word for word and never rewrite it.

It also writes the **test plan**: which briefs form one ad set (one variable changed at a time), and the launch order.

**Output: `strategy/campaign_matrix.json`**
```json
{
  "statics": [{"id": "S01", "persona": "P1", "stage": "problem_aware", "angle": "", "framework": "",
               "concept_source": ["R3", "S7"], "product_index": 0, "proof_ids": [], "market": "US/en",
               "copy": {"image_headline": "≤6 words", "cta": "", "primary_text": "", "meta_headline": "≤40 chars", "description": ""}}],
  "videos":  [{"id": "V01", "persona": "P2", "stage": "solution_aware", "format": "ugc",
               "hook_mechanic_from": "V2", "product_indexes": [0], "proof_ids": [], "market": "US/en",
               "copy": {"hook_line": "", "voiceover": "~2.5 words/s of clip", "on_screen_text": [], "primary_text": "", "meta_headline": "", "cta": ""}}],
  "test_plan": [{"ad_set": "AS1", "variable": "hook", "creatives": ["S01", "S02", "S03"]}]
}
```

## [A6] Static Prompt Writer / [A7] Video Script Writer

Run in parallel, in batches of 5 briefs per model call (so 50+ prompts stay sharp, not generic).

- **A6:** writes one prompt per static per aspect ratio (1:1, 4:5, 9:16). Inputs per prompt: the product lock v2 verbatim, the Pinterest tokens, the Meta layout, and the brand kit. In-image text stays limited to wordmark + ≤6-word headline + CTA. Copy comes word for word from the brief; A6 only decides where it sits and how it is set.
- **A7:** expands the brief's hook and VO (used word for word) into a beat-by-beat script (hook → demo/proof → CTA). Then it writes the Omni Flash 1.1 prompt beat by beat from that script, using `<IMAGE_REF_i>` product locks (extends `_omni_prompt`). Casting comes from the persona.

## [A8] Creative Director (critic)

**Always on: prompt review.** Scores each prompt 1–5 on the rubric. Any criterion below 3, or an average below 4, gets a targeted rewrite note and goes back to A6/A7, at most 2 loops. After that it ships with a warning.

| Criterion | Pass means |
|---|---|
| Product fidelity | Every lock field present; label text verbatim; no invented variants |
| URL grounding | Every claim maps to a `proof_id`; nothing the site doesn't say |
| Brand fit | Palette hexes, type style, visual mood and voice rules applied; no `avoid_words` |
| Persona × stage fit | Hook matches the awareness stage; casting and setting match the persona |
| Hook strength | First frame / first second is specific and scroll-stopping, not generic |
| Trend fit | Uses at least one Pinterest token or a high-`seen_count` pattern |
| Distinctness | Not a near-duplicate of another prompt in this campaign |
| Executability | Text ≤6 words in image; VO fits the duration; model syntax correct |

It also checks `brand_memory`: anything this brand rejected before is an automatic fail.

**Only when the user asks: rendered image and video check (A8b).**
- Images: compares the product against its lock (shape, colours, label text), checks that the headline and CTA are spelled right and readable, and checks hands and faces.
- Videos: samples frames (reuses `tools/competitor_ad_agent/video_frames.py`) and the transcript, then compares the product against its lock, checks on-screen text, VO against the script, and hands and faces.
- Failures are re-rendered once with the critic's fix note.
- Off by default; the user triggers it per campaign or per creative, because each re-render costs money.

## [A9] Launch Packager

Bundles each approved creative with its copy, placements, the targeting block from A2 and the test plan from A5, into `launch_pack.json` + a CSV/XLSX shaped for Ads Manager bulk upload.

## Memory

- **Pattern library** (`library/patterns.jsonl`): cross-brand, written by A3.
- **Brand memory** (`brands/<domain>/memory.json`): per-brand list of approved creatives, rejected creatives with a reason tag (product wrong / off-brand / weak hook / wrong vibe), and user edits (before → after). Read by A5, A6, A7 and A8.

## Runtime split

| Agent | Runs as | Why |
|---|---|---|
| A1, A2, A5, A6, A7, A8, A9 | Python + Gemini structured output | Deterministic schemas, cheap, fast, and already the pattern in `campaign_flow.py` |
| A3, A4 | Claude subagents with Playwright (A3 = existing `competitor-ad-agent`) | Browsing needs judgement: scrolling, following "more like this", choosing what's worth keeping |
| A8b | Python + Gemini image/video understanding | Multimodal comparison against the lock |

## Fix first: problems in the current code that break "on brand"

1. **Hard-coded fallbacks leak another brand's world into any run.**
   - `competitor_ad_engine.py:405` falls back to Indian deodorant/skincare competitors.
   - `_write_fallback_insights` (`competitor_ad_engine.py:1497`) writes Sanfe/BSC/Plum insights.
   - `step_6_write_prompts` (`competitor_ad_engine.py:1562`) defaults to Indian-commuter demographics and a fixed palette.

   These should fail loudly or retry, never substitute.
2. **India is hard-coded as the market** (the app is global).
   - The Ad Library search country defaults to `IN` in `competitor_ad_engine.py:553`, `:622` and `:964`, `competitor_ad_routes.py:350`, and `.claude/agents/competitor-ad-agent.md:79`.
   - The audience falls back to "Urban Indian Metros" in `competitor_ad_engine.py:521`, `:591` and `:1565`.

   A3 should search the Ad Library in the brand's main market from `brand.markets`. If that returns nothing it should try `ALL`, which the code already does at `:902`.
3. **Context is truncated.** Insights are cut to 1000 chars before prompt writing (`competitor_ad_engine.py:1584`), and synthesis only sees `ads_data[:20]` (`competitor_ad_engine.py:1466`). Pass structured `meta_refs.json` instead of truncated markdown.
4. **Two prompt writers.** `step_6_write_prompts` and `campaign_flow.write_ad_prompts` overlap. Merge them into A6/A7.
5. **QA only checks competitor names** (`step_7_qa_check`). A8 replaces it.

## Build order

1. ✅ (2026-10-07) Remove the hard-coded fallbacks; make `meta_refs.json` the handoff; merge the prompt writers.
2. ✅ (2026-10-07) A1 upgrade: product lock v2, voice rules, proof bank, review mining. (Biggest quality lever: product fidelity.)
3. ✅ (2026-10-07) A5 Strategist + A8 prompt critic (makes 25 + 25 hold quality instead of repeating itself).
4. A4 Pinterest researcher + thin-signal routing in A3.
5. Pattern library + brand memory.
6. A2 targeting block + A9 launch packager.
7. A8b rendered image and video check, run only when the user asks.
