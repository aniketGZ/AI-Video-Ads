import os
import uuid
import json
import logging
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
try:
    from PIL import Image, ImageDraw, ImageFont
    HAS_PIL = True
except ImportError:
    Image = None
    ImageDraw = None
    ImageFont = None
    HAS_PIL = False

logger = logging.getLogger(__name__)

# Pydantic Schemas for Meta Direct-Response Creative Blueprints
class MetaCreativeBlueprint(BaseModel):
    creative_id: int
    framework_key: str  # "problem_solution", "feature_callout", "social_proof", "us_vs_them", "lifestyle_hero"
    framework_name: str
    target_emotion: str
    target_audience_resonance: str
    hook_badge: str
    headline: str
    subheadline: str
    primary_text: str
    cta: str
    callout_points: List[str]
    comparison_theirs: Optional[str] = None
    comparison_ours: Optional[str] = None
    testimonial_quote: Optional[str] = None
    testimonial_author: Optional[str] = None
    visual_prompt: str
    layout_style: str

class MetaCreativeSuiteRequest(BaseModel):
    brand_name: str
    product_name: str
    product_category: str
    target_audience_persona: str
    visual_style: str
    product_visual_description: Optional[str] = None
    key_benefits: Optional[List[str]] = None
    color_palette: Optional[str] = None
    aspect_ratio: str = "4:5"
    engine: str = "qwen"
    product_image_path: Optional[str] = None
    custom_directive: Optional[str] = None
    creatives_to_render: Optional[List[int]] = None

# Typography Helper (Cross-Platform: Windows, Linux/Render.com)
def get_font(size: int, bold: bool = True):
    """Retrieve optimal TrueType font across Windows & Linux with graceful fallback."""
    if not HAS_PIL or not ImageFont:
        return None

    candidates = []

    # Windows candidate font paths
    win_names = (
        ["segoeuib.ttf", "arialbd.ttf", "calibrib.ttf"]
        if bold
        else ["segoeui.ttf", "arial.ttf", "calibri.ttf"]
    )
    for name in win_names:
        candidates.append(os.path.join("C:/Windows/Fonts", name))

    # Linux (Ubuntu/Debian on Render.com) candidate font paths
    linux_paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf" if bold else "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
        "/usr/share/fonts/TTF/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/TTF/DejaVuSans.ttf",
    ]
    candidates.extend(linux_paths)

    for path in candidates:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                pass

    # Generic family name lookup with Pillow
    generic_names = (
        ["DejaVuSans-Bold", "Arial-Bold", "Helvetica-Bold", "FreeSans-Bold"]
        if bold
        else ["DejaVuSans", "Arial", "Helvetica", "FreeSans"]
    )
    for name in generic_names:
        try:
            return ImageFont.truetype(name, size)
        except Exception:
            pass

    try:
        return ImageFont.load_default()
    except Exception:
        return None

def wrap_text(text: str, font: ImageFont.FreeTypeFont, max_width: int, draw: ImageDraw.ImageDraw) -> List[str]:
    """Wrap text to fit within a specified pixel width."""
    if not text:
        return []
    words = text.split()
    lines = []
    current_line = []
    for word in words:
        current_line.append(word)
        line_str = " ".join(current_line)
        bbox = draw.textbbox((0, 0), line_str, font=font)
        w = bbox[2] - bbox[0]
        if w > max_width:
            if len(current_line) > 1:
                current_line.pop()
                lines.append(" ".join(current_line))
                current_line = [word]
            else:
                lines.append(line_str)
                current_line = []
    if current_line:
        lines.append(" ".join(current_line))
    return lines

