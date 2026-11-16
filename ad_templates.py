"""
Meta image-ad layout templates for Nano Banana Pro.

Built from the Meta Ads Template Atlas (1:1 masters with reflow rules, six-word headlines,
one CTA, copy lives in Ads Manager), the Arriv product-shot archetypes (studio graphic,
macro texture, elemental/cooling, dewy lifestyle, outdoor light) and the photoreal prompt
template (REFERENCE ROLES -> ... -> AVOID, product lock, label fidelity).

Text rule for every template: the image carries only the brand wordmark, one headline of
six words or fewer and one CTA pill. Primary text, the Meta headline field and benefits
belong in the ad copy, not in the pixels.
"""
import re
from typing import Any, Dict, List, Optional, Tuple

PRODUCT_MODE = "product"
SERVICE_MODE = "service"

MAX_HEADLINE_WORDS = 6
MAX_CTA_WORDS = 3

# ---------------------------------------------------------------------------
# Template library
# ---------------------------------------------------------------------------
# Fields:
#   mode        product (needs a physical product, ideally a reference photo) or service (no product image)
#   frameworks  marketing frameworks this layout suits (problem_solution, feature_callout, social_proof,
#               us_vs_them, lifestyle_hero)
#   style       "photo" (photoreal campaign photography) or "illustration" (clean 3D / UI illustration)
#   set         the scene / visual device
#   hero        where and how the product (or hero object) sits
#   camera, light
#   talent      True when a model appears (uses the campaign's on-screen talent)
#   square      1:1 master zone layout for the three text elements
TEMPLATES: Dict[str, Dict[str, Any]] = {
    # ----------------------------- product mode -----------------------------
    "studio_graphic": {
        "name": "Architectural Studio Plinth",
        "mode": PRODUCT_MODE,
        "frameworks": ["feature_callout", "lifestyle_hero"],
        "style": "photo",
        "summary": "Curated architectural plinth on a textured tonal set with directional raking light and crisp contact shadows.",
        "set": "Architectural studio set with polished travertine stone or honed micro-cement plinths against a seamless matte curved wall tinted in 60% brand canvas hue. Generous negative space, zero visual clutter.",
        "hero": "The hero product commands the primary plinth in the golden ratio zone (approx 55% frame height), label perfectly squared, tack-sharp focal depth, grounded by natural contact shadow and ambient occlusion.",
        "camera": "85mm prime commercial lens, eye level with subtle 5-degree low heroic perspective, razor-sharp focus on brand packaging.",
        "light": "Sculpted 45-degree directional key light creating soft raking shadow roll-off, with delicate 20% bounce fill preserving label micro-typography and authentic material finish.",
        "talent": False,
        "square": "Headline across the top 20%, centred. Product zone 24-82%. Bottom 14%: brand wordmark on the left, CTA pill on the right.",
    },
    "macro_texture": {
        "name": "Macro Texture Swatch",
        "mode": PRODUCT_MODE,
        "frameworks": ["feature_callout"],
        "style": "photo",
        "summary": "Hero product anchored beside an authentic macro swatch of its formulation or material with raking specular texture.",
        "set": "Curated tabletop in a warm matte neutral tint of the brand canvas. In the foreground, an authentic macro swatch of the product's own formula or material (rich cream, glistening serum gel, tactile woven textile, or polished mineral), capturing microscopic tactile depth and physical realism.",
        "hero": "The product stands upright in the golden ratio vertical third, about 50% of the frame height, just behind the swatch, label facing the camera with surgical optical sharpness.",
        "camera": "100mm macro lens, 30-degree overhead angle, shallow depth of field with both product and swatch in crisp focus.",
        "light": "Soft top-down diffused daylight with clean specular highlights defining the material texture; bright, fresh, high-key commercial fidelity.",
        "talent": False,
        "square": "Headline top-left in the upper 20%, left-aligned, up to two lines. Brand wordmark small at the top-right. CTA pill bottom-left.",
    },
    "hand_held": {
        "name": "Hand-Held Hero",
        "mode": PRODUCT_MODE,
        "frameworks": ["problem_solution", "lifestyle_hero"],
        "style": "photo",
        "summary": "Hand thrusts the product toward the lens on a monochrome set.",
        "set": "Monochrome seamless set in one brand colour, nothing else in frame.",
        "hero": "A hand (sleeve in a tint of the set colour) reaches toward the lens from the lower right holding the product. Forced perspective makes the product large, about 50% of the frame height. Fingers only on the sides, label flat to the camera, fully visible and crisp; the arm falls softly out of focus.",
        "camera": "24mm lens close to the hand, slightly low angle.",
        "light": "Bright soft high-key light, gentle shadow under the hand, clean true-to-life colour.",
        "talent": False,
        "square": "Brand wordmark small at the top-left. Headline directly beneath it in the clear upper-left area, left-aligned, up to two lines. CTA pill bottom-left.",
    },
    "model_lifestyle": {
        "name": "Model Lifestyle Split",
        "mode": PRODUCT_MODE,
        "frameworks": ["social_proof", "lifestyle_hero"],
        "style": "photo",
        "summary": "Model holding the product on the left, calm space for type on the right.",
        "set": "{setting}, uncluttered, soft natural window light, colours drawn from the brand palette.",
        "hero": "The model holds the product near the cheek or shoulder, label facing the camera, fingers on the sides only. Model and product fill the left 55% of the frame; the right 45% is calm clean background.",
        "camera": "50mm at eye level, sharp on the face and the product, gentle background blur.",
        "light": "Soft daylight from the side, natural skin with real texture, no harsh shadows.",
        "talent": True,
        "square": "Right 45% column: brand wordmark small at the top, headline in the upper-middle, CTA pill directly under the headline. Nothing overlaps the model or the product.",
    },
    "elemental_set": {
        "name": "Elemental Benefit Set",
        "mode": PRODUCT_MODE,
        "frameworks": ["problem_solution"],
        "style": "photo",
        "summary": "Product on a prop bed that shows its key benefit (ice, water, botanicals, sun).",
        "set": "The product sits on an elemental prop bed that visualises its key benefit, '{benefit}'. Pick the ONE element that fits: cracked ice and cool mist for cooling or freshness, water ripples and droplets for hydration, fresh leaves and botanicals for natural ingredients, warm sunlight and sand for sun care, soft steam for warmth. Tones harmonise with the brand palette.",
        "hero": "The product stands upright centre-lower, about 45% of the frame height, label facing the camera; light droplets or condensation on its surface but the label stays legible.",
        "camera": "Low 70mm macro angle, the product tack-sharp, background softly falling off.",
        "light": "Crisp rim light separating the product from the set, clean bright fill.",
        "talent": False,
        "square": "Headline across the top 20%, centred. Brand wordmark small above the CTA pill, both centred in the bottom 14%.",
    },
    "split_contrast": {
        "name": "Before / After Split",
        "mode": PRODUCT_MODE,
        "frameworks": ["us_vs_them"],
        "style": "photo",
        "summary": "Dull 'before' half versus a bright half with the product.",
        "set": "The frame is split vertically into two halves of the same scene. LEFT: a muted, desaturated grey version showing {contrast_before}, with no product. RIGHT: the same scene bright, fresh and in brand colours, with the product in it. A clean vertical divide between them.",
        "hero": "The product stands in the right half, centred, about 45% of the frame height, label facing the camera.",
        "camera": "Eye level 50mm, identical framing on both halves.",
        "light": "Left half flat and grey; right half bright, soft and inviting.",
        "talent": False,
        "square": "Headline across the top 18%, spanning both halves, centred. Brand wordmark bottom-left, CTA pill bottom-right.",
    },
    "outdoor_light": {
        "name": "Outdoor Golden Hour",
        "mode": PRODUCT_MODE,
        "frameworks": ["lifestyle_hero"],
        "style": "photo",
        "summary": "Product held against a sunlit outdoor backdrop.",
        "set": "Sunlit outdoor backdrop that suits the audience ({setting}), softly blurred, warm golden-hour grade, natural lens flare at the edge of the frame.",
        "hero": "A hand holds the product up in the foreground, about 45% of the frame height, label sharp, flat to the camera and legible, fingers on the sides only.",
        "camera": "35mm, slightly low angle, shallow depth of field.",
        "light": "Warm low sun from behind as a rim light, soft bounce fill on the label.",
        "talent": False,
        "square": "Headline in the clear sky area across the top 22%, centred. Brand wordmark and CTA pill centred in the bottom 14%.",
    },
    # ----------------------------- service mode -----------------------------
    "chaos_grid": {
        "name": "Bento Grid Focus",
        "mode": SERVICE_MODE,
        "frameworks": ["problem_solution"],
        "style": "photo",
        "summary": "Linear/Stripe-style bento grid: chaotic workflow rendered as muted glass cards, with ONE illuminated hero module in vibrant brand accent.",
        "set": "Modern architectural glassmorphism bento layout on deep slate canvas (#090d16). Surrounding modules rendered as semi-translucent frosted glass panels with delicate 1px border glows and muted abstract data lines.",
        "hero": "ONE focal bento module in the upper 55% glows in the brand accent with a crisp micro-metric card, status pill, and clean vector visual: pure signal emerging from noise.",
        "camera": "Direct straight-on architectural perspective with subtle isometric depth.",
        "light": "Luminous chromatic bloom behind the hero bento card, rich ambient occlusion and subtle rim lighting.",
        "talent": False,
        "square": "Visual in the top 60%. Headline centred in the band below it. Bottom 14%: brand wordmark on the left, CTA pill on the right.",
    },
    "product_moment": {
        "name": "In-Product Moment",
        "mode": SERVICE_MODE,
        "frameworks": ["feature_callout"],
        "style": "photo",
        "summary": "Elevated bezel-less device displaying an authentic modern UI card mid-action with crisp typographic hierarchy.",
        "set": "Minimalist architectural studio set with subtle gradient floor. A premium bezel-less {device} sits upright at a gentle 10-degree tilt (screen oriented normally and upright, never inverted).",
        "hero": "The screen reveals a clean {brand} interface in the brand palette: clean typographic headers, masked data pills, and ONE highlighted status card in the brand accent confirming success.",
        "camera": "Three-quarter architectural view, gentle perspective, crisp device edges.",
        "light": "Soft studio light with subtle perimeter rim highlight on the glass and chassis.",
        "talent": False,
        "square": "Left 45% column: brand wordmark small at the top, headline in the middle, CTA pill below it.",
    },
    "control_panel": {
        "name": "Tactile Modern Control",
        "mode": SERVICE_MODE,
        "frameworks": ["social_proof"],
        "style": "photo",
        "summary": "Tactile precision panel in frosted glass and matte metal with luminous toggle indicators in brand accent.",
        "set": "A tactile architectural control surface in matte dark aluminum or frosted glass filling the top 58% of the frame.",
        "hero": "Three physical toggle switches or tactile sliders all set to active state, their tracks lit in the vibrant brand accent with clean engraved minimalist glyphs.",
        "camera": "45-degree three-quarter view, shallow depth of field focused sharply on the primary control toggle.",
        "light": "Soft overhead studio key light with a crisp specular line along the brushed metal bevel.",
        "talent": False,
        "square": "Panel in the top 58%. Headline centred below it. Bottom 14%: brand wordmark on the left, CTA pill on the right.",
    },
    "consolidation": {
        "name": "Bento Workflow Consolidation",
        "mode": SERVICE_MODE,
        "frameworks": ["us_vs_them"],
        "style": "photo",
        "summary": "Scattered fragmented tool windows streamline into one unified, elegant glassmorphic hub.",
        "set": "Minimalist architectural canvas with subtle directional lighting. Upper zone: fragmented small translucent cards floating with red alert indicators. Downward flow connects to the lower focal zone: one large, unified frosted glass tile glowing in brand accent with the brand initial.",
        "hero": "The unified hero tile stands isolated in calm, generous negative space, communicating effortless resolution.",
        "camera": "Straight-on architectural perspective.",
        "light": "Clean, directional studio lighting with subtle ambient bloom.",
        "talent": False,
        "square": "Illustration in the top 64%. Headline centred below it. Brand wordmark and CTA pill centred in the bottom 14%.",
    },
    "metaphor_object": {
        "name": "Sculptural Art Metaphor",
        "mode": SERVICE_MODE,
        "frameworks": ["lifestyle_hero"],
        "style": "photo",
        "summary": "Tactile sculptural art piece embodying the core product promise, crafted from authentic materials (frosted glass, brushed aluminum, matte travertine).",
        "set": "Minimalist architectural gallery alcove or seamless warm tonal cyclorama adhering to 60% brand canvas hue.",
        "hero": "ONE sculptural art object embodying '{benefit}' ({metaphor_examples}). Rendered in authentic physical materials (frosted cast glass, precision-machined brass, or honed stone) grounded by a soft contact shadow, centered in the upper 60%.",
        "camera": "Slight low angle, 85mm prime lens, object in crisp surgical focus.",
        "light": "Museum gallery directional spotlighting, delicate caustic refraction, rich textural depth and soft shadow falloff.",
        "talent": False,
        "square": "Object in the upper 60%. Headline centred below it. Brand wordmark and CTA pill centred in the bottom 14%.",
    },
    "levitation_device": {
        "name": "Dark Minimalist Bloom",
        "mode": SERVICE_MODE,
        "frameworks": ["lifestyle_hero", "feature_callout"],
        "style": "photo",
        "summary": "Upright premium device centered over a deep slate field with an atmospheric brand accent bloom.",
        "set": "A deep obsidian field (#090d16) with a soft, cinematic chromatic bloom of the brand accent emanating behind the device.",
        "hero": "A sleek generic {device} sits upright (never inverted, screen right-side up) in the upper-centre, occupying 55% of the frame height, screen displaying an authentic {brand} dashboard in clean dark mode.",
        "camera": "Straight-on commercial lens, tack-sharp edges.",
        "light": "Precise edge rim light tracing the device chassis, ambient fill from the accent bloom.",
        "talent": False,
        "square": "Device in the upper 62%. Headline centred below it. Brand wordmark and CTA pill centred in the bottom 14%.",
    },

    # ----------------------------- fashion & apparel -----------------------------
    "fashion_editorial": {
        "name": "Fashion Editorial Stance",
        "mode": PRODUCT_MODE,
        "frameworks": ["lifestyle_hero", "social_proof"],
        "style": "photo",
        "summary": "Full-length or 3/4 editorial styling on minimal architectural set or cyclorama.",
        "set": "Architectural studio set with clean limestone or tinted cyclorama wall in the lightest brand palette colour. Soft diffused daylight from large window scrim, natural shadows.",
        "hero": "The model wears the featured garment naturally with effortless posture, 3/4 or full-body framing. The cut, fabric drape, and silhouette are in tack-sharp focus.",
        "camera": "50mm portrait lens at eye level, shallow depth of field softly falling off behind.",
        "light": "Soft diffused key light, natural subtle fill preserving genuine fabric weave and color fidelity.",
        "talent": True,
        "square": "Brand wordmark top-left, headline directly under in the upper-left, CTA pill bottom-left. Calm space around model.",
    },
    "apparel_flatlay": {
        "name": "Curated Styling Flatlay",
        "mode": PRODUCT_MODE,
        "frameworks": ["feature_callout", "problem_solution"],
        "style": "photo",
        "summary": "Curated top-down styling grid of garment and tonal accessories on textured linen.",
        "set": "Top-down overhead view of textured neutral linen or polished micro-cement surface. The garment is neatly folded or styled flat alongside 1-2 minimal complementary accessories.",
        "hero": "The featured product occupies the center 60% of the flatlay, pristine folds, tags or brand label crisp and legible.",
        "camera": "90-degree direct overhead top-down shot, 50mm, completely flat plane of focus.",
        "light": "Clean directional morning light casting soft organic shadows to the lower right.",
        "talent": False,
        "square": "Headline top 20% centred. Wordmark and CTA pill in bottom 14% with breathing room.",
    },
    "garment_craft_detail": {
        "name": "Craft & Fabric Macro Crop",
        "mode": PRODUCT_MODE,
        "frameworks": ["feature_callout"],
        "style": "photo",
        "summary": "Tight macro detail crop on premium fabric weave, custom stitching, or hardware.",
        "set": "Macro studio tabletop or drape. In the foreground, a close-up macro view highlighting the product's premium material texture, precise stitching, zipper hardware, or unique fabric weave.",
        "hero": "The textural detail fills the right 60% of the frame with razor-sharp focal clarity, showing authentic touch and quality.",
        "camera": "100mm macro lens, angled 35 degrees, razor-sharp focus on the material detail.",
        "light": "High-contrast raking side light emphasizing tactile surface dimension, weave, and depth.",
        "talent": False,
        "square": "Headline top-left in clear column. Brand wordmark top-right. CTA pill bottom-left.",
    },
    "street_lifestyle": {
        "name": "Urban Street Movement",
        "mode": PRODUCT_MODE,
        "frameworks": ["lifestyle_hero", "problem_solution"],
        "style": "photo",
        "summary": "Candid model wearing the piece mid-stride in an authentic sunlit street setting.",
        "set": "Sunlit architectural city sidewalk, minimalist storefront or modern urban plaza with soft natural blur.",
        "hero": "Relatable everyday model walking mid-stride wearing the product, authentic natural motion, clothing moving realistically.",
        "camera": "35mm street camera at eye level, capturing a spontaneous lifestyle moment.",
        "light": "Golden natural outdoor daylight with crisp rim separation.",
        "talent": True,
        "square": "Headline across the upper clean sky or wall zone, CTA pill bottom-right.",
    },

    # ----------------------------- jewelry & luxury -----------------------------
    "jewelry_macro": {
        "name": "Jewelry Facet Macro",
        "mode": PRODUCT_MODE,
        "frameworks": ["feature_callout", "problem_solution", "us_vs_them"],
        "style": "photo",
        "summary": "Extreme macro close-up on slate or travertine stone with razor-sharp metallic luster.",
        "set": "Dark matte slate or warm travertine stone plinth with subtle natural mineral texture.",
        "hero": "The jewelry or watch sits upright, razor-sharp reflections on polished metal facets and clean gemstone brilliance, label/mark crisp.",
        "camera": "100mm macro, low perspective, surgical focus on the hero jewelry face.",
        "light": "Precise cinematic rim lighting with soft directional fill highlighting luster without glare.",
        "talent": False,
        "square": "Headline across top 20%. Wordmark and CTA pill bottom 14% centered.",
    },
    "jewelry_model": {
        "name": "Luxury Editorial Worn",
        "mode": PRODUCT_MODE,
        "frameworks": ["lifestyle_hero", "social_proof"],
        "style": "photo",
        "summary": "Model wearing the jewelry piece against a warm editorial backdrop.",
        "set": "Warm studio backdrop with gentle painterly chiaroscuro light and deep shadow gradation.",
        "hero": "Model's wrist, neck, ear, or hand wearing the piece, graceful poise, real skin texture with the jewelry in tack-sharp focus.",
        "camera": "85mm portrait, shallow depth of field, focused squarely on the jewelry.",
        "light": "Soft sculpted key light from 45 degrees, illuminating the jewel and natural skin tones.",
        "talent": True,
        "square": "Left column headline and CTA pill, model and piece filling the right 55%.",
    },

    # ----------------------------- food & beverage -----------------------------
    "appetite_hero": {
        "name": "Appetite Tabletop Hero",
        "mode": PRODUCT_MODE,
        "frameworks": ["lifestyle_hero", "problem_solution", "feature_callout"],
        "style": "photo",
        "summary": "Mouth-watering studio tabletop capture of food/drink at 45 degrees with fresh garnish.",
        "set": "Rustic natural wood, slate, or marble countertop with organic fresh ingredients or garnishes nearby.",
        "hero": "The food or drink product sits center-frame at peak appetizing freshness—condensation droplets, gentle steam, or glistening rich texture.",
        "camera": "50mm food photography lens, 45-degree angle, crisp depth of field.",
        "light": "Warm back-three-quarter window light creating delicious specular glints, soft fill.",
        "talent": False,
        "square": "Headline top 20% centered, CTA pill bottom 14% centered.",
    },
    "pour_action": {
        "name": "Dynamic Pour & Splash Action",
        "mode": PRODUCT_MODE,
        "frameworks": ["feature_callout", "problem_solution"],
        "style": "photo",
        "summary": "High-speed suspended pour, drizzle or splash capture in mid-air.",
        "set": "Clean studio backdrop in brand tone with surface reflections.",
        "hero": "Rich pour into a glass, drizzle of honey/sauce, or splash frozen in mid-air with crisp liquid droplets and dynamic motion.",
        "camera": "1/2000s high-speed shutter macro capture, freeze-frame clarity on liquid droplets.",
        "light": "Bright punchy rim flash isolating the droplets against the clean background.",
        "talent": False,
        "square": "Headline top-left, CTA pill bottom-left, action centered.",
    },
    "table_lifestyle": {
        "name": "Convivial Table Spread",
        "mode": PRODUCT_MODE,
        "frameworks": ["social_proof", "lifestyle_hero"],
        "style": "photo",
        "summary": "Warm dining table scene with hands reaching in to enjoy, natural convivial warmth.",
        "set": "Sunlit café or home dining table with plates, glasses, and natural linen napkins.",
        "hero": "The product in the middle of an inviting spread, everyday hands reaching in to share or pour, warm relaxed atmosphere.",
        "camera": "35mm slightly high angle capturing the communal joy of eating/drinking.",
        "light": "Warm soft sunlight filtering across the table.",
        "talent": True,
        "square": "Headline across the top, wordmark and CTA pill in bottom corner.",
    },

    # ----------------------------- electronics & tech hardware -----------------------------
    "tech_exploded_pedestal": {
        "name": "Industrial Design Plinth",
        "mode": PRODUCT_MODE,
        "frameworks": ["feature_callout", "us_vs_them"],
        "style": "photo",
        "summary": "Device standing on dark anodized pedestal with precise rim light tracing contours.",
        "set": "Matte dark grey or brushed aluminum plinth, subtle gradient background with brand accent glow.",
        "hero": "The device or hardware rests at a three-quarter angle, surgical edge reflections tracing its industrial design and port/button details.",
        "camera": "85mm product lens, eye-level, flawless edge definition and zero distortion.",
        "light": "Dual rim lights in brand accent highlighting chamfered edges, soft frontal bounce.",
        "talent": False,
        "square": "Headline across top 20%, product centered, CTA pill bottom-right.",
    },
    "desk_setup": {
        "name": "Creator Desk Setup",
        "mode": PRODUCT_MODE,
        "frameworks": ["lifestyle_hero", "problem_solution"],
        "style": "photo",
        "summary": "Aesthetic modern workstation showing device seamlessly integrated in situ.",
        "set": "Warm walnut or oak desktop, desk mat, warm ambient screen glow, small succulent plant, clean cable-free minimalism.",
        "hero": "The hardware device positioned in active use on the desk, looking essential, ergonomic and premium.",
        "camera": "40mm slightly elevated three-quarter view, gentle natural depth.",
        "light": "Warm ambient monitor glow combined with soft natural daylight from side.",
        "talent": False,
        "square": "Left 40% column for headline and CTA, desk setup on right 60%.",
    },

    # ----------------------------- home & furniture -----------------------------
    "room_scene": {
        "name": "Modern Interior In-Situ",
        "mode": PRODUCT_MODE,
        "frameworks": ["lifestyle_hero", "social_proof", "problem_solution"],
        "style": "photo",
        "summary": "Warmly lit modern living room or bedroom with product naturally situated as hero.",
        "set": "Clean Scandinavian or warm minimalist interior room with hardwood floors, neutral walls, and morning window sunlight.",
        "hero": "The furniture or home decor item situated as the harmonious centerpiece of the room, looking lived-in and inviting.",
        "camera": "35mm wide-normal lens, architectural eye level, straight verticals.",
        "light": "Natural morning sunlight streaming through sheer curtains casting soft shadows.",
        "talent": False,
        "square": "Headline top 20% centered, CTA pill bottom 14% centered.",
    },
    "corner_vignette": {
        "name": "Architectural Corner Vignette",
        "mode": PRODUCT_MODE,
        "frameworks": ["feature_callout", "lifestyle_hero"],
        "style": "photo",
        "summary": "Stylized architectural corner crop with plaster wall and serene breathing room.",
        "set": "Textured lime-wash plaster wall corner, hardwood or polished concrete floor, botanical branch in ceramic vase nearby.",
        "hero": "The product positioned in the quiet corner with generous negative space, highlighting craft and material finish.",
        "camera": "50mm, eye-level, serene composition.",
        "light": "Soft diffused raking light highlighting the wall and product textures.",
        "talent": False,
        "square": "Right column calm for headline and CTA, product in lower left.",
    },

    # ----------------------------- fitness & sports -----------------------------
    "athletic_action": {
        "name": "Athletic Motion Power",
        "mode": PRODUCT_MODE,
        "frameworks": ["lifestyle_hero", "problem_solution"],
        "style": "photo",
        "summary": "High-energy training scene with relatable athlete in motion using the gear.",
        "set": "Modern athletic training space, outdoor running track, or rugged natural trail.",
        "hero": "Everyday determined athlete in motion actively using or wearing the product, authentic sweat and determination, dynamic movement.",
        "camera": "35mm fast shutter speed, low dynamic angle capturing speed and grit.",
        "light": "Dramatic directional sun or stadium key light with crisp edge rim separating the athlete.",
        "talent": True,
        "square": "Bold headline top-left, CTA pill bottom-right, athlete centered.",
    },
    "gym_floor_hero": {
        "name": "Gym Floor Equipment Hero",
        "mode": PRODUCT_MODE,
        "frameworks": ["feature_callout", "us_vs_them"],
        "style": "photo",
        "summary": "Product resting on textured rubber gym mat or locker bench, focused lighting.",
        "set": "Textured black rubber gym mat floor, raw concrete wall, metallic locker in background.",
        "hero": "The fitness gear/supplement resting securely on the gym floor, ready for action, tactile grip surfaces clearly visible.",
        "camera": "Low ground-level 50mm shot, product commanding the frame.",
        "light": "Overhead spotlighting creating high-contrast athletic intensity.",
        "talent": False,
        "square": "Headline top 20%, CTA pill bottom 14%.",
    },

    # ----------------------------- local & professional services -----------------------------
    "service_consultation": {
        "name": "Approachable Expert Consultation",
        "mode": SERVICE_MODE,
        "frameworks": ["feature_callout", "social_proof"],
        "style": "photo",
        "summary": "Bright modern office or clinic setting with friendly expert engaging warmly.",
        "set": "Clean, bright, contemporary consultation room or clinic with warm wood accents, comfortable seating, and natural daylight.",
        "hero": "Approachable professional greeting a client with a warm smile, attentive and reassuring body language.",
        "camera": "50mm eye-level portrait lens, gentle background defocus.",
        "light": "Soft flattering window light, welcoming and trustworthy.",
        "talent": True,
        "square": "Right 45% for headline, logo, and CTA. Expert on left 55%.",
    },
    "client_result": {
        "name": "Client Transformation Result",
        "mode": SERVICE_MODE,
        "frameworks": ["problem_solution", "lifestyle_hero", "us_vs_them"],
        "style": "photo",
        "summary": "Happy customer experiencing the finished outcome with authentic relief and joy.",
        "set": "Beautiful finished home, bright clinic, or modern workspace showing the transformation.",
        "hero": "Customer smiling with genuine satisfaction, relaxed posture, enjoying the tangible result of the service.",
        "camera": "35mm natural perspective, candid and unposed.",
        "light": "Bright, uplifting, high-key natural daylight.",
        "talent": True,
        "square": "Headline across the top, CTA pill bottom-right.",
    },
}

