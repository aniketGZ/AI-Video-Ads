"""
Creative Library Presets for Meta Ads.
Curated from Pinterest graphic-design references sorted by industry
(https://github.com/aniketb1rla/pinterestrepo/tree/main/dataset).

Each preset encapsulates real design DNA:
- Design movement & aesthetic style
- Layout composition, reading hierarchy, and Meta-compliant framing
- Exact typography stacks (headline, body, recommended web fonts, treatments)
- Chromatic palette tokens (background, primary/secondary accents, mood)
- Decorative elements & studio lighting specs
- Ground-truth Pinterest pin references for visual inspiration (with raw GitHub CDN images)
- Dynamic prompt generation for Gemini Nano Banana Pro / Imagen / Flux
"""

from typing import Any, Dict, List, Optional
import re

# ---------------------------------------------------------------------------
# Industry slug mapping helpers
# ---------------------------------------------------------------------------
INDUSTRY_CATEGORY_MAP = {
    "beauty-cosmetics": ["beauty", "cosmetics", "skincare", "skin care", "makeup", "haircare", "perfume", "fragrance", "serum", "spa", "salon", "lotion", "cleanser"],
    "fintech-finance": ["fintech", "finance", "financial", "banking", "bank", "crypto", "trading", "investment", "invest", "loan", "wallet", "tax", "accounting", "insurance", "card", "money"],
    "tech-saas": ["saas", "tech", "software", "app", "mobile app", "platform", "cloud", "ai", "b2b", "developer", "analytics", "dashboard", "workflow", "api"],
    "food-beverage": ["food", "beverage", "drinks", "drink", "coffee", "cafe", "tea", "bakery", "restaurant", "burger", "pizza", "snack", "beer", "wine", "culinary", "recipe", "juice"],
    "fashion-apparel": ["fashion", "apparel", "clothing", "streetwear", "dress", "hoodie", "shoes", "sneakers", "activewear", "menswear", "womenswear", "outfit", "t-shirt", "jeans"],
    "jewelry-luxury": ["jewelry", "jewellery", "luxury", "diamond", "gold", "watch", "watches", "ring", "necklace", "earrings", "gemstone", "bracelet"],
    "fitness-sports": ["fitness", "sports", "gym", "workout", "athletic", "training", "running", "crossfit", "yoga", "exercise", "bodybuilding"],
    "healthcare-medical": ["healthcare", "medical", "clinic", "doctor", "dentist", "dental", "hospital", "therapy", "physiotherapy", "chiropractor", "pharmacy"],
    "health-wellness": ["wellness", "health", "supplement", "vitamins", "nutrition", "mental health", "ayurveda", "dietary"],
    "real-estate": ["real estate", "property", "realtor", "realty", "apartment", "villa", "home for sale", "mortgage", "broker", "listing"],
    "home-interiors": ["interior", "interiors", "furniture", "home decor", "sofa", "kitchen", "living room", "decor", "architecture"],
    "construction-trades": ["construction", "roofing", "plumbing", "contractor", "electrician", "hvac", "cleaning", "renovation", "builder", "remodel"],
    "ecommerce-retail": ["ecommerce", "e-commerce", "retail", "store", "shopping", "d2c", "dtc", "sale", "discount", "product", "shop"],
    "marketing-agency": ["marketing", "agency", "advertising", "creative agency", "seo", "branding agency", "social media agency", "growth"],
    "travel-hospitality": ["travel", "hospitality", "hotel", "resort", "tourism", "vacation", "trip", "flight", "booking", "airbnb"],
    "pets": ["pets", "pet", "dog", "cat", "puppy", "veterinary", "pet food", "grooming"],
}