# Native In-Image Typography & Layout Prompt Builder for Qwen & Nano Banana Pro
def build_native_in_image_ad_prompt(
    blueprint: Dict[str, Any],
    brand_name: str,
    product_name: str,
    product_category: str = "",
    target_audience_persona: str = "",
    aspect_ratio: str = "4:5",
    product_visual_description: str = "",
    color_palette: str = "",
    custom_directive: Optional[str] = None,
) -> str:
    """
    Constructs an ultra-high-converting direct-response prompt for Qwen-Image-2.1
    and Gemini Nano Banana Pro to render commercial typography, branding badges,
    headlines, callouts, and layout DIRECTLY inside the creative image pixels.
    """
    brand = (brand_name or "BRAND").strip()
    product = (product_name or "Product").strip()
    category = (product_category or "Consumer Goods").strip()
    persona = (target_audience_persona or "Modern consumers").strip()

    f_key = blueprint.get("framework_key", "problem_solution")
    hook_badge = blueprint.get("hook_badge", "SPECIAL OFFER").strip()
    headline = blueprint.get("headline", f"Upgrade to {product}").strip()
    subheadline = blueprint.get("subheadline", "").strip()
    cta = blueprint.get("cta", "Shop Now").strip()
    callouts = blueprint.get("callout_points", [])

    scene_base = blueprint.get("visual_prompt", "").strip()
    scene_base = (
        scene_base.replace("Do not put text in prompt.", "")
        .replace("Do NOT include text, words, or watermarks in the prompt.", "")
        .strip()
    )

    ratio_desc = "vertical 4:5 Instagram & Facebook feed" if aspect_ratio == "4:5" else (
        "square 1:1 feed" if aspect_ratio == "1:1" else (
            "full-screen 9:16 story and reel" if aspect_ratio == "9:16" else f"{aspect_ratio} landscape"
        )
    )

    framework_elements = []
    if f_key == "social_proof":
        quote = blueprint.get("testimonial_quote", "The results blew me away within days.")
        author = blueprint.get("testimonial_author", "Verified Buyer")
        framework_elements.append(
            f'• Social Proof Graphic: In the lower third, render a stylized graphic review bubble with 5 golden stars "★★★★★", '
            f'customer headline quote reading "{quote}", and verified author badge reading "— {author} ✓".'
        )
    elif f_key == "us_vs_them":
        theirs = blueprint.get("comparison_theirs", "Harsh fillers & slow results")
        ours = blueprint.get("comparison_ours", "100% pure active performance")
        framework_elements.append(
            f'• Comparison Matrix Layout: A sleek side-by-side graphic comparison panel. '
            f'Left column with muted red pill reading "✕ TRADITIONAL: {theirs}". '
            f'Right column with radiant emerald badge reading "✓ {brand.upper()}: {ours}".'
        )
    elif f_key == "feature_callout":
        callout_lines = [f'"{c}"' for c in callouts[:3]] if callouts else ['"Clean Formula"', '"Instant Impact"', '"Proven Results"']
        pills_str = " and ".join(callout_lines)
        framework_elements.append(
            f'• Feature Callout Matrix: Render 3 sleek floating graphic feature badges with checkmarks highlighting {pills_str}, '
            f'arranged cleanly with subtle frosted glass containers pointing toward key product details.'
        )
    else:
        callout_lines = [f'"{c}"' for c in callouts[:2]] if callouts else ['"Instant Visible Results"', '"Guaranteed Quality"']
        pills_str = " and ".join(callout_lines)
        framework_elements.append(
            f'• Value Props Badges: Floating graphic trust pills reading {pills_str} with radiant accent styling.'
        )

    framework_desc = "\n".join(framework_elements)
    colors_desc = f"Color palette emphasizing {color_palette}." if color_palette else "Cohesive brand color palette with premium contrast."
    details_desc = f"Physical product details: {product_visual_description}." if product_visual_description else ""

    prompt = (
        f"A masterfully designed, award-winning direct-response Meta advertisement creative in {ratio_desc} format. "
        f"Professional commercial graphic design combined seamlessly with ultra-photorealistic product photography.\n\n"
        f"HERO PRODUCT SCENE:\n"
        f"Centerstage hero product shot of {product} by {brand} ({category}). {details_desc} "
        f"{scene_base or f'Studio lighting, dramatic rim light, crisp reflections, shallow depth of field, tailored for {persona}.'} "
        f"{colors_desc}\n\n"
        f"IN-IMAGE TYPOGRAPHY & GRAPHIC LAYOUT (RENDER ALL TEXT DIRECTLY IN THE CREATIVE PIXELS):\n"
        f'• Top Header: At the top left, a crisp minimalist brand logo reading "{brand.upper()}", and at top right an official badge reading "OFFICIAL STORE ✓".\n'
        f'• Hook Eyebrow: Above the main headline, a bold graphic pill badge reading "{hook_badge.upper()}".\n'
        f'• Main Headline: Large, bold, high-contrast commercial typography prominently reading "{headline}". The headline letters must be ultra-sharp, large, perfectly readable, and styled with subtle drop shadows against the background for effortless contrast.\n'
    )
    if subheadline:
        prompt += f'• Subheadline: Supporting clean subhead reading "{subheadline}" positioned below the main headline.\n'

    if framework_desc:
        prompt += f"{framework_desc}\n"

    prompt += (
        f'• Bottom Call-To-Action: At the bottom right, a bold graphic CTA button reading "{cta.upper()} ➔" with vibrant contrast. '
        f'At the bottom left, trust text reading "30-DAY RISK-FREE TRIAL".\n\n'
        f"DESIGN QUALITY & TYPOGRAPHY RULES:\n"
        f"All text, typography, badges, and buttons must be generated directly inside the image by the model with flawless spelling, vector-sharp letterforms, high contrast against backgrounds, proper kerning, and editorial hierarchy. "
        f"The visual composition must feel like an authentic, high-converting Meta feed ad created by a top tier agency. Masterpiece commercial layout, 8K ultra-sharp details."
    )

    if custom_directive and custom_directive.strip():
        prompt += f"\nCustom directive: {custom_directive.strip()}."

    return prompt

