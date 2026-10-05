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
                "- visual_prompt (hyper-detailed commercial photography AI prompt describing composition, lighting, product hero placement, camera angle, high contrast, and depth of field. Do not put text in prompt.)\n"
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
                "visual_prompt": f"Dramatic high-contrast commercial product photography of {product_name} by {brand_name}. {product_desc}. Hero angle placed centrally on a dark textured obsidian pedestal, radiant golden rim lighting, soft diffuse studio spotlight, crisp metallic reflections, 8K ultra-sharp detail, high stopping-power commercial layout.",
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
                "visual_prompt": f"Clean minimalist luxury studio product photography of {product_name} by {brand_name}. {product_desc}. Floating weightlessly in negative space, soft ambient studio gradient background, subtle architectural shadows, precision macro details of packaging and textures, Apple-style direct-response ad composition.",
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
                "visual_prompt": f"Warm editorial lifestyle product photography of {product_name} by {brand_name}. {product_desc}. Placed gracefully on an elegant marble countertop, soft warm morning window light, shallow depth of field with blurred aspirational interior, authentic social proof aesthetic, crisp reflections, commercial direct-response quality.",
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
                "visual_prompt": f"Split-perspective commercial studio shot of {product_name} by {brand_name}. {product_desc}. Elevated on a clean minimalist geometric pedestal with radiant modern lighting, clean background contrast, high-end editorial product presentation, vivid clarity, 8K commercial resolution.",
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
                "visual_prompt": f"Cinematic aspirational lifestyle photography featuring {product_name} by {brand_name}. {product_desc}. Sunlit modern architectural space matching {persona}, golden-hour ambient rays, natural soft bokeh, premium textures, high-end Vogue/GQ editorial aesthetics, ultra-photorealistic commercial composition.",
                "layout_style": "LIFESTYLE_IN_ACTION"
            }
        ]

    return blueprints

