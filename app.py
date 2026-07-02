import os
import base64
import json
import logging
from typing import List, Optional
import requests
from bs4 import BeautifulSoup
from fastapi import FastAPI, HTTPException, UploadFile, File, Form, Header
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

DEFAULT_API_KEY = "AQ.Ab8RN6JfyEoy2Y2Pux5ClqNjjAXzPPL8mSiOYSkBWoYyifu28g"

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
    shot_5: str
    shot_6: str

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
    shot_5: str
    shot_6: str

class VideoRequest(BaseModel):
    storyboard_image_url: str
    video_prompt: str

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
            "potential color palette ideas, and key benefits. Use Google Search grounding to ensure accuracy."
        )
        
        grounding_config = types.GenerateContentConfig(
            tools=[types.Tool(google_search=types.GoogleSearch())]
        )
        
        research_response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=grounding_research_prompt,
            config=grounding_config
        )
        
        research_summary = research_response.text
        logger.info("URL Search Grounding and research completed.")

        product_images_analysis = ""
        # 2. If tangible and images are uploaded, analyze them
        if is_tangible and images:
            image_parts = []
            for img in images:
                content = await img.read()
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
                    model="gemini-2.5-flash",
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
            "For every single video script, write full script details and split them into 6 distinct storyboard shots "
            "(`shot_1` through `shot_6`) matching the 10-second arc in the template:\n"
            "- shot_1: HOOK SHOT (~1.5s)\n"
            "- shot_2: PRODUCT REVEAL (~1.5s)\n"
            "- shot_3: PRODUCT IN ACTION (~2s)\n"
            "- shot_4: BENEFIT/TRANSFORMATION (~2s)\n"
            "- shot_5: LIFESTYLE/EMOTION (~1.5s)\n"
            "- shot_6: CALL TO ACTION (~1.5s)\n\n"
            "Generate your response matching the requested schema. Make sure color_palette consists of 3-5 premium color terms, "
            "visual_style is one of (UGC_REALISTIC, CINEMATIC_PREMIUM, PIXAR_3D_STYLIZED, CLEAN_STUDIO, FOOD_APPETITE), "
            "and on_screen_talent, setting, mood_keywords are appropriately filled."
        )
        
        # Do NOT include tools here, so response_schema works perfectly
        schema_config = types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=CampaignAnalysis
        )
        
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=campaign_prompt,
            config=schema_config
        )
        
        # Parse the JSON response
        result_json = json.loads(response.text)
        
        # If user uploaded images, override/supplement product_visual_description
        if product_images_analysis:
            result_json["product_visual_description"] = product_images_analysis
            
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
            f"9:16 layout, clean white background, thin black panel borders, bold black sans-serif typography, premium advertising-agency presentation board. Grid of 6 numbered storyboard panels arranged left-to-right, top-to-bottom (2 columns x 3 rows). Each panel is a fully rendered cinematic frame — NOT a sketch — with a number badge in the top-left corner, a bold shot title, a one-line caption beneath it, and a small clock icon with its duration.\n\n"
            f"TOP HEADER (exact text, large bold type):\n"
            f"\"{req.product_name}\" — subtitle: \"TOTAL VIDEO TIME: 10 SECONDS · 6 SHOTS · {req.mood_keywords}\"\n"
            f"Legend row of 4 small icons with labels: HOOK, PRODUCT, BENEFIT, CTA.\n\n"
            f"VISUAL STYLE:\n"
            f"{style_block}\n"
            f"Color palette locked to: {req.color_palette}. Lighting: soft natural window daylight.\n\n"
            f"CONSISTENCY LOCK (critical — this board is a video-generation reference):\n"
            f"The SAME product appears in every panel where mentioned: {req.product_visual_description}. Preserve exact packaging shape, label layout, colors, cap design, materials, and proportions across all panels. Hero angle: {req.product_hero_angle}.\n"
            f"The SAME single on-screen talent appears throughout: {req.on_screen_talent}. Identical face, hair, outfit, and skin tone in every panel — no character drift.\n"
            f"Setting consistent across panels: {req.setting}.\n\n"
            f"THE 6 PANELS (render each as a distinct full-frame cinematic shot):\n\n"
            f"Panel 1 — HOOK SHOT (~1.5s): {req.shot_1} Caption text: \"{req.hook_line}\"\n"
            f"Panel 2 — PRODUCT REVEAL (~1.5s): {req.shot_2}\n"
            f"Panel 3 — PRODUCT IN ACTION (~2s): {req.shot_3}\n"
            f"Panel 4 — BENEFIT / TRANSFORMATION (~2s): {req.shot_4}\n"
            f"Panel 5 — LIFESTYLE / EMOTION (~1.5s): {req.shot_5}\n"
            f"Panel 6 — CALL TO ACTION (~1.5s): {req.shot_6} Caption text: \"{req.cta_line}\" with \"{req.logo_text}\" rendered as clean typography.\n\n"
            f"FOOTER STRIP (4 columns, small icons + short text):\n"
            f"• VIDEO FLOW: \"6 shots ≈ 10 seconds. Hook to CTA.\"\n"
            f"• CAMERA TIPS: \"macro on product texture, close-up on talent expression, wide establishing on {req.setting}, slow push-in on final CTA frame\"\n"
            f"• LIGHT & STYLE: \"soft natural window daylight, {req.color_palette}, shallow depth of field\"\n"
            f"• AUDIENCE NOTES: \"made for {req.target_audience_persona} — every frame must feel {req.mood_keywords}\"\n\n"
            f"TYPOGRAPHY RULES: all text short, high-contrast, perfectly legible; no paragraph text inside image panels; captions live in white bars below each frame, never overlapping the image.\n\n"
            f"NEGATIVE: watermark, extra logos, misspelled text, blurry frames, distorted hands, warped product packaging, inconsistent character faces, cluttered layout, overlapping panels, sketch lines, low quality."
        )
        
        logger.info(f"Generating storyboard with Imagen 4.0... Prompt length: {len(storyboard_prompt)}")
        
        result = client.models.generate_images(
            model='imagen-4.0-generate-001',
            prompt=storyboard_prompt,
            config=types.GenerateImagesConfig(
                number_of_images=1,
                output_mime_type="image/jpeg",
                aspect_ratio="9:16"
            )
        )
        
        if not result.generated_images:
            raise HTTPException(status_code=500, detail="Imagen failed to generate images")
            
        # Save generated storyboard image
        import uuid
        filename = f"storyboard_{uuid.uuid4().hex}.jpg"
        file_path = os.path.join("static/generated", filename)
        
        with open(file_path, "wb") as f:
            f.write(result.generated_images[0].image.image_bytes)
            
        logger.info(f"Storyboard generated and saved to {file_path}")
        
        return {"storyboard_image_url": f"/static/generated/{filename}"}
        
    except Exception as e:
        logger.error(f"Storyboard generation failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/generate-video")