# Creative Strategy Generator from URL & Audience Research
def generate_meta_creative_blueprints(
    brand_data: Dict[str, Any],
    client: Any = None
) -> List[Dict[str, Any]]:
    """
    Synthesizes at least 5 distinct high-converting Meta Direct Response creative blueprints
    tailored to the brand's URL analysis, product details, and target audience persona.
    """
    brand_name = brand_data.get("brand_name", "Brand")
    product_name = brand_data.get("product_name", "Product")
    category = brand_data.get("product_category", "Consumer Goods")
    persona = brand_data.get("target_audience_persona", "Daily high performers")
    visual_style = brand_data.get("visual_style", "CINEMATIC_PREMIUM")
    product_desc = brand_data.get("product_visual_description", "")
    key_benefits = brand_data.get("key_benefits", [])
    benefits_str = ", ".join(key_benefits) if key_benefits else "Premium quality, fast results, proven satisfaction"

    blueprints = []

    if client:
        try:
            from google.genai import types
            strategy_prompt = (
                f"You are a legendary Direct Response Creative Director for Meta Ads (Facebook & Instagram).\n"
                f"Analyze this brand data derived from website scraping:\n"
                f"- Brand: {brand_name}\n"
                f"- Product: {product_name} ({category})\n"
                f"- Target Audience Persona: {persona}\n"
                f"- Visual Style: {visual_style}\n"
                f"- Product Physical Details: {product_desc}\n"
                f"- Key Benefits: {benefits_str}\n\n"
                "Create EXACTLY 5 distinct, high-converting Meta Ad creative blueprints corresponding to these 5 proven frameworks:\n"
                "1. Framework 1: 'problem_solution' (The Problem-Agitation-Solution Contrast Hero)\n"
                "2. Framework 2: 'feature_callout' (Deconstructed Features & Ingredients Callout Matrix)\n"
                "3. Framework 3: 'social_proof' (5-Star Social Proof & Verified Testimonial)\n"
                "4. Framework 4: 'us_vs_them' (Us vs. Them Side-by-Side Comparison Matrix)\n"
                "5. Framework 5: 'lifestyle_hero' (Aspirational Lifestyle & Result Transformation)\n\n"
                "For each of the 5 creatives, provide:\n"
                "- creative_id (1 to 5)\n"
                "- framework_key (one of the 5 keys above)\n"
                "- framework_name (title of the framework)\n"
                "- target_emotion (core psychological trigger, e.g. 'Relief & Urgency')\n"
                "- target_audience_resonance (1-2 sentences explaining why this communicates directly to this persona)\n"
                "- hook_badge (short punchy badge e.g. '★ VOTED #1 IN 2026', '★★★★★ 4.9/5 RATED', 'TIRED OF [PAIN]?')\n"
                "- headline (5-8 words punchy high-CTR hook headline)\n"
                "- subheadline (1 concise sentence expanding benefit)\n"
                "- primary_text (full 2-3 paragraph Meta caption with hook, emotional story, 3 bullet points with emojis, CTA)\n"
                "- cta (standard button text like 'Shop Now', 'Claim 20% Off', 'Try Risk-Free')\n"
                "- callout_points (array of 3 concise benefit bullets)\n"
                "- comparison_theirs (for us_vs_them: what traditional alternatives get wrong)\n"
                "- comparison_ours (for us_vs_them: why our product wins)\n"
                "- testimonial_quote (for social_proof: authentic punchy review)\n"
                "- testimonial_author (for social_proof: e.g. 'Sarah M. · Verified Customer')\n"
                "- visual_prompt (hyper-detailed commercial Meta ad visual & typography layout prompt for AI image generation. Instruct the AI image generator to natively render the product hero shot and in-image typography with crystal-clear spelling in quotation marks: including brand name, hook badge, bold headline, callouts, and CTA button. Specify typography placement, contrast, and layout.)\n"
                "- layout_style (one of 'PROBLEM_SOLUTION_SPLIT', 'CALLOUT_POINTERS', 'TESTIMONIAL_HERO', 'US_VS_THEM_GRID', 'LIFESTYLE_IN_ACTION')\n\n"
                "Return ONLY a valid JSON array of 5 objects matching this specification."
            )

            resp = client.models.generate_content(
                model="gemini-3.6-flash",
                contents=strategy_prompt,
                config=types.GenerateContentConfig(response_mime_type="application/json")
            )
            if resp and resp.text:
                parsed = json.loads(resp.text)
                if isinstance(parsed, list) and len(parsed) >= 5:
                    blueprints = parsed[:5]
                elif isinstance(parsed, dict) and "creatives" in parsed:
                    blueprints = parsed["creatives"][:5]
        except Exception as e:
            logger.warning(f"Gemini creative strategy synthesis failed, falling back to templates: {e}")

    # Fallback / Built-in High-Converting Direct Response Blueprints
    if not blueprints or len(blueprints) < 5:
        b1 = key_benefits[0] if key_benefits and len(key_benefits) > 0 else "Instant visible results"
        b2 = key_benefits[1] if key_benefits and len(key_benefits) > 1 else "100% clean, premium formula"
        b3 = key_benefits[2] if key_benefits and len(key_benefits) > 2 else "Zero compromises or fillers"

        blueprints = [
            {
                "creative_id": 1,
                "framework_key": "problem_solution",
                "framework_name": "Problem-Solution Contrast Hero",
                "target_emotion": "Pain Relief & Urgent Hope",
                "target_audience_resonance": f"Directly calls out the everyday friction faced by {persona} and reveals {product_name} as the radiant antidote.",
                "hook_badge": "TIRED OF THE USUAL COMPROMISE?",
                "headline": f"Say Goodbye to Mediocre {category}",
                "subheadline": f"Engineered by {brand_name} to deliver {b1.lower()} from day one.",
                "primary_text": f"Tired of products that promise everything but deliver nothing?\n\nMeet {product_name} by {brand_name}. Designed specifically for {persona} who refuse to settle.\n\n✓ {b1}\n✓ {b2}\n✓ {b3}\n\nExperience the difference today. Tap below to claim yours.",
                "cta": "Shop Now",
                "callout_points": [b1, b2, b3],
                "comparison_theirs": "Slow results & cheap fillers",
                "comparison_ours": f"{b1} with {b2}",
                "testimonial_quote": f"I was skeptical until I tried {product_name}. The results blew me away.",
                "testimonial_author": "Alex K. · Verified Customer",
                "visual_prompt": (
                    f"Award-winning commercial Meta ad creative for {product_name} by {brand_name}. {product_desc}. "
                    f"Centerstage hero angle on a dark textured obsidian pedestal, radiant golden rim lighting, soft diffuse studio spotlight, crisp metallic reflections. "
                    f"Native in-image typography and layout: Top header brand reading \"{brand_name.upper()}\" with \"OFFICIAL STORE ✓\" badge. "
                    f"Upper eyebrow badge reading \"TIRED OF THE USUAL COMPROMISE?\". "
                    f"Bold high-contrast commercial headline in large modern typography reading \"Say Goodbye to Mediocre {category}\". "
                    f"Subheadline reading \"Engineered by {brand_name} to deliver {b1.lower()} from day one.\". "
                    f"Floating trust badges highlighting \"{b1}\" and \"{b2}\". "
                    f"Bottom right graphic CTA button reading \"SHOP NOW ➔\". "
                    f"Ultra-sharp direct-response advertising graphic design, 8K resolution."
                ),
                "layout_style": "PROBLEM_SOLUTION_SPLIT"
            },
            {
                "creative_id": 2,
                "framework_key": "feature_callout",
                "framework_name": "Deconstructed Feature Callout Matrix",
                "target_emotion": "Intellectual Conviction & Quality Validation",
                "target_audience_resonance": f"Appeals to analytical shoppers in {persona} by highlighting the exact proprietary engineering and ingredients.",
                "hook_badge": "PRECISION ENGINEERED FORMULA",
                "headline": f"What Makes {product_name} Superior",
                "subheadline": f"A deconstructed breakdown of why {brand_name} outperforms the rest.",
                "primary_text": f"What actually goes into {product_name}?\n\nWe stripped away all the unnecessary fluff to engineer pure performance.\n\n🔬 {b1}\n⚡ {b2}\n🛡️ {b3}\n\nSee the full specs and discover why thousands are switching.",
                "cta": "Order Today",
                "callout_points": [b1, b2, b3],
                "comparison_theirs": "Diluted formula with chemical fillers",
                "comparison_ours": "100% active, pure bioavailable ingredients",
                "testimonial_quote": "The ingredient transparency and engineering quality are unmatched.",
                "testimonial_author": "Dr. Marcus T. · Industry Specialist",
                "visual_prompt": (
                    f"Clean minimalist luxury studio Meta ad creative for {product_name} by {brand_name}. {product_desc}. "
                    f"Floating weightlessly in negative space, soft ambient studio gradient background, subtle architectural shadows, precision macro details of packaging and textures. "
                    f"Native in-image typography: Top header with \"{brand_name.upper()}\" and trust stamp. "
                    f"Eyebrow badge reading \"PRECISION ENGINEERED FORMULA\". "
                    f"Large bold headline reading \"What Makes {product_name} Superior\". "
                    f"Three sleek graphic feature callout pointers highlighting \"{b1}\", \"{b2}\", and \"{b3}\". "
                    f"Bottom right high-contrast CTA button reading \"ORDER TODAY ➔\". "
                    f"Apple-style direct-response ad typography and layout, 8K resolution."
                ),
                "layout_style": "CALLOUT_POINTERS"
            },
            {
                "creative_id": 3,
                "framework_key": "social_proof",
                "framework_name": "5-Star Social Proof & Verified Trust",
                "target_emotion": "FOMO & Unshakable Trust",
                "target_audience_resonance": f"Eliminates buyer hesitation for {persona} through authentic social validation and stellar customer ratings.",
                "hook_badge": "★★★★★ 4.9/5 (15,000+ REVIEWS)",
                "headline": f"“I Wish I Had Found {product_name} Sooner”",
                "subheadline": "Over 98% of verified customers reported noticeable improvements.",
                "primary_text": f"Over 15,000+ customers can't be wrong.\n\n“I rarely write reviews, but {product_name} completely changed my daily routine. Within a week, the difference was unmistakable.”\n\n⭐ Rated 4.9/5 across thousands of reviews.\n⭐ 30-Day 100% Money-Back Guarantee.\n\nJoin the community today.",
                "cta": "Claim Yours",
                "callout_points": ["4.9/5 Average Rating", "15,000+ Verified Customers", "30-Day Risk-Free Guarantee"],
                "comparison_theirs": "Unverified claims with zero customer backing",
                "comparison_ours": "15,000+ ecstatic reviews & 30-day money-back guarantee",
                "testimonial_quote": f"Within 3 days of using {product_name}, I was completely hooked. Essential purchase.",
                "testimonial_author": "Sarah M. · Verified Buyer",
                "visual_prompt": (
                    f"Warm editorial lifestyle Meta ad creative for {product_name} by {brand_name}. {product_desc}. "
                    f"Placed gracefully on an elegant marble countertop, soft warm morning window light, shallow depth of field with blurred aspirational interior. "
                    f"Native in-image typography: Top brand header \"{brand_name.upper()}\". "
                    f"Eyebrow badge reading \"★★★★★ 4.9/5 (15,000+ REVIEWS)\". "
                    f"Bold headline reading \"“I Wish I Had Found {product_name} Sooner”\". "
                    f"Lower third graphic review bubble with 5 golden stars \"★★★★★\" and quote reading \"“Within 3 days, I was completely hooked.” — Sarah M. ✓\". "
                    f"Bottom right CTA button reading \"CLAIM YOURS ➔\". "
                    f"Ultra-photorealistic commercial direct-response graphic design, 8K resolution."
                ),
                "layout_style": "TESTIMONIAL_HERO"
            },
            {
                "creative_id": 4,
                "framework_key": "us_vs_them",
                "framework_name": "Us vs. Them Comparison Matrix",
                "target_emotion": "Competitive Clarity & Switching Urgency",
                "target_audience_resonance": f"Clearly illustrates why traditional options fail {persona} and why upgrading to {brand_name} is the obvious choice.",
                "hook_badge": "WHY THOUSANDS ARE SWITCHING",
                "headline": f"Traditional {category} vs. {brand_name}",
                "subheadline": f"See the side-by-side proof before making your next purchase.",
                "primary_text": f"Still relying on traditional {category.lower()}?\n\nHere is what happens when you upgrade to {product_name}:\n\n❌ Traditional Brands: Slow absorption, artificial fillers, inflated retail markup.\n✅ {brand_name}: {b1}, {b2}, direct-to-consumer savings.\n\nMake the smart switch risk-free today.",
                "cta": "Switch & Save",
                "callout_points": [f"Ours: {b1}", f"Ours: {b2}", "30-Day Trial"],
                "comparison_theirs": "Artificial fillers, sluggish results, overpriced markup",
                "comparison_ours": f"{b1}, {b2}, direct-to-consumer value",
                "testimonial_quote": "After seeing the comparison, switching was a no-brainer.",
                "testimonial_author": "David L. · Verified Customer",
                "visual_prompt": (
                    f"Split-perspective commercial direct-response Meta ad for {product_name} by {brand_name}. {product_desc}. "
                    f"Elevated on a clean minimalist geometric pedestal with radiant modern lighting, clean background contrast. "
                    f"Native in-image typography: Top header reading \"{brand_name.upper()}\". "
                    f"Eyebrow pill reading \"WHY THOUSANDS ARE SWITCHING\". "
                    f"Bold headline reading \"Traditional {category} vs. {brand_name}\". "
                    f"Side-by-side graphic comparison panel: Left red badge reading \"✕ TRADITIONAL: Slow results & fillers\", Right emerald badge reading \"✓ {brand_name.upper()}: {b1} with {b2}\". "
                    f"Bottom right CTA button reading \"SWITCH & SAVE ➔\". "
                    f"Commercial advertising visual hierarchy, 8K resolution."
                ),
                "layout_style": "US_VS_THEM_GRID"
            },
            {
                "creative_id": 5,
                "framework_key": "lifestyle_hero",
                "framework_name": "Aspirational Lifestyle Transformation",
                "target_emotion": "Desire & Identity Elevation",
                "target_audience_resonance": f"Embodies the aspirational end-state of {persona}, establishing {product_name} as an indispensable lifestyle staple.",
                "hook_badge": "YOUR NEW DAILY STANDARD",
                "headline": f"Elevate Your Daily Ritual with {product_name}",
                "subheadline": f"Crafted for high performers who demand perfection.",
                "primary_text": f"Every morning brings a choice: settle for ordinary or elevate your standard.\n\n{product_name} by {brand_name} was created for {persona} who want {b1.lower()} without compromise.\n\n✨ Premium materials\n✨ Effortless integration\n✨ Unrivaled satisfaction\n\nExperience the transformation.",
                "cta": "Experience Now",
                "callout_points": ["Premium Experience", "Effortless Integration", "Uncompromised Quality"],
                "comparison_theirs": "Clunky, outdated daily routines",
                "comparison_ours": "Seamless luxury performance designed for modern life",
                "testimonial_quote": f"{product_name} elevated my entire routine. I feel the difference every single day.",
                "testimonial_author": "Elena V. · Creative Director",
                "visual_prompt": (
                    f"Cinematic aspirational lifestyle Meta ad creative featuring {product_name} by {brand_name}. {product_desc}. "
                    f"Sunlit modern architectural space matching {persona}, golden-hour ambient rays, natural soft bokeh, premium textures. "
                    f"Native in-image typography: Top header \"{brand_name.upper()}\". "
                    f"Eyebrow badge reading \"YOUR NEW DAILY STANDARD\". "
                    f"Large bold headline reading \"Elevate Your Daily Ritual with {product_name}\". "
                    f"Secondary subhead reading \"Crafted for high performers who demand perfection.\". "
                    f"Floating gold trust pills reading \"✨ Premium Materials\" and \"✨ Unrivaled Satisfaction\". "
                    f"Bottom right graphic CTA button reading \"EXPERIENCE NOW ➔\". "
                    f"High-end Vogue/GQ editorial aesthetics, ultra-photorealistic commercial composition, 8K resolution."
                ),
                "layout_style": "LIFESTYLE_IN_ACTION"
            }
        ]

    return blueprints

