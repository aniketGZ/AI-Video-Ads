# AD STORYBOARD PROMPT TEMPLATE — for Nano Banana → Omni Flash pipeline

**Pipeline:** URL Analysis Agent → fills `{{VARIABLES}}` → Nano Banana generates storyboard image → storyboard fed to Omni Flash as reference for a 10-second ad.

---

## 1. VARIABLE MAP (what your URL-analysis agent must extract & inject)

| Variable | Source / Logic | Example |
|---|---|---|
| `{{BRAND_NAME}}` | Site title / logo / og:site_name | "Prerana Wellness" |
| `{{PRODUCT_NAME}}` | Product page H1 / og:title | "Whiter & Brighter Face Wash" |
| `{{PRODUCT_CATEGORY}}` | Inferred (skincare, SaaS, apparel, food, tech, fitness…) | "herbal skincare" |
| `{{PRODUCT_VISUAL_DESCRIPTION}}` | From product images: shape, packaging, colors, label, materials. Be forensic — this is the consistency anchor. | "transparent 100ml bottle, blue gel with micro-beads, white flip cap, blue-and-white label with green botanical illustration" |
| `{{PRODUCT_HERO_ANGLE}}` | Best-looking angle from site imagery | "front label facing camera, slight 15° tilt" |
| `{{TARGET_AUDIENCE_PERSONA}}` | From copy tone, pricing, reviews, demographics signals | "women 22–35, urban India, wellness-conscious, Instagram-native" |
| `{{ON_SCREEN_TALENT}}` | Persona → a matching relatable character (age, gender, ethnicity, styling). Keep ONE consistent character. | "Indian woman, mid-20s, warm smile, minimal makeup, cream knit top" |
| `{{SETTING}}` | Category + persona → environment | "cozy sunlit bedroom with neutral decor and plants" |
| `{{MOOD_KEYWORDS}}` | 3 adjectives from brand voice | "FRESH · NATURAL · GLOWING" |
| `{{COLOR_PALETTE}}` | Extracted brand colors + 2–3 complementary ambient tones | "warm beige, soft white, botanical green, honey daylight gold" |
| `{{VISUAL_STYLE}}` | Pick ONE preset from §3 | "UGC_REALISTIC" |
| `{{ASPECT_RATIO}}` | Ad platform: Reels/TikTok → 9:16, YouTube → 16:9, Feed → 1:1 | "9:16" |
| `{{LIGHTING}}` | From style preset or brand vibe | "soft natural window daylight" |
| `{{HOOK_LINE}}` | Pain point from landing page, ≤8 words, quoted dialogue or bold claim | ""Dull skin? Watch this."" |
| `{{KEY_BENEFITS}}` | Top 3 benefits/ingredients/features from page | "brightens tone, gentle daily cleanse, herbal actives" |
| `{{CTA_LINE}}` | Site CTA, ≤6 words | "Glow naturally. Shop now." |
| `{{SHOT_LIST}}` | Auto-built from arc preset in §4, one line each | see §4 |
| `{{LOGO_TEXT}}` | Brand wordmark as plain text (safer than logo reproduction) | "PRERANA WELLNESS" |

---

## 2. MASTER PROMPT TEMPLATE (feed this string to Nano Banana)

```
Create a crisp, clean, professional AD STORYBOARD POSTER for "{{PRODUCT_NAME}}" by {{BRAND_NAME}}.

LAYOUT & FORMAT:
{{ASPECT_RATIO}} layout, clean white background, thin black panel borders, bold black sans-serif typography, premium advertising-agency presentation board. Grid of 6 numbered storyboard panels arranged left-to-right, top-to-bottom (2 columns × 3 rows for 9:16, 3 columns × 2 rows for 16:9). Each panel is a fully rendered cinematic frame — NOT a sketch — with a number badge in the top-left corner, a bold shot title, a one-line caption beneath it, and a small clock icon with its duration.

TOP HEADER (exact text, large bold type):
"{{PRODUCT_NAME}}" — subtitle: "TOTAL VIDEO TIME: 10 SECONDS · 6 SHOTS · {{MOOD_KEYWORDS}}"
Legend row of 4 small icons with labels: HOOK, PRODUCT, BENEFIT, CTA.

VISUAL STYLE:
{{VISUAL_STYLE_BLOCK}}  ← paste the full preset block from §3
Color palette locked to: {{COLOR_PALETTE}}. Lighting: {{LIGHTING}}.

CONSISTENCY LOCK (critical — this board is a video-generation reference):
The SAME product appears in every panel where mentioned: {{PRODUCT_VISUAL_DESCRIPTION}}. Preserve exact packaging shape, label layout, colors, cap design, materials, and proportions across all panels. Hero angle: {{PRODUCT_HERO_ANGLE}}.
The SAME single on-screen talent appears throughout: {{ON_SCREEN_TALENT}}. Identical face, hair, outfit, and skin tone in every panel — no character drift.
Setting consistent across panels: {{SETTING}}.

THE 6 PANELS (render each as a distinct full-frame cinematic shot):

Panel 1 — HOOK SHOT (~1.5s): {{SHOT_1}} Caption text: {{HOOK_LINE}}
Panel 2 — PRODUCT REVEAL (~1.5s): {{SHOT_2}}
Panel 3 — PRODUCT IN ACTION (~2s): {{SHOT_3}}
Panel 4 — BENEFIT / TRANSFORMATION (~2s): {{SHOT_4}}
Panel 5 — LIFESTYLE / EMOTION (~1.5s): {{SHOT_5}}
Panel 6 — CALL TO ACTION (~1.5s): {{SHOT_6}} Caption text: "{{CTA_LINE}}" with "{{LOGO_TEXT}}" rendered as clean typography.

FOOTER STRIP (4 columns, small icons + short text):
• VIDEO FLOW: "6 shots ≈ 10 seconds. Hook to CTA."
• CAMERA TIPS: "macro on product texture, close-up on {{ON_SCREEN_TALENT_SHORT}} expression, wide establishing on {{SETTING_SHORT}}, slow push-in on final CTA frame"
• LIGHT & STYLE: "{{LIGHTING}}, {{COLOR_PALETTE}}, shallow depth of field"
• AUDIENCE NOTES: "made for {{TARGET_AUDIENCE_PERSONA}} — every frame must feel {{MOOD_KEYWORDS}}"

TYPOGRAPHY RULES: all text short, high-contrast, perfectly legible; no paragraph text inside image panels; captions live in white bars below each frame, never overlapping the image.

NEGATIVE: watermark, extra logos, misspelled text, blurry frames, distorted hands, warped product packaging, inconsistent character faces, cluttered layout, overlapping panels, sketch lines, low quality.
```