# ---------------------------------------------------------------------------
# Creative Library Presets Registration (Pinterest Reference Design Atlas)
# ---------------------------------------------------------------------------
try:
    from creative_library_presets import CREATIVE_PRESETS
    for _pid, _p in CREATIVE_PRESETS.items():
        if _pid not in TEMPLATES:
            TEMPLATES[_pid] = {
                "name": _p["name"],
                "mode": PRODUCT_MODE if _p["industry_slug"] in (
                    "beauty-cosmetics", "fashion-apparel", "food-beverage",
                    "jewelry-luxury", "fitness-sports", "ecommerce-retail"
                ) else SERVICE_MODE,
                "frameworks": ["problem_solution", "feature_callout", "social_proof", "us_vs_them", "lifestyle_hero"],
                "style": "photo",
                "summary": _p["summary"],
                "set": _p["layout"]["composition"],
                "hero": _p["layout"]["hierarchy"],
                "camera": "Eye-level commercial lens with crisp focal depth",
                "light": _p["lighting"],
                "talent": False,
                "square": "Meta 1:1 master layout with headline top 20%, hero center, wordmark and CTA bottom",
            }
except Exception:
    pass

# ---------------------------------------------------------------------------
# Industry Category Classification
# ---------------------------------------------------------------------------
CATEGORY_KEYWORDS: Dict[str, Tuple[str, ...]] = {
    "fashion": (
        "fashion", "clothing", "apparel", "wear", "dress", "shirt", "pants", "jeans", "denim",
        "jacket", "coat", "hoodie", "streetwear", "activewear", "sportswear", "swimwear", "shoes",
        "footwear", "sneakers", "boots", "sandals", "heels", "bag", "handbag", "backpack", "wallet",
        "belt", "hat", "scarf", "sunglasses", "outfit", "garment", "textile"
    ),
    "jewelry": (
        "jewelry", "jewellery", "watch", "watches", "ring", "rings", "necklace", "pendant",
        "bracelet", "earrings", "gemstone", "diamond", "gold", "silver", "luxury", "chronograph"
    ),
    "food_beverage": (
        "food", "beverage", "beverages", "drink", "drinks", "coffee", "tea", "snack", "snacks",
        "chocolate", "candy", "bakery", "cookie", "cake", "sauce", "spice", "condiment", "meal",
        "restaurant", "recipe", "beer", "wine", "cocktail", "supplement", "protein",
        "nutrition", "vitamins", "gourmet", "organic", "cafe", "eats", "brew", "brews", "roast", "roaster", "culinary"
    ),
    "beauty": (
        "beauty", "skincare", "skin care", "cosmetics", "makeup", "lipstick", "lip", "serum",
        "moisturizer", "moisturiser", "lotion", "cream", "cleanser", "toner", "sunscreen", "spf",
        "haircare", "hair care", "shampoo", "conditioner", "perfume", "fragrance", "scent",
        "bodycare", "wellness", "anti-aging"
    ),
    "electronics": (
        "electronic", "electronics", "gadget", "gadgets", "tech", "audio", "headphone", "headphones",
        "earbuds", "speaker", "phone", "smartphone", "tablet", "computer", "laptop", "monitor",
        "keyboard", "mouse", "gaming", "console", "camera", "charger", "cables", "wearable",
        "hardware", "device"
    ),
    "home_living": (
        "furniture", "sofa", "couch", "chair", "table", "desk", "bed", "mattress", "bedding",
        "pillow", "decor", "home decor", "lighting", "lamp", "rug", "curtain", "kitchenware",
        "cookware", "pan", "knife", "appliance", "candle", "pet", "dog", "cat", "garden", "home",
        "dining table", "living room", "interior"
    ),
    "fitness": (
        "fitness", "workout", "gym", "exercise", "athletic", "running", "yoga", "pilates",
        "crossfit", "weights", "dumbbell", "training", "sport", "cycling", "bike", "outdoor gear"
    ),
    "local_service": (
        "dental", "dentist", "clinic", "doctor", "medical", "healthcare", "therapy", "salon",
        "barber", "barbershop", "spa", "real estate", "realtor", "property", "legal", "lawyer",
        "attorney", "consultant", "consulting", "coach", "coaching", "accounting", "cpa",
        "plumbing", "roofing", "cleaning", "contractor", "repair", "agency", "service", "services",
        "local service", "professional service"
    ),
    "fintech": (
        "fintech", "finance", "financial", "banking", "bank", "crypto", "trading",
        "investment", "invest", "loan", "wallet", "tax", "accounting", "insurance", "card", "money", "payment"
    ),
    "saas_tech": (
        "software", "saas", "app", "platform", "cloud", "api", "crm", "dashboard", "analytics",
        "automation", "b2b", "workflow", "ai ", "tool"
    ),
}