async def generate_video(
    req: VideoRequest,
    x_api_key: Optional[str] = Header(None)
):
    try:
        client = get_client(x_api_key)
        
        # Resolve storyboard image path
        # URL is like /static/generated/storyboard_xxxx.jpg
        relative_path = req.storyboard_image_url.lstrip("/")
        if not os.path.exists(relative_path):
            raise HTTPException(status_code=404, detail="Storyboard image not found locally")
            
        with open(relative_path, "rb") as img_file:
            img_bytes = img_file.read()
            
        base64_image = base64.b64encode(img_bytes).decode('utf-8')
        
        # Prepare Omni Flash instructions
        omni_prompt = (
            "IMPORTANT: The attached storyboard is a reference board. Treat each numbered panel as an "
            "individual full-screen shot, read left-to-right, top-to-bottom. Do NOT animate the collage or "
            "show the grid. Total duration 10 seconds across 6 shots with hard cuts. Preserve the exact product "
            "design and the same on-screen talent from the reference in every shot.\n\n"
            f"Ad Motion Guidelines: {req.video_prompt}\n"
            "Animate this storyboard into a high-quality vertical 9:16 advertising video."
        )
        
        logger.info("Calling Omni Flash interactions API for video generation...")
        
        interaction = client.interactions.create(
            model='gemini-omni-flash-preview',
            input=[
                {"type": "image", "data": base64_image, "mime_type": "image/jpeg"},
                {"type": "text", "text": omni_prompt}
            ]
        )
        
        video_b64 = None
        mime_type = "video/mp4"
        
        # Find video in interaction response
        if hasattr(interaction, 'output_video') and interaction.output_video:
            video_b64 = interaction.output_video.data
            mime_type = interaction.output_video.mime_type or "video/mp4"
        else:
            # Fallback scan of steps
            for step in getattr(interaction, 'steps', []):
                if isinstance(step, dict) and step.get('type') == 'model_output' and step.get('content'):
                    for part in step['content']:
                        if part.get('type') == 'video':
                            video_b64 = part.get('data')
                            mime_type = part.get('mime_type', 'video/mp4')
                            break
                            
        if not video_b64:
            raise HTTPException(status_code=500, detail="Omni Flash did not return any video bytes")
            
        # Decode and save the video file
        import uuid
        filename = f"ad_video_{uuid.uuid4().hex}.mp4"
        file_path = os.path.join("static/generated", filename)
        
        with open(file_path, "wb") as f:
            f.write(base64.b64decode(video_b64))
            
        logger.info(f"Video generated and saved to {file_path}")
        
        return {"video_url": f"/static/generated/{filename}"}
        
    except Exception as e:
        logger.error(f"Video generation failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

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