CREATIVE_PRESETS: Dict[str, Dict[str, Any]] = {
    # =========================================================================
    # BEAUTY & COSMETICS
    # =========================================================================
    "beauty_editorial_rhode": {
        "id": "beauty_editorial_rhode",
        "name": "Rhode Editorial Skincare Minimalist",
        "industry_slug": "beauty-cosmetics",
        "industry_label": "Beauty & Cosmetics",
        "movement": "Organic Luxury Minimalist / Editorial Skincare Aesthetic",
        "summary": "Warm travertine pedestal, organic morning light caustics, and delicate editorial Didone typography inspired by Rhode and Aesop.",
        "inspiration_source": "Pinterest Creative Library (Rhode & Aesop Skincare Collections)",
        "reference_pins": [
            {
                "pin_id": "1000291767255653778",
                "title": "Rhode Organic Luxury Serum Layout",
                "pin_url": "https://www.pinterest.com/pin/1000291767255653778/",
                "image_url": "https://raw.githubusercontent.com/aniketb1rla/pinterestrepo/main/dataset/beauty-cosmetics/1000291767255653778.jpg",
            },
            {
                "pin_id": "1012747035363432272",
                "title": "Aesop Botanical Travertine Still Life",
                "pin_url": "https://www.pinterest.com/pin/1012747035363432272/",
                "image_url": "https://raw.githubusercontent.com/aniketb1rla/pinterestrepo/main/dataset/beauty-cosmetics/1012747035363432272.jpg",
            },
            {
                "pin_id": "1019924646876106847",
                "title": "Minimalist Serum Pedestal & Soft Light",
                "pin_url": "https://www.pinterest.com/pin/1019924646876106847/",
                "image_url": "https://raw.githubusercontent.com/aniketb1rla/pinterestrepo/main/dataset/beauty-cosmetics/1019924646876106847.jpg",
            },
        ],
        "colors": {
            "background_tone": "#f2e8dc",
            "primary_accent": "#8d3624",
            "secondary_accent": "#cf9572",
            "text_color": "#0f172a",
            "luminance_mode": "light",
            "temperature": "warm",
            "palette": ["#f2e8dc", "#8d3624", "#e8dbc5", "#cf9572", "#bd9889", "#1e293b"],
            "mood": "Serene, pure, rejuvenating, warm organic luxury and dewy radiance",
        },
        "typography": {
            "headline_font_style": "High-Contrast Editorial Serif or Modern Didone",
            "body_font_style": "Ultra-Clean Geometric Sans or Delicate Light Sans",
            "recommended_headline_fonts": ["Playfair Display", "Cormorant Garamond", "Canela", "Fraunces"],
            "recommended_body_fonts": ["Plus Jakarta Sans", "Montserrat", "Jost"],
            "treatment_effects": "Wide-tracked sentence case (+0.08em) with elegant italicized emphasis on key benefit words",
            "hierarchy_order": "Top delicate headline -> Central hero pedestal -> Bottom minimalist pill CTA",
        },
        "layout": {
            "layout_type": "Centered Hero Pedestal with Generous Negative Space",
            "composition": "Top delicate editorial headline, central premium cosmetic bottle upright on smooth organic travertine pedestal, bottom botanical ingredients notes and soft CTA pill.",
            "hierarchy": "Editorial Benefit Headline -> Hero Cosmetic Bottle -> Ingredient Callout Badge -> Pill CTA",
            "aspect_ratio_code": "4:5",
            "spacing_density": "Generous breathable margins with high-end luxury focal point",
        },
        "lighting": "Warm morning sunlight filtering through sheer linen curtains, casting soft natural shadows and delicate water caustics.",
        "decorative_elements": [
            "Smooth natural travertine stone pedestal",
            "Organic sunlight caustics and subtle water ripple reflections",
            "Single fresh botanical leaf or dew droplet accent",
            "Frosted glass bottle with crisp embossed typography",
        ],
        "meta_ad_rules": "Minimal type, zero clutter, single product focus, CTA pill rounded with high-contrast fill.",
    },

    "beauty_clinical_ordinary": {
        "id": "beauty_clinical_ordinary",
        "name": "Clinical Formulations & Ingredient Science",
        "industry_slug": "beauty-cosmetics",
        "industry_label": "Beauty & Cosmetics",
        "movement": "Swiss Typographic & Pure Formulation Science",
        "summary": "Crisp white studio, scientific dropper bottle, pure typography, and active ingredient percentage callout inspired by The Ordinary.",
        "inspiration_source": "Pinterest Creative Library (The Ordinary Skincare Branding Collection)",
        "reference_pins": [
            {
                "pin_id": "1012747035363432272",
                "title": "Active Botanical Formulation Layout",
                "pin_url": "https://www.pinterest.com/pin/1012747035363432272/",
                "image_url": "https://raw.githubusercontent.com/aniketb1rla/pinterestrepo/main/dataset/beauty-cosmetics/1012747035363432272.jpg",
            },
            {
                "pin_id": "1000291767255653778",
                "title": "Clean Minimal Apothecary Serum Post",
                "pin_url": "https://www.pinterest.com/pin/1000291767255653778/",
                "image_url": "https://raw.githubusercontent.com/aniketb1rla/pinterestrepo/main/dataset/beauty-cosmetics/1000291767255653778.jpg",
            },
        ],
        "colors": {
            "background_tone": "#f8fafc",
            "primary_accent": "#2563eb",
            "secondary_accent": "#0f172a",
            "text_color": "#0f172a",
            "luminance_mode": "light",
            "temperature": "cool",
            "palette": ["#f8fafc", "#0f172a", "#2563eb", "#64748b", "#e2e8f0"],
            "mood": "Clinical authority, dermatological trust, formulation purity, and clean precision",
        },
        "typography": {
            "headline_font_style": "Precision Swiss Grotesk or Monospaced Data Header",
            "body_font_style": "Clean Technical Sans-Serif",
            "recommended_headline_fonts": ["Cabinet Grotesk", "Plus Jakarta Sans", "Inter", "Space Grotesk"],
            "recommended_body_fonts": ["Inter", "Roboto Mono", "Plus Jakarta Sans"],
            "treatment_effects": "High-contrast bold title with crisp technical uppercase subtitle (+0.14em)",
            "hierarchy_order": "Top formulation headline -> Crisp dropper hero -> Active ingredient badge -> Clean CTA",
        },
        "layout": {
            "layout_type": "Asymmetric Swiss Laboratory Grid",
            "composition": "Top-left scientific headline with active compound percentage, tack-sharp apothecary dropper bottle on white acrylic block, bottom technical CTA pill.",
            "hierarchy": "Clinical Claim -> Dropper Product Hero -> Active Formulation Note -> CTA Button",
            "aspect_ratio_code": "4:5",
            "spacing_density": "Architectural grid alignment with clinical white negative space",
        },
        "lighting": "Clean high-key commercial laboratory lighting, crisp specular reflections on glass dropper, pristine shadowless fill.",
        "decorative_elements": [
            "White matte acrylic laboratory plinth",
            "Single suspended amber dropper with glistening droplet",
            "Crisp laboratory formulation badge (e.g. 10% Niacinamide + Zinc)",
            "Minimalist measuring gradations",
        ],
        "meta_ad_rules": "Rigorous typography, high legibility on mobile feed, sharp edges.",
    },

    "beauty_glossier_dewy": {
        "id": "beauty_glossier_dewy",
        "name": "Glossier Dewy Pop & Pastel High-Key",
        "industry_slug": "beauty-cosmetics",
        "industry_label": "Beauty & Cosmetics",
        "movement": "High-Key Dewy Pastel & Playful Glow",
        "summary": "Playful pastel backdrop, glossy gel swatches, and fresh dewy skin texture inspired by Glossier and Drunk Elephant.",
        "inspiration_source": "Pinterest Creative Library (Glossier & Drunk Elephant Social Ad Design)",
        "reference_pins": [
            {
                "pin_id": "1019924646876106847",
                "title": "Dewy Radiance & Hydration Glow Ad",
                "pin_url": "https://www.pinterest.com/pin/1019924646876106847/",
                "image_url": "https://raw.githubusercontent.com/aniketb1rla/pinterestrepo/main/dataset/beauty-cosmetics/1019924646876106847.jpg",
            },
        ],
        "colors": {
            "background_tone": "#fdf2f8",
            "primary_accent": "#db2777",
            "secondary_accent": "#f472b6",
            "text_color": "#1f2937",
            "luminance_mode": "light",
            "temperature": "warm",
            "palette": ["#fdf2f8", "#db2777", "#f472b6", "#fef3c7", "#111827"],
            "mood": "Fresh, joyful, unbothered, radiant dewy skin, effortless youthfulness",
        },
        "typography": {
            "headline_font_style": "Friendly Rounded Sans or Confident Humanist Display",
            "body_font_style": "Warm Rounded Sans-Serif",
            "recommended_headline_fonts": ["Plus Jakarta Sans", "Syne", "Outfit", "Clash Display"],
            "recommended_body_fonts": ["Plus Jakarta Sans", "Inter"],
            "treatment_effects": "Lowercase friendly punchline or punchy bold all-caps with generous line spacing",
            "hierarchy_order": "Catchy benefit hook -> High-gloss swatch hero -> Floating pill badge -> Rounded CTA",
        },
        "layout": {
            "layout_type": "Diagonal Playful Flow with Texture Swatch",
            "composition": "Bold playful hook headline across top, hero product angled dynamically beside a glossy gel/balm smear, vibrant pill CTA bottom right.",
            "hierarchy": "Hook Headline -> Glossy Swatch & Tube -> Benefit Pill -> Rounded CTA",
            "aspect_ratio_code": "4:5",
            "spacing_density": "Energetic flow with balanced breathing room",
        },
        "lighting": "Bright softbox beauty fill with luminous specular highlight along the glossy formula swatch.",
        "decorative_elements": [
            "Glossy translucent gel smear with sparkling light reflection",
            "Soft pastel gradient backdrop in brand pink/coral tints",
            "Dewy water mist specks on product cap",
        ],
        "meta_ad_rules": "Vibrant colors that pop in the Facebook/Instagram feed; clear product label.",
    },

    # =========================================================================
    # FINTECH & FINANCE
    # =========================================================================
    "fintech_dark_glassmorphism": {
        "id": "fintech_dark_glassmorphism",
        "name": "Dark Neon Glassmorphic Neo-Bank",
        "industry_slug": "fintech-finance",
        "industry_label": "FinTech & Finance",
        "movement": "Cyberpunk Neo-Brutalist & Glassmorphic FinTech",
        "summary": "Deep obsidian slate backdrop, floating translucent frosted metal credit card, and vibrant neon accents inspired by Revolut and Monzo.",
        "inspiration_source": "Pinterest Creative Library (Fintech & Trading App Post Designs)",
        "reference_pins": [
            {
                "pin_id": "1011550766302180678",
                "title": "Fintech Dark Neo-Card Banking Creative",
                "pin_url": "https://www.pinterest.com/pin/1011550766302180678/",
                "image_url": "https://raw.githubusercontent.com/aniketb1rla/pinterestrepo/main/dataset/fintech-finance/1011550766302180678.jpg",
            },
            {
                "pin_id": "1014295147344534170",
                "title": "ScaleApp FinTech Purple Violet Card Suite",
                "pin_url": "https://www.pinterest.com/pin/1014295147344534170/",
                "image_url": "https://raw.githubusercontent.com/aniketb1rla/pinterestrepo/main/dataset/fintech-finance/1014295147344534170.jpg",
            },
        ],
        "colors": {
            "background_tone": "#0a0d14",
            "primary_accent": "#10b981",
            "secondary_accent": "#8b5cf6",
            "text_color": "#ffffff",
            "luminance_mode": "dark",
            "temperature": "cool",
            "palette": ["#0a0d14", "#10b981", "#8b5cf6", "#1e293b", "#ffffff"],
            "mood": "High-velocity wealth, cutting-edge security, frictionless global financial power",
        },
        "typography": {
            "headline_font_style": "Heavy Extended Sans-Serif or Neo-Grotesk Display",
            "body_font_style": "Ultra-Clean Monospace & Geometric Sans",
            "recommended_headline_fonts": ["Cabinet Grotesk", "Clash Display", "Plus Jakarta Sans", "Syne"],
            "recommended_body_fonts": ["Plus Jakarta Sans", "Space Mono", "Inter"],
            "treatment_effects": "Bold condensed all-caps headline with glowing gradient highlight on primary verb",
            "hierarchy_order": "Punchy wealth headline -> Floating metallic card -> Growth stat badge -> High-contrast CTA",
        },
        "layout": {
            "layout_type": "Dynamic 3D Card Levitation at 15-degree Tilt",
            "composition": "Top bold high-contrast headline, central 3D frosted metal card floating with subtle edge rim glow, bottom sleek pill CTA button with neon accent border.",
            "hierarchy": "Power Headline -> Levitating Metallic Card -> Verified Security Pill -> Action CTA",
            "aspect_ratio_code": "4:5",
            "spacing_density": "Deep immersive dark space with intense focal lighting on the card",
        },
        "lighting": "Cinematic edge rim lighting in vivid emerald/violet, soft volumetric gradient bloom behind the card, deep ambient shadow falloff.",
        "decorative_elements": [
            "Floating frosted glass/metal card with holographic chip reflection",
            "Subtle floating 3D metallic currency tokens or coin tokens in soft blur",
            "Ambient neon gradient bloom rising from bottom-center",
            "Precision hairline grid backdrop with faint bokeh dots",
        ],
        "meta_ad_rules": "Strict compliance: no fabricated returns or star ratings. High contrast for instant thumb-stopping feed power.",
    },

    "fintech_swiss_trust": {
        "id": "fintech_swiss_trust",
        "name": "High-Trust Swiss Editorial Finance",
        "industry_slug": "fintech-finance",
        "industry_label": "FinTech & Finance",
        "movement": "Swiss International Typographic & Institutional Trust",
        "summary": "Crisp white/navy canvas, architectural typography, and structured financial metrics inspired by Stripe and Mercury.",
        "inspiration_source": "Pinterest Creative Library (Mercury & Stripe Modern B2B Finance)",
        "reference_pins": [
            {
                "pin_id": "1014717359807139681",
                "title": "Clean Swiss Monochrome Financial Suite",
                "pin_url": "https://www.pinterest.com/pin/1014717359807139681/",
                "image_url": "https://raw.githubusercontent.com/aniketb1rla/pinterestrepo/main/dataset/fintech-finance/1014717359807139681.jpg",
            },
        ],
        "colors": {
            "background_tone": "#f8fafc",
            "primary_accent": "#0f172a",
            "secondary_accent": "#0284c7",
            "text_color": "#0f172a",
            "luminance_mode": "light",
            "temperature": "neutral",
            "palette": ["#f8fafc", "#0f172a", "#0284c7", "#e2e8f0", "#334155"],
            "mood": "Rock-solid security, institutional credibility, transparent ease, calm financial control",
        },
        "typography": {
            "headline_font_style": "High-Authority Swiss Serif / Display Hybrid",
            "body_font_style": "Precision Geometric Sans",
            "recommended_headline_fonts": ["Plus Jakarta Sans", "Inter", "Cabinet Grotesk", "Playfair Display"],
            "recommended_body_fonts": ["Inter", "Plus Jakarta Sans"],
            "treatment_effects": "Clean sentence case with surgical tracking (-0.02em) and dark slate weight",
            "hierarchy_order": "Authority Headline -> Clean metric interface card -> Trust badge -> Crisp dark CTA",
        },
        "layout": {
            "layout_type": "Balanced Column Split with Clean Interface Tile",
            "composition": "Left column holds brand wordmark, clear promise headline and dark CTA pill; right column displays a pristine white card with abstract financial growth curve and verified checkmark.",
            "hierarchy": "Trust Headline -> Interface Card Tile -> Security Indicator -> Deep Navy CTA",
            "aspect_ratio_code": "4:5",
            "spacing_density": "Uncluttered Swiss grid with generous 32px margins",
        },
        "lighting": "Clean, flat architectural lighting, gentle ambient occlusion beneath the interface card, zero harsh glare.",
        "decorative_elements": [
            "Pristine rounded white card tile with subtle 1px border (#e2e8f0)",
            "Minimalist verified shield or checkmark badge in brand cyan",
            "Faint architectural grid lines indicating precision ledger accounting",
        ],
        "meta_ad_rules": "Clear messaging, high trust value, compliant with financial advertising rules.",
    },

    # =========================================================================
    # TECH, SAAS & APPS
    # =========================================================================
    "saas_bento_grid": {
        "id": "saas_bento_grid",
        "name": "Modern Bento Grid Feature Showcase",
        "industry_slug": "tech-saas",
        "industry_label": "Tech, SaaS & Apps",
        "movement": "Apple & Linear Bento Grid UI Movement",
        "summary": "Modular rounded cards, glowing gradient borders, and sleek feature badges inspired by Linear, Raycast, and Apple.",
        "inspiration_source": "Pinterest Creative Library (SaaS Product Launch & UI Card Posts)",
        "reference_pins": [
            {
                "pin_id": "1008595279052523159",
                "title": "Software AI SaaS Bento Feature Grid",
                "pin_url": "https://www.pinterest.com/pin/1008595279052523159/",
                "image_url": "https://raw.githubusercontent.com/aniketb1rla/pinterestrepo/main/dataset/tech-saas/1008595279052523159.jpg",
            },
            {
                "pin_id": "1008595279057793902",
                "title": "Modern App Launch Bento Showcase",
                "pin_url": "https://www.pinterest.com/pin/1008595279057793902/",
                "image_url": "https://raw.githubusercontent.com/aniketb1rla/pinterestrepo/main/dataset/tech-saas/1008595279057793902.jpg",
            },
        ],
        "colors": {
            "background_tone": "#090d16",
            "primary_accent": "#38bdf8",
            "secondary_accent": "#818cf8",
            "text_color": "#ffffff",
            "luminance_mode": "dark",
            "temperature": "cool",
            "palette": ["#090d16", "#38bdf8", "#818cf8", "#1e293b", "#0f172a"],
            "mood": "Precision engineering, frictionless velocity, intelligent automation, modern dev aesthetic",
        },
        "typography": {
            "headline_font_style": "Geometric Technical Sans with Tight Tracking",
            "body_font_style": "Clean Developer Sans / Micro Monospace",
            "recommended_headline_fonts": ["Plus Jakarta Sans", "Cabinet Grotesk", "Inter", "Uncut Sans"],
            "recommended_body_fonts": ["Inter", "Plus Jakarta Sans", "Space Grotesk"],
            "treatment_effects": "Tight tracking (-0.03em) with radiant gradient on key feature keyword",
            "hierarchy_order": "SaaS Headline -> Central Bento Card Array -> Automation Pill -> Punchy CTA",
        },
        "layout": {
            "layout_type": "Bento Grid Arrangement (3 Modular Tiles)",
            "composition": "Top headline with subtle category tag; center shows a large hero bento card featuring a live UI preview flanked by 2 smaller metric pill cards; bottom high-contrast CTA pill.",
            "hierarchy": "Value Proposition Headline -> Hero Bento Tile -> Supporting Stat Tiles -> Action CTA",
            "aspect_ratio_code": "4:5",
            "spacing_density": "Tight 12px card gutters with clean negative space surrounding the cluster",
        },
        "lighting": "Subtle perimeter card backlight with glowing linear gradient strokes (1px border with cyan-to-indigo shine).",
        "decorative_elements": [
            "Frosted acrylic bento tiles with 1px luminous stroke",
            "Abstract UI progress bars and active toggle status indicator",
            "Soft ambient spotlight emanating from behind the central bento tile",
        ],
        "meta_ad_rules": "Abstract UI elements only (no illegible tiny text); headline under 6 words.",
    },

    "saas_dark_gradient_bloom": {
        "id": "saas_dark_gradient_bloom",
        "name": "Dark Futuristic AI & Cloud Platform",
        "industry_slug": "tech-saas",
        "industry_label": "Tech, SaaS & Apps",
        "movement": "Futuristic AI Dark Mode with Iridescent Bloom",
        "summary": "Deep obsidian backdrop, glowing iridescent radial bloom, and floating device screen inspired by Vercel and Supabase.",
        "inspiration_source": "Pinterest Creative Library (AI Software & SaaS Launch Designs)",
        "reference_pins": [
            {
                "pin_id": "1011198922601143414",
                "title": "Futuristic Cloud Platform Halo Creative",
                "pin_url": "https://www.pinterest.com/pin/1011198922601143414/",
                "image_url": "https://raw.githubusercontent.com/aniketb1rla/pinterestrepo/main/dataset/tech-saas/1011198922601143414.jpg",
            },
        ],
        "colors": {
            "background_tone": "#030712",
            "primary_accent": "#6366f1",
            "secondary_accent": "#ec4899",
            "text_color": "#ffffff",
            "luminance_mode": "dark",
            "temperature": "cool",
            "palette": ["#030712", "#6366f1", "#ec4899", "#111827", "#f3f4f6"],
            "mood": "Next-generation intelligence, seamless automation, magical productivity, effortless scalability",
        },
        "typography": {
            "headline_font_style": "Ultra-Clean Display Sans with Modern Stylistic Sets",
            "body_font_style": "Geometric Sans",
            "recommended_headline_fonts": ["Plus Jakarta Sans", "Syne", "Cabinet Grotesk", "Clash Display"],
            "recommended_body_fonts": ["Inter", "Plus Jakarta Sans"],
            "treatment_effects": "High-contrast bold white headline with radiant purple-to-pink chromatic fill on hero word",
            "hierarchy_order": "Hero AI Hook -> Levitating Floating UI Screen -> Feature Pill -> CTA Button",
        },
        "layout": {
            "layout_type": "Floating Isometric Screen with Radial Gradient Halo",
            "composition": "Centered headline in the upper third; sleek generic tablet/laptop tilted at 12 degrees floating over a radiant purple/indigo energy bloom; crisp pill CTA bottom center.",
            "hierarchy": "Benefit Headline -> Floating Screen Asset -> Ambient Status Glow -> Action Pill",
            "aspect_ratio_code": "4:5",
            "spacing_density": "Deep spatial depth with concentrated light at the focal point",
        },
        "lighting": "Dramatic back-three-quarter rim illumination with a vibrant circular gradient bloom in the background.",
        "decorative_elements": [
            "Floating glass tablet with laser-sharp edge highlights",
            "Radial chromatic halo in electric violet and cyber blue",
            "Faint geometric horizon line giving immense scale",
        ],
        "meta_ad_rules": "Device screen must show clean abstract shapes, never realistic complex mockups that blur on mobile.",
    },

    # =========================================================================
    # FOOD & BEVERAGE
    # =========================================================================
    "food_artisanal_table": {
        "id": "food_artisanal_table",
        "name": "Artisanal Tabletop & Warm Gastronomy",
        "industry_slug": "food-beverage",
        "industry_label": "Food & Beverage",
        "movement": "Gastronomic Editorial & Natural Artisanal Warmth",
        "summary": "Rustic timber surface, warm chiaroscuro window light, fresh organic garnishes, and mouth-watering tactile depth.",
        "inspiration_source": "Pinterest Creative Library (Coffee Shop & Gourmet Food Ads)",
        "reference_pins": [
            {
                "pin_id": "1009580441482030426",
                "title": "Artisanal Cafe Tabletop & Roast Coffee Post",
                "pin_url": "https://www.pinterest.com/pin/1009580441482030426/",
                "image_url": "https://raw.githubusercontent.com/aniketb1rla/pinterestrepo/main/dataset/food-beverage/1009580441482030426.jpg",
            },
            {
                "pin_id": "1017672847076669230",
                "title": "Gourmet Plating Still Life & Warm Window Light",
                "pin_url": "https://www.pinterest.com/pin/1017672847076669230/",
                "image_url": "https://raw.githubusercontent.com/aniketb1rla/pinterestrepo/main/dataset/food-beverage/1017672847076669230.jpg",
            },
        ],
        "colors": {
            "background_tone": "#261a14",
            "primary_accent": "#c29b68",
            "secondary_accent": "#f5ebd7",
            "text_color": "#ffffff",
            "luminance_mode": "dark",
            "temperature": "warm",
            "palette": ["#261a14", "#c29b68", "#4a281b", "#f5ebd7", "#e3dcd8"],
            "mood": "Rich, comforting, sensory indulgence, handcrafted culinary excellence",
        },
        "typography": {
            "headline_font_style": "Warm High-Contrast Editorial Serif or Artisanal Slab",
            "body_font_style": "Clean Warm Sans-Serif",
            "recommended_headline_fonts": ["Playfair Display", "Fraunces", "Cormorant Garamond", "Cinzel"],
            "recommended_body_fonts": ["Plus Jakarta Sans", "Jost"],
            "treatment_effects": "Graceful serif headline with warm gold or cream tint and subtle organic letter spacing",
            "hierarchy_order": "Sensory Headline -> Appetizing Tabletop Dish -> Flavor Profile Pill -> Warm CTA",
        },
        "layout": {
            "layout_type": "45-Degree Overhead Gastronomic Tabletop Composition",
            "composition": "Top warm headline centered in clear space; center captures the dish/beverage at peak freshness with gentle steam and natural textures; bottom refined pill CTA.",
            "hierarchy": "Appetite Hook -> Steaming Culinary Dish -> Natural Garnish Accents -> Order Now Pill",
            "aspect_ratio_code": "4:5",
            "spacing_density": "Rich atmospheric depth with focused sharpness on the culinary hero",
        },
        "lighting": "Warm morning window light from 45 degrees creating luscious specular highlights on surface sauces, glazes, or coffee crema.",
        "decorative_elements": [
            "Handcrafted ceramic plate or textured ribbed tumbler glass",
            "Raw linen napkin and rustic dark walnut wood table grain",
            "Scattered fresh coffee beans, cocoa powder dusting, or culinary herb garnish",
            "Subtle gentle steam rising into the air",
        ],
        "meta_ad_rules": "Appetite appeal is #1. Specular glints on liquid or food texture must look authentic.",
    },

    "food_dynamic_splash": {
        "id": "food_dynamic_splash",
        "name": "Dynamic Suspended Splash & Beverage Action",
        "industry_slug": "food-beverage",
        "industry_label": "Food & Beverage",
        "movement": "High-Speed Dynamic Beverage Action",
        "summary": "Crisp suspended splash, frozen crystal droplets, cold condensation on glass, and electric brand energy.",
        "inspiration_source": "Pinterest Creative Library (Beverage & Energy Drink Commercial Posters)",
        "reference_pins": [
            {
                "pin_id": "1025483777685182991",
                "title": "Chilled Beverage Splash Action Creative",
                "pin_url": "https://www.pinterest.com/pin/1025483777685182991/",
                "image_url": "https://raw.githubusercontent.com/aniketb1rla/pinterestrepo/main/dataset/food-beverage/1025483777685182991.jpg",
            },
        ],
        "colors": {
            "background_tone": "#0f172a",
            "primary_accent": "#ea580c",
            "secondary_accent": "#facc15",
            "text_color": "#ffffff",
            "luminance_mode": "dark",
            "temperature": "warm",
            "palette": ["#0f172a", "#ea580c", "#facc15", "#1e293b", "#ffffff"],
            "mood": "Thirst-quenching, intense freshness, energizing rush, crystal clarity",
        },
        "typography": {
            "headline_font_style": "Heavy Punchy Condensed Grotesk",
            "body_font_style": "Geometric High-Impact Sans",
            "recommended_headline_fonts": ["Cabinet Grotesk", "Clash Display", "Syne", "Archivo Black"],
            "recommended_body_fonts": ["Plus Jakarta Sans", "Inter"],
            "treatment_effects": "High-impact uppercase headline (+0.05em) with punchy vibrant color contrast",
            "hierarchy_order": "Energetic Hook -> Suspended Splash Hero -> Flavor Badge -> Punchy CTA",
        },
        "layout": {
            "layout_type": "Centered Explosive Freeze-Frame Hero",
            "composition": "Bold punchy headline across top; central beverage bottle/can with liquid splash and crystal droplets frozen in mid-air around it; high-contrast pill CTA bottom right.",
            "hierarchy": "Bold Hook Headline -> Splash Action Hero -> Fruit / Flavor Callout -> High-Energy CTA",
            "aspect_ratio_code": "4:5",
            "spacing_density": "Action fills center 60% with clean margins top and bottom for type",
        },
        "lighting": "High-speed 1/2000s strobe rim lighting highlighting every individual liquid droplet and edge contours.",
        "decorative_elements": [
            "Glistening condensation droplets on chilled matte aluminum or glass",
            "Suspended frozen splash crown with crystal clarity",
            "Fresh citrus slice or ingredient exploding outward with kinetic energy",
        ],
        "meta_ad_rules": "High contrast against dark or vibrant backdrop for instant scroll-stopping power.",
    },

    # =========================================================================
    # FASHION & APPAREL
    # =========================================================================
    "fashion_editorial_lookbook": {
        "id": "fashion_editorial_lookbook",
        "name": "High-Fashion Architectural Editorial",
        "industry_slug": "fashion-apparel",
        "industry_label": "Fashion & Apparel",
        "movement": "Modern Architectural Editorial & Swiss Fashion Minimalist",
        "summary": "Textured limestone cyclorama, diffused daylight scrim, effortless posture, and high-fashion editorial Didone typography.",
        "inspiration_source": "Pinterest Creative Library (Fashion & Lifestyle Lookbook Ads)",
        "reference_pins": [
            {
                "pin_id": "1047086982135537478",
                "title": "Editorial Newsletter Layout for Fashion & Lifestyle",
                "pin_url": "https://www.pinterest.com/pin/1047086982135537478/",
                "image_url": "https://raw.githubusercontent.com/aniketb1rla/pinterestrepo/main/dataset/fashion-apparel/1047086982135537478.jpg",
            },
            {
                "pin_id": "1096978421769184175",
                "title": "Minimalist Neutral Lookbook Editorial",
                "pin_url": "https://www.pinterest.com/pin/1096978421769184175/",
                "image_url": "https://raw.githubusercontent.com/aniketb1rla/pinterestrepo/main/dataset/fashion-apparel/1096978421769184175.jpg",
            },
        ],
        "colors": {
            "background_tone": "#ede8e1",
            "primary_accent": "#1c1917",
            "secondary_accent": "#854d0e",
            "text_color": "#1c1917",
            "luminance_mode": "light",
            "temperature": "warm",
            "palette": ["#ede8e1", "#1c1917", "#854d0e", "#d6cebe", "#fdfbf7"],
            "mood": "Timeless sophistication, understated luxury, sculptural silhouette, tactile craftsmanship",
        },
        "typography": {
            "headline_font_style": "High-Contrast Luxury Didone or Ultra-Wide Extended Grotesk",
            "body_font_style": "Clean Architectural Sans",
            "recommended_headline_fonts": ["Playfair Display", "Cormorant Garamond", "Canela", "Cinzel"],
            "recommended_body_fonts": ["Plus Jakarta Sans", "Montserrat", "Jost"],
            "treatment_effects": "Wide-spaced uppercase tracking (+0.18em) with delicate line height",
            "hierarchy_order": "Brand Wordmark -> Editorial Collection Title -> Model Hero -> Minimalist CTA",
        },
        "layout": {
            "layout_type": "Asymmetric Architectural Split (Model Left 55%, Calm Right 45%)",
            "composition": "Model in full silhouette wearing the garment on the left against warm limestone cyclorama; clean right column carries brand mark, collection title, and subtle pill CTA.",
            "hierarchy": "Brand Logo -> Model Silhouette & Fabric Drape -> Collection Title -> Clean Pill CTA",
            "aspect_ratio_code": "4:5",
            "spacing_density": "Generous editorial whitespace allowing fabric drape and silhouette to breathe",
        },
        "lighting": "Soft diffused daylight from a massive 12x12 window scrim, subtle natural shadows revealing fabric weave and cut.",
        "decorative_elements": [
            "Warm limestone plaster wall with subtle tactile tooth",
            "Flawless fabric drape and crisp hemline focus",
            "Natural ambient daylight with warm tone grade",
        ],
        "meta_ad_rules": "Single focal point, high aesthetic appeal, minimal overlay text.",
    },

    "fashion_streetwear_bold": {
        "id": "fashion_streetwear_bold",
        "name": "Korean & Urban Streetwear Poster",
        "industry_slug": "fashion-apparel",
        "industry_label": "Fashion & Apparel",
        "movement": "Raw Urban Streetwear & High-Contrast Brutalism",
        "summary": "Heavy condensed sans-serif, high-contrast flash photography, oversized silhouettes, and raw concrete textures.",
        "inspiration_source": "Pinterest Creative Library (Korean Streetwear & Clothing Brand Posters)",
        "reference_pins": [
            {
                "pin_id": "1119214944920442592",
                "title": "Urban Streetwear Poster & Oversized Silhouette",
                "pin_url": "https://www.pinterest.com/pin/1119214944920442592/",
                "image_url": "https://raw.githubusercontent.com/aniketb1rla/pinterestrepo/main/dataset/fashion-apparel/1119214944920442592.jpg",
            },
        ],
        "colors": {
            "background_tone": "#18181b",
            "primary_accent": "#e11d48",
            "secondary_accent": "#d4d4d8",
            "text_color": "#ffffff",
            "luminance_mode": "dark",
            "temperature": "cool",
            "palette": ["#18181b", "#e11d48", "#d4d4d8", "#27272a", "#ffffff"],
            "mood": "Raw authenticity, rebellious energy, oversized proportions, street culture vanguard",
        },
        "typography": {
            "headline_font_style": "Heavy Ultra-Condensed Grotesk / Brutalist Display",
            "body_font_style": "Technical Monospace / Industrial Sans",
            "recommended_headline_fonts": ["Cabinet Grotesk", "Clash Display", "Archivo Black", "Syne"],
            "recommended_body_fonts": ["Space Mono", "Inter"],
            "treatment_effects": "Massive oversized condensed typography filling the upper edge with zero margin",
            "hierarchy_order": "Oversized Streetwear Title -> Candid Model Stride -> Drop Tag -> Solid CTA",
        },
        "layout": {
            "layout_type": "Full-Bleed Candid Street Snapshot with Heavy Overlay Type",
            "composition": "Top section locked with bold condensed typography; center captures model walking mid-stride wearing oversized garment in authentic urban alley/crosswalk; bottom solid CTA pill.",
            "hierarchy": "Heavy Typography Header -> Candid Action Model -> Street Location Badge -> CTA",
            "aspect_ratio_code": "4:5",
            "spacing_density": "High density, street-smart raw crop with commanding visual weight",
        },
        "lighting": "High-contrast direct camera flash creating sharp graphic drop shadows against weathered concrete.",
        "decorative_elements": [
            "Raw architectural concrete and asphalt textures",
            "Authentic motion blur on shoe or hemline mid-stride",
            "Barcode or technical garment spec badge in corner",
        ],
        "meta_ad_rules": "Raw, candid, unposed feel that out-performs traditional staged ads on Meta feeds.",
    },

    # =========================================================================
    # JEWELRY & LUXURY
    # =========================================================================
    "jewelry_chiaroscuro_macro": {
        "id": "jewelry_chiaroscuro_macro",
        "name": "Chiaroscuro Travertine & Gold Facet",
        "industry_slug": "jewelry-luxury",
        "industry_label": "Jewelry & Luxury",
        "movement": "High-Luxury Chiaroscuro & Facet Macro Precision",
        "summary": "Deep obsidian slate or warm travertine plinth, surgical rim lighting, and razor-sharp metallic facet reflections.",
        "inspiration_source": "Pinterest Creative Library (Collezione Lumina & Diamond Jewelry Ads)",
        "reference_pins": [
            {
                "pin_id": "1039487157758564075",
                "title": "Jewelry Collection Luxury Facet Macro",
                "pin_url": "https://www.pinterest.com/pin/1039487157758564075/",
                "image_url": "https://raw.githubusercontent.com/aniketb1rla/pinterestrepo/main/dataset/jewelry-luxury/1039487157758564075.jpg",
            },
            {
                "pin_id": "1046453663443413734",
                "title": "Collezione Lumina Gold & Diamond Suite",
                "pin_url": "https://www.pinterest.com/pin/1046453663443413734/",
                "image_url": "https://raw.githubusercontent.com/aniketb1rla/pinterestrepo/main/dataset/jewelry-luxury/1046453663443413734.jpg",
            },
        ],
        "colors": {
            "background_tone": "#140d0a",
            "primary_accent": "#d4af37",
            "secondary_accent": "#8c2d19",
            "text_color": "#ffffff",
            "luminance_mode": "dark",
            "temperature": "warm",
            "palette": ["#140d0a", "#d4af37", "#8c2d19", "#3f1f1a", "#faf5ea"],
            "mood": "Opulent rarity, heirloom craft, surgical luster, timeless prestige",
        },
        "typography": {
            "headline_font_style": "High-Contrast Luxury Didone with Graceful Ligatures",
            "body_font_style": "Delicate Wide-Tracked Sans",
            "recommended_headline_fonts": ["Playfair Display", "Cormorant Garamond", "Cinzel", "Canela"],
            "recommended_body_fonts": ["Montserrat", "Plus Jakarta Sans", "Jost"],
            "treatment_effects": "Wide-spaced uppercase serif (+0.2em) with luminous metallic gold tint",
            "hierarchy_order": "Heirloom Headline -> Razor-Sharp Jewel Hero -> Purity Hallmark -> Subtle CTA",
        },
        "layout": {
            "layout_type": "Centered Macro Plinth with Extreme Shallow Focus",
            "composition": "Top delicate luxury title; center presents the 18k gold jewelry piece upright on dark slate with surgical diamond facet highlights; bottom minimalist gold-bordered CTA pill.",
            "hierarchy": "Luxury Title -> Glistening Jewelry Hero -> 18K / Diamond Spec -> Gold Pill CTA",
            "aspect_ratio_code": "4:5",
            "spacing_density": "Profound atmospheric darkness framing a solitary blinding point of light",
        },
        "lighting": "Dramatic chiaroscuro with surgical fiber-optic key lights tracing the bevels, zero specular glare on the stone.",
        "decorative_elements": [
            "Rough-hewn dark basalt or polished warm travertine plinth",
            "Rainbow prismatic caustics refracted through the diamond/gemstone",
            "Subtle soft-focus velvet drape in background",
        ],
        "meta_ad_rules": "Ultra-sharp image quality, pristine metallic reflections, luxury restraint.",
    },

    # =========================================================================
    # FITNESS & SPORTS
    # =========================================================================
    "fitness_high_contrast_motion": {
        "id": "fitness_high_contrast_motion",
        "name": "High-Energy Athletic Kineticism",
        "industry_slug": "fitness-sports",
        "industry_label": "Fitness & Sports",
        "movement": "Kinetic Athletic Energy & Stadium Rim Power",
        "summary": "Dramatic directional key light, authentic athletic grit, bold condensed headline, and sharp kinetic freeze-frame.",
        "inspiration_source": "Pinterest Creative Library (Gym Fitness Posters & Training Campaigns)",
        "reference_pins": [
            {
                "pin_id": "1008947122796257417",
                "title": "Athletic Movement & Kinetic Training Poster",
                "pin_url": "https://www.pinterest.com/pin/1008947122796257417/",
                "image_url": "https://raw.githubusercontent.com/aniketb1rla/pinterestrepo/main/dataset/fitness-sports/1008947122796257417.jpg",
            },
            {
                "pin_id": "1020909809298538495",
                "title": "Stadium Rim Power & Athlete Performance Ad",
                "pin_url": "https://www.pinterest.com/pin/1020909809298538495/",
                "image_url": "https://raw.githubusercontent.com/aniketb1rla/pinterestrepo/main/dataset/fitness-sports/1020909809298538495.jpg",
            },
        ],
        "colors": {
            "background_tone": "#09090b",
            "primary_accent": "#f97316",
            "secondary_accent": "#e4e4e7",
            "text_color": "#ffffff",
            "luminance_mode": "dark",
            "temperature": "warm",
            "palette": ["#09090b", "#f97316", "#e4e4e7", "#27272a", "#18181b"],
            "mood": "Uncompromising discipline, explosive power, grit, personal triumph, peak physical capability",
        },
        "typography": {
            "headline_font_style": "Heavy Condensed Athletic Display / Slanted Power Sans",
            "body_font_style": "Dynamic Condensed Sans",
            "recommended_headline_fonts": ["Cabinet Grotesk", "Clash Display", "Archivo Black", "Syne"],
            "recommended_body_fonts": ["Plus Jakarta Sans", "Inter"],
            "treatment_effects": "Slanted (italicized) condensed uppercase with high-contrast electric orange accent",
            "hierarchy_order": "Power Mantra Headline -> Determined Athlete in Motion -> Performance Pill -> CTA",
        },
        "layout": {
            "layout_type": "Dynamic Low-Angle Kinetic Freeze",
            "composition": "Top high-impact condensed headline; center features determined everyday athlete mid-exercise with authentic sweat and rim light separation; bottom solid high-visibility CTA pill.",
            "hierarchy": "Mantra Headline -> Kinetic Athlete Action -> Performance Spec -> High-Vis CTA",
            "aspect_ratio_code": "4:5",
            "spacing_density": "Muscular, tight composition filled with athletic power",
        },
        "lighting": "Dramatic dual-stadium rim lights cutting through cool atmospheric mist, high-contrast muscle contouring.",
        "decorative_elements": [
            "Textured raw rubber gym flooring with chalk powder dust specks",
            "Authentic beads of sweat glistening under directional spotlights",
            "Subtle athletic stadium lens flare across the top edge",
        ],
        "meta_ad_rules": "Real everyday athlete (no fake influencer tropes); high contrast stops thumbs instantly.",
    },

    # =========================================================================
    # HEALTHCARE & MEDICAL / HEALTH & WELLNESS
    # =========================================================================
    "healthcare_trust_clinical": {
        "id": "healthcare_trust_clinical",
        "name": "Calm Empathetic Clinical Trust",
        "industry_slug": "healthcare-medical",
        "industry_label": "Healthcare & Medical",
        "movement": "Modern Healthcare Human-Centered Trust",
        "summary": "Luminous clean white canvas, serene ocean blue/sage accents, reassuring professional warmth, and clear care credentials.",
        "inspiration_source": "Pinterest Creative Library (Physical Therapy & Healthcare Clinic Posts)",
        "reference_pins": [
            {
                "pin_id": "1021332021766105090",
                "title": "Modern Healthcare Consultation Post",
                "pin_url": "https://www.pinterest.com/pin/1021332021766105090/",
                "image_url": "https://raw.githubusercontent.com/aniketb1rla/pinterestrepo/main/dataset/healthcare-medical/1021332021766105090.jpg",
            },
            {
                "pin_id": "1027454102538904996",
                "title": "Physical Therapy Social Media Design & Healthcare Clinic Post",
                "pin_url": "https://www.pinterest.com/pin/1027454102538904996/",
                "image_url": "https://raw.githubusercontent.com/aniketb1rla/pinterestrepo/main/dataset/healthcare-medical/1027454102538904996.jpg",
            },
        ],
        "colors": {
            "background_tone": "#f0fdf4",
            "primary_accent": "#0284c7",
            "secondary_accent": "#0d9488",
            "text_color": "#0f172a",
            "luminance_mode": "light",
            "temperature": "cool",
            "palette": ["#f0fdf4", "#0284c7", "#0d9488", "#e0f2fe", "#0f172a"],
            "mood": "Calm relief, medical authority, empathetic reassurance, restorative healing",
        },
        "typography": {
            "headline_font_style": "Modern Clean Humanist Sans or Compassionate Hybrid",
            "body_font_style": "Ultra-Legible Healthcare Sans",
            "recommended_headline_fonts": ["Plus Jakarta Sans", "Inter", "Cabinet Grotesk", "Outfit"],
            "recommended_body_fonts": ["Plus Jakarta Sans", "Inter"],
            "treatment_effects": "Gentle, authoritative sentence case with generous breathing room",
            "hierarchy_order": "Empathetic Solution Headline -> Friendly Practitioner & Patient -> Care Badge -> CTA",
        },
        "layout": {
            "layout_type": "Human-Centered Split with Credential Badges",
            "composition": "Top compassionate headline addressing patient relief; center shows warm smiling clinician consultation in sunlit modern clinic; bottom verified credentials badge and booking CTA pill.",
            "hierarchy": "Relief Headline -> Empathetic Clinician Interaction -> Board Certified Badge -> Book CTA",
            "aspect_ratio_code": "4:5",
            "spacing_density": "Uncluttered, airy, high breathing room creating immediate calm",
        },
        "lighting": "Soft natural daylight streaming through large clinic windows, clean white bounce fill, zero clinical harshness.",
        "decorative_elements": [
            "Warm natural wood accents and leafy green fiddle-leaf fig plant in clinic",
            "Verified clinic credential badge with subtle rounded drop shadow",
            "Clean consultation clipboard or tablet showing gentle progress chart",
        ],
        "meta_ad_rules": "Strict adherence: no fabricated patient reviews or unproven cure claims; empathetic benefit-led copy.",
    },

    "wellness_botanical_organic": {
        "id": "wellness_botanical_organic",
        "name": "Holistic Botanical Dietary & Supplement",
        "industry_slug": "health-wellness",
        "industry_label": "Health & Wellness",
        "movement": "Clean Organic Botanical & Modern Wellness",
        "summary": "Earth tone palette, fresh herbal botanicals, amber glass bottle, and gentle morning shadows inspired by AG1 and Ritual.",
        "inspiration_source": "Pinterest Creative Library (AG1 Supplement & Aesthetic Wellness Ads)",
        "reference_pins": [
            {
                "pin_id": "1037376095432885310",
                "title": "Aesthetic Dietary Supplement & Botanical Earth Tones",
                "pin_url": "https://www.pinterest.com/pin/1037376095432885310/",
                "image_url": "https://raw.githubusercontent.com/aniketb1rla/pinterestrepo/main/dataset/health-wellness/1037376095432885310.jpg",
            },
            {
                "pin_id": "1087197166316617564",
                "title": "Daily Wellness Ritual & Clean Supplement Still Life",
                "pin_url": "https://www.pinterest.com/pin/1087197166316617564/",
                "image_url": "https://raw.githubusercontent.com/aniketb1rla/pinterestrepo/main/dataset/health-wellness/1087197166316617564.jpg",
            },
        ],
        "colors": {
            "background_tone": "#f4f0ec",
            "primary_accent": "#065f46",
            "secondary_accent": "#a16207",
            "text_color": "#1c1917",
            "luminance_mode": "light",
            "temperature": "warm",
            "palette": ["#f4f0ec", "#065f46", "#a16207", "#e2e8f0", "#1c1917"],
            "mood": "Whole-body vitality, clean daily ritual, pure organic origin, grounded mindfulness",
        },
        "typography": {
            "headline_font_style": "Refined Editorial Serif or Serene Organic Sans",
            "body_font_style": "Clean Natural Sans",
            "recommended_headline_fonts": ["Cormorant Garamond", "Playfair Display", "Plus Jakarta Sans", "Canela"],
            "recommended_body_fonts": ["Plus Jakarta Sans", "Jost"],
            "treatment_effects": "Warm earthy typography with soft letter spacing and natural confidence",
            "hierarchy_order": "Wellness Benefit Headline -> Amber Supplement Bottle -> Botanical Callout -> Soft Pill CTA",
        },
        "layout": {
            "layout_type": "Sunlit Botanical Still Life Hero",
            "composition": "Top headline celebrating daily vitality; center amber glass bottle upright on pale linen beside fresh botanical ingredients and morning window shadows; bottom forest green CTA pill.",
            "hierarchy": "Daily Ritual Headline -> Amber Supplement Hero -> Clean Ingredient Note -> Vitality CTA",
            "aspect_ratio_code": "4:5",
            "spacing_density": "Harmonious balance of organic objects and clean breathing room",
        },
        "lighting": "Warm morning sunlight filtering through olive tree branches casting delicate dapple shadows across the linen.",
        "decorative_elements": [
            "Amber glass bottle with minimalist matte paper label",
            "Fresh botanical sprigs (mint, rosemary, or citrus leaf)",
            "Textured neutral linen runner over pale micro-cement surface",
        ],
        "meta_ad_rules": "No false medical guarantees; highlight daily ritual, certified purity, and botanical simplicity.",
    },

    # =========================================================================
    # REAL ESTATE & HOME INTERIORS
    # =========================================================================
    "realestate_luxury_architectural": {
        "id": "realestate_luxury_architectural",
        "name": "Golden Hour Luxury Architectural Estate",
        "industry_slug": "real-estate",
        "industry_label": "Real Estate",
        "movement": "Modern Architectural Warmth & Luxury Property",
        "summary": "Sun-drenched Scandinavian interior, hardwood floors, high ceilings, warm afternoon light, and refined luxury sans typography.",
        "inspiration_source": "Pinterest Creative Library (Real Estate Social Media Posts & Modern Architecture)",
        "reference_pins": [
            {
                "pin_id": "1007328641665899862",
                "title": "Sunlit Luxury Architectural Interior Vista",
                "pin_url": "https://www.pinterest.com/pin/1007328641665899862/",
                "image_url": "https://raw.githubusercontent.com/aniketb1rla/pinterestrepo/main/dataset/real-estate/1007328641665899862.jpg",
            },
            {
                "pin_id": "1029987377293469597",
                "title": "Modern Property Showcase & Golden Hour View",
                "pin_url": "https://www.pinterest.com/pin/1029987377293469597/",
                "image_url": "https://raw.githubusercontent.com/aniketb1rla/pinterestrepo/main/dataset/real-estate/1029987377293469597.jpg",
            },
        ],
        "colors": {
            "background_tone": "#0a1128",
            "primary_accent": "#c5a880",
            "secondary_accent": "#f4f1ea",
            "text_color": "#ffffff",
            "luminance_mode": "dark",
            "temperature": "warm",
            "palette": ["#0a1128", "#c5a880", "#f4f1ea", "#1c2541", "#3a506b"],
            "mood": "Sanctuary, architectural elegance, aspirational lifestyle, generational security",
        },
        "typography": {
            "headline_font_style": "Architectural Extended Sans or Elegant Didone",
            "body_font_style": "Crisp Editorial Sans",
            "recommended_headline_fonts": ["Plus Jakarta Sans", "Cinzel", "Playfair Display", "Cabinet Grotesk"],
            "recommended_body_fonts": ["Plus Jakarta Sans", "Montserrat"],
            "treatment_effects": "Wide-spaced uppercase header (+0.15em) with warm gold accenting on key location word",
            "hierarchy_order": "Architectural Statement Headline -> Panoramic Living Space -> Property Specs Pill -> Tour CTA",
        },
        "layout": {
            "layout_type": "Full-Bleed Architectural Vista with Floating Spec Banner",
            "composition": "Breathtaking eye-level photograph of sunlit open-plan architectural interior with floor-to-ceiling windows looking out over serene landscape; top transparent headline; bottom spec badge and tour CTA.",
            "hierarchy": "Property Headline -> Architectural Interior Vista -> 3 Bed / 2 Bath Spec Badge -> Tour Now Pill",
            "aspect_ratio_code": "4:5",
            "spacing_density": "Expansive architectural breathing room with straight vertical lines",
        },
        "lighting": "Golden hour sunlight streaming through floor-to-ceiling glass, illuminating hardwood flooring and neutral designer furnishings.",
        "decorative_elements": [
            "Floor-to-ceiling sliding glass doors with serene green garden backdrop",
            "Sleek architectural spec bar (Beds • Baths • Sq Ft) in frosted pill container",
            "Minimalist designer pendant lighting hanging gracefully",
        ],
        "meta_ad_rules": "Real estate ads must lead with lifestyle aspiration and clean architectural composition.",
    },

    # =========================================================================
    # CONSTRUCTION & HOME SERVICES
    # =========================================================================
    "construction_contractor_trust": {
        "id": "construction_contractor_trust",
        "name": "High-Trust Contractor Craftsmanship",
        "industry_slug": "construction-trades",
        "industry_label": "Construction & Home Services",
        "movement": "Reliable Tradesman Authority & High-Contrast Trust",
        "summary": "Crisp navy/gold badge layout, professional craftsmanship focus, certified warranty signals, and high-trust local authority.",
        "inspiration_source": "Pinterest Creative Library (Roofing & Home Improvement Social Posts)",
        "reference_pins": [
            {
                "pin_id": "1030761433480756871",
                "title": "Roofing & Home Improvement Contractor Post",
                "pin_url": "https://www.pinterest.com/pin/1030761433480756871/",
                "image_url": "https://raw.githubusercontent.com/aniketb1rla/pinterestrepo/main/dataset/construction-trades/1030761433480756871.jpg",
            },
            {
                "pin_id": "1038361257820453353",
                "title": "Licensed & Insured Home Renovation Ad",
                "pin_url": "https://www.pinterest.com/pin/1038361257820453353/",
                "image_url": "https://raw.githubusercontent.com/aniketb1rla/pinterestrepo/main/dataset/construction-trades/1038361257820453353.jpg",
            },
        ],
        "colors": {
            "background_tone": "#0f172a",
            "primary_accent": "#f59e0b",
            "secondary_accent": "#0284c7",
            "text_color": "#ffffff",
            "luminance_mode": "dark",
            "temperature": "warm",
            "palette": ["#0f172a", "#f59e0b", "#0284c7", "#1e293b", "#ffffff"],
            "mood": "Unshakeable reliability, honest craftsmanship, dependable protection, local community pride",
        },
        "typography": {
            "headline_font_style": "Heavy Bold Slab / Rugged Construction Sans",
            "body_font_style": "High-Legibility Sans",
            "recommended_headline_fonts": ["Cabinet Grotesk", "Archivo Black", "Clash Display", "Plus Jakarta Sans"],
            "recommended_body_fonts": ["Plus Jakarta Sans", "Inter"],
            "treatment_effects": "High-contrast bold all-caps with golden yellow emphasis on guarantee or service",
            "hierarchy_order": "Problem / Solution Headline -> Finished Craftsmanship Photo -> Warranty Badge -> Call/Quote CTA",
        },
        "layout": {
            "layout_type": "High-Contrast Solution Frame with Certified Seal",
            "composition": "Top punchy guarantee headline; center showcases finished roof, kitchen renovation or clean installation by friendly uniformed crew; bottom verified local license badge and Get Free Quote pill CTA.",
            "hierarchy": "Reliability Headline -> Flawless Finished Workmanship -> Lifetime Warranty Seal -> Free Quote CTA",
            "aspect_ratio_code": "4:5",
            "spacing_density": "Sturdy, balanced grid with clear bold trust badges",
        },
        "lighting": "Bright, clear outdoor daylight or clean task work lighting showing immaculate finish and clean lines.",
        "decorative_elements": [
            "Golden verified guarantee seal badge (e.g. Licensed & Insured)",
            "Crisp before/after split line or finished architectural detail",
            "Friendly tradesperson in clean branded company polo smiling at work",
        ],
        "meta_ad_rules": "Local trust is paramount: emphasize upfront pricing, warranty, and fast response.",
    },

    # =========================================================================
    # E-COMMERCE & RETAIL / D2C
    # =========================================================================
    "ecommerce_d2c_studio_pedestal": {
        "id": "ecommerce_d2c_studio_pedestal",
        "name": "Modern D2C Studio Pedestal Hero",
        "industry_slug": "ecommerce-retail",
        "industry_label": "E-commerce & Retail",
        "movement": "Modern D2C Pop Minimalist Studio",
        "summary": "Dual-tone pastel set, geometric pedestal, crisp directional shadow, vibrant product spotlight, and high-converting CTA pill.",
        "inspiration_source": "Pinterest Creative Library (D2C Brand & High-Converting Product Ads)",
        "reference_pins": [
            {
                "pin_id": "1006624954233458422",
                "title": "Your Ad Has 3 Seconds: Meta Ads Creative Tip",
                "pin_url": "https://www.pinterest.com/pin/1006624954233458422/",
                "image_url": "https://raw.githubusercontent.com/aniketb1rla/pinterestrepo/main/dataset/ecommerce-retail/1006624954233458422.jpg",
            },
            {
                "pin_id": "1070941986408981426",
                "title": "High-Converting D2C Product Launch Plinth",
                "pin_url": "https://www.pinterest.com/pin/1070941986408981426/",
                "image_url": "https://raw.githubusercontent.com/aniketb1rla/pinterestrepo/main/dataset/ecommerce-retail/1070941986408981426.jpg",
            },
        ],
        "colors": {
            "background_tone": "#f1f5f9",
            "primary_accent": "#4f46e5",
            "secondary_accent": "#06b6d4",
            "text_color": "#0f172a",
            "luminance_mode": "light",
            "temperature": "neutral",
            "palette": ["#f1f5f9", "#4f46e5", "#06b6d4", "#e2e8f0", "#0f172a"],
            "mood": "Instant desire, high conversion velocity, fresh modern delight, frictionless checkout",
        },
        "typography": {
            "headline_font_style": "Punchy Modern Grotesk with Tight Letterforms",
            "body_font_style": "Clean Conversion Sans",
            "recommended_headline_fonts": ["Plus Jakarta Sans", "Cabinet Grotesk", "Clash Display", "Syne"],
            "recommended_body_fonts": ["Plus Jakarta Sans", "Inter"],
            "treatment_effects": "High-contrast bold headline with clean sentence case and 0 tracking",
            "hierarchy_order": "Value Hook Headline -> Upright Product Hero on Pedestal -> Offer Pill -> Shop Now CTA",
        },
        "layout": {
            "layout_type": "Centered Hero Plinth with High-Visibility Offer Pill",
            "composition": "Top 20% carries a short compelling hook; center 60% spotlights the product standing upright on dual-tone geometric plinths with a crisp 45-degree shadow; bottom 20% anchors brand mark and Shop Now pill.",
            "hierarchy": "Irresistible Hook -> Hero Product Asset -> Feature Callout Pill -> Shop Now CTA",
            "aspect_ratio_code": "4:5",
            "spacing_density": "Clean negative space allowing the product packaging and colors to dominate",
        },
        "lighting": "Clean studio key light from upper left casting a crisp graphic 45-degree shadow; soft ambient bounce filling packaging labels.",
        "decorative_elements": [
            "Cylindrical or rectangular geometric plinth in tint of brand accent",
            "Crisp hard graphic shadow adding tactile 3D physical presence",
            "High-contrast offer or benefit pill badge (e.g. Free Shipping)",
        ],
        "meta_ad_rules": "Designed for maximum CTR on Meta mobile feed; product is huge and unmistakable.",
    },

    # =========================================================================
    # MARKETING & AGENCIES
    # =========================================================================
    "marketing_bold_statement": {
        "id": "marketing_bold_statement",
        "name": "Award-Winning Typographic Agency Creative",
        "industry_slug": "marketing-agency",
        "industry_label": "Marketing & Agencies",
        "movement": "Swiss Typographic & Award-Winning Creative Agency Aesthetic",
        "summary": "High-contrast monochrome or primary split, oversized conceptual typography, and provocative copywriting inspired by Pentagram and Droga5.",
        "inspiration_source": "Pinterest Creative Library (Creative Agency Campaigns & Brand Identity Posters)",
        "reference_pins": [
            {
                "pin_id": "1046664769667324036",
                "title": "Creative Agency Campaign Layout & Provocative Type",
                "pin_url": "https://www.pinterest.com/pin/1046664769667324036/",
                "image_url": "https://raw.githubusercontent.com/aniketb1rla/pinterestrepo/main/dataset/marketing-agency/1046664769667324036.jpg",
            },
            {
                "pin_id": "581527370672921140",
                "title": "Cable Creative Ads – High Impact Agency Concept",
                "pin_url": "https://www.pinterest.com/pin/581527370672921140/",
                "image_url": "https://raw.githubusercontent.com/aniketb1rla/pinterestrepo/main/dataset/marketing-agency/581527370672921140.jpg",
            },
        ],
        "colors": {
            "background_tone": "#000000",
            "primary_accent": "#ff2d55",
            "secondary_accent": "#ffffff",
            "text_color": "#ffffff",
            "luminance_mode": "dark",
            "temperature": "cool",
            "palette": ["#000000", "#ff2d55", "#ffffff", "#27272a", "#f43f5e"],
            "mood": "Provocative intelligence, razor-sharp wit, undeniable creative authority, scroll-stopping punch",
        },
        "typography": {
            "headline_font_style": "Massive Bold Grotesk or Editorial High-Contrast Serif",
            "body_font_style": "Swiss Precision Sans",
            "recommended_headline_fonts": ["Cabinet Grotesk", "Clash Display", "Playfair Display", "Archivo Black"],
            "recommended_body_fonts": ["Inter", "Plus Jakarta Sans"],
            "treatment_effects": "Unapologetically bold display type taking center stage with extreme negative margin",
            "hierarchy_order": "Provocative Headline -> Conceptual Visual Metaphor -> Agency Signature -> CTA",
        },
        "layout": {
            "layout_type": "Provocative Typographic Command & Center Metaphor",
            "composition": "Massive high-impact statement across top and middle; clever single conceptual 3D metaphor object in center; bottom minimal signature and Let's Talk pill CTA.",
            "hierarchy": "Provocative Hook -> Conceptual Object -> Strategic Proof -> Action CTA",
            "aspect_ratio_code": "4:5",
            "spacing_density": "Calculated tension between massive bold type and stark negative space",
        },
        "lighting": "High-contrast theatrical gallery lighting with a single razor spotlight on the central conceptual object.",
        "decorative_elements": [
            "Single sculptural metaphor object (e.g. glowing key, architectural prism, molten glass)",
            "Crisp hairline divider separating bold claim from agency attribution",
        ],
        "meta_ad_rules": "Extreme scroll-stopper; challenges industry complacency in under 2 seconds.",
    },
}


