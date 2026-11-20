"""
Creative Editor API Routes
Provides AI-powered inpainting (brush mask + prompt) and subject background removal
using pure Google Gemini (Nano Banana Pro / Nano Banana 2.1) and PIL.
"""

import base64
import io
import logging
import os
import re
import uuid
from typing import Any, Dict, Optional

import httpx
from fastapi import APIRouter, File, Form, Header, HTTPException, Request, UploadFile
from PIL import Image, ImageDraw

from media_utils import (
    require_gemini_client as require_client,
    resolve_generated_path,
    save_generated_media,
    GENERATED_DIR,
    read_upload,
    IMAGE_EXTS,
    MAX_IMAGE_BYTES,
    image_model,
    DEFAULT_IMAGE_MODEL,
)

logger = logging.getLogger("edit_routes")

router = APIRouter(prefix="/api/edit", tags=["Creative Editor"])


async def _resolve_image_bytes(
    image_url: Optional[str] = None,
    image_file: Optional[UploadFile] = None,
) -> tuple[bytes, str]:
    """Resolves raw image bytes and mime type from either an upload or a URL/path."""
    if image_file and image_file.filename:
        raw, _, mime = await read_upload(image_file, IMAGE_EXTS, ".png", MAX_IMAGE_BYTES)
        return raw, mime

    if not image_url or not image_url.strip():
        raise HTTPException(status_code=400, detail="An image URL or image file is required.")

    clean_url = image_url.strip()

    # 1. Try local disk path if it points to /static/generated/
    local_path = resolve_generated_path(clean_url)
    if local_path and os.path.exists(local_path):
        try:
            with open(local_path, "rb") as f:
                data = f.read()
            ext = os.path.splitext(local_path)[1].lower()
            mime = "image/png" if ext == ".png" else "image/jpeg"
            return data, mime
        except Exception as e:
            logger.warning(f"Failed to read local generated file {local_path}: {e}")

    # 2. Try fetching from remote URL or Supabase CDN
    target_url = clean_url
    if target_url.startswith("/static/generated/"):
        sb_url = os.environ.get("SUPABASE_URL", "").rstrip("/")
        if sb_url:
            fname = os.path.basename(target_url)
            target_url = f"{sb_url}/storage/v1/object/public/generated/{fname}"

    if target_url.startswith("http://") or target_url.startswith("https://"):
        try:
            async with httpx.AsyncClient(timeout=20.0, follow_redirects=True) as http_client:
                res = await http_client.get(target_url)
                if res.status_code == 200:
                    mime = res.headers.get("content-type", "image/png").split(";")[0]
                    return res.content, mime
                else:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Could not fetch image from {target_url} (HTTP {res.status_code})",
                    )
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Failed to download image: {e}")

    raise HTTPException(status_code=400, detail="Invalid image path or URL.")


def _decode_mask_bytes(mask_data: str, target_size: tuple[int, int]) -> bytes:
    """
    Decodes base64 data URL mask into binary black-and-white PNG bytes.
    White pixels = region to edit. Black pixels = untouched.
    """
    if not mask_data or not mask_data.strip():
        raise HTTPException(status_code=400, detail="Mask drawing is required.")

    try:
        # Strip data URL prefix if present
        payload = mask_data
        if "base64," in payload:
            payload = payload.split("base64,")[1]

        raw = base64.b64decode(payload)
        mask_img = Image.open(io.BytesIO(raw))

        # Resize mask to match base image dimensions exactly if needed
        if mask_img.size != target_size:
            mask_img = mask_img.resize(target_size, Image.Resampling.NEAREST)

        # Convert to RGBA
        mask_rgba = mask_img.convert("RGBA")

        # Create binary L mask (255 where brush painted, 0 elsewhere)
        bw_mask = Image.new("L", target_size, 0)
        # Check alpha channel or color intensity
        r, g, b, a = mask_rgba.split()
        
        # Pixels with alpha > 20 or brightness > 30 are considered painted mask
        bw_mask = a.point(lambda p: 255 if p > 20 else 0)

        out_buf = io.BytesIO()
        bw_mask.save(out_buf, format="PNG")
        return out_buf.getvalue()
    except Exception as e:
        logger.error(f"Failed to decode mask drawing: {e}", exc_info=True)
        raise HTTPException(status_code=400, detail=f"Invalid mask data: {e}")


