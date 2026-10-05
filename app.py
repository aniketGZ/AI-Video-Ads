import os
import base64
import json
import logging
from typing import List, Optional
import requests
from bs4 import BeautifulSoup
import asyncio
from fastapi import FastAPI, HTTPException, UploadFile, File, Form, Header, Request, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from google import genai
from google.genai import types
from moneyprinter_engine import execute_moneyprinter_job, persist_job_update, JOBS_CACHE_FILE
from self_hosted_engine import (
    load_dotenv,
    get_image_api_url,
    get_image_api_key,
    get_video_api_url,
    get_video_api_key,
    is_self_hosted_enabled,
    should_fallback_to_gemini,
    get_public_ip,
    get_diagnostics,
    image_file_to_data_uri,
    image_bytes_to_data_uri,
    generate_image_async,
    generate_video_async,
)
from meta_creative_engine import (
    generate_meta_creative_blueprints,
    render_meta_ad_composite,
    generate_single_meta_creative,
)

# Load configuration from .env file
load_dotenv()

class MoneyPrinterRequest(BaseModel):
    subject: str
    custom_script: Optional[str] = None
    aspect_ratio: str = "9:16"
    voice_name: str = "en-US-ChristopherNeural"
    pixabay_key: Optional[str] = None
    burn_subtitles: bool = True

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Viral AI Video Ad Generator")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ensure generated directory exists
os.makedirs("static/generated", exist_ok=True)

DEFAULT_API_KEY = ""

# Define Pydantic structures for schema validation
class VideoAdScript(BaseModel):
    video_style_type: str
    hook_line: str
    voiceover: str
    visual_directions: str
    cta_line: str
    shot_1: str
    shot_2: str
    shot_3: str
    shot_4: str

class AdGroup(BaseModel):
    name: str
    angle: str
    videos: List[VideoAdScript]

class CampaignAnalysis(BaseModel):
    brand_name: str
    product_name: str
    product_category: str
    product_visual_description: str
    product_hero_angle: str
    target_audience_persona: str
    on_screen_talent: str
    setting: str
    mood_keywords: str
    color_palette: str
    visual_style: str
    logo_text: str
    key_benefits: List[str]
    ad_groups: List[AdGroup]

class StoryboardRequest(BaseModel):
    brand_name: str
    product_name: str
    product_category: str
    product_visual_description: str
    product_hero_angle: str
    target_audience_persona: str
    on_screen_talent: str
    setting: str
    mood_keywords: str
    color_palette: str
    visual_style: str
    logo_text: str
    key_benefits: List[str]
    video_style_type: str
    hook_line: str
    cta_line: str
    shot_1: str
    shot_2: str
    shot_3: str
    shot_4: str
    product_image_paths: Optional[List[str]] = None
    use_self_hosted: Optional[bool] = None

class VideoRequest(BaseModel):
    storyboard_image_url: str
    video_prompt: str
    product_image_paths: Optional[List[str]] = None
    generator: str = "minimax"
    aspect_ratio: str = "9:16"
    mpt_service_url: Optional[str] = None
    voice_script: Optional[str] = None
    hook_line: Optional[str] = None
    use_self_hosted: Optional[bool] = None

class SelfHostedConfigRequest(BaseModel):
    image_api_url: Optional[str] = None
    image_api_key: Optional[str] = None
    video_api_url: Optional[str] = None
    video_api_key: Optional[str] = None
    use_self_hosted: Optional[bool] = None
    fallback_to_gemini: Optional[bool] = None

# Helper to get the GenAI client
def get_client(api_key: Optional[str] = None) -> Optional[genai.Client]:
    key = api_key or os.environ.get("GEMINI_API_KEY") or DEFAULT_API_KEY
    if not key or not str(key).strip():
        return None
    try:
        return genai.Client(api_key=str(key).strip())
    except Exception as e:
        logger.warning(f"Could not initialize GenAI client: {e}")
        return None

# Basic web scraper helper
def scrape_url(url: str) -> str:
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
        }
        res = requests.get(url, headers=headers, timeout=10)
        res.raise_for_status()
        soup = BeautifulSoup(res.text, "html.parser")
        
        # Remove scripts, styles
        for s in soup(["script", "style", "meta", "noscript"]):
            s.decompose()
            
        text = soup.get_text(separator="\n")
        # Clean up whitespace
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        return "\n".join(chunk for chunk in chunks if chunk)[:8000] # Limit to 8k chars
    except Exception as e:
        logger.error(f"Web scraping failed: {e}")
        return ""

@app.post("/api/analyze")
async def analyze_campaign(
    url: str = Form(...),
    is_tangible: bool = Form(False),
    images: Optional[List[UploadFile]] = File(None),
    x_api_key: Optional[str] = Header(None)
):
    try:
        client = get_client(x_api_key)
        
        # 1. Scrape & ground URL using Search Grounding
        logger.info("Step 1: Running Google Search Grounding to analyze the URL...")
        scraped_content = scrape_url(url)
        
        grounding_research_prompt = (
            f"You are a professional research agent analyzing the brand landing page URL: {url}.\n"
            f"Here is some scraped text from the site:\n{scraped_content}\n\n"
            "Analyze the website thoroughly. Identify the brand name, core product name, product category, "
            "detailed list of services or products showcased, target demographics, brand voice/tone, "
            "potential color palette ideas, and key benefits. Use Google Search grounding to ensure accuracy.\n\n"
            "At the very end of your response, you MUST include a line in the exact format:\n"
            "SELECTED_DEMOGRAPHIC_ETHNICITY: <one of the categories listed below>\n\n"
            "Choose the single most appropriate target demographic category for this website from this list:\n"
            "- Han Chinese\n"
            "- South Asian (Indo-Aryan / Hindustani)\n"
            "- Bengali\n"
            "- Arab\n"
            "- European (Slavic & Western European)\n"
            "- Latino / Mestizo\n"
            "- Japanese\n"
            "- Javanese (Southeast Asian)\n"
            "- Turkish\n"
            "- Sub-Saharan African (West African & Bantu)\n"
        )
        
        grounding_config = types.GenerateContentConfig(
            tools=[types.Tool(google_search=types.GoogleSearch())]
        )
        
        research_response = client.models.generate_content(
            model="gemini-3.6-flash",
            contents=grounding_research_prompt,
            config=grounding_config
        )
        
        research_summary = research_response.text
        logger.info("URL Search Grounding and research completed.")

        # Extract target demographic ethnicity and load corresponding characters from library
        selected_ethnicity = "European (Slavic & Western European)"  # Fallback
        import re
        match = re.search(r"SELECTED_DEMOGRAPHIC_ETHNICITY:\s*(.+)", research_summary, re.IGNORECASE)
        if match:
            selected_ethnicity = match.group(1).strip()
            logger.info(f"Target demographic ethnicity identified: {selected_ethnicity}")
        else:
            logger.warning("Could not find SELECTED_DEMOGRAPHIC_ETHNICITY line in research summary. Using fallback.")
            
        avatars = get_avatars_by_ethnicity(selected_ethnicity)
        logger.info(f"Loaded {len(avatars)} candidate avatars matching demographic: {selected_ethnicity}")
        
        avatars_txt = ""
        for av in avatars:
            avatars_txt += (
                f"- ID: {av['id']}\n"
                f"  Name: {av['name']}\n"
                f"  Gender: {av['gender']}\n"
                f"  Age: {av['age']}\n"
                f"  Occupation: {av.get('occupation', '')}\n"
                f"  Prompt Sheet: {av['prompt']}\n\n"
            )

        product_images_analysis = ""
        saved_image_paths = []
        # 2. If tangible and images are uploaded, analyze them
        if is_tangible and images:
            image_parts = []
            import uuid
            for img in images:
                content = await img.read()
                # Save the image to disk for Nano Banana Pro reference
                ext = os.path.splitext(img.filename)[1] or ".jpg"
                filename = f"product_{uuid.uuid4().hex}{ext}"
                file_path = os.path.join("static/generated", filename)
                with open(file_path, "wb") as f:
                    f.write(content)
                saved_image_paths.append(f"/static/generated/{filename}")
                
                image_parts.append(
                    types.Part.from_bytes(data=content, mime_type=img.content_type)
                )
            
            if image_parts:
                logger.info("Analyzing product images for forensic details...")
                image_prompt = (
                    "Describe the product in these images in extreme detail for consistency in video generation. "
                    "Detail its packaging shape, materials, main colors, logo layout, cap type, dimensions, "
                    "text on the label, contents color (e.g. blue gel with beads), and best looking hero angles."
                )
                image_analysis_response = client.models.generate_content(
                    model="gemini-3.6-flash",
                    contents=[image_prompt] + image_parts
                )
                product_images_analysis = image_analysis_response.text
                logger.info(f"Product image analysis completed: {product_images_analysis[:100]}...")

        # 3. Step 2: Compile prompt for campaign building using the Pydantic schema
        logger.info("Step 2: Calling Gemini with schema validation to build the ad campaign...")
        campaign_prompt = (
            f"You are a professional campaign builder and Meta ads script writer.\n"
            f"Based on the following research summary of the brand:\n{research_summary}\n\n"
        )
        
        if product_images_analysis:
            campaign_prompt += f"Visual description of the physical product from uploaded images:\n{product_images_analysis}\n\n"
            
        campaign_prompt += (
            "Create a best-in-class campaign containing exactly 6 ad groups. "
            "Each ad group should focus on a distinct service or product angle showcased in the research summary. "
            "For each ad group, write exactly 3 video scripts selecting from these styles:\n"
            "1. Before/After videos\n"
            "2. Person Clone videos\n"
            "3. Authoritative Videos\n"
            "4. Green Screen Videos\n"
            "5. Product Explainer/showcase\n"
            "6. Comment response video\n"
            "7. Split Screen Video\n"
            "8. Testimonial Video\n"
            "9. Storytelling video\n"
            "10. Creative Product studio shoot\n\n"
            "For every single video script, write full script details and split them into exactly 4 distinct storyboard shots "
            "(`shot_1` through `shot_4`) matching the 10-second arc in the template:\n"
            "- shot_1: HOOK SHOT (~2.5s)\n"
            "- shot_2: PRODUCT REVEAL & ACTION (~2.5s)\n"
            "- shot_3: BENEFIT/TRANSFORMATION (~2.5s)\n"
            "- shot_4: CALL TO ACTION / CTA SHOT (~2.5s)\n\n"
            "CRITICAL INSTRUCTIONS FOR VOICEOVER FLOW & AUDIO TYPE:\n"
            "- The voiceover text across all 4 shots must form a continuous, naturally flowing narration.\n"
            "- Avoid abrupt transitions, disjointed sentences, or sudden pauses. Every shot's voiceover should connect smoothly to the next to build a cohesive narrative.\n"
            "- Keep all text crisp, clean, engaging, and high-impact. Avoid clutter or over-explaining.\n"
            "- IMPORTANT: You MUST specifically format every segment of audio/speech using prefix tags to distinguish between dialogue spoken by an on-screen model vs a voiceover narration. Use `[Dialogue: \"spoken text\"]` (when the on-screen talent speaks directly to the camera with lipsync) or `[Voiceover: \"narrated text\"]` (when the audio is read as off-screen narration without lipsync). Make sure every line in the voiceover field has one of these prefixes.\n\n"
            "Generate your response matching the requested schema. Make sure color_palette consists of 3-5 premium color terms, "
            "visual_style is one of (UGC_REALISTIC, CINEMATIC_PREMIUM, PIXAR_3D_STYLIZED, CLEAN_STUDIO, FOOD_APPETITE).\n\n"
            f"You MUST select one target demographic avatar from the list of available characters below. "
            f"For the `on_screen_talent` field in the response schema, copy the EXACT `Prompt Sheet` of the selected character. "
            f"Do not edit or change the Prompt Sheet text; it must be a verbatim copy so it acts as a consistent character lock in our image/video models.\n\n"
            f"AVAILABLE TARGET DEMOGRAPHIC AVATARS:\n{avatars_txt}\n\n"
            "Ensure that on_screen_talent, setting, and mood_keywords are fully and appropriately filled."
        )
        
        # Do NOT include tools here, so response_schema works perfectly
        schema_config = types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=CampaignAnalysis
        )
        
        response = client.models.generate_content(
            model="gemini-3.6-flash",
            contents=campaign_prompt,
            config=schema_config
        )
        
        # Parse the JSON response
        result_json = json.loads(response.text)
        
        # If user uploaded images, override/supplement product_visual_description
        if product_images_analysis:
            result_json["product_visual_description"] = product_images_analysis
            
        result_json["product_image_paths"] = saved_image_paths

        # Generate 5 High-Converting Meta Direct-Response Creative Blueprints
        try:
            logger.info("Synthesizing 5 high-converting Meta Direct Response Creative Blueprints from URL analysis...")
            result_json["meta_creative_blueprints"] = generate_meta_creative_blueprints(
                result_json, client=client
            )
        except Exception as meta_bp_err:
            logger.warning(f"Error generating meta blueprints, using robust templates: {meta_bp_err}")
            result_json["meta_creative_blueprints"] = generate_meta_creative_blueprints(result_json, client=None)

        return result_json
        
    except Exception as e:
        logger.error(f"Campaign analysis failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/campaign/generate-meta-ad")