# ---------------------------------------------------------------------------
# Dynamic Creative Themes Registry (Multi-Theme Variety from Pinterest Atlas)
# ---------------------------------------------------------------------------

DIVERSE_PRESET_ID = "diverse"

DIVERSE_PRESET: Dict[str, Any] = {
    "id": "diverse",
    "name": "Diverse Creative Mix (Varied Themes)",
    "industry_slug": "all",
    "industry_label": "All Industries (Multi-Theme Variety)",
    "movement": "Diverse High-Contrast Strategic Creative Mix",
    "summary": "Dynamically assigns each static ad brief a distinct, high-contrast creative theme (Split-Screen Us vs Them, Macro Texture, Model Lifestyle, Elemental Splash, Typographic Poster, Bento Grid, etc.) tailored to its marketing framework for maximum campaign visual variety.",
    "inspiration_source": "Pinterest Design Atlas (Multi-Theme Variety)",
    "reference_pins": [
        {
            "pin_id": "1006624954233458422",
            "title": "High-Converting D2C Product Launch Plinth",
            "pin_url": "https://www.pinterest.com/pin/1006624954233458422/",
            "image_url": "https://raw.githubusercontent.com/aniketb1rla/pinterestrepo/main/dataset/ecommerce-retail/1006624954233458422.jpg",
        },
        {
            "pin_id": "1046664769667324036",
            "title": "High Impact Typographic Campaign Concept",
            "pin_url": "https://www.pinterest.com/pin/1046664769667324036/",
            "image_url": "https://raw.githubusercontent.com/aniketb1rla/pinterestrepo/main/dataset/marketing-agency/1046664769667324036.jpg",
        },
        {
            "pin_id": "1008595279052523159",
            "title": "Modern Modular Bento Feature Grid",
            "pin_url": "https://www.pinterest.com/pin/1008595279052523159/",
            "image_url": "https://raw.githubusercontent.com/aniketb1rla/pinterestrepo/main/dataset/tech-saas/1008595279052523159.jpg",
        },
        {
            "pin_id": "1012747035363432272",
            "title": "Organic Botanical Travertine Still Life",
            "pin_url": "https://www.pinterest.com/pin/1012747035363432272/",
            "image_url": "https://raw.githubusercontent.com/aniketb1rla/pinterestrepo/main/dataset/beauty-cosmetics/1012747035363432272.jpg",
        },
    ],
    "colors": {
        "background_tone": "#0f172a",
        "primary_accent": "#6366f1",
        "secondary_accent": "#38bdf8",
        "text_color": "#ffffff",
        "luminance_mode": "dark",
        "temperature": "neutral",
        "palette": ["#0f172a", "#1e293b", "#6366f1", "#38bdf8", "#f8fafc"],
        "mood": "Dynamic, versatile, multi-angle, high-contrast creative variety",
    },
    "typography": {
        "headline_font_style": "Contrasting Multi-Aesthetic Typography (Editorial Serif, Swiss Bold, Geometric Display)",
        "body_font_style": "Clean Contemporary Sans-Serif",
        "recommended_headline_fonts": ["Plus Jakarta Sans", "Syne", "Playfair Display", "Clash Display"],
        "recommended_body_fonts": ["Inter", "Plus Jakarta Sans"],
        "treatment_effects": "Dynamic per-theme typographic hierarchy tailored to headline length and hook",
        "hierarchy_order": "Dynamic per theme archetype",
    },
    "layout": {
        "layout_type": "Multi-Theme Varied Creative Campaign",
        "composition": "Varied compositional frameworks: 50/50 split comparison, macro extreme close-up, authentic model in-situ, raw elemental splash, or modular bento architecture.",
        "hierarchy": "Varied",
        "aspect_ratio_code": "4:5",
        "spacing_density": "Optimal negative space with high mobile thumb-stopping power",
    },
    "lighting": "Contrasting directional lighting tailored to each creative angle (golden hour, studio rim light, high-key lab fill, dramatic chiaroscuro).",
    "decorative_elements": [
        "Theme-specific organic props",
        "Authentic tactile textures",
        "Dynamic water caustics or splashes",
        "Geometric framing cards",
    ],
    "meta_ad_rules": "Strict 3-element budget per ad, maximum visual variety across campaign batch.",
}