def detect_product_category(category: Any, business_type: Optional[str] = "", product_name: Optional[str] = "") -> str:
    """Classifies brand into a specific industry vertical using weighted scoring."""
    extra_sources = []
    if isinstance(category, dict):
        d = category
        category = d.get("brand_category") or d.get("category") or ""
        business_type = business_type or d.get("business_type") or ""
        product_name = product_name or d.get("product_name") or ""
        extra_sources.extend([
            str(d.get("brand_name") or ""),
            str(d.get("brand_description") or ""),
            str(d.get("summary") or ""),
            str(d.get("product_visual_description") or ""),
        ])

    cat_clean = (str(category or "")).strip().lower()
    if cat_clean in CATEGORY_KEYWORDS:
        return cat_clean

    cat_text = f" {cat_clean} "
    extra_text = f" {str(business_type or '').lower()} {str(product_name or '').lower()} {' '.join(s.lower() for s in extra_sources if s)} "

    best_cat = None
    best_score = 0

    for cat_name, keywords in CATEGORY_KEYWORDS.items():
        score = 0
        for k in keywords:
            pattern = r"(?:\b|_)" + re.escape(k.lower()) + r"(?:\b|_)"
            if re.search(pattern, cat_text):
                score += 3
            elif re.search(pattern, extra_text):
                score += 1
        if score > best_score:
            best_score = score
            best_cat = cat_name

    if best_cat and best_score > 0:
        return best_cat
    return "general_product" if "physical" in (business_type or "").lower() or not business_type else "general_service"