@router.post("/inpaint")
async def inpaint_creative(
    image_url: Optional[str] = Form(None),
    image_file: Optional[UploadFile] = File(None),
    mask_data: str = Form(...),
    prompt: str = Form(...),
    model: str = Form("nano-banana-pro"),
    x_api_key: Optional[str] = Header(None),
):
    """
    Inpaints the masked area of a creative using Google Gemini multimodal vision.
    The brush mask defines the modification region; surrounding image is preserved.
    """
    from google.genai import types

    clean_prompt = (prompt or "").strip()
    if not clean_prompt:
        raise HTTPException(status_code=400, detail="Please enter instructions for the selected area.")

    client = require_client(x_api_key)

    # 1. Resolve base image bytes & dimensions
    base_bytes, base_mime = await _resolve_image_bytes(image_url, image_file)
    try:
        base_pil = Image.open(io.BytesIO(base_bytes))
        target_size = base_pil.size
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Base image cannot be read: {e}")

    # 2. Decode mask into matching binary PNG bytes
    mask_bytes = _decode_mask_bytes(mask_data, target_size)

    # 3. Model resolution
    chosen_meta = image_model(model)
    model_id = chosen_meta["id"]

    # 4. Multimodal inpainting instructions for Gemini
    inpaint_directive = (
        f"Inpainting instruction: The first image is the base advertising creative. "
        f"The second image is a binary mask where WHITE marks the exact region to edit, "
        f"and BLACK marks the untouched region. "
        f"Perform this edit ONLY within the white marked region: {clean_prompt}. "
        f"Ensure seamless photorealistic blending, matching lighting, natural shadow transitions, "
        f"and keep everything outside the white mask unchanged."
    )

    contents = [
        types.Part.from_bytes(data=base_bytes, mime_type=base_mime),
        types.Part.from_bytes(data=mask_bytes, mime_type="image/png"),
        inpaint_directive,
    ]

    try:
        logger.info(f"Submitting Gemini inpainting request with model {model_id}...")
        resp = client.models.generate_content(
            model=model_id,
            contents=contents,
        )

        out_bytes: Optional[bytes] = None
        if resp.candidates and resp.candidates[0].content and resp.candidates[0].content.parts:
            for part in resp.candidates[0].content.parts:
                if getattr(part, "inline_data", None) and part.inline_data.data:
                    out_bytes = part.inline_data.data
                    break

        if not out_bytes:
            raise RuntimeError("Gemini inpainting completed without returning an image.")

        # Save to permanent Supabase Storage & local /tmp
        filename = f"edited_inpaint_{uuid.uuid4().hex}.png"
        saved_url = save_generated_media(filename, out_bytes, "image/png")

        return {
            "status": "success",
            "image_url": saved_url,
            "filename": filename,
            "width": target_size[0],
            "height": target_size[1],
            "action": "inpaint",
            "prompt": clean_prompt,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Inpainting generation failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Inpainting failed: {e}")


@router.post("/remove-bg")
async def remove_background(
    image_url: Optional[str] = Form(None),
    image_file: Optional[UploadFile] = File(None),
    background_style: str = Form("transparent"),
    model: str = Form("nano-banana-pro"),
    x_api_key: Optional[str] = Header(None),
):
    """
    Isolates the subject/product and removes or replaces the background using Gemini.
    Styles: 'transparent', 'studio_white', 'studio_neutral', 'solid_black'
    """
    from google.genai import types

    client = require_client(x_api_key)

    # 1. Resolve base image bytes & dimensions
    base_bytes, base_mime = await _resolve_image_bytes(image_url, image_file)
    try:
        base_pil = Image.open(io.BytesIO(base_bytes))
        target_size = base_pil.size
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Base image cannot be read: {e}")

    chosen_meta = image_model(model)
    model_id = chosen_meta["id"]

    style_clean = (background_style or "transparent").strip().lower()

    if style_clean == "studio_white":
        bg_instruction = "Place the isolated subject on a pure seamless solid studio white (#FFFFFF) background with subtle soft ground contact shadow."
    elif style_clean == "studio_neutral":
        bg_instruction = "Place the isolated subject on a minimalist smooth neutral warm-gray (#EFEFEF) studio backdrop with gentle contact shadow."
    elif style_clean == "solid_black":
        bg_instruction = "Place the isolated subject on an elegant luxury solid matte black (#000000) backdrop with rim edge lighting."
    else:  # transparent
        bg_instruction = "Extract and isolate the primary foreground subject/product completely. Place it on a solid pure #FFFFFF seamless background with crisp, razor-sharp clean edges."

    prompt = (
        f"Subject isolation directive: Identify the main foreground product or person in this image. "
        f"Cleanly isolate them, removing the existing environment and all background clutter completely. "
        f"{bg_instruction} "
        f"Keep all product details, textures, logos, materials, and labels 100% photorealistic and sharp."
    )

    contents = [
        types.Part.from_bytes(data=base_bytes, mime_type=base_mime),
        prompt,
    ]

    try:
        logger.info(f"Submitting Gemini background removal with model {model_id} (style={style_clean})...")
        resp = client.models.generate_content(
            model=model_id,
            contents=contents,
        )

        out_bytes: Optional[bytes] = None
        if resp.candidates and resp.candidates[0].content and resp.candidates[0].content.parts:
            for part in resp.candidates[0].content.parts:
                if getattr(part, "inline_data", None) and part.inline_data.data:
                    out_bytes = part.inline_data.data
                    break

        if not out_bytes:
            raise RuntimeError("Gemini background removal completed without returning an image.")

        # If transparent background is requested, apply precision corner flood-fill alpha transparency
        if style_clean == "transparent":
            try:
                raw_img = Image.open(io.BytesIO(out_bytes)).convert("RGBA")
                w, h = raw_img.size
                # Flood-fill background from corners to make background transparent without wiping white within the subject
                for corner in [(0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1)]:
                    ImageDraw.floodfill(raw_img, corner, (0, 0, 0, 0), thresh=28)

                out_buf = io.BytesIO()
                raw_img.save(out_buf, format="PNG")
                out_bytes = out_buf.getvalue()
            except Exception as fe:
                logger.warning(f"Could not apply alpha transparency flood-fill: {fe}")

        filename = f"edited_bg_removed_{uuid.uuid4().hex}.png"
        saved_url = save_generated_media(filename, out_bytes, "image/png")

        return {
            "status": "success",
            "image_url": saved_url,
            "filename": filename,
            "width": target_size[0],
            "height": target_size[1],
            "action": "remove_background",
            "style": style_clean,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Background removal failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Background removal failed: {e}")