---

## 3. VISUAL STYLE PRESETS (`{{VISUAL_STYLE_BLOCK}}`) — app picks one by category

**UGC_REALISTIC** (skincare, wellness, D2C consumer goods)
> Photorealistic UGC creator style, shot-on-phone authenticity with editorial polish, real relatable human moments, natural expressions, soft natural daylight, home environment, 8K detail, no CGI look.

**CINEMATIC_PREMIUM** (tech, audio, fashion, automotive)
> High-end commercial cinematography, realistic handheld camera physics, golden-hour urban tones, shallow depth of field, luxury campaign finish, motivated lighting, 4K HDR realism.

**PIXAR_3D_STYLIZED** (food, kids, playful brands, mascots)
> Premium Pixar-style 3D stylized rendering, soft global illumination, vivid but calm color grading, charming expressive character, gentle depth of field, serene polished CG finish.

**CLEAN_STUDIO** (SaaS, electronics, minimal luxury)
> Minimal studio product photography, seamless backdrop in brand color, controlled softbox lighting, floating product hero shots, precise reflections, Apple-style negative space.

**FOOD_APPETITE** (F&B, restaurants)
> Macro food cinematography, steam and texture emphasis, rich saturated appetite colors, slow-motion-feel splash and drizzle moments, warm inviting kitchen light.

---

## 4. SHOT-ARC PRESET (10 seconds · 6 shots) — how the app builds `{{SHOT_1..6}}`

Each shot line = **[framing] + [subject action] + [product visibility] + [camera move hint]**. One sentence, concrete verbs, no abstractions.

| # | Beat | Formula |
|---|---|---|
| 1 | Hook | Close-up of {{ON_SCREEN_TALENT}} in {{SETTING}} reacting to the pain point; direct eye contact with camera; product not yet visible; slight handheld push-in. |
| 2 | Reveal | Macro product shot — {{PRODUCT_VISUAL_DESCRIPTION}} held toward camera at {{PRODUCT_HERO_ANGLE}}; shallow depth of field; background bokeh. |
| 3 | Action | Medium shot of talent using/applying/interacting with the product; hands and product both clearly visible; natural motion; match-cut friendly framing. |
| 4 | Payoff | Close-up of the visible result or benefit ({{KEY_BENEFITS}}); expression of satisfaction; soft rack focus from product to face. |
| 5 | Lifestyle | Wide relatable moment — talent living the benefit in {{SETTING}}; product placed naturally in frame; warm ambient tone. |
| 6 | CTA | Hero end-frame: talent smiling, product held at chest level, label crisp and dominant, slow push-in, space reserved for CTA text. |

For 8-shot variants (fast-cut social ads), split beats 3 and 4 into two shots each at ~1.25s.

---

## 5. OMNI FLASH HANDOFF NOTE (prepend to your video-gen prompt, not the image prompt)

```
IMPORTANT: The attached storyboard is a reference board. Treat each numbered panel as an individual full-screen shot, read left-to-right, top-to-bottom. Do NOT animate the collage or show the grid. Total duration 10 seconds across 6 shots with hard cuts. Preserve the exact product design and the same on-screen talent from the reference in every shot.
```

---

## 6. FILLED MINI-EXAMPLE (skincare, for QA-testing the pipeline)

> Create a crisp, clean, professional AD STORYBOARD POSTER for "Whiter & Brighter Face Wash" by Prerana Wellness. 9:16 layout, clean white background... Panel 1 — HOOK SHOT (~1.5s): Close-up of an Indian woman in her mid-20s in a sunlit beige bedroom, touching her cheek with a concerned-then-curious expression, direct eye contact, product not yet visible, slight handheld push-in. Caption text: "Dull skin? Watch this." ... *(continue with §2 filled end-to-end)*

---

## 7. IMPLEMENTATION TIPS

1. **Keep all in-image text ≤8 words per string** and pass it in quotes — Nano Banana renders short quoted strings far more accurately than paragraphs.
2. **The consistency lock section is the highest-value block** — Omni Flash inherits whatever the board shows, so panel-to-panel character/product drift in the storyboard becomes drift in the video. If the user's URL has real product photos, also pass one as a reference image alongside this prompt and add: "Use the exact product from the reference image."
3. **Never let the app invent claims** — `{{KEY_BENEFITS}}` and `{{HOOK_LINE}}` must come verbatim-adjacent from the landing page to avoid generating misleading ad copy.
4. **Fallbacks:** if audience detection is low-confidence, default `{{ON_SCREEN_TALENT}}` to a 25–34 neutral-styled persona matching the site's geography; if no brand colors extract, default to "warm neutral beige + white + one accent from the product packaging."
5. Validate the generated board before video handoff: 6 numbered panels present, header text spelled correctly, product visible in panels 2, 3, and 6.