STATIC_THEMES: Dict[str, Dict[str, Any]] = {
    "split_contrast": {
        "id": "split_contrast",
        "template_id": "split_contrast",
        "name": "Split-Screen Us vs Them (Comparison)",
        "industry_slug": "ecommerce-retail",
        "industry_label": "Comparison & Problem-Solution",
        "movement": "High-Contrast Problem/Solution Split",
        "summary": "Polarizing 50/50 dual vertical split contrasting the painful legacy friction on the left with the effortless, radiant brand solution on the right.",
        "inspiration_source": "Pinterest Design Atlas (Before/After & Comparison Creatives)",
        "reference_pins": [
            {
                "pin_id": "1006624954233458422",
                "title": "High-Converting D2C Comparison & Hook Framework",
                "pin_url": "https://www.pinterest.com/pin/1006624954233458422/",
                "image_url": "https://raw.githubusercontent.com/aniketb1rla/pinterestrepo/main/dataset/ecommerce-retail/1006624954233458422.jpg",
            },
            {
                "pin_id": "1046664769667324036",
                "title": "Direct Polar Contrast & Brand vs Them",
                "pin_url": "https://www.pinterest.com/pin/1046664769667324036/",
                "image_url": "https://raw.githubusercontent.com/aniketb1rla/pinterestrepo/main/dataset/marketing-agency/1046664769667324036.jpg",
            },
        ],
        "colors": {
            "background_tone": "#0f172a",
            "primary_accent": "#ef4444",
            "secondary_accent": "#10b981",
            "text_color": "#ffffff",
            "luminance_mode": "dual",
            "temperature": "contrast",
            "palette": ["#1e293b", "#ef4444", "#10b981", "#f8fafc", "#0f172a"],
            "mood": "Decisive, transformative, clear problem-solution polarization",
        },
        "typography": {
            "headline_font_style": "High-Impact Swiss Grotesk or Condensed Sans",
            "body_font_style": "Clean Geometric Sans",
            "recommended_headline_fonts": ["Plus Jakarta Sans", "Cabinet Grotesk", "Inter"],
            "recommended_body_fonts": ["Inter", "Plus Jakarta Sans"],
            "treatment_effects": "High optical contrast dual badges (THEIR WAY vs YOUR WAY)",
            "hierarchy_order": "Top headline -> 50/50 Split Canvas -> Centered CTA pill",
        },
        "layout": {
            "layout_type": "Vertical Split 50/50 Problem vs Solution",
            "composition": "Sharp vertical divider: left half shows cluttered, desaturated everyday problem; right half shows illuminated, flawless brand solution.",
            "hierarchy": "Hook Headline -> Before/After Panels -> Bottom CTA Pill",
            "aspect_ratio_code": "4:5",
            "spacing_density": "Structured, balanced split grid",
        },
        "lighting": "Contrasting dual lighting: flat muted desaturated light on left, warm radiant directional spotlight on right.",
        "decorative_elements": [
            "Thin crisp vertical dividing rule",
            "Subtle 'Before / After' or 'Them / Us' pill badges",
            "Contrasting color temperatures",
        ],
        "meta_ad_rules": "Strictly balanced split, instant visual comprehension on mobile feed.",
    },

    "macro_texture": {
        "id": "macro_texture",
        "template_id": "macro_texture",
        "name": "Macro Ingredient & Tactile Craft Detail",
        "industry_slug": "beauty-cosmetics",
        "industry_label": "Sensory & Material Detail",
        "movement": "Extreme Sensory Macro Materiality & Craft",
        "summary": "Sensory macro close-up celebrating rich formula texture, glistening droplets, woven fabric weave, or precision material grain with the hero product resting within.",
        "inspiration_source": "Pinterest Design Atlas (Sensory Texture & Macro Craft)",
        "reference_pins": [
            {
                "pin_id": "1039487157758564075",
                "title": "Luxury Facet Macro & Extreme Material Detail",
                "pin_url": "https://www.pinterest.com/pin/1039487157758564075/",
                "image_url": "https://raw.githubusercontent.com/aniketb1rla/pinterestrepo/main/dataset/jewelry-luxury/1039487157758564075.jpg",
            },
            {
                "pin_id": "1019924646876106847",
                "title": "Dewy Formula Texture & Glistening Swatch",
                "pin_url": "https://www.pinterest.com/pin/1019924646876106847/",
                "image_url": "https://raw.githubusercontent.com/aniketb1rla/pinterestrepo/main/dataset/beauty-cosmetics/1019924646876106847.jpg",
            },
        ],
        "colors": {
            "background_tone": "#fdfbf7",
            "primary_accent": "#c2410c",
            "secondary_accent": "#78350f",
            "text_color": "#1c1917",
            "luminance_mode": "light",
            "temperature": "warm",
            "palette": ["#fdfbf7", "#c2410c", "#fed7aa", "#78350f", "#1c1917"],
            "mood": "Sensory, visceral, decadent, authentic tactile craftsmanship",
        },
        "typography": {
            "headline_font_style": "Editorial Serif or Delicate Display",
            "body_font_style": "Minimal Sans-Serif",
            "recommended_headline_fonts": ["Playfair Display", "Canela", "Fraunces"],
            "recommended_body_fonts": ["Plus Jakarta Sans", "Inter"],
            "treatment_effects": "Wide-spaced editorial caption tracking",
            "hierarchy_order": "Top sensory hook -> Extreme macro texture canvas -> Bottom pill CTA",
        },
        "layout": {
            "layout_type": "Hero Subject Nested in Extreme Macro Texture Swatch",
            "composition": "The hero product rests directly in a rich, tactile macro swatch of its key formula, raw ingredient, or artisan material.",
            "hierarchy": "Sensory Headline -> Macro Texture Field -> Pill CTA",
            "aspect_ratio_code": "4:5",
            "spacing_density": "Tactile, organic, luxurious edge-to-edge texture",
        },
        "lighting": "Raking 45-degree macro lighting casting crisp microscopic shadows to accentuate formula depth and viscosity.",
        "decorative_elements": [
            "Creamy fluid swirl or organic raw ingredient particles",
            "Microscopic glistening dew droplets",
            "Natural shallow depth of field with creamy bokeh",
        ],
        "meta_ad_rules": "Tack-sharp foreground focal point, soft blurred perimeter.",
    },

    "model_lifestyle": {
        "id": "model_lifestyle",
        "template_id": "model_lifestyle",
        "name": "Authentic Model Lifestyle & Contextual Human Touch",
        "industry_slug": "fashion-apparel",
        "industry_label": "Lifestyle & Human Connection",
        "movement": "Editorial Candid Lifestyle & Emotional Connection",
        "summary": "Natural human interaction with the product in a bright, lived-in context; authentic expression, genuine skin texture, and soft daylight.",
        "inspiration_source": "Pinterest Design Atlas (Editorial Lifestyle & Human Connection)",
        "reference_pins": [
            {
                "pin_id": "1047086982135537478",
                "title": "Editorial Newsletter Layout for Fashion & Lifestyle",
                "pin_url": "https://www.pinterest.com/pin/1047086982135537478/",
                "image_url": "https://raw.githubusercontent.com/aniketb1rla/pinterestrepo/main/dataset/fashion-apparel/1047086982135537478.jpg",
            },
            {
                "pin_id": "1007328641665899862",
                "title": "Sunlit Luxury Architectural Interior Vista",
                "pin_url": "https://www.pinterest.com/pin/1007328641665899862/",
                "image_url": "https://raw.githubusercontent.com/aniketb1rla/pinterestrepo/main/dataset/real-estate/1007328641665899862.jpg",
            },
        ],
        "colors": {
            "background_tone": "#f4ede4",
            "primary_accent": "#0f172a",
            "secondary_accent": "#9a3412",
            "text_color": "#0f172a",
            "luminance_mode": "light",
            "temperature": "warm",
            "palette": ["#f4ede4", "#0f172a", "#9a3412", "#e2d5c3", "#334155"],
            "mood": "Warm, relatable, authentic, aspirational yet grounded everyday life",
        },
        "typography": {
            "headline_font_style": "Warm Humanist Sans or Confident Modern Editorial",
            "body_font_style": "Refined Editorial Sans",
            "recommended_headline_fonts": ["Plus Jakarta Sans", "Syne", "Ogg", "Outfit"],
            "recommended_body_fonts": ["Plus Jakarta Sans", "Inter"],
            "treatment_effects": "Clean uncluttered typography floating over natural negative space",
            "hierarchy_order": "Top candid headline -> Hero model interacting with product -> Floating pill CTA",
        },
        "layout": {
            "layout_type": "Editorial In-Situ Human Context",
            "composition": "Authentic talent actively using or holding the hero product in an unforced, candid moment inside a bright contemporary living environment.",
            "hierarchy": "Benefit Statement -> Candid Model Action -> Product In Hand -> CTA Pill",
            "aspect_ratio_code": "4:5",
            "spacing_density": "Expansive environmental breathing room",
        },
        "lighting": "Natural daylight pouring through a large window, soft ambient fill, zero artificial flash.",
        "decorative_elements": [
            "Authentic architectural interior details (ceramic mug, linen throw, natural wood)",
            "Soft morning sunbeams",
            "Natural human gestures and unforced smiles",
        ],
        "meta_ad_rules": "No airbrushed plastic skin, genuine human texture with real pores.",
    },

    "elemental_set": {
        "id": "elemental_set",
        "template_id": "elemental_set",
        "name": "Elemental Splash & Raw Nature Immersion",
        "industry_slug": "health-wellness",
        "industry_label": "Sensory & High Energy",
        "movement": "Dynamic Organic Elements & High-Energy Freshness",
        "summary": "Hero product immersed in crisp splashing water droplets, fresh botanical clippings, or textured crushed stone for organic freshness and vitality.",
        "inspiration_source": "Pinterest Design Atlas (Organic Botanical & Liquid Splash)",
        "reference_pins": [
            {
                "pin_id": "1037376095432885310",
                "title": "Aesthetic Dietary Supplement & Botanical Earth Tones",
                "pin_url": "https://www.pinterest.com/pin/1037376095432885310/",
                "image_url": "https://raw.githubusercontent.com/aniketb1rla/pinterestrepo/main/dataset/health-wellness/1037376095432885310.jpg",
            },
            {
                "pin_id": "1025483777685182991",
                "title": "Chilled Beverage Splash Action Creative",
                "pin_url": "https://www.pinterest.com/pin/1025483777685182991/",
                "image_url": "https://raw.githubusercontent.com/aniketb1rla/pinterestrepo/main/dataset/food-beverage/1025483777685182991.jpg",
            },
        ],
        "colors": {
            "background_tone": "#0369a1",
            "primary_accent": "#38bdf8",
            "secondary_accent": "#0284c7",
            "text_color": "#ffffff",
            "luminance_mode": "vibrant",
            "temperature": "cool",
            "palette": ["#0369a1", "#38bdf8", "#0284c7", "#f0f9ff", "#082f49"],
            "mood": "Invigorating, pristine, high-energy, refreshing, pure hydration",
        },
        "typography": {
            "headline_font_style": "Punchy Bold Sans-Serif",
            "body_font_style": "Geometric Technical Sans",
            "recommended_headline_fonts": ["Plus Jakarta Sans", "Cabinet Grotesk", "Clash Display"],
            "recommended_body_fonts": ["Inter", "Plus Jakarta Sans"],
            "treatment_effects": "High optical legibility over dynamic environmental elements",
            "hierarchy_order": "Top punchy hook -> Kinetic elemental product hero -> Bottom tactile CTA",
        },
        "layout": {
            "layout_type": "Dynamic Kinetic Elemental Immersion",
            "composition": "The hero product anchors the center of the frame as dynamic splashing water or organic botanical fragments explode outward in a frozen microsecond.",
            "hierarchy": "Action Hook -> Frozen Splash Hero -> Tactile CTA Pill",
            "aspect_ratio_code": "4:5",
            "spacing_density": "Dynamic kinetic movement with clear typography safe zone",
        },
        "lighting": "High-speed strobe lighting freezing water droplets in mid-air with crystal-clear specular highlights.",
        "decorative_elements": [
            "Crystal-clear splashing water droplets and fine mist",
            "Fresh botanical leaves or organic fruit wedges",
            "Reflective ripples and refracted caustics",
        ],
        "meta_ad_rules": "Tack-sharp product silhouette, crystal-clear liquid droplets.",
    },

    "marketing_bold_statement": {
        "id": "marketing_bold_statement",
        "template_id": "marketing_bold_statement",
        "name": "High-Impact Typographic Bold Poster",
        "industry_slug": "marketing-agency",
        "industry_label": "High-Impact Typographic",
        "movement": "Swiss Bold Poster & Provocative Statement",
        "summary": "Massive, confident statement headline dominating the visual frame, high optical contrast, razor-sharp product grounding, zero filler.",
        "inspiration_source": "Pinterest Design Atlas (High Impact Typographic Posters)",
        "reference_pins": [
            {
                "pin_id": "1046664769667324036",
                "title": "Creative Agency Campaign Layout & Provocative Type",
                "pin_url": "https://www.pinterest.com/pin/1046664769667324036/",
                "image_url": "https://raw.githubusercontent.com/aniketb1rla/pinterestrepo/main/dataset/marketing-agency/1046664769667324036.jpg",
            },
            {
                "pin_id": "1119214944920442592",
                "title": "Urban Streetwear Poster & Oversized Silhouette",
                "pin_url": "https://www.pinterest.com/pin/1119214944920442592/",
                "image_url": "https://raw.githubusercontent.com/aniketb1rla/pinterestrepo/main/dataset/fashion-apparel/1119214944920442592.jpg",
            },
        ],
        "colors": {
            "background_tone": "#09090b",
            "primary_accent": "#e11d48",
            "secondary_accent": "#fafafa",
            "text_color": "#ffffff",
            "luminance_mode": "dark",
            "temperature": "contrast",
            "palette": ["#09090b", "#e11d48", "#fafafa", "#27272a", "#71717a"],
            "mood": "Bold, provocative, unapologetic, authoritative, high-conversion directness",
        },
        "typography": {
            "headline_font_style": "Monumental Condensed Grotesk or Ultra-Bold Editorial Serif",
            "body_font_style": "Technical Monospace or Precision Sans",
            "recommended_headline_fonts": ["Clash Display", "Cabinet Grotesk", "Syne", "Druk"],
            "recommended_body_fonts": ["Inter", "Space Grotesk"],
            "treatment_effects": "Massive display sizing (commanding 40% of canvas) with tight line-height",
            "hierarchy_order": "Dominant Statement Headline -> Anchored Product Silhouette -> High-Contrast CTA",
        },
        "layout": {
            "layout_type": "Typographic Poster Dominance",
            "composition": "Massive high-contrast typography commands the upper half of the canvas; the product is grounded with intense directional shadow in the lower third.",
            "hierarchy": "Monumental Statement -> Grounded Product Silhouette -> Solid Pill CTA",
            "aspect_ratio_code": "4:5",
            "spacing_density": "Graphic tension, high negative space contrast",
        },
        "lighting": "Dramatic chiaroscuro with deep directional shadows and sharp rim light defining the product contours.",
        "decorative_elements": [
            "Oversized typographic glyphs or quotes",
            "Architectural grid framing lines",
            "Stark solid background canvas",
        ],
        "meta_ad_rules": "Single clear message, zero visual noise, unstoppable scroll-stopping contrast.",
    },

    "outdoor_light": {
        "id": "outdoor_light",
        "template_id": "outdoor_light",
        "name": "Sun-Drenched Golden Hour & Natural Shadows",
        "industry_slug": "real-estate",
        "industry_label": "Natural Sunlit & Architecture",
        "movement": "Warm Architectural Sunlit Naturalism",
        "summary": "Long warm directional sunbeams casting geometric raking shadows across a clean stone patio or sunlit room, vibrant warmth and organic authenticity.",
        "inspiration_source": "Pinterest Design Atlas (Sunlit Architecture & Golden Hour Still Life)",
        "reference_pins": [
            {
                "pin_id": "1007328641665899862",
                "title": "Sunlit Luxury Architectural Interior Vista",
                "pin_url": "https://www.pinterest.com/pin/1007328641665899862/",
                "image_url": "https://raw.githubusercontent.com/aniketb1rla/pinterestrepo/main/dataset/real-estate/1007328641665899862.jpg",
            },
            {
                "pin_id": "1017672847076669230",
                "title": "Gourmet Plating Still Life & Warm Window Light",
                "pin_url": "https://www.pinterest.com/pin/1017672847076669230/",
                "image_url": "https://raw.githubusercontent.com/aniketb1rla/pinterestrepo/main/dataset/food-beverage/1017672847076669230.jpg",
            },
        ],
        "colors": {
            "background_tone": "#fef3c7",
            "primary_accent": "#d97706",
            "secondary_accent": "#451a03",
            "text_color": "#1e293b",
            "luminance_mode": "light",
            "temperature": "warm",
            "palette": ["#fef3c7", "#d97706", "#451a03", "#fde68a", "#78350f"],
            "mood": "Golden, optimistic, serene, radiant, sun-drenched architectural purity",
        },
        "typography": {
            "headline_font_style": "Editorial Serif or Delicate Modern Display",
            "body_font_style": "Geometric Sans",
            "recommended_headline_fonts": ["Playfair Display", "Cormorant Garamond", "Fraunces"],
            "recommended_body_fonts": ["Plus Jakarta Sans", "Inter"],
            "treatment_effects": "Subtle italicized key benefit phrase, wide letter spacing",
            "hierarchy_order": "Top sunlit benefit -> Hero product on sun-drenched ledge -> Crisp pill CTA",
        },
        "layout": {
            "layout_type": "Golden Hour Environmental Still Life",
            "composition": "The hero product rests on an architectural limestone ledge bathed in warm late-afternoon sunbeams with long dramatic shadows.",
            "hierarchy": "Warm Headline -> Product in Sunbeam -> Pill CTA",
            "aspect_ratio_code": "4:5",
            "spacing_density": "Expansive architectural negative space",
        },
        "lighting": "Warm low-angle golden hour sunlight (3200K) creating rich warm highlights and geometric architectural shadows.",
        "decorative_elements": [
            "Warm architectural window frame shadows",
            "Smooth natural limestone or micro-cement ledge",
            "Subtle fluttering palm or olive leaf shadow silhouette",
        ],
        "meta_ad_rules": "Natural warm color grading, genuine cinematic sun flare.",
    },

    "beauty_clinical_ordinary": {
        "id": "beauty_clinical_ordinary",
        "template_id": "beauty_clinical_ordinary",
        "name": "Clinical Formulations & Ingredient Science",
        "industry_slug": "beauty-cosmetics",
        "industry_label": "Science & Medical Precision",
        "movement": "Swiss Typographic & Pure Formulation Science",
        "summary": "Crisp white studio, scientific dropper bottle, pure typography, and active ingredient percentage callout inspired by The Ordinary.",
        "inspiration_source": "Pinterest Design Atlas (The Ordinary Clinical Formulations)",
        "reference_pins": [
            {
                "pin_id": "1012747035363432272",
                "title": "Active Botanical Formulation Layout",
                "pin_url": "https://www.pinterest.com/pin/1012747035363432272/",
                "image_url": "https://raw.githubusercontent.com/aniketb1rla/pinterestrepo/main/dataset/beauty-cosmetics/1012747035363432272.jpg",
            },
            {
                "pin_id": "1000291767255653778",
                "title": "Clean Minimal Apothecary Serum Post",
                "pin_url": "https://www.pinterest.com/pin/1000291767255653778/",
                "image_url": "https://raw.githubusercontent.com/aniketb1rla/pinterestrepo/main/dataset/beauty-cosmetics/1000291767255653778.jpg",
            },
        ],
        "colors": {
            "background_tone": "#f8fafc",
            "primary_accent": "#2563eb",
            "secondary_accent": "#0f172a",
            "text_color": "#0f172a",
            "luminance_mode": "light",
            "temperature": "cool",
            "palette": ["#f8fafc", "#0f172a", "#2563eb", "#64748b", "#e2e8f0"],
            "mood": "Clinical authority, dermatological trust, formulation purity, and clean precision",
        },
        "typography": {
            "headline_font_style": "Precision Swiss Grotesk or Monospaced Data Header",
            "body_font_style": "Clean Technical Sans-Serif",
            "recommended_headline_fonts": ["Cabinet Grotesk", "Plus Jakarta Sans", "Inter", "Space Grotesk"],
            "recommended_body_fonts": ["Inter", "Roboto Mono", "Plus Jakarta Sans"],
            "treatment_effects": "High-contrast bold title with crisp technical uppercase subtitle (+0.14em)",
            "hierarchy_order": "Top formulation headline -> Crisp dropper hero -> Active ingredient badge -> Clean CTA",
        },
        "layout": {
            "layout_type": "Asymmetric Swiss Laboratory Grid",
            "composition": "Top-left scientific headline with active compound percentage, tack-sharp apothecary dropper bottle on white acrylic block, bottom technical CTA pill.",
            "hierarchy": "Clinical Claim -> Dropper Product Hero -> Active Formulation Note -> CTA Button",
            "aspect_ratio_code": "4:5",
            "spacing_density": "Architectural grid alignment with clinical white negative space",
        },
        "lighting": "Clean high-key commercial laboratory lighting, crisp specular reflections on glass dropper, pristine shadowless fill.",
        "decorative_elements": [
            "White matte acrylic laboratory plinth",
            "Single suspended amber dropper with glistening droplet",
            "Crisp laboratory formulation badge",
        ],
        "meta_ad_rules": "Rigorous typography, high legibility on mobile feed, sharp edges.",
    },

    "saas_bento_grid": {
        "id": "saas_bento_grid",
        "template_id": "saas_bento_grid",
        "name": "Modular Bento Grid & Feature Architecture",
        "industry_slug": "tech-saas",
        "industry_label": "Software & Tech Ecosystem",
        "movement": "Modern High-Tech Bento Grid Architecture",
        "summary": "Crisp modular bento cards highlighting key metrics, floating UI details, and ecosystem features in a structured visual system.",
        "inspiration_source": "Pinterest Design Atlas (Modern Bento UI Layouts)",
        "reference_pins": [
            {
                "pin_id": "1008595279052523159",
                "title": "Software AI SaaS Bento Feature Grid",
                "pin_url": "https://www.pinterest.com/pin/1008595279052523159/",
                "image_url": "https://raw.githubusercontent.com/aniketb1rla/pinterestrepo/main/dataset/tech-saas/1008595279052523159.jpg",
            },
            {
                "pin_id": "1008595279057793902",
                "title": "Modern App Launch Bento Showcase",
                "pin_url": "https://www.pinterest.com/pin/1008595279057793902/",
                "image_url": "https://raw.githubusercontent.com/aniketb1rla/pinterestrepo/main/dataset/tech-saas/1008595279057793902.jpg",
            },
        ],
        "colors": {
            "background_tone": "#030712",
            "primary_accent": "#6366f1",
            "secondary_accent": "#38bdf8",
            "text_color": "#f9fafb",
            "luminance_mode": "dark",
            "temperature": "cool",
            "palette": ["#030712", "#111827", "#6366f1", "#38bdf8", "#f9fafb"],
            "mood": "Intelligent, streamlined, cutting-edge, engineered precision",
        },
        "typography": {
            "headline_font_style": "Geometric Technical Sans or Modern Tech Grotesk",
            "body_font_style": "Clean Tech Sans",
            "recommended_headline_fonts": ["Plus Jakarta Sans", "Inter", "Cabinet Grotesk"],
            "recommended_body_fonts": ["Inter", "Plus Jakarta Sans"],
            "treatment_effects": "High-contrast clean headings with micro-tag badges",
            "hierarchy_order": "Top headline -> Bento Grid Modules -> High-Conversion CTA",
        },
        "layout": {
            "layout_type": "Modular 3-Cell Bento Architecture",
            "composition": "Structured bento grid arrangement: primary hero card displaying product/screen, secondary metric card with growth percentage, tertiary speed pill.",
            "hierarchy": "Core Hook -> Bento System -> Conversion CTA",
            "aspect_ratio_code": "4:5",
            "spacing_density": "Precision 12px grid gaps with rounded container cards",
        },
        "lighting": "Subtle top-down studio ambient glow, soft linear card borders with translucent glassmorphic gradient.",
        "decorative_elements": [
            "Translucent glassmorphic bento cards with fine borders",
            "Subtle glowing gradient halo",
            "Crisp data metric badges",
        ],
        "meta_ad_rules": "Strict upright screens, zero inverted UI, crisp typography.",
    },

    "appetite_hero": {
        "id": "appetite_hero",
        "template_id": "appetite_hero",
        "name": "Sensory Appetite & Dynamic Action",
        "industry_slug": "food-beverage",
        "industry_label": "Culinary & Beverage",
        "movement": "Sensory Tabletop & Dynamic Kinetic Action",
        "summary": "Mouth-watering sensory close-up with warm rustic tabletop, dynamic pour or glaze, appetizing depth of field and warm lighting.",
        "inspiration_source": "Pinterest Design Atlas (Gourmet Food & Beverage Still Life)",
        "reference_pins": [
            {
                "pin_id": "1009580441482030426",
                "title": "Artisanal Cafe Tabletop & Roast Coffee Post",
                "pin_url": "https://www.pinterest.com/pin/1009580441482030426/",
                "image_url": "https://raw.githubusercontent.com/aniketb1rla/pinterestrepo/main/dataset/food-beverage/1009580441482030426.jpg",
            },
            {
                "pin_id": "1025483777685182991",
                "title": "Chilled Beverage Splash Action Creative",
                "pin_url": "https://www.pinterest.com/pin/1025483777685182991/",
                "image_url": "https://raw.githubusercontent.com/aniketb1rla/pinterestrepo/main/dataset/food-beverage/1025483777685182991.jpg",
            },
        ],
        "colors": {
            "background_tone": "#271710",
            "primary_accent": "#f97316",
            "secondary_accent": "#fbbf24",
            "text_color": "#ffffff",
            "luminance_mode": "dark",
            "temperature": "warm",
            "palette": ["#271710", "#f97316", "#fbbf24", "#78350f", "#fef3c7"],
            "mood": "Rich, indulgent, comforting, mouth-watering, artisanal warmth",
        },
        "typography": {
            "headline_font_style": "Sensory Serif or Bold Friendly Display",
            "body_font_style": "Warm Rounded Sans",
            "recommended_headline_fonts": ["Fraunces", "Syne", "Playfair Display"],
            "recommended_body_fonts": ["Plus Jakarta Sans", "Inter"],
            "treatment_effects": "Warm organic typography with golden accent glow",
            "hierarchy_order": "Top appetizing hook -> Hero dish / bottle close-up -> Tactile CTA pill",
        },
        "layout": {
            "layout_type": "Artisanal Tabletop Close-Up",
            "composition": "Hero culinary item or bottle centered on dark rustic wood or textured slate, accompanied by raw ingredients and shallow focus.",
            "hierarchy": "Sensory Headline -> Mouthwatering Hero Focus -> Bottom CTA",
            "aspect_ratio_code": "4:5",
            "spacing_density": "Warm, intimate tabletop density",
        },
        "lighting": "Warm side window backlight highlighting steam, glaze, or condensation droplets with rich golden highlights.",
        "decorative_elements": [
            "Coarse sea salt crystals or raw cacao nibs scattered naturally",
            "Warm rustic dark timber or slate surface",
            "Delicate wisp of steam or glistening glaze highlight",
        ],
        "meta_ad_rules": "Natural appetizing color temperature, zero plastic looking food.",
    },

    "ecommerce_d2c_studio_pedestal": {
        "id": "ecommerce_d2c_studio_pedestal",
        "template_id": "ecommerce_d2c_studio_pedestal",
        "name": "Refined Studio Plinth & Minimalist Luxury",
        "industry_slug": "ecommerce-retail",
        "industry_label": "D2C Studio & Minimalist Luxury",
        "movement": "Modern Minimalist Commercial Still Life",
        "summary": "Clean sculptural plinth, controlled studio rim lighting, refined negative space, high-conversion mobile readability.",
        "inspiration_source": "Pinterest Design Atlas (D2C Product Launch Plinths)",
        "reference_pins": [
            {
                "pin_id": "1006624954233458422",
                "title": "Your Ad Has 3 Seconds: Meta Ads Creative Tip",
                "pin_url": "https://www.pinterest.com/pin/1006624954233458422/",
                "image_url": "https://raw.githubusercontent.com/aniketb1rla/pinterestrepo/main/dataset/ecommerce-retail/1006624954233458422.jpg",
            },
            {
                "pin_id": "1070941986408981426",
                "title": "High-Converting D2C Product Launch Plinth",
                "pin_url": "https://www.pinterest.com/pin/1070941986408981426/",
                "image_url": "https://raw.githubusercontent.com/aniketb1rla/pinterestrepo/main/dataset/ecommerce-retail/1070941986408981426.jpg",
            },
        ],
        "colors": {
            "background_tone": "#f1f5f9",
            "primary_accent": "#0ea5e9",
            "secondary_accent": "#0f172a",
            "text_color": "#0f172a",
            "luminance_mode": "light",
            "temperature": "neutral",
            "palette": ["#f1f5f9", "#0f172a", "#0ea5e9", "#cbd5e1", "#334155"],
            "mood": "Pure, premium, uncluttered, focused, high-conversion directness",
        },
        "typography": {
            "headline_font_style": "Clean Contemporary Display Sans",
            "body_font_style": "Geometric Sans",
            "recommended_headline_fonts": ["Plus Jakarta Sans", "Cabinet Grotesk", "Outfit"],
            "recommended_body_fonts": ["Plus Jakarta Sans", "Inter"],
            "treatment_effects": "Crisp sentence-case typography with balanced kerning",
            "hierarchy_order": "Top clean headline -> Central hero plinth -> High-contrast CTA pill",
        },
        "layout": {
            "layout_type": "Centered Hero Pedestal with Generous Negative Space",
            "composition": "The hero product stands firmly on a sculptural matte pedestal in the center of the frame, surrounded by 30% clean negative space.",
            "hierarchy": "Value Hook -> Central Hero Product -> High-Contrast CTA Button",
            "aspect_ratio_code": "4:5",
            "spacing_density": "Uncluttered mobile-first negative space",
        },
        "lighting": "Sculpted 3-point studio lighting with crisp key light, soft fill, and subtle rim light separating the product from the seamless background.",
        "decorative_elements": [
            "Geometric matte sculptural pedestal",
            "Clean soft gradient floor reflection",
            "Directional soft contact shadow",
        ],
        "meta_ad_rules": "Strictly 3 text elements, maximum clarity on mobile screens.",
    },
}