async def generate_meta_image_ad(
    brand_name: str = Form(...),
    product_name: str = Form(...),
    product_category: str = Form(""),
    target_audience_persona: str = Form(""),
    visual_style: str = Form(""),
    product_visual_description: Optional[str] = Form(None),
    angle_name: str = Form("Problem-Solution"),
    angle_description: Optional[str] = Form(None),
    aspect_ratio: str = Form("4:5"),
    engine: str = Form("qwen"),
    product_image_path: Optional[str] = Form(None),
    product_image: Optional[UploadFile] = File(None),
    custom_directive: Optional[str] = Form(None),
    steps: int = Form(35),
    seed: Optional[int] = Form(None),
    x_api_key: Optional[str] = Header(None),
    x_image_api_key: Optional[str] = Header(None)
):
    """
    Generate high-converting Meta (Instagram & Facebook Feed + Stories) creative & copy package.
    Synthesizes Primary Text, Headline, and CTA tailored to the analyzed target audience persona,
    and produces an ultra-photorealistic image creative anchored to user-uploaded product photos.
    """
    try:
        import uuid
        client = get_client(x_api_key)

        # 1. Synthesize Meta Ad Copy & Visual Generation Prompt with Gemini
        meta_prompt_instructions = (
            f"You are a top 1% Meta (Facebook & Instagram) Direct Response Creative Director and Copywriter.\n"
            f"Craft high-converting Meta ad copy and a photorealistic visual generation prompt based on this analyzed brand data:\n"
            f"- Brand Name: {brand_name}\n"
            f"- Product Name: {product_name}\n"
            f"- Product Category: {product_category}\n"
            f"- Target Audience Persona: {target_audience_persona}\n"
            f"- Visual Brand Style: {visual_style}\n"
            f"- Physical Product Details: {product_visual_description or 'High-quality consumer product'}\n"
            f"- Marketing Angle / Hook: {angle_name} - {angle_description or ''}\n"
            f"- Ad Placement Format: {aspect_ratio} ({'Instagram/Facebook Feed' if aspect_ratio in ['1:1', '4:5'] else 'Instagram Stories/Reels'})\n"
        )
        if custom_directive and custom_directive.strip():
            meta_prompt_instructions += f"- User Creative Directive: {custom_directive.strip()}\n"

        meta_prompt_instructions += (
            "\nReturn ONLY a valid JSON object with these EXACT keys:\n"
            "{\n"
            '  "primary_text": "Compelling Meta feed post caption (2-3 short punchy paragraphs, hook addressing audience pain point, clear transformation, subtle social proof, 2-3 clean emojis, closing CTA hook).",\n'
            '  "headline": "High-CTR feed headline next to the CTA button (5-7 words max, bold and punchy, e.g. \'Say Goodbye to Muscle Fatigue 👋\')",\n'
            '  "cta": "Standard Meta CTA button text (e.g. \'Shop Now\', \'Claim Offer\', \'Learn More\', \'Order Today\')",\n'
            '  "visual_prompt": "Hyper-descriptive commercial photography prompt for AI image generation. Describe the product placed naturally in the aspirational lifestyle setting of the target audience persona (setting, natural lighting, elegant depth of field, premium materials, high stopping-power commercial composition, 8K ultra-sharp details). Do NOT include text, words, or watermarks in the prompt."\n'
            "}"
        )

        primary_text = ""
        headline = ""
        cta = "Shop Now"
        visual_prompt = ""

        if client:
            try:
                copy_resp = client.models.generate_content(
                    model="gemini-3.6-flash",
                    contents=meta_prompt_instructions,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json"
                    )
                )
                if copy_resp and copy_resp.text:
                    parsed_copy = json.loads(copy_resp.text)
                    primary_text = parsed_copy.get("primary_text", "").strip()
                    headline = parsed_copy.get("headline", "").strip()
                    cta = parsed_copy.get("cta", "Shop Now").strip()
                    visual_prompt = parsed_copy.get("visual_prompt", "").strip()
            except Exception as copy_err:
                logger.warning(f"Gemini copy synthesis error: {copy_err}")

        # Intelligent fallbacks if Gemini is offline or unavailable
        if not primary_text:
            primary_text = (
                f"Still searching for the ultimate {product_category.lower() or 'upgrade'}?\n\n"
                f"Meet {product_name} by {brand_name}. Engineered specifically for {target_audience_persona or 'daily high performers'}.\n\n"
                f"✨ Experience the difference. Tap below to claim yours today."
            )
        if not headline:
            headline = f"Discover {product_name} · Built For You"
        if not visual_prompt:
            visual_prompt = (
                f"Award-winning commercial product photography of {product_name} by {brand_name}. "
                f"{product_visual_description or ''}. "
                f"Seamlessly placed in a stylish modern setting tailored for {target_audience_persona}. "
                f"Natural soft window daylight, crisp reflections, shallow depth of field, 8K ultra-sharp detail, high-end editorial aesthetic."
            )

        # 2. Aspect Ratio Dimension Resolution
        ratio_map = {
            "1:1": (1024, 1024),
            "4:5": (1024, 1280),
            "9:16": (1024, 1792),
            "16:9": (1792, 1024),
        }
        target_w, target_h = ratio_map.get(aspect_ratio, (1024, 1280))

        # 3. Product Reference Image Resolution
        product_bytes = None
        product_data_uri = None
        mime_type = "image/png"

        # Check direct upload first
        if product_image and product_image.filename:
            product_bytes = await product_image.read()
            if product_bytes:
                ext = os.path.splitext(product_image.filename)[1].lower() or ".png"
                mime_type = "image/jpeg" if ext in [".jpg", ".jpeg"] else ("image/webp" if ext == ".webp" else "image/png")
                save_name = f"meta_ref_{uuid.uuid4().hex}{ext}"
                save_path = os.path.join("static/generated", save_name)
                with open(save_path, "wb") as f:
                    f.write(product_bytes)
                product_data_uri = image_bytes_to_data_uri(product_bytes, mime_type)
        # Check referenced product_image_path from campaign analysis
        elif product_image_path:
            clean_path = product_image_path.lstrip("/").replace("\\", "/")
            if os.path.exists(clean_path):
                with open(clean_path, "rb") as f:
                    product_bytes = f.read()
                ext = os.path.splitext(clean_path)[1].lower() or ".png"
                mime_type = "image/jpeg" if ext in [".jpg", ".jpeg"] else ("image/webp" if ext == ".webp" else "image/png")
                product_data_uri = image_bytes_to_data_uri(product_bytes, mime_type)

        # 4. Engine Dispatch (Qwen-Image-2.1 vs Gemini Nano Banana Pro)
        image_bytes = None
        used_model = "Qwen-Image-2.1 (Self-Hosted)"
        engine_clean = (engine or "qwen").lower().strip()
        is_banana = engine_clean in ["gemini", "banana", "nano-banana", "nano-banana-pro", "nanobanana"]
        use_qwen = not is_banana and (engine_clean in ["qwen", "self-hosted"] or is_self_hosted_enabled())

        if use_qwen:
            try:
                logger.info(
                    f"[Meta Ad Studio] Dispatching to Qwen-Image-2.1: {target_w}x{target_h}, steps={steps}, has_ref={bool(product_data_uri)}"
                )
                image_bytes = await generate_image_async(
                    prompt=visual_prompt,
                    width=target_w,
                    height=target_h,
                    steps=steps,
                    seed=seed,
                    image_uri=product_data_uri,
                    api_key=x_image_api_key or get_image_api_key(),
                    timeout=600
                )
                used_model = "Qwen-Image-2.1 (Self-Hosted)"
            except Exception as qwen_err:
                logger.warning(f"[Meta Ad Studio] Qwen-Image-2.1 failed: {qwen_err}")
                if should_fallback_to_gemini() and engine_clean not in ["qwen"]:
                    logger.info("[Meta Ad Studio] Falling back to Gemini Nano Banana Pro...")
                else:
                    raise HTTPException(status_code=503, detail=str(qwen_err))

        if not image_bytes:
            if not client:
                raise HTTPException(status_code=400, detail="Gemini API Key required for Nano Banana Pro generation.")
            logger.info("[Meta Ad Studio] Generating with Gemini Nano Banana Pro (nano-banana-pro-preview)...")
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
                raise HTTPException(status_code=500, detail="Model failed to return image bytes.")
            used_model = "nano-banana-pro-preview"

        # 5. Save generated Meta creative
        out_filename = f"meta_ad_{uuid.uuid4().hex}.png"
        out_path = os.path.join("static/generated", out_filename)
        if isinstance(image_bytes, str):
            image_bytes = image_bytes.encode('latin1')
        with open(out_path, "wb") as f:
            f.write(image_bytes)

        logger.info(f"[Meta Ad Studio] Successfully generated Meta Image Ad: {out_path}")

        # 6. Render high-converting Direct Response composite ad
        composite_filename = f"meta_ad_composite_{uuid.uuid4().hex}.png"
        composite_path = os.path.join("static/generated", composite_filename)
        final_image_url = f"/static/generated/{out_filename}"
        try:
            single_blueprint = {
                "creative_id": 1,
                "framework_key": "problem_solution",
                "framework_name": angle_name,
                "hook_badge": "VERIFIED SOLUTION",
                "headline": headline,
                "subheadline": f"Engineered by {brand_name} for daily high performance.",
                "primary_text": primary_text,
                "cta": cta,
                "callout_points": [headline, "100% Quality Guaranteed", "Fast Expedited Shipping"],
            }
            render_meta_ad_composite(
                base_image_path=out_path,
                blueprint=single_blueprint,
                brand_name=brand_name,
                product_name=product_name,
                output_path=composite_path,
                aspect_ratio=aspect_ratio
            )
            final_image_url = f"/static/generated/{composite_filename}"
        except Exception as comp_err:
            logger.warning(f"Composite overlay generation fallback: {comp_err}")

        return {
            "status": "success",
            "image_url": f"/static/generated/{out_filename}",
            "raw_image_url": f"/static/generated/{out_filename}",
            "composite_image_url": final_image_url,
            "filename": out_filename,
            "primary_text": primary_text,
            "headline": headline,
            "cta": cta,
            "brand_name": brand_name,
            "product_name": product_name,
            "angle": angle_name,
            "aspect_ratio": aspect_ratio,
            "width": target_w,
            "height": target_h,
            "model_used": used_model,
            "engine": "banana" if ("banana" in used_model or is_banana) else "qwen",
            "visual_prompt": visual_prompt,
            "has_product_reference": bool(product_bytes)
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[Meta Ad Studio] Generation failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/campaign/meta-creative-suite/blueprints")
async def get_meta_creative_blueprints_endpoint(
    request: Request,
    x_api_key: Optional[str] = Header(None)
):
    try:
        body = await request.json()
        client = get_client(x_api_key)
        blueprints = generate_meta_creative_blueprints(body, client=client)
        return {"status": "success", "blueprints": blueprints}
    except Exception as e:
        logger.error(f"Generate blueprints failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/campaign/meta-creative-suite/render-one")
async def render_meta_creative_suite_one(
    blueprint_json: str = Form(...),
    brand_name: str = Form(...),
    product_name: str = Form(...),
    product_category: str = Form(""),
    target_audience_persona: str = Form(""),
    aspect_ratio: str = Form("4:5"),
    engine: str = Form("qwen"),
    product_image_path: Optional[str] = Form(None),
    product_image: Optional[UploadFile] = File(None),
    custom_directive: Optional[str] = Form(None),
    steps: int = Form(35),
    x_api_key: Optional[str] = Header(None),
    x_image_api_key: Optional[str] = Header(None)
):
    try:
        blueprint = json.loads(blueprint_json)
        client = get_client(x_api_key)
        
        product_bytes = None
        mime_type = "image/png"
        if product_image and product_image.filename:
            product_bytes = await product_image.read()
            ext = os.path.splitext(product_image.filename)[1].lower() or ".png"
            mime_type = "image/jpeg" if ext in [".jpg", ".jpeg"] else ("image/webp" if ext == ".webp" else "image/png")

        res = await generate_single_meta_creative(
            blueprint=blueprint,
            brand_name=brand_name,
            product_name=product_name,
            product_category=product_category,
            target_audience_persona=target_audience_persona,
            aspect_ratio=aspect_ratio,
            engine=engine,
            product_image_path=product_image_path,
            product_bytes=product_bytes,
            mime_type=mime_type,
            custom_directive=custom_directive,
            steps=steps,
            client=client,
            api_key=x_api_key,
            image_api_key=x_image_api_key
        )
        return res
    except Exception as e:
        logger.error(f"Render one meta creative failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/campaign/meta-creative-suite/render-all")
async def render_meta_creative_suite_all(
    blueprints_json: str = Form(...),
    brand_name: str = Form(...),
    product_name: str = Form(...),
    product_category: str = Form(""),
    target_audience_persona: str = Form(""),
    aspect_ratio: str = Form("4:5"),
    engine: str = Form("qwen"),
    product_image_path: Optional[str] = Form(None),
    product_image: Optional[UploadFile] = File(None),
    steps: int = Form(35),
    x_api_key: Optional[str] = Header(None),
    x_image_api_key: Optional[str] = Header(None)
):
    try:
        blueprints = json.loads(blueprints_json)
        client = get_client(x_api_key)
        
        product_bytes = None
        mime_type = "image/png"
        if product_image and product_image.filename:
            product_bytes = await product_image.read()
            ext = os.path.splitext(product_image.filename)[1].lower() or ".png"
            mime_type = "image/jpeg" if ext in [".jpg", ".jpeg"] else ("image/webp" if ext == ".webp" else "image/png")

        results = []
        for bp in blueprints:
            try:
                res = await generate_single_meta_creative(
                    blueprint=bp,
                    brand_name=brand_name,
                    product_name=product_name,
                    product_category=product_category,
                    target_audience_persona=target_audience_persona,
                    aspect_ratio=aspect_ratio,
                    engine=engine,
                    product_image_path=product_image_path,
                    product_bytes=product_bytes,
                    mime_type=mime_type,
                    steps=steps,
                    client=client,
                    api_key=x_api_key,
                    image_api_key=x_image_api_key
                )
                results.append(res)
            except Exception as item_err:
                logger.warning(f"Error rendering creative #{bp.get('creative_id')}: {item_err}")

        return {"status": "success", "creatives": results}
    except Exception as e:
        logger.error(f"Render all meta creatives failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/campaign/meta-ads")
async def get_meta_ads_history():
    """Retrieve session generated Meta image ads."""
    gen_dir = "static/generated"
    items = []
    if os.path.exists(gen_dir):
        files = [f for f in os.listdir(gen_dir) if f.startswith("meta_ad_") and f.endswith(".png")]
        files.sort(key=lambda x: os.path.getmtime(os.path.join(gen_dir, x)), reverse=True)
        for f in files[:20]:
            items.append({
                "filename": f,
                "url": f"/static/generated/{f}",
                "created_at": os.path.getmtime(os.path.join(gen_dir, f))
            })
    return {"meta_ads": items}

@app.post("/api/generate-storyboard")
async def generate_storyboard(
    req: StoryboardRequest,
    x_api_key: Optional[str] = Header(None),
    x_image_api_key: Optional[str] = Header(None)
):
    try:
        client = get_client(x_api_key)
        
        # Read the storyboard template
        template_path = "storyboard_prompt_template.md"
        if os.path.exists(template_path):
            with open(template_path, "r", encoding="utf-8") as f:
                template_content = f.read()
        else:
            raise HTTPException(status_code=500, detail="Storyboard template not found")
            
        # Parse visual style presets from template
        # UGC_REALISTIC, CINEMATIC_PREMIUM, PIXAR_3D_STYLIZED, CLEAN_STUDIO, FOOD_APPETITE
        style_blocks = {
            "UGC_REALISTIC": "Photorealistic UGC creator style, shot-on-phone authenticity with editorial polish, real relatable human moments, natural expressions, soft natural daylight, home environment, 8K detail, no CGI look.",
            "CINEMATIC_PREMIUM": "High-end commercial cinematography, realistic handheld camera physics, golden-hour urban tones, shallow depth of field, luxury campaign finish, motivated lighting, 4K HDR realism.",
            "PIXAR_3D_STYLIZED": "Premium Pixar-style 3D stylized rendering, soft global illumination, vivid but calm color grading, charming expressive character, gentle depth of field, serene polished CG finish.",
            "CLEAN_STUDIO": "Minimal studio product photography, seamless backdrop in brand color, controlled softbox lighting, floating product hero shots, precise reflections, Apple-style negative space.",
            "FOOD_APPETITE": "Macro food cinematography, steam and texture emphasis, rich saturated appetite colors, slow-motion-feel splash and drizzle moments, warm inviting kitchen light."
        }
        
        style_block = style_blocks.get(req.visual_style, style_blocks["UGC_REALISTIC"])
        
        # Fill variables in the prompt template
        storyboard_prompt = (
            f"Create a crisp, clean, professional AD STORYBOARD POSTER for \"{req.product_name}\" by {req.brand_name}.\n\n"
            f"LAYOUT & FORMAT:\n"
            f"9:16 layout, clean white background, thin black panel borders, bold black sans-serif typography, premium advertising-agency presentation board. Grid of 4 numbered storyboard panels arranged left-to-right, top-to-bottom (2 columns x 2 rows). Each panel is a fully rendered cinematic frame — NOT a sketch — with a number badge in the top-left corner, a bold shot title, a one-line caption beneath it, and a small clock icon with its duration.\n\n"
            f"TOP HEADER (exact text, large bold type):\n"
            f"\"{req.product_name}\" — subtitle: \"TOTAL VIDEO TIME: 10 SECONDS · 4 SHOTS · {req.mood_keywords}\"\n"
            f"Legend row of 4 small icons with labels: HOOK, REVEAL, BENEFIT, CTA.\n\n"
            f"VISUAL STYLE:\n"
            f"{style_block}\n"
            f"Color palette locked to: {req.color_palette}. Lighting: soft natural window daylight.\n\n"
            f"CONSISTENCY LOCK (critical — this board is a video-generation reference):\n"
            f"The SAME product appears in every panel where mentioned: {req.product_visual_description}. Preserve exact packaging shape, label layout, colors, cap design, materials, and proportions across all panels. Hero angle: {req.product_hero_angle}.\n"
            f"The SAME single on-screen talent appears throughout: {req.on_screen_talent}. Identical face, hair, outfit, and skin tone in every panel — no character drift.\n"
            f"Setting consistent across panels: {req.setting}.\n\n"
            f"THE 4 PANELS (render each as a distinct full-frame cinematic shot):\n\n"
            f"Panel 1 — HOOK SHOT (~2.5s): {req.shot_1} Caption text: \"{req.hook_line}\"\n"
            f"Panel 2 — PRODUCT REVEAL & ACTION (~2.5s): {req.shot_2}\n"
            f"Panel 3 — BENEFIT / TRANSFORMATION (~2.5s): {req.shot_3}\n"
            f"Panel 4 — CALL TO ACTION / CTA (~2.5s): {req.shot_4} Caption text: \"{req.cta_line}\" with \"{req.logo_text}\" rendered as clean typography.\n\n"
            f"FOOTER STRIP (4 columns, small icons + short text):\n"
            f"• VIDEO FLOW: \"4 shots ≈ 10 seconds. Hook to CTA.\"\n"
            f"• CAMERA TIPS: \"macro on product texture, close-up on talent expression, wide establishing on {req.setting}, slow push-in on final CTA frame\"\n"
            f"• LIGHT & STYLE: \"soft natural window daylight, {req.color_palette}, shallow depth of field\"\n"
            f"• AUDIENCE NOTES: \"made for {req.target_audience_persona} — every frame must feel {req.mood_keywords}\"\n\n"
            f"TYPOGRAPHY RULES: all text short, high-contrast, perfectly legible; no paragraph text inside image panels; captions live in white bars below each frame, never overlapping the image.\n\n"
            f"NEGATIVE: watermark, extra logos, misspelled text, blurry frames, distorted hands, warped product packaging, inconsistent character faces, cluttered layout, overlapping panels, sketch lines, low quality."
        )
        
        # Check self-hosted preference
        use_self_hosted = req.use_self_hosted if req.use_self_hosted is not None else is_self_hosted_enabled()
        image_bytes = None
        used_model = "nano-banana-pro-preview"

        ref_image_uri = None
        if req.product_image_paths:
            for img_path in req.product_image_paths:
                rel_path = img_path.lstrip("/")
                if os.path.exists(rel_path):
                    ref_image_uri = image_file_to_data_uri(rel_path)
                    break

        if use_self_hosted:
            try:
                logger.info(f"Generating storyboard with Qwen-Image-2.1 (Self-Hosted)... Prompt length: {len(storyboard_prompt)}")
                image_bytes = await generate_image_async(
                    prompt=storyboard_prompt,
                    width=1536 if not ref_image_uri else None,
                    height=2752 if not ref_image_uri else None,
                    steps=35,
                    image_uri=ref_image_uri,
                    api_key=x_image_api_key or get_image_api_key(),
                    timeout=600
                )
                used_model = "Qwen-Image-2.1 (Self-Hosted)"
            except Exception as sh_err:
                logger.warning(f"Self-hosted Qwen-Image-2.1 failed: {sh_err}")
                if should_fallback_to_gemini() and client:
                    logger.info("Falling back to Gemini Nano Banana Pro...")
                else:
                    raise HTTPException(status_code=503, detail=str(sh_err))

        if not image_bytes:
            # Fallback or default to Gemini Nano Banana Pro
            logger.info(f"Generating storyboard with Nano Banana Pro (nano-banana-pro-preview)... Prompt length: {len(storyboard_prompt)}")
            
            # Prepare contents with reference images if provided
            contents = [storyboard_prompt]
            if req.product_image_paths:
                logger.info(f"Adding {len(req.product_image_paths)} product images as consistency reference to Nano Banana Pro...")
                for img_path in req.product_image_paths:
                    relative_path = img_path.lstrip("/")
                    if os.path.exists(relative_path):
                        with open(relative_path, "rb") as f:
                            img_data = f.read()
                        if isinstance(img_data, str):
                            img_data = img_data.encode('latin1')
                        ext = os.path.splitext(img_path)[1].lower()
                        mime_type = "image/jpeg"
                        if ext == ".png":
                            mime_type = "image/png"
                        elif ext == ".gif":
                            mime_type = "image/gif"
                        elif ext == ".webp":
                            mime_type = "image/webp"
                            
                        contents.append(
                            types.Part.from_bytes(data=img_data, mime_type=mime_type)
                        )
            
            response = client.models.generate_content(
                model='nano-banana-pro-preview',
                contents=contents
            )
            
            if response.candidates:
                for part in response.candidates[0].content.parts:
                    if part.inline_data and part.inline_data.data:
                        image_bytes = part.inline_data.data
                        break
                        
            if not image_bytes:
                raise HTTPException(status_code=500, detail="Nano Banana Pro failed to generate storyboard image")
            used_model = "nano-banana-pro-preview"
                
        # Save generated storyboard image
        import uuid
        ext = ".png" if "Qwen" in used_model else ".jpg"
        filename = f"storyboard_{uuid.uuid4().hex}{ext}"
        file_path = os.path.join("static/generated", filename)
        
        if isinstance(image_bytes, str):
            image_bytes = image_bytes.encode('latin1')
        with open(file_path, "wb") as f:
            f.write(image_bytes)
            
        logger.info(f"Storyboard generated with {used_model} and saved to {file_path}")
        return {"storyboard_image_url": f"/static/generated/{filename}", "model_used": used_model}
        
    except Exception as e:
        logger.error(f"Storyboard generation failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

def extract_video_url(data: dict) -> Optional[str]:
    if not data:
        return None
    result_urls = data.get("resultUrls") or data.get("result_urls")
    if result_urls and isinstance(result_urls, list) and len(result_urls) > 0:
        return result_urls[0]
    for key in ["video_url", "resultUrl", "result_video_url", "url", "videoUrl"]:
        if data.get(key):
            return data.get(key)
    result = data.get("result")
    if result and isinstance(result, dict):
        for key in ["video_url", "resultUrl", "result_video_url", "url", "videoUrl"]:
            if result.get(key):
                return result.get(key)
        res_urls = result.get("resultUrls") or result.get("result_urls")
        if res_urls and isinstance(res_urls, list) and len(res_urls) > 0:
            return res_urls[0]
    return None

def safe_b64decode(data) -> bytes:
    if isinstance(data, bytes):
        if b"ftyp" in data[:20]:
            return data
        try:
            return base64.b64decode(data)
        except Exception:
            return data
    elif isinstance(data, str):
        if data.startswith("data:"):
            if "," in data:
                data = data.split(",", 1)[1]
        try:
            return base64.b64decode(data)
        except Exception:
            return data.encode('latin1')
    raise TypeError(f"Unsupported video data type: {type(data)}")

def safe_b64encode(data) -> bytes:
    if isinstance(data, str):
        data = data.encode('latin1')
    return base64.b64encode(data)

def get_avatars_by_ethnicity(ethnicity_query: str) -> List[dict]:
    try:
        library_path = "avatar_character_library.json"
        if not os.path.exists(library_path):
            logger.warning("avatar_character_library.json not found in workspace")
            return []
        with open(library_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        # Try to find matching ethnicity group
        query = ethnicity_query.lower()
        for eth_group in data.get("ethnicities", []):
            group_name = eth_group.get("ethnicity", "").lower()
            group_region = eth_group.get("region", "").lower()
            
            # Simple substring matching
            if query in group_name or group_name in query or query in group_region or group_region in query:
                logger.info(f"Matched library group: {eth_group.get('ethnicity')}")
                return eth_group.get("avatars", [])
                
        # Fallback: if no match, just return European (Slavic & Western European)
        for eth_group in data.get("ethnicities", []):
            if "european" in eth_group.get("ethnicity", "").lower():
                logger.info(f"Fallback to European library group")
                return eth_group.get("avatars", [])
                
        # Last resort fallback: first group
        if data.get("ethnicities"):
            return data["ethnicities"][0].get("avatars", [])
    except Exception as e:
        logger.error(f"Error reading avatar library: {e}")
    return []

# Global dictionary to track asynchronous background video jobs
video_jobs = {}

async def poll_seedance_background(
    task_id: str,
    job_id: str,
    headers: dict,
    video_public_url: Optional[str]
):
    try:
        max_retries = 450  # Poll for up to 15 minutes in the background
        delay = 2
        
        for i in range(max_retries):
            await asyncio.sleep(delay)
            poll_url = f"https://api.kie.ai/api/v1/jobs/recordInfo?taskId={task_id}"
            poll_res = requests.get(poll_url, headers=headers, timeout=10)
            if poll_res.status_code == 200:
                poll_json = poll_res.json()
                if poll_json.get("code") == 200:
                    job_data = poll_json.get("data", {})
                    status = job_data.get("status", "").lower()
                    logger.info(f"Background Kie AI task {task_id} status: {status}")
                    
                    # Save status check JSON to public path for debugging
                    try:
                        import json
                        with open("static/generated/kie_poll_debug.json", "w") as df:
                            json.dump(poll_json, df, indent=2)
                    except Exception as de:
                        logger.error(f"Failed to write poll debug: {de}")
                        
                    if status in ["success", "succeeded", "finished", "completed", "done"]:
                        video_public_url = extract_video_url(job_data)
                        break
                    elif status in ["fail", "failed", "error"]:
                        video_jobs[job_id] = {
                            "status": "failed",
                            "error": f"Kie AI task failed: {poll_json.get('msg')}"
                        }
                        return
                else:
                    logger.error(f"Kie AI recordInfo returned error: {poll_json}")
            else:
                logger.error(f"Kie AI recordInfo HTTP error: {poll_res.text}")
                
        if not video_public_url:
            video_jobs[job_id] = {
                "status": "failed",
                "error": "Kie AI video generation timed out (15 minutes)"
            }
            return
            
        logger.info(f"Video generation successful on Kie AI. Downloading: {video_public_url}")
        
        video_res = requests.get(video_public_url, timeout=45)
        video_res.raise_for_status()
        
        import uuid
        filename = f"ad_video_{uuid.uuid4().hex}.mp4"
        file_path = os.path.join("static/generated", filename)
        
        with open(file_path, "wb") as f:
            f.write(video_res.content)
            
        logger.info(f"Downloaded video and saved locally to {file_path}")
        video_jobs[job_id] = {
            "status": "success",
            "video_url": f"/static/generated/{filename}"
        }
    except Exception as e:
        logger.error(f"Background video polling failed: {e}", exc_info=True)
        video_jobs[job_id] = {
            "status": "failed",
            "error": str(e)
        }

async def generate_omni_background(
    job_id: str,
    storyboard_image_url: str,
    video_prompt: str,
    product_image_paths: Optional[List[str]],
    api_key: Optional[str],
    aspect_ratio: str = "9:16"
):
    try:
        client = get_client(api_key)
        
        # Resolve storyboard image path
        relative_path = storyboard_image_url.lstrip("/")
        if not os.path.exists(relative_path):
            video_jobs[job_id] = {"status": "failed", "error": "Storyboard image not found locally"}
            return
            
        with open(relative_path, "rb") as img_file:
            img_bytes = img_file.read()
            
        base64_image = safe_b64encode(img_bytes).decode('utf-8')
        
        # Prepare Omni Flash instructions
        is_vertical = aspect_ratio == "9:16"
        ratio_term = "vertical 9:16" if is_vertical else "landscape 16:9"
        omni_prompt = (
            "IMPORTANT: The attached storyboard is a reference board. Treat each numbered panel as an "
            "individual full-screen shot, read left-to-right, top-to-bottom. Do NOT animate the collage or "
            "show the grid. Total duration 10 seconds across 4 shots with hard cuts. "
            "Preserve the exact product design, label layout, package look-and-feel, and talent from the reference storyboard in every shot. "
            "Also reference the attached product photos to ensure the product appears identical and consistent in the generated video.\n\n"
            f"Ad Motion Guidelines: {video_prompt}\n"
            f"Animate this storyboard into a high-quality {ratio_term} advertising video."
        )
        
        inputs = []
        
        # 1. Add Storyboard Image reference
        inputs.append({"type": "image", "data": base64_image, "mime_type": "image/jpeg"})
        
        # 2. Add original uploaded product image references if available
        if product_image_paths:
            logger.info(f"Adding {len(product_image_paths)} uploaded product image references to Omni Flash...")
            for img_path in product_image_paths:
                rel_path = img_path.lstrip("/")
                if os.path.exists(rel_path):
                    with open(rel_path, "rb") as f:
                        img_data = f.read()
                    base64_ref = safe_b64encode(img_data).decode('utf-8')
                    ext = os.path.splitext(img_path)[1].lower()
                    mime_type = "image/jpeg"
                    if ext == ".png":
                        mime_type = "image/png"
                    elif ext == ".gif":
                        mime_type = "image/gif"
                    elif ext == ".webp":
                        mime_type = "image/webp"
                        
                    inputs.append({"type": "image", "data": base64_ref, "mime_type": mime_type})
        
        # 3. Add text prompt instructions
        inputs.append({"type": "text", "text": omni_prompt})
        
        logger.info("Calling Omni Flash interactions API in the background...")
        interaction = client.interactions.create(
            model='gemini-omni-flash-preview',
            input=inputs
        )
        
        video_b64 = None
        if hasattr(interaction, 'output_video') and interaction.output_video:
            video_b64 = interaction.output_video.data
        else:
            for step in getattr(interaction, 'steps', []):
                if isinstance(step, dict) and step.get('type') == 'model_output' and step.get('content'):
                    for part in step['content']:
                        if part.get('type') == 'video':
                            video_b64 = part.get('data')
                            break
                            
        if not video_b64:
            video_jobs[job_id] = {"status": "failed", "error": "Omni Flash did not return any video bytes"}
            return
            
        import uuid
        filename = f"ad_video_{uuid.uuid4().hex}.mp4"
        file_path = os.path.join("static/generated", filename)
        
        video_data = safe_b64decode(video_b64)
        with open(file_path, "wb") as f:
            f.write(video_data)
            
        logger.info(f"Video generated and saved to {file_path}")
        video_jobs[job_id] = {
            "status": "success",
            "video_url": f"/static/generated/{filename}"
        }
        
    except Exception as e:
        logger.error(f"Omni Flash background generation failed: {e}", exc_info=True)
        video_jobs[job_id] = {"status": "failed", "error": str(e)}

async def generate_minimax_background(
    job_id: str,
    storyboard_image_url: str,
    video_prompt: str,
    aspect_ratio: str = "9:16",
    product_image_paths: Optional[List[str]] = None,
    api_key: Optional[str] = None,
    api_url: Optional[str] = None,
    fallback_gemini_key: Optional[str] = None
):
    """Generate ad video using self-hosted MiniMax-H3 (SGLang) server with audio."""
    try:
        import time
        persist_job_update(job_id, {
            "status": "processing",
            "progress_msg": "Queued for MiniMax-H3 GPU server...",
            "progress": 5,
            "created_at": time.time()
        }, video_jobs)

        # Resolve storyboard reference image
        relative_path = storyboard_image_url.lstrip("/")
        first_frame_uri = None
        if os.path.exists(relative_path):
            first_frame_uri = image_file_to_data_uri(relative_path)
        elif product_image_paths:
            for p in product_image_paths:
                p_rel = p.lstrip("/")
                if os.path.exists(p_rel):
                    first_frame_uri = image_file_to_data_uri(p_rel)
                    break

        if not first_frame_uri:
            persist_job_update(job_id, {
                "status": "failed",
                "error": "Storyboard reference image not found locally"
            }, video_jobs)
            return

        aspect = "9:16" if aspect_ratio == "9:16" else "16:9"

        def on_poll(st_dict, poll_count):
            secs = poll_count * 10
            persist_job_update(job_id, {
                "status": "processing",
                "progress_msg": f"MiniMax-H3 synthesizing video & stereo audio... (~{secs}s elapsed)",
                "progress": min(10 + poll_count * 7, 92)
            }, video_jobs)

        logger.info(f"Triggering MiniMax-H3 video job for {job_id} (aspect={aspect}, duration=5s)...")
        video_bytes = await generate_video_async(
            prompt=video_prompt,
            seconds=5,
            aspect=aspect,
            short_edge=768,
            steps=30,
            first_frame_uri=first_frame_uri,
            api_url=api_url,
            api_key=api_key,
            poll_every=10,
            max_wait=1200,
            progress_callback=on_poll
        )

        import uuid
        filename = f"ad_video_{uuid.uuid4().hex}.mp4"
        file_path = os.path.join("static/generated", filename)

        with open(file_path, "wb") as f:
            f.write(video_bytes)

        logger.info(f"MiniMax-H3 video saved to {file_path}")
        persist_job_update(job_id, {
            "status": "success",
            "video_url": f"/static/generated/{filename}",
            "engine": "MiniMax-H3"
        }, video_jobs)

    except Exception as e:
        logger.error(f"MiniMax-H3 video generation failed: {e}", exc_info=True)
        if should_fallback_to_gemini() and fallback_gemini_key:
            logger.info("Falling back to Gemini Omni Flash...")
            persist_job_update(job_id, {
                "status": "processing",
                "progress_msg": "Self-hosted server offline/busy. Falling back to Gemini Omni Flash..."
            }, video_jobs)
            await generate_omni_background(
                job_id=job_id,
                storyboard_image_url=storyboard_image_url,
                video_prompt=video_prompt,
                product_image_paths=product_image_paths,
                api_key=fallback_gemini_key,
                aspect_ratio=aspect_ratio
            )
        else:
            persist_job_update(job_id, {
                "status": "failed",
                "error": str(e)
            }, video_jobs)

@app.post("/api/generate-video")
async def generate_video(
    req: VideoRequest,
    request: Request,
    background_tasks: BackgroundTasks,
    x_api_key: Optional[str] = Header(None),
    x_kie_key: Optional[str] = Header(None),
    x_video_api_key: Optional[str] = Header(None)
):
    try:
        import uuid
        import time
        job_id = f"job_{uuid.uuid4().hex}"
        video_jobs[job_id] = {"status": "processing", "created_at": time.time()}
        
        # Check if MiniMax-H3 should be used
        use_minimax = (
            req.generator in ["minimax", "self-hosted"] or
            req.use_self_hosted is True or
            (req.use_self_hosted is None and is_self_hosted_enabled() and req.generator not in ["seedance", "moneyprinter", "mpt", "omni-flash-forced"])
        )

        if use_minimax and req.generator not in ["seedance", "moneyprinter", "mpt"]:
            logger.info(f"Dispatching MiniMax-H3 self-hosted video task for job {job_id}...")
            background_tasks.add_task(
                generate_minimax_background,
                job_id=job_id,
                storyboard_image_url=req.storyboard_image_url,
                video_prompt=req.video_prompt,
                aspect_ratio=req.aspect_ratio,
                product_image_paths=req.product_image_paths,
                api_key=x_video_api_key or get_video_api_key(),
                api_url=get_video_api_url(),
                fallback_gemini_key=x_api_key or os.environ.get("GEMINI_API_KEY")
            )
            return {"status": "processing", "job_id": job_id}

        elif req.generator == "seedance":
            kie_key = x_kie_key or os.environ.get("KIE_API_KEY")
            if kie_key:
                kie_key = kie_key.strip()
            
            key_len = len(kie_key) if kie_key else 0
            masked_key = f"{kie_key[:4]}...{kie_key[-4:]}" if key_len > 8 else "too_short"
            logger.info(f"Using Kie AI API Key: length={key_len}, key={masked_key}")
            
            if not kie_key:
                raise HTTPException(status_code=400, detail="Kie AI API Key is required for Seedance 2 Mini")
                
            base_url = str(request.base_url).rstrip("/")
            if "127.0.0.1" in base_url or "localhost" in base_url:
                logger.warning("Localhost detected! Kie AI will not be able to fetch your local reference images.")
            
            storyboard_public_url = f"{base_url}{req.storyboard_image_url}"
            reference_urls = [storyboard_public_url]
            if req.product_image_paths:
                for path in req.product_image_paths:
                    reference_urls.append(f"{base_url}{path}")
                    
            kie_url = "https://api.kie.ai/api/v1/jobs/createTask"
            headers = {
                "Authorization": f"Bearer {kie_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": "bytedance/seedance-2-mini",
                "input": {
                    "prompt": req.video_prompt,
                    "aspect_ratio": req.aspect_ratio,
                    "reference_image_urls": reference_urls,
                    "duration": 10
                }
            }
            
            logger.info(f"Triggering Kie AI task for model bytedance/seedance-2-mini...")
            res = requests.post(kie_url, json=payload, headers=headers, timeout=15)
            if res.status_code != 200:
                raise HTTPException(status_code=res.status_code, detail=f"Kie AI error: {res.text}")
                
            res_json = res.json()
            if res_json.get("code") != 200:
                raise HTTPException(status_code=400, detail=f"Kie AI createTask failed: {res_json.get('msg')}")
                
            task_id = res_json.get("data", {}).get("taskId")
            if not task_id:
                raise HTTPException(status_code=500, detail="Kie AI response did not contain a taskId")
                
            logger.info(f"Kie AI task created successfully. Task ID: {task_id}. Dispatching background poller...")
            
            background_tasks.add_task(
                poll_seedance_background,
                task_id=task_id,
                job_id=job_id,
                headers=headers,
                video_public_url=None
            )
            return {"status": "processing", "job_id": job_id}
            
        elif req.generator in ["moneyprinter", "mpt"]:
            client = get_client(x_api_key)
            subject = req.hook_line or req.video_prompt[:60]
            script = req.voice_script or req.video_prompt
            pix_key = os.environ.get("PIXABAY_API_KEY")
            
            logger.info(f"Triggering in-process MoneyPrinterTurbo generator for job {job_id}...")
            background_tasks.add_task(
                execute_moneyprinter_job,
                job_id=job_id,
                subject=subject,
                custom_script=script,
                aspect_ratio=req.aspect_ratio,
                voice_name="en-US-ChristopherNeural",
                pixabay_key=pix_key,
                burn_subtitles=True,
                client=client,
                job_store=video_jobs
            )
            return {"status": "processing", "job_id": job_id}
            
        else:
            # Default: omni-flash
            background_tasks.add_task(
                generate_omni_background,
                job_id=job_id,
                storyboard_image_url=req.storyboard_image_url,
                video_prompt=req.video_prompt,
                product_image_paths=req.product_image_paths,
                api_key=x_api_key,
                aspect_ratio=req.aspect_ratio
            )
            return {"status": "processing", "job_id": job_id}
            
    except Exception as e:
        logger.error(f"Video generation failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/moneyprinter/generate")
async def generate_moneyprinter_standalone(
    req: MoneyPrinterRequest,
    background_tasks: BackgroundTasks,
    x_api_key: Optional[str] = Header(None)
):
    try:
        import uuid
        import time
        job_id = f"mpt_{uuid.uuid4().hex}"
        persist_job_update(job_id, {
            "status": "processing",
            "progress_step": "1/4",
            "progress_msg": "Starting MoneyPrinter Turbo pipeline...",
            "created_at": time.time()
        }, video_jobs)
        
        client = get_client(x_api_key)
        pix_key = req.pixabay_key or os.environ.get("PIXABAY_API_KEY")
        
        logger.info(f"Starting standalone MoneyPrinterTurbo task {job_id} for subject: '{req.subject}'")
        background_tasks.add_task(
            execute_moneyprinter_job,
            job_id=job_id,
            subject=req.subject,
            custom_script=req.custom_script,
            aspect_ratio=req.aspect_ratio,
            voice_name=req.voice_name,
            pixabay_key=pix_key,
            burn_subtitles=req.burn_subtitles,
            client=client,
            job_store=video_jobs
        )
        return {"status": "processing", "job_id": job_id}
    except Exception as e:
        logger.error(f"Failed to start MoneyPrinter task: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


async def generate_studio_video_background(
    job_id: str,
    mode: str,
    prompt: str,
    negative_prompt: Optional[str],
    aspect_ratio: str,
    resolution: str,
    duration: int,
    reference_image_paths: List[str],
    first_frame_path: Optional[str],
    last_frame_path: Optional[str],
    source_video_path: Optional[str],
    api_key: Optional[str],
    generator: str = "minimax",
    video_api_key: Optional[str] = None,
    short_edge: Optional[int] = None,
    steps: Optional[int] = None,
    seed: Optional[int] = None
):
    try:
        import time
        # Check if MiniMax-H3 should be used
        use_minimax = (
            generator in ["minimax", "self-hosted"] or
            (is_self_hosted_enabled() and generator not in ["omni-flash", "omniflash", "omni-flash-forced"])
        )

        if use_minimax and mode in ["prompt_images", "first_last_frame", "t2va", "fl2va_single", "fl2va_dual"]:
            try:
                persist_job_update(job_id, {
                    "status": "processing",
                    "progress_msg": "Queued for MiniMax-H3 GPU server (video + stereo audio)...",
                    "progress": 5,
                    "created_at": time.time()
                }, video_jobs)

                first_frame_uri = None
                last_frame_uri = None

                if mode in ["first_last_frame", "fl2va_dual"]:
                    if first_frame_path and os.path.exists(first_frame_path):
                        first_frame_uri = image_file_to_data_uri(first_frame_path)
                    if last_frame_path and os.path.exists(last_frame_path):
                        last_frame_uri = image_file_to_data_uri(last_frame_path)
                elif mode in ["prompt_images", "fl2va_single"]:
                    if first_frame_path and os.path.exists(first_frame_path):
                        first_frame_uri = image_file_to_data_uri(first_frame_path)
                    elif reference_image_paths and os.path.exists(reference_image_paths[0]):
                        first_frame_uri = image_file_to_data_uri(reference_image_paths[0])

                target_short_edge = short_edge
                if not target_short_edge:
                    if resolution in ("1344p", "1080p", "4k", "4K", "1344"):
                        target_short_edge = 1344
                    elif resolution in ("480p", "480"):
                        target_short_edge = 480
                    else:
                        target_short_edge = 768

                aspect = "9:16" if aspect_ratio == "9:16" else ("16:9" if aspect_ratio == "16:9" else "auto")
                dur = max(4, min(15, int(duration)))
                num_steps = steps if (steps and 20 <= steps <= 50) else 30

                def on_studio_poll(st_dict, poll_count):
                    secs = poll_count * 10
                    persist_job_update(job_id, {
                        "status": "processing",
                        "progress_msg": f"MiniMax-H3 synthesizing video & audio... (~{secs}s elapsed)",
                        "progress": min(10 + poll_count * 7, 92)
                    }, video_jobs)

                logger.info(
                    f"Triggering MiniMax-H3 video job for {job_id} "
                    f"(mode={mode}, short_edge={target_short_edge}, dur={dur}s, steps={num_steps}, seed={seed})..."
                )
                video_bytes = await generate_video_async(
                    prompt=prompt,
                    seconds=dur,
                    aspect=aspect,
                    short_edge=target_short_edge,
                    steps=num_steps,
                    seed=seed,
                    first_frame_uri=first_frame_uri,
                    last_frame_uri=last_frame_uri,
                    api_key=video_api_key or get_video_api_key(),
                    api_url=get_video_api_url(),
                    poll_every=10,
                    max_wait=1200,
                    progress_callback=on_studio_poll
                )

                import uuid
                filename = f"minimax_video_{uuid.uuid4().hex}.mp4"
                file_path = os.path.join("static/generated", filename)

                with open(file_path, "wb") as f:
                    f.write(video_bytes)

                logger.info(f"MiniMax-H3 video saved to {file_path}")
                persist_job_update(job_id, {
                    "status": "success",
                    "video_url": f"/static/generated/{filename}",
                    "mode": mode,
                    "resolution": f"{target_short_edge}p",
                    "short_edge": target_short_edge,
                    "aspect_ratio": aspect,
                    "duration": dur,
                    "steps": num_steps,
                    "seed": seed,
                    "prompt": prompt,
                    "engine": "MiniMax-H3",
                    "has_audio": True
                }, video_jobs)
                return

            except Exception as minimax_err:
                logger.warning(f"MiniMax-H3 studio generation failed: {minimax_err}")
                if should_fallback_to_gemini() and api_key and generator not in ["minimax"]:
                    logger.info("Falling back to Gemini Omni Flash for studio video...")
                    persist_job_update(job_id, {
                        "status": "processing",
                        "progress_msg": "Self-hosted server busy/offline. Falling back to Gemini Omni Flash..."
                    }, video_jobs)
                else:
                    persist_job_update(job_id, {
                        "status": "failed",
                        "error": str(minimax_err)
                    }, video_jobs)
                    return

        client = get_client(api_key)
        
        # Build prompt instructions based on mode
        orientation_label = "horizontal landscape (16:9)" if aspect_ratio == "16:9" else ("vertical portrait (9:16)" if aspect_ratio == "9:16" else "square (1:1)")
        
        system_instructions = (
            f"Generate an ultra-high quality AI video in {orientation_label}, target resolution: {resolution}, duration: {duration} seconds.\n"
        )
        
        if mode == "first_last_frame":
            studio_prompt = (
                f"{system_instructions}\n"
                "MODE: FIRST FRAME & LAST FRAME INTERPOLATION.\n"
                "The first attached image represents the EXACT START FRAME (t=0.0s).\n"
                f"The second attached image represents the EXACT LAST FRAME (t={duration}.0s).\n"
                "Render a fluid, continuous cinematic sequence transitioning seamlessly from the start frame composition to the end frame composition.\n"
                f"Action and motion directions: {prompt}\n"
            )
        elif mode == "edit_video":
            studio_prompt = (
                f"{system_instructions}\n"
                "MODE: VIDEO-TO-VIDEO EDITING / RE-RENDERING.\n"
                "The attached video is the source reference video.\n"
                "Modify and transform the source video following these edit instructions while preserving camera motion, core composition, and subject timing:\n"
                f"Edit Instructions: {prompt}\n"
            )
        else: # prompt_images
            ref_clause = f"Reference the {len(reference_image_paths)} attached reference images to maintain strict character identity, asset appearance, lighting, and style consistency.\n" if reference_image_paths else ""
            studio_prompt = (
                f"{system_instructions}\n"
                "MODE: TEXT & REFERENCE IMAGES TO VIDEO.\n"
                f"{ref_clause}"
                f"Scene Description and Action: {prompt}\n"
            )
            
        if negative_prompt and negative_prompt.strip():
            studio_prompt += f"NEGATIVE PROMPT (strictly avoid): {negative_prompt.strip()}\n"

        inputs = []
        
        # 1. First & Last Frame Mode
        if mode == "first_last_frame":
            for frame_path in [first_frame_path, last_frame_path]:
                if frame_path and os.path.exists(frame_path):
                    with open(frame_path, "rb") as f:
                        img_bytes = f.read()
                    b64 = safe_b64encode(img_bytes).decode('utf-8')
                    ext = os.path.splitext(frame_path)[1].lower()
                    mime = "image/png" if ext == ".png" else ("image/webp" if ext == ".webp" else "image/jpeg")
                    inputs.append({"type": "image", "data": b64, "mime_type": mime})
                    
        # 2. Edit Video Mode
        elif mode == "edit_video" and source_video_path and os.path.exists(source_video_path):
            with open(source_video_path, "rb") as f:
                vid_bytes = f.read()
            b64 = safe_b64encode(vid_bytes).decode('utf-8')
            ext = os.path.splitext(source_video_path)[1].lower()
            mime = "video/quicktime" if ext in [".mov", ".qt"] else ("video/webm" if ext == ".webm" else "video/mp4")
            inputs.append({"type": "video", "data": b64, "mime_type": mime})
            
        # 3. Reference images
        elif reference_image_paths:
            for img_path in reference_image_paths:
                if img_path and os.path.exists(img_path):
                    with open(img_path, "rb") as f:
                        img_bytes = f.read()
                    b64 = safe_b64encode(img_bytes).decode('utf-8')
                    ext = os.path.splitext(img_path)[1].lower()
                    mime = "image/png" if ext == ".png" else ("image/webp" if ext == ".webp" else "image/jpeg")
                    inputs.append({"type": "image", "data": b64, "mime_type": mime})
                    
        inputs.append({"type": "text", "text": studio_prompt})
        
        logger.info(f"Dispatching Studio Omni Flash video job {job_id} (mode={mode}, res={resolution}, ratio={aspect_ratio}, dur={duration}s)...")
        
        video_b64 = None
        # Attempt primary generation using client.interactions.create
        try:
            interaction = client.interactions.create(
                model='gemini-omni-flash-preview',
                input=inputs
            )
            if hasattr(interaction, 'output_video') and interaction.output_video:
                video_b64 = interaction.output_video.data
            else:
                for step in getattr(interaction, 'steps', []):
                    if isinstance(step, dict) and step.get('type') == 'model_output' and step.get('content'):
                        for part in step['content']:
                            if part.get('type') == 'video':
                                video_b64 = part.get('data')
                                break
        except Exception as api_err:
            logger.warning(f"Interactions API attempt failed: {api_err}. Trying generate_videos fallback...")
            try:
                config_args = {
                    "aspect_ratio": aspect_ratio,
                    "resolution": resolution,
                    "duration_seconds": duration,
                }
                if negative_prompt:
                    config_args["negative_prompt"] = negative_prompt
                    
                first_img = None
                if mode == "first_last_frame" and first_frame_path and os.path.exists(first_frame_path):
                    with open(first_frame_path, "rb") as f:
                        first_img = types.Image(image_bytes=f.read())
                elif reference_image_paths and os.path.exists(reference_image_paths[0]):
                    with open(reference_image_paths[0], "rb") as f:
                        first_img = types.Image(image_bytes=f.read())
                        
                if mode == "first_last_frame" and last_frame_path and os.path.exists(last_frame_path):
                    with open(last_frame_path, "rb") as f:
                        config_args["last_frame"] = types.Image(image_bytes=f.read())
                        
                gen_config = types.GenerateVideosConfig(**config_args)
                op = client.models.generate_videos(
                    model="gemini-omni-flash-preview",
                    prompt=prompt,
                    image=first_img,
                    config=gen_config
                )
                import time
                while not op.done:
                    time.sleep(5)
                    op = client.operations.get(op)
                if op.response and op.response.generated_videos:
                    video_bytes = op.response.generated_videos[0].video.video_bytes
                    video_b64 = safe_b64encode(video_bytes).decode('utf-8')
            except Exception as gen_err:
                logger.error(f"Fallback generate_videos also failed: {gen_err}")
                raise api_err
                
        if not video_b64:
            video_jobs[job_id] = {"status": "failed", "error": "Omni Flash 1.1 did not return any video output"}
            return
            
        import uuid
        filename = f"studio_video_{uuid.uuid4().hex}.mp4"
        file_path = os.path.join("static/generated", filename)
        
        video_data = safe_b64decode(video_b64)
        with open(file_path, "wb") as f:
            f.write(video_data)
            
        logger.info(f"Studio video successfully generated and saved to {file_path}")
        video_jobs[job_id] = {
            "status": "success",
            "video_url": f"/static/generated/{filename}",
            "mode": mode,
            "resolution": resolution,
            "aspect_ratio": aspect_ratio,
            "duration": duration,
            "prompt": prompt,
            "engine": "Omni Flash 1.1"
        }
    except Exception as e:
        logger.error(f"Studio background generation failed: {e}", exc_info=True)
        video_jobs[job_id] = {"status": "failed", "error": str(e)}

@app.post("/api/studio/generate-video")
async def studio_generate_video(
    background_tasks: BackgroundTasks,
    mode: str = Form("prompt_images"),
    prompt: str = Form(...),
    negative_prompt: Optional[str] = Form(None),
    aspect_ratio: str = Form("16:9"),
    resolution: str = Form("720p"),
    duration: int = Form(6),
    generator: str = Form("minimax"),
    short_edge: Optional[int] = Form(None),
    steps: Optional[int] = Form(None),
    seed: Optional[int] = Form(None),
    reference_images: Optional[List[UploadFile]] = File(None),
    first_frame: Optional[UploadFile] = File(None),
    last_frame: Optional[UploadFile] = File(None),
    source_video: Optional[UploadFile] = File(None),
    x_api_key: Optional[str] = Header(None),
    x_video_api_key: Optional[str] = Header(None)
):
    try:
        import uuid
        import time
        job_id = f"job_studio_{uuid.uuid4().hex}"
        video_jobs[job_id] = {"status": "processing", "created_at": time.time()}
        
        # Save reference images if present
        saved_ref_paths = []
        if reference_images:
            for img in reference_images:
                if img and img.filename:
                    ext = os.path.splitext(img.filename)[1] or ".jpg"
                    fname = f"ref_{uuid.uuid4().hex}{ext}"
                    fpath = os.path.join("static/generated", fname)
                    content = await img.read()
                    with open(fpath, "wb") as f:
                        f.write(content)
                    saved_ref_paths.append(fpath)
                    
        # Save first and last frame if present
        saved_first_frame = None
        if first_frame and first_frame.filename:
            ext = os.path.splitext(first_frame.filename)[1] or ".jpg"
            fname = f"frame_start_{uuid.uuid4().hex}{ext}"
            fpath = os.path.join("static/generated", fname)
            content = await first_frame.read()
            with open(fpath, "wb") as f:
                f.write(content)
            saved_first_frame = fpath
            
        saved_last_frame = None
        if last_frame and last_frame.filename:
            ext = os.path.splitext(last_frame.filename)[1] or ".jpg"
            fname = f"frame_end_{uuid.uuid4().hex}{ext}"
            fpath = os.path.join("static/generated", fname)
            content = await last_frame.read()
            with open(fpath, "wb") as f:
                f.write(content)
            saved_last_frame = fpath
            
        saved_source_video = None
        if source_video and source_video.filename:
            ext = os.path.splitext(source_video.filename)[1] or ".mp4"
            fname = f"source_vid_{uuid.uuid4().hex}{ext}"
            fpath = os.path.join("static/generated", fname)
            content = await source_video.read()
            with open(fpath, "wb") as f:
                f.write(content)
            saved_source_video = fpath
            
        background_tasks.add_task(
            generate_studio_video_background,
            job_id=job_id,
            mode=mode,
            prompt=prompt,
            negative_prompt=negative_prompt,
            aspect_ratio=aspect_ratio,
            resolution=resolution,
            duration=duration,
            reference_image_paths=saved_ref_paths,
            first_frame_path=saved_first_frame,
            last_frame_path=saved_last_frame,
            source_video_path=saved_source_video,
            api_key=x_api_key,
            generator=generator,
            video_api_key=x_video_api_key,
            short_edge=short_edge,
            steps=steps,
            seed=seed
        )
        
        return {"status": "processing", "job_id": job_id}
    except Exception as e:
        logger.error(f"Studio video dispatch failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/image-studio/generate")
async def generate_image_ad(
    prompt: str = Form(...),
    aspect_ratio: str = Form("1:1"),
    style_preset: Optional[str] = Form(None),
    engine: str = Form("qwen"),
    steps: int = Form(35),
    seed: Optional[int] = Form(None),
    negative_prompt: Optional[str] = Form(None),
    product_image: Optional[UploadFile] = File(None),
    x_api_key: Optional[str] = Header(None),
    x_image_api_key: Optional[str] = Header(None)
):
    """
    Generate high-converting AI Image Ads using self-hosted Qwen-Image-2.1 or Gemini fallback.
    Supports pure text-to-ad creative as well as product photo placement/remix.
    """
    try:
        import uuid
        
        # 1. Map aspect ratios to optimal model resolutions
        ratio_dimensions = {
            "1:1": (1024, 1024),
            "9:16": (1024, 1792),
            "16:9": (1792, 1024),
            "4:5": (1024, 1280),
        }
        target_w, target_h = ratio_dimensions.get(aspect_ratio, (1024, 1024))
        
        # 2. Style Preset Enrichment
        style_prompts = {
            "luxury_podium": "High-end luxury commercial advertisement, product displayed on an elegant white marble pedestal with brass accents, dramatic soft rim lighting, subtle volumetric atmosphere, crisp studio reflections, 8K ultra-sharp editorial quality.",
            "ugc_lifestyle": "Authentic UGC creator ad photo, held naturally in hands or placed on a warm wooden cafe table, soft natural golden morning window light, realistic smartphone photo depth of field, relatable candid lifestyle aesthetic.",
            "neon_cyber": "Electrifying cyberpunk ad visual, vibrant neon cyan and magenta rim lighting, dark glossy reflective wet floor, moody atmospheric volumetric smoke, futuristic energetic aesthetic, 8K commercial rendering.",
            "nature_botanical": "Organic botanical product advertisement, resting on earthy moss and natural river stones, lush green tropical leaves, gentle sun rays filtering through foliage, clean eco-friendly aesthetic.",
            "dramatic_splash": "High-speed dynamic splash advertisement, crystalline liquid splashes and droplets frozen in mid-air around the product, dramatic studio strobe lighting, vibrant energetic commercial composition.",
            "minimal_dtc": "Minimalist modern direct-to-consumer (DTC) advertisement, seamless pastel studio backdrop, soft diffused softbox illumination, floating product hero angle, clean Apple-inspired negative space, ultra crisp presentation."
        }
        
        enriched_prompt = prompt.strip()
        preset_desc = style_prompts.get(style_preset)
        if preset_desc:
            enriched_prompt = f"{enriched_prompt}. Style: {preset_desc}"
            
        if negative_prompt and negative_prompt.strip():
            enriched_prompt = f"{enriched_prompt} (Negative prompt: avoid {negative_prompt.strip()})"

        # 3. Handle Product Image (for Product Placement / Remix Mode)
        product_bytes = None
        product_data_uri = None
        mime_type = "image/png"
        
        if product_image and product_image.filename:
            product_bytes = await product_image.read()
            if product_bytes:
                ext = os.path.splitext(product_image.filename)[1].lower() or ".png"
                if ext in (".jpg", ".jpeg"):
                    mime_type = "image/jpeg"
                elif ext == ".webp":
                    mime_type = "image/webp"
                else:
                    mime_type = "image/png"
                
                temp_filename = f"product_in_{uuid.uuid4().hex}{ext}"
                saved_product_path = os.path.join("static/generated", temp_filename)
                with open(saved_product_path, "wb") as f:
                    f.write(product_bytes)
                    
                product_data_uri = image_bytes_to_data_uri(product_bytes, mime_type)
                logger.info(f"[Image Studio] Product image attached ({len(product_bytes)} bytes) for product remix/placement.")

        # 4. Engine dispatch (Qwen-Image-2.1 vs Gemini Nano Banana Pro)
        image_bytes = None
        used_model = "Qwen-Image-2.1 (Self-Hosted)"
        engine_clean = (engine or "qwen").lower().strip()
        is_banana = engine_clean in ["gemini", "banana", "nano-banana", "nano-banana-pro", "nanobanana"]
        use_qwen = not is_banana and (engine_clean in ["qwen", "self-hosted"] or is_self_hosted_enabled())
        
        if use_qwen:
            try:
                logger.info(
                    f"[Image Studio] Dispatching to Qwen-Image-2.1: size={target_w}x{target_h}, "
                    f"steps={steps}, has_product={bool(product_data_uri)}..."
                )
                image_bytes = await generate_image_async(
                    prompt=enriched_prompt,
                    width=target_w,
                    height=target_h,
                    steps=steps,
                    seed=seed,
                    image_uri=product_data_uri,
                    api_key=x_image_api_key or get_image_api_key(),
                    timeout=600
                )
                used_model = "Qwen-Image-2.1 (Self-Hosted)"
            except Exception as qwen_err:
                logger.warning(f"[Image Studio] Qwen-Image-2.1 server error: {qwen_err}")
                if should_fallback_to_gemini() and engine_clean not in ["qwen"]:
                    logger.info("[Image Studio] Attempting fallback to Gemini Nano Banana Pro...")
                else:
                    raise HTTPException(status_code=503, detail=str(qwen_err))
                    
        if not image_bytes:
            client = get_client(x_api_key)
            if not client:
                raise HTTPException(
                    status_code=400,
                    detail="Gemini API Key is required for Gemini Nano Banana Pro."
                )
            logger.info("[Image Studio] Generating with Gemini Nano Banana Pro (nano-banana-pro-preview)...")
            contents = [enriched_prompt]
            if product_bytes:
                contents.append(types.Part.from_bytes(data=product_bytes, mime_type=mime_type))
            
            response = client.models.generate_content(
                model='nano-banana-pro-preview',
                contents=contents
            )
            if response.candidates:
                for part in response.candidates[0].content.parts:
                    if part.inline_data and part.inline_data.data:
                        image_bytes = part.inline_data.data
                        break
                        
            if not image_bytes:
                raise HTTPException(status_code=500, detail="Gemini model did not return any image data.")
            used_model = "nano-banana-pro-preview"

        # 5. Save generated image with model-specific prefix
        prefix = "banana_ad_" if ("banana" in used_model or is_banana) else "qwen_ad_"
        out_filename = f"{prefix}{uuid.uuid4().hex}.png"
        out_path = os.path.join("static/generated", out_filename)
        if isinstance(image_bytes, str):
            image_bytes = image_bytes.encode('latin1')
        with open(out_path, "wb") as f:
            f.write(image_bytes)

        logger.info(f"[Image Studio] Successfully generated image ad: {out_path} using {used_model}")
        return {
            "status": "success",
            "image_url": f"/static/generated/{out_filename}",
            "filename": out_filename,
            "model_used": used_model,
            "engine": "banana" if ("banana" in used_model or is_banana) else "qwen",
            "aspect_ratio": aspect_ratio,
            "width": target_w,
            "height": target_h,
            "prompt": prompt,
            "enriched_prompt": enriched_prompt,
            "style_preset": style_preset or "custom",
            "has_product_reference": bool(product_bytes)
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[Image Studio] Generation failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/image-studio/history")
async def get_image_studio_history(engine: Optional[str] = None):
    """Retrieve recent generated image ads filtered by engine (qwen vs banana)."""
    gen_dir = "static/generated"
    items = []
    if os.path.exists(gen_dir):
        files = [f for f in os.listdir(gen_dir) if f.endswith(".png")]
        if engine:
            e = engine.lower().strip()
            if e in ["qwen", "self-hosted"]:
                files = [f for f in files if (f.startswith("qwen_ad_") or f.startswith("image_ad_")) and not f.startswith("banana_ad_")]
            elif e in ["banana", "gemini", "nano-banana", "nano-banana-pro"]:
                files = [f for f in files if f.startswith("banana_ad_") or f.startswith("gemini_ad_")]
        else:
            files = [f for f in files if f.startswith("qwen_ad_") or f.startswith("banana_ad_") or f.startswith("image_ad_")]
            
        files.sort(key=lambda x: os.path.getmtime(os.path.join(gen_dir, x)), reverse=True)
        for f in files[:24]:
            is_b = f.startswith("banana_ad_")
            items.append({
                "filename": f,
                "url": f"/static/generated/{f}",
                "model_used": "nano-banana-pro-preview" if is_b else "Qwen-Image-2.1",
                "engine": "banana" if is_b else "qwen",
                "created_at": os.path.getmtime(os.path.join(gen_dir, f))
            })
    return {"images": items}

@app.get("/api/self-hosted/status")
async def self_hosted_status():
    """Diagnostic health check for self-hosted Image and Video GPU servers."""
    return get_diagnostics()

@app.post("/api/self-hosted/configure")
async def self_hosted_configure(cfg: SelfHostedConfigRequest):
    """Dynamically update self-hosted settings."""
    if cfg.image_api_url is not None:
        os.environ["IMAGE_API_URL"] = cfg.image_api_url
    if cfg.image_api_key is not None:
        os.environ["IMAGE_API_KEY"] = cfg.image_api_key
    if cfg.video_api_url is not None:
        os.environ["VIDEO_API_URL"] = cfg.video_api_url
    if cfg.video_api_key is not None:
        os.environ["VIDEO_API_KEY"] = cfg.video_api_key
    if cfg.use_self_hosted is not None:
        os.environ["USE_SELF_HOSTED"] = "true" if cfg.use_self_hosted else "false"
    if cfg.fallback_to_gemini is not None:
        os.environ["FALLBACK_TO_GEMINI"] = "true" if cfg.fallback_to_gemini else "false"
    return get_diagnostics()

@app.get("/api/video-status/{job_id}")
async def get_video_status(job_id: str):
    import time
    job = video_jobs.get(job_id)
    if not job and os.path.exists(JOBS_CACHE_FILE):
        try:
            with open(JOBS_CACHE_FILE, "r", encoding="utf-8") as f:
                disk_cache = json.load(f)
                if job_id in disk_cache:
                    job = disk_cache[job_id]
                    video_jobs[job_id] = job
        except Exception:
            pass

    if not job:
        raise HTTPException(
            status_code=404,
            detail="Job not found. The server may have restarted or deployed. Please click Generate to start."
        )

    # Automatically fail any job stuck in processing for over 1800 seconds (30 minutes)
    created_at = job.get("created_at")
    if job.get("status") == "processing" and created_at and (time.time() - created_at > 1800):
        job["status"] = "failed"
        job["error"] = "Task exceeded maximum allowed time (30 minutes). Please try generating again."
        persist_job_update(job_id, job, video_jobs)

    return job

# Mount static folders
app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/css", StaticFiles(directory="static/css"), name="css")
app.mount("/js", StaticFiles(directory="static/js"), name="js")

# Serve index.html at root (supports both GET and HEAD for cloud health checks)
@app.api_route("/", methods=["GET", "HEAD"])
async def read_index(request: Request):
    from fastapi.responses import FileResponse, Response
    if request.method == "HEAD":
        return Response(status_code=200)
    return FileResponse("static/index.html")

# Dedicated health check endpoint for Render/cloud deployment monitors
@app.api_route("/healthz", methods=["GET", "HEAD"])
@app.api_route("/health", methods=["GET", "HEAD"])
async def health_check():
    return {"status": "ok"}

# Favicon handler to prevent 404 spam
@app.get("/favicon.ico")
async def favicon():
    from fastapi.responses import Response
    return Response(status_code=204)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=True)
