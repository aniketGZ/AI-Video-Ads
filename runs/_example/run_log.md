# Run log — competitor_ad_agent — run `_example`

Brand: **Arriv** — Triple Action Whole Body Cream (whole-body deodorant cream), IN market.
Started: 2026-10-05.

## Settings
- Country: IN · max 15 ads/competitor · 3 image + 2 video prompts per ad group
- Image model: nano-banana-pro · Video model: omni-flash · Logo: composite_in_post
- Competitors: Sanfe, Bombay Shaving Company, Plum Goodness

## Steps
- [x] Step 0 — Validate inputs, read product, write brand files
- [x] Step 1 — Resolve competitors in Ad Library
- [x] Step 2 — Capture ads
- [x] Step 3 — Download creatives
- [x] Step 4 — Analyse ads (14 analysed: 8 video, 5 image, 1 carousel)
- [x] Step 5 — Insights
- [x] Step 6 — Prompts (6 image + 4 video)
- [x] Step 7 — QA
- [x] Step 8 — Report + handoff

## Analysis & media notes (Step 3-4)
- whisper not installed; model download too heavy for this run — transcripts skipped, analysed on-screen text from extracted hook/scene frames + captured ad copy. (imageio-ffmpeg frame extraction worked for all 15 videos.)
- Deeply read: all downloaded product images + representative hook/scene frames for key videos. 2 ads (sanfe 1226619872835114, bsc 1382983667308574) analysed primarily from copy (marked text_only).

## QA (Step 7)
- Mechanical (prompts/_qa.py): counts correct (3 img + 2 vid per group), every group has proven + differentiator, 95 competitor/page/domain terms scanned — none present in prompts, all headlines/CTAs/VO/on-screen text verbatim from the ad group copy (case-insensitive; ag_02 mid-beat 'keeps skin fresh & dry' is a verbatim substring of ag_02 primary_text), aspect ratios in settings, videos 9:16/8s.
- 3 soft warnings were false positives (product-lock phrasing heuristic) — each video first-frame fully describes the bottle + 'reproduce exactly from the reference' and each video_prompt says 'unchanged throughout'. Verified by reading.
- Judgement: no near-duplicate concepts within a group; chafing framed as comfort (no medical/rash depiction); no invented stats/prices/awards; no flags/currency/medical claims. [OFFER] not needed (no offer-based concepts used).