# Register diverse preset into CREATIVE_PRESETS
CREATIVE_PRESETS[DIVERSE_PRESET_ID] = DIVERSE_PRESET


# ---------------------------------------------------------------------------
# Resolver & Query Functions
# ---------------------------------------------------------------------------

def get_all_presets() -> List[Dict[str, Any]]:
    """Returns all available creative reference presets, with Diverse Creative Mix as first option."""
    # Ensure diverse is first, then unique presets
    seen = {DIVERSE_PRESET_ID}
    ordered = [DIVERSE_PRESET]
    for p in CREATIVE_PRESETS.values():
        if p["id"] not in seen:
            seen.add(p["id"])
            ordered.append(p)
    return ordered


def get_preset_by_id(preset_id: str) -> Optional[Dict[str, Any]]:
    """Fetches a specific creative preset or static theme by ID."""
    if not preset_id:
        return None
    if preset_id == DIVERSE_PRESET_ID:
        return DIVERSE_PRESET
    if preset_id in STATIC_THEMES:
        return STATIC_THEMES[preset_id]
    return CREATIVE_PRESETS.get(preset_id)


def get_theme_by_id(theme_id: str) -> Optional[Dict[str, Any]]:
    """Fetches a static creative theme by ID."""
    return STATIC_THEMES.get(theme_id) or CREATIVE_PRESETS.get(theme_id)