# High-Converting Direct Response Graphic Compositor
def render_meta_ad_composite(
    base_image_path: str,
    blueprint: Dict[str, Any],
    brand_name: str,
    product_name: str,
    output_path: str,
    aspect_ratio: str = "4:5"
) -> str:
    """
    Renders a production-grade Meta ad creative combining:
    - Base photographic scene / product placement
    - Proper branding header & verified badges
    - High-contrast hook eyebrow, typography hierarchy, and drop-shadows
    - Framework-specific graphic badges (feature pills, 5-star ratings, comparison matrix)
    - High-CTR CTA button sticker
    """
    ratio_map = {
        "1:1": (1024, 1024),
        "4:5": (1024, 1280),
        "9:16": (1024, 1792),
        "16:9": (1792, 1024),
    }
    target_w, target_h = ratio_map.get(aspect_ratio, (1024, 1280))

    # 1. Load or initialize base canvas
    if os.path.exists(base_image_path):
        try:
            base_img = Image.open(base_image_path).convert("RGBA")
            # Resize and crop to fill target dimensions
            img_w, img_h = base_img.size
            scale = max(target_w / img_w, target_h / img_h)
            new_w = int(img_w * scale)
            new_h = int(img_h * scale)
            resized = base_img.resize((new_w, new_h), Image.Resampling.LANCZOS)
            # Center crop
            left = (new_w - target_w) // 2
            top = (new_h - target_h) // 2
            canvas = resized.crop((left, top, left + target_w, top + target_h))
        except Exception as e:
            logger.warning(f"Error loading base image {base_image_path}: {e}")
            canvas = Image.new("RGBA", (target_w, target_h), (12, 16, 28, 255))
    else:
        canvas = Image.new("RGBA", (target_w, target_h), (12, 16, 28, 255))

    # 2. Add subtle dark gradient scrims at top & bottom for 100% typography contrast
    overlay = Image.new("RGBA", (target_w, target_h), (0, 0, 0, 0))
    d_overlay = ImageDraw.Draw(overlay)

    # Top scrim (0 to 300px)
    for y in range(0, min(320, target_h)):
        alpha = int(170 * (1.0 - (y / 320.0) ** 1.3))
        d_overlay.line([(0, y), (target_w, y)], fill=(8, 10, 18, alpha))

    # Bottom scrim (from target_h - 400 to target_h)
    bottom_start = max(0, target_h - 420)
    for y in range(bottom_start, target_h):
        progress = (y - bottom_start) / 420.0
        alpha = int(210 * (progress ** 1.2))
        d_overlay.line([(0, y), (target_w, y)], fill=(6, 8, 16, alpha))

    # Composite scrims
    canvas = Image.alpha_composite(canvas, overlay)
    draw = ImageDraw.Draw(canvas)

    # Resolve typography fonts
    f_brand = get_font(22, True)
    f_badge = get_font(18, True)
    f_headline = get_font(38 if target_w == 1024 else 44, True)
    f_subhead = get_font(21, False)
    f_callout = get_font(20, True)
    f_stars = get_font(26, True)
    f_cta = get_font(23, True)

    pad_x = 44
    usable_w = target_w - (pad_x * 2)

    # --- TOP BRAND HEADER BAR ---
    top_y = 36
    brand_title = (brand_name or "BRAND").upper()
    brand_bbox = draw.textbbox((0, 0), brand_title, font=f_brand)
    brand_w = brand_bbox[2] - brand_bbox[0]
    brand_pill_w = brand_w + 36
    brand_pill_h = 38

    # Frosted brand capsule
    draw.rounded_rectangle(
        [pad_x, top_y, pad_x + brand_pill_w, top_y + brand_pill_h],
        radius=10,
        fill=(14, 18, 30, 225),
        outline=(255, 255, 255, 45),
        width=1
    )
    draw.text((pad_x + 18, top_y + 8), brand_title, fill=(255, 255, 255), font=f_brand)

    # Top right: Direct Response Trust Stamp
    stamp_text = "OFFICIAL STORE ✓"
    stamp_bbox = draw.textbbox((0, 0), stamp_text, font=f_badge)
    stamp_w = stamp_bbox[2] - stamp_bbox[0]
    stamp_x = target_w - pad_x - stamp_w - 24
    draw.rounded_rectangle(
        [stamp_x, top_y, target_w - pad_x, top_y + brand_pill_h],
        radius=10,
        fill=(16, 185, 129, 35),
        outline=(16, 185, 129, 120),
        width=1
    )
    draw.text((stamp_x + 12, top_y + 9), stamp_text, fill=(52, 211, 153), font=f_badge)

    # --- HOOK EYEBROW & MAIN HEADLINE ---
    headline_y = top_y + brand_pill_h + 20

    # Eyebrow Hook Badge
    hook_badge = blueprint.get("hook_badge", "SPECIAL OFFER").upper()
    badge_color = (24, 119, 242, 235)  # Meta Blue default
    badge_text_color = (255, 255, 255)
    f_key = blueprint.get("framework_key", "")

    if f_key == "social_proof":
        badge_color = (245, 158, 11, 235)  # Amber
    elif f_key == "us_vs_them":
        badge_color = (139, 92, 246, 235)  # Purple
    elif f_key == "problem_solution":
        badge_color = (239, 68, 68, 235)   # Coral/Red

    badge_bbox = draw.textbbox((0, 0), hook_badge, font=f_badge)
    badge_w = badge_bbox[2] - badge_bbox[0] + 28
    draw.rounded_rectangle(
        [pad_x, headline_y, pad_x + badge_w, headline_y + 32],
        radius=8,
        fill=badge_color,
        outline=(255, 255, 255, 80),
        width=1
    )
    draw.text((pad_x + 14, headline_y + 6), hook_badge, fill=badge_text_color, font=f_badge)

    headline_y += 42
    headline_text = blueprint.get("headline", f"Upgrade to {product_name}")
    head_lines = wrap_text(headline_text, f_headline, usable_w, draw)[:2]

    # Draw headline lines with drop shadow for legibility
    for hl in head_lines:
        # Subtle dark shadow
        draw.text((pad_x + 2, headline_y + 2), hl, fill=(0, 0, 0, 210), font=f_headline)
        draw.text((pad_x, headline_y), hl, fill=(255, 255, 255), font=f_headline)
        headline_y += 46

    # Subheadline
    subhead_text = blueprint.get("subheadline", "")
    if subhead_text:
        sub_lines = wrap_text(subhead_text, f_subhead, usable_w, draw)[:1]
        for sl in sub_lines:
            draw.text((pad_x + 1, headline_y + 1), sl, fill=(0, 0, 0, 180), font=f_subhead)
            draw.text((pad_x, headline_y), sl, fill=(203, 213, 225), font=f_subhead)
            headline_y += 30

    # --- FRAMEWORK SPECIFIC GRAPHIC OVERLAYS ---
    if f_key == "social_proof":
        # 5-Star Rating Pill + Frosted Customer Quote Bubble
        quote_box_y = target_h - 300
        quote_box_h = 135
        draw.rounded_rectangle(
            [pad_x, quote_box_y, target_w - pad_x, quote_box_y + quote_box_h],
            radius=16,
            fill=(10, 14, 26, 225),
            outline=(245, 158, 11, 110),
            width=1
        )
        # Gold stars
        draw.text((pad_x + 20, quote_box_y + 16), "★★★★★", fill=(245, 158, 11), font=f_stars)
        draw.text((pad_x + 140, quote_box_y + 18), "VERIFIED 5-STAR REVIEW", fill=(251, 191, 36), font=f_badge)

        quote = blueprint.get("testimonial_quote", "“This changed my entire routine.”")
        q_lines = wrap_text(f"“{quote.strip('“”\"')}”", f_callout, usable_w - 40, draw)[:2]
        qy = quote_box_y + 54
        for ql in q_lines:
            draw.text((pad_x + 20, qy), ql, fill=(255, 255, 255), font=f_callout)
            qy += 26

        author = blueprint.get("testimonial_author", "Verified Buyer")
        draw.text((pad_x + 20, quote_box_y + 104), f"— {author} ✓", fill=(148, 163, 184), font=f_badge)

    elif f_key == "us_vs_them":
        # Dual Comparison Columns
        comp_y = target_h - 290
        comp_h = 125
        col_w = (usable_w - 16) // 2

        # Left Column: Others / The Old Way (Muted Red)
        draw.rounded_rectangle(
            [pad_x, comp_y, pad_x + col_w, comp_y + comp_h],
            radius=14,
            fill=(26, 12, 16, 220),
            outline=(239, 68, 68, 80),
            width=1
        )
        draw.text((pad_x + 16, comp_y + 14), "✕ TRADITIONAL", fill=(248, 113, 113), font=f_badge)
        theirs_text = blueprint.get("comparison_theirs", "Harsh fillers & slow results")
        th_lines = wrap_text(theirs_text, f_badge, col_w - 32, draw)[:2]
        ty = comp_y + 44
        for tl in th_lines:
            draw.text((pad_x + 16, ty), f"• {tl}", fill=(203, 213, 225), font=f_badge)
            ty += 24

        # Right Column: Our Brand (Radiant Emerald)
        right_x = pad_x + col_w + 16
        draw.rounded_rectangle(
            [right_x, comp_y, right_x + col_w, comp_y + comp_h],
            radius=14,
            fill=(10, 28, 20, 225),
            outline=(16, 185, 129, 140),
            width=1
        )
        draw.text((right_x + 16, comp_y + 14), f"✓ {brand_name.upper()}", fill=(52, 211, 153), font=f_badge)
        ours_text = blueprint.get("comparison_ours", "100% Pure, fast visible results")
        o_lines = wrap_text(ours_text, f_badge, col_w - 32, draw)[:2]
        oy = comp_y + 44
        for ol in o_lines:
            draw.text((right_x + 16, oy), f"• {ol}", fill=(255, 255, 255), font=f_badge)
            oy += 24

    elif f_key == "feature_callout":
        # 3 Floating Feature Callout Badges
        callouts = blueprint.get("callout_points", [])[:3]
        cy = target_h - 290
        for idx, callout in enumerate(callouts):
            draw.rounded_rectangle(
                [pad_x, cy, target_w - pad_x, cy + 36],
                radius=10,
                fill=(12, 16, 28, 215),
                outline=(24, 119, 242, 90),
                width=1
            )
            draw.text((pad_x + 14, cy + 7), "✓", fill=(52, 211, 153), font=f_callout)
            draw.text((pad_x + 38, cy + 7), callout, fill=(255, 255, 255), font=f_callout)
            cy += 44

    else:
        # Default Problem-Solution / Lifestyle Transformation Bullets
        callouts = blueprint.get("callout_points", [])[:3]
        if callouts:
            cy = target_h - 275
            for callout in callouts[:2]:
                draw.rounded_rectangle(
                    [pad_x, cy, target_w - pad_x, cy + 38],
                    radius=10,
                    fill=(10, 14, 26, 220),
                    outline=(255, 255, 255, 40),
                    width=1
                )
                draw.text((pad_x + 16, cy + 8), "✨", fill=(251, 191, 36), font=f_badge)
                draw.text((pad_x + 44, cy + 8), callout, fill=(255, 255, 255), font=f_callout)
                cy += 46

    # --- BOTTOM CTA RIBBON / BUTTON ---
    cta_y = target_h - 105
    cta_h = 62
    cta_btn_w = 260
    cta_btn_x = target_w - pad_x - cta_btn_w

    # Left: Trust seal / Guarantee
    draw.text((pad_x, cta_y + 12), "30-DAY RISK-FREE TRIAL", fill=(148, 163, 184), font=f_badge)
    draw.text((pad_x, cta_y + 34), "Free Expedited Shipping Included", fill=(100, 116, 139), font=f_badge)

    # Right: High-Contrast CTA Button
    cta_text = f"{blueprint.get('cta', 'SHOP NOW').upper()}  ➔"
    draw.rounded_rectangle(
        [cta_btn_x, cta_y, target_w - pad_x, cta_y + cta_h],
        radius=14,
        fill=(24, 119, 242, 255),
        outline=(255, 255, 255, 120),
        width=1
    )
    # Centered CTA text
    cta_bbox = draw.textbbox((0, 0), cta_text, font=f_cta)
    cta_w = cta_bbox[2] - cta_bbox[0]
    draw.text((cta_btn_x + (cta_btn_w - cta_w) // 2, cta_y + 18), cta_text, fill=(255, 255, 255), font=f_cta)

    # 3. Save final composite image
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    canvas.convert("RGB").save(output_path, "PNG", quality=95)
    logger.info(f"[Meta Compositor] Rendered direct response ad: {output_path}")
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
    Renders a single high-converting Meta creative:
    1. Synthesizes photorealistic commercial scene matching the framework visual prompt.
    2. Runs direct response graphic compositor with branding, typography hierarchy, badges, and CTA.
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

    visual_prompt = blueprint.get("visual_prompt", "")
    if custom_directive and custom_directive.strip():
        visual_prompt += f" Additional creative direction: {custom_directive.strip()}."

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