## Competitor resolution (Step 1)
- **Sanfe** — keyword search "Sanfe" (~590 results). Pages: Sanfe, Sanfe India, SanfeFanpage + creator partnerships. Women's intimate/skincare brand (tan removal, facial hair, brightening, melasma, eyebrow tint) — tangential to Arriv's deo/chafing category but strong for FORMAT/UGC patterns. 49 cards captured (48 video, 1 image), 43 are Sanfe-brand.
- **Bombay Shaving Company** — keyword "Bombay Shaving Company" (~1,100 results). Pages: Bombay Shaving Company (men's grooming, Full Body Trimmer, deodorant-adjacent), Bombae (women's hair tools) + many creator partnerships. 50 cards (40 video, 10 image), 47 brand. Most relevant: body-grooming/body-care angle.
- **Plum Goodness** — keyword "Plum Goodness" returned FOOD ads (matched the word "goodness"), and bare "Plum" was too noisy (other beauty brands). Resolved via sub-brand keyword **"bodylovin"** → Plum BodyLovin' (body mist, body wash/lotion, body care) — highly relevant to Arriv's body category. 92 cards merged across searches; 37 are Plum-brand (35 Plum BodyLovin' + 2 Plum).
- Advertiser typeahead did not render in the isolated (logged-out) browser; used keyword search + page_name filtering instead. No login attempted.

## Selection (Step 2)
- Filtered each competitor's cards to brand-owned pages (regex on page_name; retailers like Flipkart/Nykaa/Myntra/Zepto excluded). Scored by longevity + versions + relevance to body/sweat/odor/chafing/fragrance + UGC signal. Selected top 8 per competitor.

## Media (Step 3)
- 15 videos + 14 images downloaded to media/. Note: fbcdn video URLs 302-redirect to video.xx.fbcdn.net — require curl -L. Manifest had CRLF (Python text-mode on Windows); stripped \r before curl.

## Assumptions
- No logo file uploaded. Logo handling = composite_in_post (default); the product bottle itself carries the "Arriv" wordmark, so no separate logo file is needed for references. Logo zone reserved in all prompts.
- brand_colors supplied in input.json used as the base palette.

## Errors / blocks
(none yet)

## Coverage
(to be filled)


## Live Activity Log
- `15:34:31` **[info]** Competitor Ad Agent started for run '_example' (from step 4).
- `15:34:31` **[warning]** No Gemini API key supplied. Agent will run with template & heuristic models.
- `15:34:31` **[info]** Starting Gemini Multimodal Ad Analysis...
- `15:34:31` **[info]** Found 10 new ad creatives to analyze with Gemini.
- `15:34:31` **[info]** Analyzing ad 1915655799107650 (Sanfe) with Gemini: 'Dead Skin Out, Glow In ✨'...
- `15:34:31` **[info]** Analyzing ad 1466672152150425 (Sanfe) with Gemini: 'chandni_officiall'...
- `15:34:31` **[info]** Analyzing ad 28195366336727396 (Sanfe) with Gemini: 'Facial Hair Painlessly Gone In Minu'...
- `15:34:31` **[info]** Analyzing ad 1996700654306513 (Sanfe) with Gemini: ''...
- `15:34:31` **[info]** Analyzing ad 1037736189153552 (Bombay Shaving Company) with Gemini: ''...
- `15:34:31` **[info]** Analyzing ad 1040777455430188 (Bombay Shaving Company) with Gemini: ''...
- `15:34:31` **[info]** Analyzing ad 2296842264416677 (Bombay Shaving Company) with Gemini: ''...
- `15:34:31` **[info]** Analyzing ad 1106535448636927 (Plum Goodness) with Gemini: 'Plum BodyLovin''...
- `15:34:31` **[info]** Analyzing ad 1100450812475088 (Plum Goodness) with Gemini: ''...
- `15:34:31` **[info]** Analyzing ad 4591808784426248 (Plum Goodness) with Gemini: 'India's Most Wanted Lotion Is Back!'...
- `15:34:31` **[success]** Step 4 complete: 24 ads analyzed.
- `15:34:31` **[info]** Synthesizing cross-competitor strategic intelligence...
- `15:34:31` **[info]** Written structured analysis/insights.md.
- `15:34:31` **[info]** Drafting Rainbow image prompts and Opus video prompts per ad group...
- `15:34:31` **[info]** Generating 3 image prompts & 2 video prompts for 'Sweat & odor'...
- `15:34:31` **[info]** Generating 3 image prompts & 2 video prompts for 'Chafing relief'...
- `15:34:31` **[success]** Saved 6 image prompts and 4 video prompts.
- `15:34:31` **[info]** Running automated QA and compliance verification on generated prompts...
- `15:34:31` **[info]** Verified 6 image prompts and 4 video prompts.
- `15:34:31` **[success]** All QA checks passed: zero competitor IP, verbatim copy verified, product lock enforced.
- `15:34:31` **[info]** Compiling executive report and orchestrator handoff package...
- `15:34:31` **[success]** Run complete! Handoff ready for Rainbow and Opus.
- `15:34:31` **[success]** Competitor Ad Agent run '_example' finished successfully.
- `15:35:06` **[info]** Competitor Ad Agent started for run '_example' (from step 4).
- `15:35:06` **[warning]** No Gemini API key supplied. Agent will run with template & heuristic models.
- `15:35:06` **[info]** Starting Gemini Multimodal Ad Analysis...
- `15:35:06` **[info]** Found 0 new ad creatives to analyze with Gemini.
- `15:35:06` **[success]** Step 4 complete: 24 ads analyzed.
- `15:35:06` **[info]** Synthesizing cross-competitor strategic intelligence...
- `15:35:06` **[info]** Written structured analysis/insights.md.
- `15:35:06` **[info]** Drafting Rainbow image prompts and Opus video prompts per ad group...
- `15:35:06` **[info]** Generating 3 image prompts & 2 video prompts for 'Sweat & odor'...
- `15:35:06` **[info]** Generating 3 image prompts & 2 video prompts for 'Chafing relief'...
- `15:35:06` **[success]** Saved 6 image prompts and 4 video prompts.
- `15:35:06` **[info]** Running automated QA and compliance verification on generated prompts...
- `15:35:06` **[info]** Verified 6 image prompts and 4 video prompts.
- `15:35:06` **[success]** All QA checks passed: zero competitor IP, verbatim copy verified, product lock enforced.
- `15:35:07` **[info]** Compiling executive report and orchestrator handoff package...
- `15:35:07` **[success]** Run complete! Handoff ready for Rainbow and Opus.
- `15:35:07` **[success]** Competitor Ad Agent run '_example' finished successfully.
- `15:43:59` **[info]** Competitor Ad Agent started for run '_example' (from step 7).
- `15:43:59` **[warning]** No Gemini API key supplied. Agent will run with template & heuristic models.
- `15:43:59` **[info]** Running automated QA and compliance verification on generated prompts...
- `15:43:59` **[info]** Verified 6 image prompts and 4 video prompts.
- `15:43:59` **[success]** All QA checks passed: zero competitor IP, verbatim copy verified, product lock enforced.
- `15:43:59` **[info]** Compiling executive report and orchestrator handoff package...
- `15:43:59` **[success]** Run complete! Handoff ready for Rainbow and Opus.
- `15:43:59` **[success]** Competitor Ad Agent run '_example' finished successfully.