def get_diverse_theme_for_brief(
    framework: str,
    category: str = "",
    business_type: str = "",
    index: int = 0,
    chosen_tmpl: str = "",
) -> Dict[str, Any]:
    """
    Intelligently assigns a contrasting, purpose-built static creative theme
    for a brief to ensure campaign-wide visual variety across Meta feeds.
    Matches marketing framework to aesthetic theme, while rotating contrasting archetypes
    so adjacent briefs in a batch never repeat the same layout or set design.
    """
    fw = (framework or "").lower().strip()
    cat = (category or "").lower().strip()
    
    # 1. If LLM Art Director selected a specific valid theme, respect it
    if chosen_tmpl and chosen_tmpl not in ("chaos_grid", "metaphor_object", "consolidation", "product_moment", "control_panel", "levitation_device", "diverse"):
        if chosen_tmpl in STATIC_THEMES:
            return STATIC_THEMES[chosen_tmpl]
        if chosen_tmpl in CREATIVE_PRESETS:
            return CREATIVE_PRESETS[chosen_tmpl]

    # 2. Framework-driven primary theme mappings
    framework_theme_map = {
        "us_vs_them": "split_contrast",
        "problem_solution": "split_contrast",
        "before_after": "split_contrast",
        "cost_comparison": "split_contrast",
        "alternative_comparison": "split_contrast",
        
        "feature_callout": "macro_texture",
        "ingredient_spotlight": "macro_texture",
        "material_craft": "macro_texture",
        "formula_breakdown": "macro_texture",
        "craft_detail": "macro_texture",
        
        "lifestyle_hero": "model_lifestyle",
        "founder_story": "model_lifestyle",
        "in_situ": "model_lifestyle",
        "daily_routine": "model_lifestyle",
        "social_validation": "model_lifestyle",
        
        "sensory_immersion": "elemental_set",
        "freshness_ritual": "elemental_set",
        "natural_origin": "elemental_set",
        "refresh": "elemental_set",
        "pure_elements": "elemental_set",
        
        "social_proof": "marketing_bold_statement",
        "bold_claim": "marketing_bold_statement",
        "provocative_question": "marketing_bold_statement",
        "press_quote": "marketing_bold_statement",
        "paradox": "marketing_bold_statement",
        
        "bento_features": "saas_bento_grid",
        "tech_architecture": "saas_bento_grid",
        "workflow_speed": "saas_bento_grid",
        "ecosystem": "saas_bento_grid",
        "dashboard_analytics": "saas_bento_grid",
        
        "golden_hour": "outdoor_light",
        "architectural_space": "outdoor_light",
        
        "appetite_appeal": "appetite_hero",
        "culinary_craft": "appetite_hero",
        "taste_hook": "appetite_hero",
    }

    # 3. Industry-specific overrides for certain frameworks
    is_food = any(k in cat for k in ("food", "beverage", "drink", "coffee", "culinary", "restaurant"))
    is_beauty = any(k in cat for k in ("beauty", "skincare", "cosmetic", "derma", "serum", "clinical"))
    is_tech = any(k in cat or k in business_type.lower() for k in ("saas", "tech", "software", "app", "b2b"))

    matched_id = framework_theme_map.get(fw)
    
    if matched_id == "macro_texture" and is_beauty and (index % 2 == 1):
        matched_id = "beauty_clinical_ordinary"
    elif matched_id == "elemental_set" and is_food:
        matched_id = "appetite_hero"
    elif not matched_id and is_tech:
        matched_id = "saas_bento_grid"

    # 4. If framework did not match directly, or to guarantee diversity across batches:
    # Rotate through the core contrasting sequence modulated by index
    DIVERSITY_ROTATION = [
        "split_contrast",
        "macro_texture",
        "model_lifestyle",
        "elemental_set",
        "marketing_bold_statement",
        "outdoor_light",
        "beauty_clinical_ordinary" if is_beauty else ("appetite_hero" if is_food else "saas_bento_grid"),
        "ecommerce_d2c_studio_pedestal",
    ]

    if not matched_id:
        matched_id = DIVERSITY_ROTATION[index % len(DIVERSITY_ROTATION)]

    theme = STATIC_THEMES.get(matched_id) or CREATIVE_PRESETS.get(matched_id) or STATIC_THEMES["split_contrast"]
    return theme