# Category-specific template mappings for marketing frameworks
CATEGORY_DEFAULTS: Dict[str, Dict[str, str]] = {
    "fashion": {
        "problem_solution": "street_lifestyle",
        "feature_callout": "garment_craft_detail",
        "social_proof": "fashion_editorial",
        "us_vs_them": "fashion_editorial",
        "lifestyle_hero": "fashion_editorial",
        "_single": "apparel_flatlay",
    },
    "jewelry": {
        "problem_solution": "jewelry_macro",
        "feature_callout": "jewelry_macro",
        "social_proof": "jewelry_model",
        "us_vs_them": "jewelry_macro",
        "lifestyle_hero": "jewelry_model",
        "_single": "jewelry_macro",
    },
    "food_beverage": {
        "problem_solution": "appetite_hero",
        "feature_callout": "pour_action",
        "social_proof": "table_lifestyle",
        "us_vs_them": "appetite_hero",
        "lifestyle_hero": "table_lifestyle",
        "_single": "appetite_hero",
    },
    "electronics": {
        "problem_solution": "desk_setup",
        "feature_callout": "tech_exploded_pedestal",
        "social_proof": "desk_setup",
        "us_vs_them": "tech_exploded_pedestal",
        "lifestyle_hero": "desk_setup",
        "_single": "tech_exploded_pedestal",
    },
    "home_living": {
        "problem_solution": "room_scene",
        "feature_callout": "corner_vignette",
        "social_proof": "room_scene",
        "us_vs_them": "corner_vignette",
        "lifestyle_hero": "room_scene",
        "_single": "room_scene",
    },
    "fitness": {
        "problem_solution": "athletic_action",
        "feature_callout": "gym_floor_hero",
        "social_proof": "athletic_action",
        "us_vs_them": "athletic_action",
        "lifestyle_hero": "athletic_action",
        "_single": "gym_floor_hero",
    },
    "local_service": {
        "problem_solution": "client_result",
        "feature_callout": "service_consultation",
        "social_proof": "service_consultation",
        "us_vs_them": "client_result",
        "lifestyle_hero": "client_result",
        "_single": "service_consultation",
    },
    "beauty": {
        "problem_solution": "elemental_set",
        "feature_callout": "macro_texture",
        "social_proof": "model_lifestyle",
        "us_vs_them": "split_contrast",
        "lifestyle_hero": "outdoor_light",
        "_single": "studio_graphic",
    },
    "saas_tech": {
        "problem_solution": "saas_bento_grid",
        "feature_callout": "saas_bento_grid",
        "social_proof": "saas_bento_grid",
        "us_vs_them": "saas_bento_grid",
        "lifestyle_hero": "saas_dark_gradient_bloom",
        "_single": "saas_bento_grid",
    },
    "fintech": {
        "problem_solution": "fintech_swiss_trust",
        "feature_callout": "fintech_dark_glassmorphism",
        "social_proof": "fintech_swiss_trust",
        "us_vs_them": "fintech_dark_glassmorphism",
        "lifestyle_hero": "fintech_dark_glassmorphism",
        "_single": "fintech_dark_glassmorphism",
    },
}

