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

class VideoRequest(BaseModel):
    storyboard_image_url: str
    video_prompt: str
    product_image_paths: Optional[List[str]] = None
    generator: str = "omni-flash"
    aspect_ratio: str = "9:16"

# Helper to get the GenAI client
def get_client(api_key: Optional[str] = None) -> genai.Client:
    key = api_key or os.environ.get("GEMINI_API_KEY") or DEFAULT_API_KEY
    return genai.Client(api_key=key)

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
        return result_json
        
    except Exception as e:
        logger.error(f"Campaign analysis failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/generate-storyboard")
async def generate_storyboard(
    req: StoryboardRequest,
    x_api_key: Optional[str] = Header(None)
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
        
        image_bytes = None
        if response.candidates:
            for part in response.candidates[0].content.parts:
                if part.inline_data and part.inline_data.data:
                    image_bytes = part.inline_data.data
                    break
                    
        if not image_bytes:
            raise HTTPException(status_code=500, detail="Nano Banana Pro failed to generate storyboard image")
            
        # Save generated storyboard image
        import uuid
        filename = f"storyboard_{uuid.uuid4().hex}.jpg"
        file_path = os.path.join("static/generated", filename)
        
        if isinstance(image_bytes, str):
            image_bytes = image_bytes.encode('latin1')
        with open(file_path, "wb") as f:
            f.write(image_bytes)
            
        logger.info(f"Storyboard generated and saved to {file_path}")
        
        return {"storyboard_image_url": f"/static/generated/{filename}"}
        
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

@app.post("/api/generate-video")
async def generate_video(
    req: VideoRequest,
    request: Request,
    background_tasks: BackgroundTasks,
    x_api_key: Optional[str] = Header(None),
    x_kie_key: Optional[str] = Header(None)
):
    try:
        import uuid
        job_id = f"job_{uuid.uuid4().hex}"
        video_jobs[job_id] = {"status": "processing"}
        
        if req.generator == "seedance":
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

@app.get("/api/video-status/{job_id}")
async def get_video_status(job_id: str):
    job = video_jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job

# Mount static folder
app.mount("/static", StaticFiles(directory="static"), name="static")

# Serve index.html at root
@app.get("/")
async def read_index():
    from fastapi.responses import FileResponse
    return FileResponse("static/index.html")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=True)
