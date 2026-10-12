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
        "name": "Studio Graphic Hero",
        "mode": PRODUCT_MODE,
        "frameworks": ["feature_callout", "lifestyle_hero"],
        "style": "photo",
        "summary": "Product on a plinth, solid brand-colour set, one hard graphic shadow.",
        "set": "Seamless solid studio set in the lightest brand colour, floor curving into the wall. One or two simple geometric plinths in tints of the same hue. Nothing else in frame.",
        "hero": "The product stands upright on the front plinth, centred, about 40% of the frame height, label square to the camera.",
        "camera": "Eye level to slightly low, 85mm product lens, the whole product in sharp focus.",
        "light": "Hard directional key light from the upper left casting one crisp graphic shadow of the product across the floor at about 45 degrees; soft fill so the label stays readable.",
        "talent": False,
        "square": "Headline across the top 20%, centred. Product zone 24-82%. Bottom 14%: brand wordmark on the left, CTA pill on the right.",
    },
    "macro_texture": {
        "name": "Macro Texture Swatch",
        "mode": PRODUCT_MODE,
        "frameworks": ["feature_callout"],
        "style": "photo",
        "summary": "Product beside a macro swatch of its own formula or material.",
        "set": "Clean tabletop in a pale tint of the brand accent. In the foreground, one confident swatch of the product's own formula or material (cream, gel, liquid, powder or fabric, whichever fits this product), with a fingertip lifting a glossy peak from it.",
        "hero": "The product stands upright in the right third, about 45% of the frame height, just behind the swatch, label facing the camera and in sharp focus.",
        "camera": "100mm macro, 30 degrees from above, shallow depth of field with the product and swatch both sharp.",
        "light": "Soft top-down light with a clean specular highlight on the swatch; bright, fresh, high-key.",
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
        "name": "Chaos Grid",
        "mode": SERVICE_MODE,
        "frameworks": ["problem_solution"],
        "style": "illustration",
        "summary": "A crowded UI surface with one calm block in the brand accent.",
        "set": "A flat UI-style illustration of a {chaos_surface}, edge to edge in the top 60% of the frame, oppressively full of overlapping blocks in muted greys, slate blues and dull reds. All UI text is drawn as abstract grey bars, never readable words or numbers.",
        "hero": "Exactly ONE block is rendered in the brand accent with a small check-mark icon and breathing room around it: calm signal in the noise.",
        "camera": "Straight-on flat view.",
        "light": "Even, flat, clean.",
        "talent": False,
        "square": "Visual in the top 60%. Headline centred in the band below it. Bottom 14%: brand wordmark on the left, CTA pill on the right.",
    },
    "product_moment": {
        "name": "In-Product Moment",
        "mode": SERVICE_MODE,
        "frameworks": ["feature_callout"],
        "style": "illustration",
        "summary": "Device showing the app mid-action with one highlighted confirmation card.",
        "set": "A sleek generic {device} (no real manufacturer branding) at a gentle 12-degree tilt on a soft gradient field built from the brand palette.",
        "hero": "The screen shows a clean {brand} interface in the brand palette: abstract UI bars instead of words, any amounts masked as bullets, and ONE highlighted card in the brand accent with a check mark, the product doing its job. The device fills the right 55% of the frame.",
        "camera": "Three-quarter view, gentle perspective, crisp edges.",
        "light": "Soft studio light, subtle reflection on the glass.",
        "talent": False,
        "square": "Left 45% column: brand wordmark small at the top, headline in the middle, CTA pill below it.",
    },
    "control_panel": {
        "name": "Control Room",
        "mode": SERVICE_MODE,
        "frameworks": ["social_proof"],
        "style": "illustration",
        "summary": "Tactile panel of toggles switched on in the brand accent: control and trust.",
        "set": "A tactile soft-touch control panel filling the top 58% of the frame, seen at a slight angle.",
        "hero": "Three physical toggle switches all set to ON, their tracks lit in the brand accent, each with a tiny engraved icon (no words, no numbers).",
        "camera": "45-degree three-quarter view, shallow depth of field on the nearest toggle.",
        "light": "Soft overhead studio light with a crisp highlight along the panel edge.",
        "talent": False,
        "square": "Panel in the top 58%. Headline centred below it. Bottom 14%: brand wordmark on the left, CTA pill on the right.",
    },
    "consolidation": {
        "name": "Before / After Consolidation",
        "mode": SERVICE_MODE,
        "frameworks": ["us_vs_them"],
        "style": "illustration",
        "summary": "Scattered tool windows collapse into one clean app tile.",
        "set": "Thin line-art illustration on the brand field. UPPER area: five or six small generic app windows scattered and overlapping at slight angles, each with a red notification dot (no numbers, no real logos). A single downward arrow leads to the LOWER area: one large clean rounded app tile in the brand accent showing the brand's initial.",
        "hero": "The single app tile, centred, isolated in calm space.",
        "camera": "Straight-on flat view.",
        "light": "Even and clean.",
        "talent": False,
        "square": "Illustration in the top 64%. Headline centred below it. Brand wordmark and CTA pill centred in the bottom 14%.",
    },
    "metaphor_object": {
        "name": "Abstract 3D Metaphor",
        "mode": SERVICE_MODE,
        "frameworks": ["lifestyle_hero"],
        "style": "illustration",
        "summary": "One sculptural 3D object that embodies the core promise.",
        "set": "A smooth gradient field derived from the brand palette.",
        "hero": "ONE sculptural 3D object that embodies the promise '{benefit}' ({metaphor_examples}). Choose one; render it in matte and glossy materials in the brand palette, floating with a soft contact shadow, centred in the upper 60%.",
        "camera": "Slight low angle, 85mm, object in crisp focus.",
        "light": "Soft key light with a gentle rim glow in the brand accent.",
        "talent": False,
        "square": "Object in the upper 60%. Headline centred below it. Brand wordmark and CTA pill centred in the bottom 14%.",
    },
    "levitation_device": {
        "name": "Dark Levitation",
        "mode": SERVICE_MODE,
        "frameworks": ["lifestyle_hero", "feature_callout"],
        "style": "illustration",
        "summary": "Device floating over a deep brand-tinted field with an accent bloom.",
        "set": "A deep field in the darkest brand colour with a soft bloom of the brand accent rising behind the hero.",
        "hero": "A sleek generic {device} floats at a 15-degree tilt in the upper-centre, about 55% of the frame height, screen showing a calm {brand} interface: abstract UI bars, masked values as bullets, one accent element.",
        "camera": "Slight low angle, 85mm, crisp edges.",
        "light": "Rim light tracing the device edges, glow from the accent bloom.",
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
        "problem_solution": "chaos_grid",
        "feature_callout": "product_moment",
        "social_proof": "control_panel",
        "us_vs_them": "consolidation",
        "lifestyle_hero": "metaphor_object",
        "_single": "levitation_device",
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
        "problem_solution": "chaos_grid",
        "feature_callout": "product_moment",
        "social_proof": "control_panel",
        "us_vs_them": "consolidation",
        "lifestyle_hero": "metaphor_object",
        "_single": "levitation_device",
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
    return [
        {"id": tid, "name": t["name"], "summary": t["summary"], "frameworks": t["frameworks"]}
        for tid, t in TEMPLATES.items() if t["mode"] == mode
    ]


def resolve_template_id(blueprint: Any, mode: str, category: str = "") -> str:
    """Use the blueprint's template if it fits the mode, else pick category-tailored default."""
    if isinstance(blueprint, str):
        blueprint = {"template_id": blueprint, "framework_key": blueprint}
    elif not isinstance(blueprint, dict):
        blueprint = {}

    tid = (blueprint.get("template_id") or "").strip()
    if tid in TEMPLATES and TEMPLATES[tid]["mode"] == mode:
        return tid

    framework = blueprint.get("framework_key") or "_single"

    # Prioritize industry category mapping
    cat_key = detect_product_category(category)
    if cat_key in CATEGORY_DEFAULTS:
        cat_map = CATEGORY_DEFAULTS[cat_key]
        if framework in cat_map:
            return cat_map[framework]
        if "_single" in cat_map:
            return cat_map["_single"]

    return FRAMEWORK_DEFAULTS[mode].get(framework, FRAMEWORK_DEFAULTS[mode]["_single"])


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
    lines: List[str] = []

    # REFERENCE ROLES — the product lock comes first so the model treats the photo as the hero, not inspiration
    if mode == PRODUCT_MODE:
        lines.append("REFERENCE ROLES")
        if has_product_ref:
            ref_name = "IMAGE 1"
            desc = (product_visual_description or "").strip()
            lines.append(
                f"{ref_name} = PRODUCT-REF: the real {product} by {brand}. Use THIS exact product as the hero of the ad. "
                "Reproduce it exactly: identical shape, proportions, cap or closure, colours, materials, finish and label layout. "
                "Do not redesign, restyle, recolour or invent packaging. Keep large label words legible and correctly spelled; "
                "never replace label text with invented words."
                + (f" Product spec from the photo: {desc[:900]}" if desc else "")
            )
        else:
            desc = (product_visual_description or "").strip()
            lines.append(
                f"No product photo supplied. The hero product is {product} by {brand}"
                + (f": {desc[:500]}" if desc else ".")
                + " Keep the packaging simple and believable; do not invent claims on the label."
            )
        lines.append("")

    lines.append("FORMAT")
    lines.append(f"Meta {aspect_ratio} social ad. {_ratio_layout(t['square'], aspect_ratio)} Keep 6% clear margin on every edge.")
    lines.append("")

    lines.append("STYLE")
    if photo:
        lines.append(f"{t['name']}: real high-end D2C campaign photograph for {product_category or 'a consumer brand'}, shot on a full-frame camera, not CGI.")
    else:
        lines.append(f"{t['name']}: premium, clean 3D and UI illustration for a {product_category or 'digital'} brand, studio-crisp, no photographic noise.")
    lines.append("")

    lines.append("SET")
    lines.append(f(t["set"]))
    if scene_hint:
        lines.append(f"Scene detail: {scene_hint.strip()[:400]}")
    lines.append("")

    if t["talent"]:
        lines.append("TALENT")
        lines.append(
            (talent.strip()[:700] if talent else f"One model who reflects {target_audience_persona or 'the target audience'}.")
            + " Genuine, relaxed expression, eye contact with the lens, natural skin texture, everyday relatable appearance. Not a celebrity, actor, or glamorous influencer."
        )
        lines.append("")

    lines.append("HERO" if mode == SERVICE_MODE else "PRODUCT PLACEMENT")
    lines.append(f(t["hero"]))
    if mode == PRODUCT_MODE:
        lines.append("Show ONE unit of the product at true real-world size. Nothing overlaps or hides the label. No text or graphics are drawn over the product.")
    lines.append("")

    lines.append("CAMERA")
    lines.append(t["camera"])
    lines.append("")
    lines.append("LIGHT")
    lines.append(t["light"])
    lines.append("")

    lines.append("BRAND COLOURS")
    lines.append(
        f"Use only this palette: {color_palette}. The most saturated colour is the accent (CTA pill and at most one other touch)."
        if color_palette else
        "A restrained palette of two neutrals plus one saturated brand accent used for the CTA pill."
    )
    lines.append("")

    lines.append("TYPOGRAPHY: exactly three text elements, nothing else")
    lines.append(f'1. Brand wordmark: "{brand}", small, clean, in the brand colours.')
    lines.append(f'2. Headline: "{image_headline}", bold modern sans-serif, large and high-contrast, at most two lines, each word rendered once.')
    lines.append(f'3. CTA pill: "{cta_text}", a fully rounded pill in the brand accent with short white or dark text.')
    lines.append("Spell every string exactly as quoted. No other words, numbers, badges, ratings, prices, labels or captions anywhere in the image (product packaging text excepted).")
    lines.append("")

    if photo:
        lines.append("REALISM")
        lines.append("Natural colour, fine grain, soft highlight roll-off, true depth of field. Skin with real texture, not airbrushed. Product edges crisp and physically grounded with a believable contact shadow.")
        lines.append("")

    if custom_directive and custom_directive.strip():
        lines.append("ART DIRECTOR NOTE")
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
    """Ad prompt that borrows concept and layout from an analysed competitor ad and applies our branding.

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

    lines: List[str] = ["REFERENCE ROLES"]
    desc = (product_visual_description or "").strip()
    if product_img:
        lines.append(
            f"IMAGE {product_img} = PRODUCT-REF: the real {product} by {brand}, the hero of this ad. Reproduce it exactly: "
            "identical shape, proportions, cut, colours, materials, finish and label or print. Never redesign it or "
            "invent label text." + (f" Product spec: {desc[:900]}" if desc else "")
        )
    else:
        lines.append(f"The hero product is {product} by {brand}" + (f": {desc[:700]}" if desc else ".")
                     + " Keep it simple and believable; never invent label text or claims.")
    if layout_img:
        lines.append(
            f"IMAGE {layout_img} = LAYOUT-REF: a live competitor ad, used ONLY for its concept and layout: composition, "
            "framing, camera distance, pose type, where the text sits, how much text there is and the visual hierarchy. "
            "Do NOT copy its brand, logo, model's face, celebrity likeness or identity, garments, product, packaging, colours or any of its words. "
            "Depict an everyday, relatable real person with natural unretouched skin, NOT a celebrity, model, or influencer."
        )
    if logo_img:
        lines.append(
            f"IMAGE {logo_img} = BRAND LOGO: the real {brand} logo. Place it as given (same letterforms, proportions and "
            "colour), small and crisp, on a clean area"
            + (" that is dark enough for this light logo" if logo_tone == "light" else "")
            + ". Never redraw, restyle, recolour or retype it."
        )
    lines.append("")

    lines.append("CONCEPT")
    lines.append((concept or "").strip() or f"Adapt the reference ad's idea to {product} for {target_audience_persona or 'the target audience'}.")
    lines.append("")

    lines.append("LAYOUT (keep from the reference)")
    layout_bits = [
        f"composition: {r.get('composition')}" if r.get("composition") else "",
        f"product presence: {r.get('product_presence')}" if r.get("product_presence") else "",
        f"people: {r.get('people')}" if r.get("people") else "",
        f"lighting: {r.get('lighting')}" if r.get("lighting") else "",
    ]
    lines.append("; ".join(b for b in layout_bits if b) + "." if any(layout_bits) else "Follow the reference layout.")
    fit = {
        "9:16": " Keep all text and the product out of the top 14% and bottom 20% (Meta's interface covers them).",
        "16:9": " Re-flow it side by side if the reference is vertical: text in one third, the hero in the rest.",
    }.get(aspect_ratio, " Keep the reference's order and alignment, adding or trimming space around the hero.")
    lines.append(f"Adapt the layout to a Meta {aspect_ratio} frame.{fit} Keep 6% clear margin on every edge.")
    lines.append("")

    lines.append("SCENE")
    lines.append((scene_hint or "").strip()[:400] or f"{(setting or r.get('setting') or 'a setting that suits the audience').strip()}.")
    if talent and (r.get("people") or "none") != "none":
        lines.append(f"Talent: {talent.strip()[:600]} Genuine expression, natural skin texture.")
    lines.append("")

    lines.append("BRAND STYLE")
    if kit:
        lines.append(
            f"Colours by role: background {kit.get('background_hex')}, text {kit.get('text_hex')}, primary {kit.get('primary_hex')}, "
            f"CTA pill {kit.get('accent_hex')}"
            + (f", supporting {', '.join(kit.get('supporting_hexes') or [])}" if kit.get("supporting_hexes") else "")
            + ". Use no other brand colours."
        )
        if kit.get("visual_mood"):
            lines.append(f"Mood: {kit['visual_mood']}.")
    elif color_palette:
        lines.append(f"Use only this palette: {color_palette}. The most saturated colour is the CTA pill.")
    lines.append("")

    lines.append("TYPOGRAPHY: exactly three text elements, placed where the reference puts its text")
    lines.append(f'1. Brand logo from IMAGE {logo_img}.' if logo_img else f'1. Brand wordmark: "{brand}", small, in the brand colours.')
    headline_type = kit.get("headline_type") or "bold modern sans-serif"
    lines.append(f'2. Headline: "{image_headline}" in {headline_type}, large and high-contrast, at most two lines, each word rendered once.')
    lines.append(f'3. CTA pill: "{cta_text}", a fully rounded pill in {kit.get("accent_hex") or "the brand accent"} with short, legible text.')
    lines.append("Spell every string exactly as quoted. No other words, numbers, badges, ratings, prices or captions (product labels excepted).")
    lines.append("")

    lines.append("REALISM")
    lines.append("Real high-end D2C campaign photograph, full-frame camera, natural colour, fine grain, true depth of field, real skin texture, crisp product edges.")
    lines.append("")

    if custom_directive and custom_directive.strip():
        lines.append("ART DIRECTOR NOTE")
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
    ]
    if mode == PRODUCT_MODE:
        avoid += ["extra or duplicate products", "a redesigned or warped product", "misspelled or invented label text",
                  "deformed hands", "extra fingers"]
    else:
        avoid += ["readable UI words or numbers", "real banking or card numbers", "stock-photo people", "glowing brains, robots, circuit boards"]
    if photo:
        avoid += [
            "CGI or 3D-render look", "plastic skin", "HDR", "oversaturation", "visible studio equipment",
            "celebrity likeness", "famous actors or influencers", "glamorous airbrushed skin",
        ]
    avoid += [x for x in (extra or []) if x]
    return ["AVOID", ", ".join(avoid) + "."]