# Which template each marketing framework uses by default, per mode
FRAMEWORK_DEFAULTS = {
    PRODUCT_MODE: {
        "problem_solution": "studio_graphic",
        "feature_callout": "studio_graphic",
        "social_proof": "model_lifestyle",
        "us_vs_them": "split_contrast",
        "lifestyle_hero": "outdoor_light",
        "_single": "studio_graphic",
    },
    SERVICE_MODE: {
        "problem_solution": "saas_bento_grid",
        "feature_callout": "saas_bento_grid",
        "social_proof": "saas_bento_grid",
        "us_vs_them": "saas_bento_grid",
        "lifestyle_hero": "saas_dark_gradient_bloom",
        "_single": "saas_bento_grid",
    },
}

FINTECH_WORDS = ("fintech", "finance", "financial", "bank", "payment", "card", "loan", "credit", "insurance",
                 "invest", "wallet", "money", "lending", "tax", "payroll", "accounting", "crypto")
SAAS_WORDS = ("software", "saas", "app", "platform", "api", "ai ", "tool", "cloud", "analytics", "crm",
              "automation", "dashboard", "subscription", "online course", "agency", "consult", "service")


def detect_brand_mode(business_type: Optional[str], category: Optional[str], has_product_ref: bool) -> str:
    """A product photo always means product mode; otherwise trust the analysis, then keywords."""
    if has_product_ref:
        return PRODUCT_MODE
    bt = (business_type or "").lower()
    if bt:
        return PRODUCT_MODE if "physical" in bt or bt == "product" else SERVICE_MODE
    cat = f" {(category or '').lower()} "
    if any(w in cat for w in FINTECH_WORDS + SAAS_WORDS):
        return SERVICE_MODE
    return PRODUCT_MODE