# Direct Response Creative Delivery Helper (Zero Overlay Layer)
def render_meta_ad_composite(
    base_image_path: str,
    blueprint: Dict[str, Any],
    brand_name: str,
    product_name: str,
    output_path: str,
    aspect_ratio: str = "4:5"
) -> str:
    """
    Ensures the Meta creative image is properly dimensioned and saved for direct delivery.
    All typography, branding badges, headlines, and layouts are natively synthesized into the pixels
    by the AI models (Qwen-Image-2.1 or Gemini Nano Banana Pro), completely eliminating artificial overlay layers.
    """
    ratio_map = {
        "1:1": (1024, 1024),
        "4:5": (1024, 1280),
        "9:16": (1024, 1792),
        "16:9": (1792, 1024),
    }
    target_w, target_h = ratio_map.get(aspect_ratio, (1024, 1280))
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    if os.path.exists(base_image_path):
        if HAS_PIL and Image:
            try:
                with Image.open(base_image_path) as base_img:
                    img_w, img_h = base_img.size
                    if (img_w, img_h) == (target_w, target_h):
                        base_img.save(output_path, "PNG", quality=95)
                    else:
                        scale = max(target_w / img_w, target_h / img_h)
                        new_w = int(img_w * scale)
                        new_h = int(img_h * scale)
                        resized = base_img.resize((new_w, new_h), Image.Resampling.LANCZOS)
                        left = (new_w - target_w) // 2
                        top = (new_h - target_h) // 2
                        canvas = resized.crop((left, top, left + target_w, top + target_h))
                        canvas.save(output_path, "PNG", quality=95)
                logger.info(f"[Meta Delivery] Verified native AI creative at: {output_path}")
                return output_path
            except Exception as e:
                logger.debug(f"PIL image resize skipped, falling back to direct copy: {e}")
        import shutil
        shutil.copyfile(base_image_path, output_path)
        return output_path
    else:
        if HAS_PIL and Image:
            canvas = Image.new("RGB", (target_w, target_h), (12, 16, 28))
            canvas.save(output_path, "PNG", quality=95)
        return output_path