def get_presets_for_industry(industry_or_category: str) -> List[Dict[str, Any]]:
    """Returns presets matching a specific industry slug or brand category keyword."""
    cat_clean = (industry_or_category or "").strip().lower()
    
    # Direct match on industry slug
    matches = [p for p in CREATIVE_PRESETS.values() if p["industry_slug"] == cat_clean]
    if matches:
        return matches

    # Keyword match through INDUSTRY_CATEGORY_MAP
    best_slug = None
    for slug, keywords in INDUSTRY_CATEGORY_MAP.items():
        if slug in cat_clean or any(k in cat_clean for k in keywords):
            best_slug = slug
            break
            
    if best_slug:
        return [p for p in CREATIVE_PRESETS.values() if p["industry_slug"] == best_slug]

    return list(CREATIVE_PRESETS.values())


def detect_best_preset_for_brand(
    brand_category: str = "",
    business_type: str = "",
    product_name: str = "",
    brand_name: str = "",
) -> Dict[str, Any]:
    """
    Intelligently scores and detects the single best creative reference preset
    for a brand based on its category, business type, and naming.
    """
    full_text = f" {brand_category} {business_type} {product_name} {brand_name} ".lower()

    # 1. Direct keyword scanning against category map
    best_slug = None
    best_score = 0
    for slug, keywords in INDUSTRY_CATEGORY_MAP.items():
        score = 0
        if slug in full_text:
            score += 5
        for kw in keywords:
            pattern = r"(?:\b|_)" + re.escape(kw) + r"(?:\b|_)"
            if re.search(pattern, full_text):
                score += 2
        if score > best_score:
            best_score = score
            best_slug = slug

    # If an industry was matched, pick the premier preset for that industry
    if best_slug:
        ind_presets = [p for p in CREATIVE_PRESETS.values() if p["industry_slug"] == best_slug]
        if ind_presets:
            return ind_presets[0]

    # Fallback based on physical product vs digital service
    if "physical" in business_type.lower() or "product" in business_type.lower() or not business_type:
        return CREATIVE_PRESETS["ecommerce_d2c_studio_pedestal"]
    return CREATIVE_PRESETS["saas_bento_grid"]