def _service_flavour(business_type: Optional[str], category: Optional[str]) -> str:
    text = f"{business_type or ''} {category or ''}".lower()
    return "fintech" if any(w in text for w in FINTECH_WORDS) else "saas"


def templates_for_mode(mode: str) -> List[Dict[str, Any]]:
    try:
        from creative_library_presets import CREATIVE_PRESETS
        preset_ids = set(CREATIVE_PRESETS.keys())
    except Exception:
        preset_ids = set()

    items = [
        {"id": tid, "name": t["name"], "summary": t["summary"], "frameworks": t["frameworks"], "is_preset": tid in preset_ids}
        for tid, t in TEMPLATES.items() if t["mode"] == mode
    ]
    items.sort(key=lambda x: 0 if x.get("is_preset") else 1)
    return items


def resolve_template_id(blueprint: Any, mode: str, category: str = "") -> str:
    """Use the blueprint's template if it fits the mode, else pick category-tailored default."""
    if isinstance(blueprint, str):
        blueprint = {"template_id": blueprint, "framework_key": blueprint}
    elif not isinstance(blueprint, dict):
        blueprint = {}

    # 1. If blueprint has an explicit template_id (from theme assignment or art direction), prioritize it
    tid = (blueprint.get("template_id") or "").strip()
    if tid and tid != "diverse":
        try:
            from creative_library_presets import CREATIVE_PRESETS
            if tid in CREATIVE_PRESETS:
                return tid
        except Exception:
            pass
        if tid in TEMPLATES:
            return tid

    # 2. If a specific creative library preset is specified (and not diverse), respect it
    preset_id = (blueprint.get("preset_id") or "").strip()
    if preset_id and preset_id != "diverse" and preset_id in TEMPLATES:
        return preset_id

    # 3. Prioritize industry category mapping
    framework = blueprint.get("framework_key") or "_single"
    cat_key = detect_product_category(category)
    if cat_key in CATEGORY_DEFAULTS:
        cat_map = CATEGORY_DEFAULTS[cat_key]
        if framework in cat_map:
            return cat_map[framework]
        if "_single" in cat_map:
            return cat_map["_single"]

    # 4. If tid fits the mode and is valid
    if tid and tid in TEMPLATES and TEMPLATES[tid]["mode"] == mode:
        return tid

    return FRAMEWORK_DEFAULTS.get(mode, {}).get(framework, FRAMEWORK_DEFAULTS.get(mode, {}).get("_single", "saas_bento_grid" if mode == SERVICE_MODE else "studio_graphic"))


def short_headline(text: Optional[str], max_words: int = MAX_HEADLINE_WORDS) -> str:
    """Trim to a short in-image headline (long strings render badly and read as clutter)."""
    words = re.sub(r"\s+", " ", (text or "").strip().strip('"“”')).split(" ")
    words = [w for w in words if w]
    if len(words) <= max_words:
        return " ".join(words)
    return " ".join(words[:max_words]).rstrip(",;:-–—")


def _ratio_layout(square_layout: str, aspect_ratio: str) -> str:
    if aspect_ratio == "4:5":
        return f"Vertical 4:5 extension of this square layout: {square_layout} Add the extra height as breathing room around the hero; keep the same order and alignment."
    if aspect_ratio == "9:16":
        return (
            "Full-screen 9:16 Stories/Reels re-layout: the scene bleeds to every edge, but keep ALL text and the product "
            "out of the top 14% and bottom 20% (Meta's interface covers them). Stack the brand wordmark and headline above "
            "the hero in the middle band, and the CTA pill just under the hero, above the bottom 20%."
        )
    if aspect_ratio == "16:9":
        return "Landscape 16:9 re-layout as a left/right split: brand wordmark, headline and CTA pill stacked in the left 40%, the hero visual in the right 60%."
    return f"Square 1:1 master: {square_layout}"