async def generate_single_meta_creative(
    blueprint: Dict[str, Any],
    brand_name: str,
    product_name: str,
    product_category: str = "",
    target_audience_persona: str = "",
    aspect_ratio: str = "4:5",
    engine: str = "qwen",
    product_image_path: Optional[str] = None,
    product_bytes: Optional[bytes] = None,
    mime_type: str = "image/png",
    custom_directive: Optional[str] = None,
    steps: int = 35,
    seed: Optional[int] = None,
    client: Any = None,
    api_key: Optional[str] = None,
    image_api_key: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Renders a single high-converting Meta creative with native in-image typography:
    1. Synthesizes a direct-response ad prompt instructing Qwen/Nano Banana Pro to render
       typography, layout, badges, headlines, and product visuals directly in the pixels.
    2. Dispatches to the AI image model and saves the native creative.
    """
    from self_hosted_engine import (
        generate_image_async,
        is_self_hosted_enabled,
        should_fallback_to_gemini,
        get_image_api_key,
        image_bytes_to_data_uri,
    )
    from google.genai import types

    cid = blueprint.get("creative_id", 1)
    ratio_map = {
        "1:1": (1024, 1024),
        "4:5": (1024, 1280),
        "9:16": (1024, 1792),
        "16:9": (1792, 1024),
    }
    target_w, target_h = ratio_map.get(aspect_ratio, (1024, 1280))

    visual_prompt = build_native_in_image_ad_prompt(
        blueprint=blueprint,
        brand_name=brand_name,
        product_name=product_name,
        product_category=product_category,
        target_audience_persona=target_audience_persona,
        aspect_ratio=aspect_ratio,
        product_visual_description="",
        custom_directive=custom_directive,
    )

    # Product reference resolution
    product_data_uri = None
    if product_bytes:
        product_data_uri = image_bytes_to_data_uri(product_bytes, mime_type)
    elif product_image_path:
        clean_path = product_image_path.lstrip("/").replace("\\", "/")
        if os.path.exists(clean_path):
            with open(clean_path, "rb") as f:
                product_bytes = f.read()
            ext = os.path.splitext(clean_path)[1].lower() or ".png"
            mime_type = "image/jpeg" if ext in [".jpg", ".jpeg"] else ("image/webp" if ext == ".webp" else "image/png")
            product_data_uri = image_bytes_to_data_uri(product_bytes, mime_type)

    engine_clean = (engine or "qwen").lower().strip()
    is_banana = engine_clean in ["gemini", "banana", "nano-banana", "nano-banana-pro", "nanobanana"]
    use_qwen = not is_banana and (engine_clean in ["qwen", "self-hosted"] or is_self_hosted_enabled())

    image_bytes = None
    used_model = "Qwen-Image-2.1 (Self-Hosted)"

    if use_qwen:
        try:
            logger.info(f"[Meta Creative #{cid}] Dispatching to Qwen-Image-2.1 ({target_w}x{target_h})...")
            image_bytes = await generate_image_async(
                prompt=visual_prompt,
                width=target_w,
                height=target_h,
                steps=steps,
                seed=seed,
                image_uri=product_data_uri,
                api_key=image_api_key or get_image_api_key(),
                timeout=600
            )
            used_model = "Qwen-Image-2.1 (Self-Hosted)"
        except Exception as qwen_err:
            logger.warning(f"[Meta Creative #{cid}] Qwen failed: {qwen_err}")
            if not should_fallback_to_gemini() and engine_clean in ["qwen"]:
                raise

    if not image_bytes:
        if not client:
            from app import get_client
            client = get_client(api_key)
        if not client:
            raise RuntimeError("Gemini API Client required for Nano Banana Pro generation.")
        logger.info(f"[Meta Creative #{cid}] Generating with Gemini Nano Banana Pro...")
        contents = [visual_prompt]
        if product_bytes:
            contents.append(types.Part.from_bytes(data=product_bytes, mime_type=mime_type))

        response = client.models.generate_content(
            model="nano-banana-pro-preview",
            contents=contents
        )
        if response.candidates:
            for part in response.candidates[0].content.parts:
                if part.inline_data and part.inline_data.data:
                    image_bytes = part.inline_data.data
                    break
        if not image_bytes:
            raise RuntimeError("Model failed to return image bytes.")
        used_model = "nano-banana-pro-preview"

    # Save raw AI render
    raw_filename = f"meta_raw_{cid}_{uuid.uuid4().hex}.png"
    raw_path = os.path.join("static/generated", raw_filename)
    if isinstance(image_bytes, str):
        image_bytes = image_bytes.encode('latin1')
    with open(raw_path, "wb") as f:
        f.write(image_bytes)

    # Render high-converting direct response composite ad
    comp_filename = f"meta_suite_{cid}_{uuid.uuid4().hex}.png"
    comp_path = os.path.join("static/generated", comp_filename)
    render_meta_ad_composite(
        base_image_path=raw_path,
        blueprint=blueprint,
        brand_name=brand_name,
        product_name=product_name,
        output_path=comp_path,
        aspect_ratio=aspect_ratio
    )

    return {
        "status": "success",
        "creative_id": cid,
        "framework_key": blueprint.get("framework_key", "general"),
        "framework_name": blueprint.get("framework_name", "Meta Creative"),
        "target_emotion": blueprint.get("target_emotion", "High Intent"),
        "target_audience_resonance": blueprint.get("target_audience_resonance", ""),
        "hook_badge": blueprint.get("hook_badge", ""),
        "headline": blueprint.get("headline", ""),
        "subheadline": blueprint.get("subheadline", ""),
        "primary_text": blueprint.get("primary_text", ""),
        "cta": blueprint.get("cta", "Shop Now"),
        "callout_points": blueprint.get("callout_points", []),
        "image_url": f"/static/generated/{comp_filename}",
        "raw_image_url": f"/static/generated/{raw_filename}",
        "composite_image_url": f"/static/generated/{comp_filename}",
        "aspect_ratio": aspect_ratio,
        "width": target_w,
        "height": target_h,
        "model_used": used_model,
        "engine": "banana" if ("banana" in used_model or is_banana) else "qwen",
        "visual_prompt": visual_prompt,
        "has_product_reference": bool(product_bytes)
    }