# ---------------------------------------------------------------------------
# High-End Prompt Builder using Creative Library Presets
# ---------------------------------------------------------------------------

def build_preset_creative_prompt(
    preset_id: str,
    *,
    brand_name: str,
    product_name: str,
    headline: str,
    cta: str = "Shop Now",
    aspect_ratio: str = "4:5",
    product_visual_description: str = "",
    color_palette: str = "",
    custom_directive: Optional[str] = None,
    has_product_ref: bool = False,
    has_logo: bool = False,
    setting: str = "",
    talent: str = "",
    scene_hint: str = "",
    brand_kit: Optional[Dict[str, Any]] = None,
) -> str:
    """
    Constructs an award-winning, senior-graphic-designer-grade commercial Meta ad prompt
    for Gemini Nano Banana 2.1 anchored in the exact design DNA of the selected creative preset.
    Follows core design principles: Visual Hierarchy, 60-30-10 Color Theory, Golden Ratio
    composition, strict typographic hierarchy, tactile materiality, and anti-AI-slop guardrails.
    """
    preset = get_preset_by_id(preset_id) or CREATIVE_PRESETS.get("ecommerce_d2c_studio_pedestal") or CREATIVE_PRESETS["beauty_editorial_rhode"]
    
    brand = (brand_name or "Brand").strip()
    product = (product_name or "the featured product").strip()
    headline_clean = (headline or "Discover Excellence").strip()
    cta_clean = (cta or "Shop Now").strip()

    # Determine ratio framing & negative space rules
    ratio_instructions = {
        "1:1": "Square 1:1 master grid. Centered visual equilibrium, headline across top 20%, hero subject commanding central 55-60%, 8% perimeter margin safety buffer, brand wordmark bottom-left, CTA pill bottom-right.",
        "4:5": "Vertical 4:5 Meta Mobile Feed master. High thumb-stopping power, headline positioned in upper 18% with calm negative space, hero subject claiming central 58-62%, lower 14% reserved for brand mark and conversion pill CTA, 8% outer boundary margin.",
        "9:16": "Full-bleed 9:16 vertical Stories & Reels master. Expansive environmental canvas with safe-zone margin: top 14% and bottom 20% clear of UI overlays, hero centered, headline upper-third.",
        "16:9": "Horizontal 16:9 landscape master. 40/60 asymmetric golden ratio split: typography and CTA anchored in left 40% column; hero subject and set occupying right 60% with generous negative space."
    }.get(aspect_ratio, "Vertical 4:5 Meta Mobile Feed master.")

    # Chromatic palette tokens (60-30-10 Color Theory)
    preset_colors = preset.get("colors") or {}
    bg_tone = preset_colors.get("background_tone", "#f8fafc")
    prim_accent = preset_colors.get("primary_accent", "#2563eb")
    sec_accent = preset_colors.get("secondary_accent", "#0f172a")
    mood = preset_colors.get("mood", "Clean, modern, high-contrast commercial aesthetic")
    palette_str = ", ".join(preset_colors.get("palette", ["#f8fafc", "#0f172a", "#2563eb"])[:5])

    # Harmonize with brand kit if provided
    if brand_kit:
        if brand_kit.get("accent_hex"):
            prim_accent = brand_kit["accent_hex"]
        if brand_kit.get("primary_hex"):
            sec_accent = brand_kit["primary_hex"]
        if brand_kit.get("background_hex"):
            bg_tone = brand_kit["background_hex"]
        if brand_kit.get("visual_mood"):
            mood = f"{brand_kit['visual_mood']}. {mood}"

    # Typographic craft
    typo = preset.get("typography") or {}
    headline_style = typo.get("headline_font_style", "High-Contrast Sans-Serif")
    rec_fonts = ", ".join(typo.get("recommended_headline_fonts", ["Plus Jakarta Sans", "Inter"])[:3])
    rec_body_fonts = ", ".join(typo.get("recommended_body_fonts", ["Plus Jakarta Sans", "Inter"])[:2])
    treatment = typo.get("treatment_effects", "Balanced kerning with high optical contrast")
    hierarchy_order = typo.get("hierarchy_order", "Top Headline -> Hero Center -> Pill CTA")

    # Decor & Lighting
    decor = ", ".join(preset.get("decorative_elements") or [])
    lighting = preset.get("lighting", "Studio key light with directional contact shadow")
    movement = preset.get("movement", "High-Contrast Commercial Aesthetic")
    summary = preset.get("summary", "Commercial ad creative")

    # Dynamic set composition: allow scene_hint to guide composition rather than hardcoding plinths
    preset_comp = preset.get("layout", {}).get("composition", "Clean centered composition with hero subject commanding visual weight.")
    layout_type = preset.get("layout", {}).get("layout_type", "Commercial Layout")
    if scene_hint:
        composition_spec = f"{scene_hint.strip().rstrip('.')}. Architectural framing inspired by {layout_type}."
        props_spec = f"Authentic props supporting the scene ({scene_hint.strip()}), accented by {decor}." if decor else f"Authentic props supporting the scene: {scene_hint.strip()}."
    else:
        composition_spec = preset_comp
        props_spec = decor

    # Product reference lock instructions
    product_lock_section = ""
    if has_product_ref:
        product_lock_section = (
            "HERO SUBJECT (PRODUCT LOCK - IMAGE 1):\n"
            f"- IMAGE 1 depicts the authentic {product} by {brand}.\n"
            "- Reproduce this EXACT product with absolute commercial fidelity: identical packaging silhouette, "
            "cap/closure, materials, surface finish, color tone, and physical label graphics.\n"
            "- Do NOT redesign, re-label, warp, or invent packaging details. Keep all brand labeling crisp and physically accurate."
        )
    elif product_visual_description:
        product_lock_section = f"HERO SUBJECT: {product}. Appearance & physical form: {product_visual_description}."
    else:
        product_lock_section = f"HERO SUBJECT: {product} for {brand}. Grounded, premium physical execution."

    # Logo instruction
    if has_logo:
        logo_line = f"Brand Logo: Render the authentic {brand} logo from IMAGE 2 small, crisp, and optically balanced in the top or bottom corner."
    else:
        logo_line = f'Brand Wordmark: "{brand}" rendered in clean, refined minimalist typography, optically tracked.'

    # Scene direction and custom directive
    scene_section = f"\nSPECIFIC SCENE ART DIRECTION: {scene_hint}" if scene_hint else ""
    setting_section = f"\nENVIRONMENT CONTEXT: {setting}" if setting else ""
    talent_section = f"\nTALENT CASTING: {talent} (natural, unforced expression, authentic skin texture with real pores and micro-details. Not a celebrity, actor, or glamorous influencer; zero airbrushed influencer tropes)" if talent else ""
    directive_section = f"\nEXECUTIVE CREATIVE DIRECTIVE: {custom_directive}" if custom_directive else ""

    prompt = f"""[ROLE: Senior Executive Art Director & Master Commercial Graphic Designer]
Design an award-winning Meta feed ad creative for {brand} ({preset['industry_label']}), adhering strictly to master graphic design principles (Visual Hierarchy, 60-30-10 Color Theory, Golden Ratio Spacing, and Typographic Precision).

DESIGN DNA & INSPIRATION:
- Movement / Aesthetic: {movement}
- Curated Reference Source: {preset['inspiration_source']}
- Design Essence: {summary}

1. VISUAL HIERARCHY & COMPOSITIONAL ARCHITECTURE:
- Canvas Format: Meta {aspect_ratio} ({ratio_instructions})
- Focal Anchor: The hero subject commands 58-62% of visual weight as the primary optical entry point.
- Optical Flow: Clear, intentional reading hierarchy ({hierarchy_order}).
- Negative Space: Preserve 25-35% uncluttered, breathable negative space around the hero to ensure instant thumb-stopping clarity on mobile feeds.
- Boundary Safety: Maintain a minimum 8% clean perimeter margin free of critical text or subject edges.

2. HERO SUBJECT & PLACEMENT:
{product_lock_section}
- Physical Grounding: Ground the subject firmly with realistic contact shadows and directional ambient occlusion. No floating or ungrounded objects.

3. TYPOGRAPHIC CRAFT & STRICT META 3-ELEMENT BUDGET:
Render EXACTLY THREE text elements in the pixels—no secondary subheadings, no bullet points, no fake badges:
  1. {logo_line}
  2. HEADLINE: "{headline_clean}"
     - Typographic Style: {headline_style} (inspired by {rec_fonts})
     - Typographic Treatment: {treatment}. High optical contrast against background, perfect kerning and leading, zero word wrapping artifacts.
  3. CALL TO ACTION (CTA): "{cta_clean}"
     - CTA Treatment: High-contrast tactile pill capsule button with clean rounded geometry, crisp centered lettering in {rec_body_fonts}.
  * Strict Rule: Spell each quoted string exactly. Do not render any additional text, numbers, or ratings in the final artwork.

4. STUDIO SET DESIGN & TEXTURES:
- Architectural Composition: {composition_spec}
- Material Finishes & Props: {props_spec}
- Tactile Textures: Authentic real-world physical materials (e.g. textured stone, brushed metal, frosted glass, organic caustics, or paper grain).{scene_section}{setting_section}{talent_section}

5. LIGHTING & 60-30-10 CHROMATIC HARMONY:
- Studio Lighting: {lighting}
- 60% Dominant Canvas Foundation: {bg_tone} creating a calm, cohesive environmental backdrop.
- 30% Structural Secondary Tones: {sec_accent} and tonal gradations supporting composition and depth.
- 10% High-Contrast Accent Pop: {prim_accent} strictly focused on the CTA pill and brand mark for immediate conversion pull.
- Color Mood: {mood} (Swatches: {palette_str}).{directive_section}

6. ANTI-AI SLOP GUARDRAILS:
- STRICTLY FORBIDDEN: Levitating geometric cubes or spheres, generic purple/cyan cyber-glows, plastic airbrushed skin, extra fingers or deformed anatomy, duplicate products, muddy compositions, and illegible pseudo-text."""

    return prompt.strip()