def build_template_prompt(
    *,
    template_id: str,
    mode: str,
    brand_name: str,
    product_name: str,
    product_category: str = "",
    target_audience_persona: str = "",
    aspect_ratio: str = "1:1",
    headline: str = "",
    cta: str = "Shop Now",
    scene_hint: str = "",
    product_visual_description: str = "",
    color_palette: str = "",
    setting: str = "",
    talent: str = "",
    benefit: str = "",
    contrast_before: str = "",
    business_type: str = "",
    has_product_ref: bool = False,
    custom_directive: Optional[str] = None,
) -> str:
    cat_key = detect_product_category(product_category, business_type, product_name)
    # Guard against non-beauty categories being forced into skincare cream swatches or ice mist
    if template_id == "macro_texture" and cat_key != "beauty":
        if cat_key in CATEGORY_DEFAULTS and "feature_callout" in CATEGORY_DEFAULTS[cat_key]:
            template_id = CATEGORY_DEFAULTS[cat_key]["feature_callout"]
    elif template_id == "elemental_set" and cat_key not in ("beauty", "food_beverage"):
        if cat_key in CATEGORY_DEFAULTS and "problem_solution" in CATEGORY_DEFAULTS[cat_key]:
            template_id = CATEGORY_DEFAULTS[cat_key]["problem_solution"]
    elif template_id in ("chaos_grid", "product_moment", "control_panel", "consolidation") and cat_key == "local_service":
        template_id = "service_consultation"

    try:
        from creative_library_presets import CREATIVE_PRESETS, build_preset_creative_prompt
        if template_id in CREATIVE_PRESETS:
            return build_preset_creative_prompt(
                template_id,
                brand_name=brand_name,
                product_name=product_name,
                headline=short_headline(headline) or f"Meet {product_name or 'the product'}",
                cta=short_headline(cta, MAX_CTA_WORDS) or "Shop Now",
                aspect_ratio=aspect_ratio,
                product_visual_description=product_visual_description,
                color_palette=color_palette,
                custom_directive=custom_directive,
                has_product_ref=has_product_ref,
                setting=setting,
                talent=talent,
            )
    except Exception:
        pass

    t = TEMPLATES.get(template_id, TEMPLATES["studio_graphic"])
    brand = (brand_name or "Brand").strip()
    product = (product_name or "the product").strip()
    image_headline = short_headline(headline) or f"Meet {product}"
    cta_text = short_headline(cta, MAX_CTA_WORDS) or "Shop Now"
    flavour = _service_flavour(business_type, product_category)

    fill = {
        "brand": brand,
        "setting": (setting or "a bright, modern interior that suits the audience").strip().rstrip("."),
        "benefit": (benefit or "the product's main benefit").strip(),
        "contrast_before": (contrast_before or "the everyday problem this product solves").strip().rstrip("."),
        "chaos_surface": "transaction ledger full of manual payment rows" if flavour == "fintech" else "overbooked week calendar and task board",
        "device": "smartphone" if flavour == "fintech" else "laptop",
        "metaphor_examples": (
            "e.g. a shield for security, a key for access, an hourglass for speed, a vault door for savings"
            if flavour == "fintech"
            else "e.g. interlocking rings for integration, a rising staircase for growth, an hourglass for time saved, a compass for clarity"
        ),
    }

    def f(text: str) -> str:
        for k, v in fill.items():
            text = text.replace("{" + k + "}", v)
        return text

    photo = t["style"] == "photo"
    lines: List[str] = [
        "[ROLE: Senior Executive Art Director & Master Commercial Graphic Designer]",
        f"Craft an award-winning Meta {aspect_ratio} commercial ad creative for {brand} ({product_category or 'Commercial'}).",
        "Strictly enforce core graphic design principles: dominant visual hierarchy, 60-30-10 color theory, generous negative space, tactile materiality, and typographic craft.",
        "",
    ]

    # REFERENCE ROLES — the product lock comes first so the model treats the photo as the hero, not inspiration
    if mode == PRODUCT_MODE:
        lines.append("REFERENCE ROLES & PRODUCT FIDELITY")
        if has_product_ref:
            ref_name = "IMAGE 1"
            desc = (product_visual_description or "").strip()
            lines.append(
                f"{ref_name} = PRODUCT-REF: the authentic {product} by {brand}. Use THIS exact product as the hero of the ad. "
                "Reproduce it with absolute commercial fidelity: identical silhouette, proportions, cap or closure, materials, finish, and label graphics. "
                "Do NOT redesign, restyle, recolour, warp, or invent packaging. Keep label typography tack-sharp and legible; "
                "never replace brand text with invented words."
                + (f" Product spec from reference: {desc[:900]}" if desc else "")
            )
        else:
            desc = (product_visual_description or "").strip()
            lines.append(
                f"The hero product is {product} by {brand}"
                + (f": {desc[:500]}" if desc else ".")
                + " Grounded, believable commercial execution. Never invent fake claims on packaging."
            )
        lines.append("")

    lines.append("FORMAT & VISUAL HIERARCHY")
    lines.append(
        f"Meta {aspect_ratio} commercial feed format. {_ratio_layout(t['square'], aspect_ratio)} "
        "The hero subject commands 55-60% of visual weight as the primary optical entry point. "
        "Preserve 25-35% calm, uncluttered negative space for thumb-stopping clarity on mobile screens. "
        "Maintain an 8% outer boundary margin safety buffer."
    )
    lines.append("")

    lines.append("STYLE & AESTHETIC")
    if photo:
        lines.append(f"{t['name']}: high-end editorial commercial photograph for {product_category or 'a consumer brand'}, shot on a full-frame 85mm prime lens, authentic photographic depth, not CGI.")
    else:
        lines.append(f"{t['name']}: premium, clean modern design for a {product_category or 'digital'} brand, studio-crisp, elegant glassmorphic surfaces, zero visual clutter.")
    lines.append("")

    lines.append("STUDIO SET & MATERIAL TEXTURES")
    lines.append(f(t["set"]))
    if scene_hint:
        lines.append(f"Scene detail: {scene_hint.strip()[:400]}")
    lines.append("Materiality: authentic physical textures (honed stone, brushed aluminum, frosted glass, organic caustics, micro-shadows).")
    lines.append("")

    if t["talent"]:
        lines.append("TALENT CASTING")
        lines.append(
            (talent.strip()[:700] if talent else f"One model reflecting {target_audience_persona or 'the target audience'}.")
            + " Genuine, relaxed posture, authentic eye contact, natural skin texture with real pores and fine micro-details. Not a celebrity, actor, or glamorous influencer."
        )
        lines.append("")

    lines.append("HERO SUBJECT PLACEMENT")
    lines.append(f(t["hero"]))
    if mode == PRODUCT_MODE:
        lines.append("Show ONE unit of the product at authentic scale. Physically grounded with realistic contact shadow and ambient occlusion. Nothing overlaps or hides the label.")
    else:
        lines.append("Ensure any tech device or screen is strictly upright and oriented normally (never inverted, upside-down, or backwards).")
    lines.append("")

    lines.append("CAMERA")
    lines.append(t["camera"])
    lines.append("")
    lines.append("LIGHTING & SHADOW ARCHITECTURE")
    lines.append(f"{t['light']} Sculpted 45-degree directional key light, soft natural fill, and physically accurate contact shadows.")
    lines.append("")

    lines.append("60-30-10 CHROMATIC HARMONY")
    lines.append(
        f"Palette tokens: {color_palette}. "
        "Apply 60% dominant canvas tone, 30% structural secondary palette, and 10% high-contrast accent pop dedicated strictly to the CTA pill and brand mark."
        if color_palette else
        "Restrained 60-30-10 chromatic harmony: 60% neutral canvas tone, 30% supporting tonal depth, and 10% saturated accent pop reserved for the CTA pill."
    )
    lines.append("")

    lines.append("TYPOGRAPHY: STRICT META 3-ELEMENT BUDGET (nothing else)")
    lines.append(f'1. Brand wordmark: "{brand}" rendered clean, refined, optically tracked in the brand palette.')
    lines.append(f'2. Headline: "{image_headline}" rendered in bold modern sans or high-contrast editorial serif, large optical contrast, at most two lines, each word rendered once.')
    lines.append(f'3. CTA pill: "{cta_text}" rendered as a tactile rounded pill capsule button in the saturated brand accent with centered legible label.')
    lines.append("Spell every string exactly as quoted. STRICT RULE: No other words, numbers, badges, star ratings, or captions in the pixels (authentic product packaging excepted).")
    lines.append("")

    if photo:
        lines.append("COMMERCIAL REALISM & TACTILE DEPTH")
        lines.append("True optical color science, fine cinematic grain, soft highlight roll-off, natural depth of field. Authentic unretouched skin texture. Tack-sharp product boundaries firmly grounded in space.")
        lines.append("")

    if custom_directive and custom_directive.strip():
        lines.append("EXECUTIVE ART DIRECTOR NOTE")
        lines.append(custom_directive.strip()[:300])
        lines.append("")

    lines += _avoid_lines(mode, photo)
    return "\n".join(lines)


def build_reference_prompt(
    *,
    reference: dict,
    concept: str,
    brand_name: str,
    product_name: str,
    product_category: str = "",
    target_audience_persona: str = "",
    aspect_ratio: str = "4:5",
    headline: str = "",
    cta: str = "Shop Now",
    scene_hint: str = "",
    product_visual_description: str = "",
    color_palette: str = "",
    brand_kit: Optional[dict] = None,
    has_product_ref: bool = False,
    has_layout_ref: bool = True,
    has_logo: bool = False,
    logo_tone: str = "dark",
    setting: str = "",
    talent: str = "",
    custom_directive: Optional[str] = None,
) -> str:
    """Ad prompt that borrows concept and layout from an analysed competitor ad and applies our branding
    under senior graphic design principles.

    Attached images, in order: product photo (if any), the competitor layout reference, our logo (if any)."""
    brand = (brand_name or "Brand").strip()
    product = (product_name or "the product").strip()
    image_headline = short_headline(headline) or f"Meet {product}"
    cta_text = short_headline(cta, MAX_CTA_WORDS) or "Shop Now"
    kit = brand_kit or {}
    r = reference or {}

    n = 0
    product_img = layout_img = logo_img = None
    if has_product_ref:
        n += 1
        product_img = n
    if has_layout_ref:
        n += 1
        layout_img = n
    if has_logo:
        n += 1
        logo_img = n

    lines: List[str] = [
        "[ROLE: Senior Executive Art Director & Master Commercial Graphic Designer]",
        f"Craft an award-winning Meta {aspect_ratio} commercial ad creative for {brand} borrowing proven compositional hierarchy from reference.",
        "Strictly enforce core design principles: visual hierarchy, 60-30-10 color theory, 25-35% negative space, and typographic craft.",
        "",
        "REFERENCE ROLES & STRUCTURAL ANCHORS",
    ]
    desc = (product_visual_description or "").strip()
    if product_img:
        lines.append(
            f"IMAGE {product_img} = PRODUCT-REF: the real {product} by {brand}, the hero of this ad. Reproduce it with absolute fidelity: "
            "identical silhouette, proportions, cut, materials, finish, and label graphics. Never redesign or warp packaging."
            + (f" Product spec: {desc[:900]}" if desc else "")
        )
    else:
        lines.append(f"The hero product is {product} by {brand}" + (f": {desc[:700]}" if desc else ".")
                     + " Grounded, believable commercial execution; never invent fake label claims.")
    if layout_img:
        lines.append(
            f"IMAGE {layout_img} = LAYOUT-REF: a live competitor ad, used ONLY for its compositional architecture: framing, "
            "camera distance, focal hierarchy, where text sits, and visual balance. "
            "Do NOT copy its competitor brand, logo, celebrity face, garments, packaging, or colors. "
            "Depict an everyday, relatable real person with natural unretouched skin, NOT a celebrity, model, or influencer."
        )
    if logo_img:
        lines.append(
            f"IMAGE {logo_img} = BRAND LOGO: the authentic {brand} logo. Place it as provided (same letterforms, proportions and "
            "palette), small, clean, and optically balanced"
            + (" on a sufficiently dark surface for this light logo" if logo_tone == "light" else "")
            + ". Never redraw or distort the logo."
        )
    lines.append("")

    lines.append("STRATEGIC CONCEPT")
    lines.append((concept or "").strip() or f"Adapt the reference layout's core commercial hierarchy to {product} for {target_audience_persona or 'the target audience'}.")
    lines.append("")

    lines.append("COMPOSITIONAL ARCHITECTURE (from reference)")
    layout_bits = [
        f"composition: {r.get('composition')}" if r.get("composition") else "",
        f"product presence: {r.get('product_presence')}" if r.get("product_presence") else "",
        f"people: {r.get('people')}" if r.get("people") else "",
        f"lighting: {r.get('lighting')}" if r.get("lighting") else "",
    ]
    lines.append("; ".join(b for b in layout_bits if b) + "." if any(layout_bits) else "Follow the reference layout balance.")
    fit = {
        "9:16": " Safe zone discipline: keep all critical text and hero subject out of top 14% and bottom 20% UI overlays.",
        "16:9": " Golden ratio horizontal split: typography and CTA in left 40% column; hero subject in right 60%.",
    }.get(aspect_ratio, " Maintain reference balance with 25-35% calm negative space around the hero subject.")
    lines.append(f"Adapt layout to Meta {aspect_ratio} frame.{fit} Maintain an 8% outer margin safety zone.")
    lines.append("")

    lines.append("STUDIO SCENE & MATERIALS")
    lines.append((scene_hint or "").strip()[:400] or f"{(setting or r.get('setting') or 'a modern, premium environment that suits the audience').strip()}.")
    lines.append("Emphasize authentic physical materiality: real textures, soft contact shadows, natural light reflections.")
    if talent and (r.get("people") or "none") != "none":
        lines.append(f"Talent: {talent.strip()[:600]} Natural expression, unforced posture, authentic unretouched skin texture.")
    lines.append("")

    lines.append("BRAND SYSTEM & 60-30-10 CHROMATIC HARMONY")
    if kit:
        lines.append(
            f"Brand palette by role: 60% background canvas {kit.get('background_hex')}, 30% structural secondary {kit.get('primary_hex')}, "
            f"10% conversion accent pop {kit.get('accent_hex')} for CTA pill and brand mark"
            + (f", supporting {', '.join(kit.get('supporting_hexes') or [])}" if kit.get("supporting_hexes") else "")
            + ". Use no extraneous colors."
        )
        if kit.get("visual_mood"):
            lines.append(f"Mood: {kit['visual_mood']}.")
    elif color_palette:
        lines.append(f"Palette: {color_palette}. 60% dominant canvas tone, 30% secondary structure, 10% saturated accent on CTA pill.")
    lines.append("")

    lines.append("TYPOGRAPHY: STRICT META 3-ELEMENT BUDGET (nothing else)")
    lines.append(f'1. Brand logo from IMAGE {logo_img}.' if logo_img else f'1. Brand wordmark: "{brand}" (refined, optically tracked).')
    headline_type = kit.get("headline_type") or "bold modern sans-serif or editorial serif"
    lines.append(f'2. Headline: "{image_headline}" in {headline_type}, high optical contrast, max two lines, each word rendered once.')
    lines.append(f'3. CTA pill: "{cta_text}", rounded tactile pill button in {kit.get("accent_hex") or "the saturated brand accent"} with crisp legible label.')
    lines.append("Spell each string exactly as quoted. STRICT RULE: No other words, badges, star ratings, or numbers in the image.")
    lines.append("")

    lines.append("COMMERCIAL REALISM & FINISH")
    lines.append("Authentic high-end commercial photograph, full-frame camera lens, natural color science, fine cinematic grain, true depth of field, natural skin texture, physically grounded contact shadows.")
    lines.append("")

    if custom_directive and custom_directive.strip():
        lines.append("EXECUTIVE ART DIRECTOR NOTE")
        lines.append(custom_directive.strip()[:300])
        lines.append("")

    lines += _avoid_lines(PRODUCT_MODE, True, extra=[
        f"the competitor's brand name, logo, words or colours from IMAGE {layout_img}" if layout_img else "",
        "the reference model's face", "a redrawn or misspelled logo",
    ])
    return "\n".join(lines)


def _avoid_lines(mode: str, photo: bool, extra: Optional[List[str]] = None) -> List[str]:
    avoid = [
        "any text other than the three quoted strings", "paragraphs or sub-headlines", "bullet lists or feature badges",
        "star ratings, review counts, percentages, prices or discounts", "watermarks", "logos of other companies",
        "cluttered layout", "text overlapping the hero",
        "levitating orbs or floating geometric cubes", "garish cyan/purple neon cyber-mush", "plastic or waxy skin",
        "unreadable pseudo-text or fake UI numbers", "warped anatomy or deformed fingers",
    ]
    if mode == PRODUCT_MODE:
        avoid += ["extra or duplicate products", "a redesigned or warped product", "misspelled or invented label text",
                  "deformed hands", "extra fingers", "floating ungrounded product"]
    else:
        avoid += ["readable UI words or numbers", "real banking or card numbers", "stock-photo people", "glowing brains, robots, circuit boards", "upside-down or inverted device screens"]
    if photo:
        avoid += [
            "CGI or 3D-render look", "plastic skin", "HDR", "oversaturation", "visible studio equipment",
            "celebrity likeness", "famous actors or influencers", "glamorous airbrushed skin",
        ]
    avoid += [x for x in (extra or []) if x]
    return ["AVOID (STRICT ANTI-AI SLOP GUARDRAILS)", ", ".join(avoid) + "."]
