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
from urllib.parse import urlparse
from fastapi import APIRouter, File, Form, Header, HTTPException, Request, UploadFile
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageStat

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
    """Resolves raw image bytes and mime type from either an upload, data URL, local file, or remote URL."""
    if image_file and image_file.filename:
        raw, _, mime = await read_upload(image_file, IMAGE_EXTS, ".png", MAX_IMAGE_BYTES)
        return raw, mime

    if not image_url or not image_url.strip():
        raise HTTPException(status_code=400, detail="An image URL or image file is required.")

    clean_url = image_url.strip()

    # 1. Base64 data URL (e.g. from local file uploads or canvas transfers)
    if clean_url.startswith("data:image/"):
        try:
            header, b64_part = clean_url.split(",", 1)
            raw = base64.b64decode(b64_part)
            mime = "image/png"
            if "image/jpeg" in header or "image/jpg" in header:
                mime = "image/jpeg"
            elif "image/webp" in header:
                mime = "image/webp"
            return raw, mime
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid data URL image: {e}")

    # 2. Extract relative path from absolute URL if pointing to localhost or web server
    parsed = urlparse(clean_url)
    target_path = parsed.path if parsed.scheme in ("http", "https") else clean_url
    target_path = target_path.replace("\\", "/").strip()

    # 3. Try local disk path inside generated folder
    local_path = resolve_generated_path(target_path)
    if local_path and os.path.exists(local_path):
        try:
            with open(local_path, "rb") as f:
                data = f.read()
            ext = os.path.splitext(local_path)[1].lower()
            mime = "image/png" if ext == ".png" else ("image/jpeg" if ext in (".jpg", ".jpeg") else "image/webp")
            return data, mime
        except Exception as e:
            logger.warning(f"Failed to read local generated file {local_path}: {e}")

    # 4. Try local workspace static file (e.g. /static/demo/..., /static/showcase_videos/...)
    base_dir = os.path.dirname(os.path.abspath(__file__))
    static_root = os.path.realpath(os.path.join(base_dir, "static"))
    rel_static = target_path.lstrip("/")
    if rel_static.startswith("static/"):
        rel_static = rel_static[len("static/"):]
    cand_static = os.path.realpath(os.path.join(static_root, rel_static))
    if cand_static.startswith(static_root) and os.path.isfile(cand_static):
        try:
            with open(cand_static, "rb") as f:
                data = f.read()
            ext = os.path.splitext(cand_static)[1].lower()
            mime = "image/png" if ext == ".png" else ("image/jpeg" if ext in (".jpg", ".jpeg") else "image/webp")
            return data, mime
        except Exception as e:
            logger.warning(f"Failed to read local static file {cand_static}: {e}")

    # 5. Remote fetch from Supabase CDN or remote URL
    fetch_url = clean_url
    if target_path.startswith("/static/generated/"):
        sb_url = os.environ.get("SUPABASE_URL", "").rstrip("/")
        if sb_url:
            fname = os.path.basename(target_path)
            fetch_url = f"{sb_url}/storage/v1/object/public/generated/{fname}"

    if fetch_url.startswith("http://") or fetch_url.startswith("https://"):
        try:
            async with httpx.AsyncClient(timeout=25.0, follow_redirects=True) as http_client:
                res = await http_client.get(fetch_url)
                if res.status_code == 200:
                    mime = res.headers.get("content-type", "image/png").split(";")[0]
                    return res.content, mime
                else:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Could not fetch image from {fetch_url} (HTTP {res.status_code})",
                    )
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Failed to download image: {e}")

    raise HTTPException(status_code=400, detail="Invalid image path or URL.")


def _decode_mask_img(mask_data: str, target_size: tuple[int, int]) -> tuple[Image.Image, bytes]:
    """
    Decodes base64 data URL mask into binary black-and-white PIL Image and PNG bytes.
    White pixels (255) = region to edit. Black pixels (0) = untouched.
    """
    if not mask_data or not mask_data.strip():
        raise HTTPException(status_code=400, detail="Mask drawing is required.")

    try:
        payload = mask_data
        if "base64," in payload:
            payload = payload.split("base64,")[1]

        raw = base64.b64decode(payload)
        mask_img = Image.open(io.BytesIO(raw))

        if mask_img.size != target_size:
            mask_img = mask_img.resize(target_size, Image.Resampling.NEAREST)

        mask_rgba = mask_img.convert("RGBA")
        r, g, b, a = mask_rgba.split()
        a_extrema = a.getextrema()

        # If alpha has transparency (not solid opaque everywhere):
        if a_extrema[0] < 250:
            bw_mask = a.point(lambda p: 255 if p > 30 else 0)
        else:
            # Solid opaque canvas (black background #000000 with white/colored strokes)
            gray = mask_img.convert("L")
            bw_mask = gray.point(lambda p: 255 if p > 40 else 0)

        extrema = bw_mask.getextrema()
        if extrema[1] == 0:
            raise HTTPException(status_code=400, detail="Mask is empty. Please paint over the area you wish to modify.")

        out_buf = io.BytesIO()
        bw_mask.save(out_buf, format="PNG")
        return bw_mask, out_buf.getvalue()
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to decode mask drawing: {e}", exc_info=True)
        raise HTTPException(status_code=400, detail=f"Invalid mask data: {e}")


def _match_border_tone(gen_img: Image.Image, base_img: Image.Image, bw_mask: Image.Image) -> Image.Image:
    """Aligns gen_img's RGB exposure/color to base_img using the untouched ring right outside the mask."""
    ring_outer = bw_mask.filter(ImageFilter.MaxFilter(25))
    ring = ImageChops.subtract(ring_outer, bw_mask)
    stat_base = ImageStat.Stat(base_img.convert("RGB"), mask=ring)
    if not stat_base.count or stat_base.count[0] == 0:
        return gen_img
    stat_gen = ImageStat.Stat(gen_img.convert("RGB"), mask=ring)

    deltas = [
        max(-35.0, min(35.0, stat_base.mean[c] - stat_gen.mean[c]))
        for c in range(3)
    ]
    if all(abs(d) < 0.75 for d in deltas):
        return gen_img

    r, g, b, a = gen_img.convert("RGBA").split()
    channels = []
    for ch, d in zip((r, g, b), deltas):
        lut = [max(0, min(255, int(round(i + d)))) for i in range(256)]
        channels.append(ch.point(lut))
    return Image.merge("RGBA", (*channels, a))


def _seamless_inpaint_composite(
    gen_img: Image.Image,
    base_rgba: Image.Image,
    bw_mask: Image.Image,
) -> Image.Image:
    """Matches border tone and blends with a wide, smooth-feathered mask to prevent visible patch seams."""
    aligned_gen = _match_border_tone(gen_img, base_rgba, bw_mask)

    min_dim = min(base_rgba.size)
    feather = max(14, min(36, int(min_dim * 0.025)))
    dilate_k = max(5, min(21, (feather // 2) | 1))
    soft_mask = bw_mask.filter(ImageFilter.MaxFilter(dilate_k)).filter(
        ImageFilter.GaussianBlur(radius=feather)
    )
    return Image.composite(aligned_gen, base_rgba, soft_mask)


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

    # 2. Decode mask into matching binary PNG bytes & PIL Image
    bw_mask, mask_bytes = _decode_mask_img(mask_data, target_size)

    # 3. Model resolution
    chosen_meta = image_model(model)
    model_id = chosen_meta["id"]

    # 4. Multimodal inpainting instructions for Gemini
    inpaint_directive = (
        f"Inpainting instruction: The first image is the base advertising creative. "
        f"The second image is a binary mask where WHITE marks the exact region to edit, "
        f"and BLACK marks the untouched region. "
        f"Perform this edit ONLY within the white marked region: {clean_prompt}. "
        f"CRITICAL SEAMLESS BLENDING: Match the exact background color, gradient, luminance, surface texture, "
        f"and film grain of the surrounding untouched pixels. Do NOT darken, brighten, or tint the masked area, "
        f"and leave zero visible brush outline, halo, or bounding box. Keep everything outside the white mask identical."
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
        cand = resp.candidates[0] if (resp.candidates and len(resp.candidates) > 0) else None
        if cand:
            if cand.finish_reason and str(cand.finish_reason) not in ("STOP", "FinishReason.STOP"):
                logger.warning(f"Inpaint finish reason: {cand.finish_reason}")
                if "SAFETY" in str(cand.finish_reason).upper():
                    raise HTTPException(
                        status_code=400,
                        detail="Inpainting was blocked by safety filters. Please adjust the prompt or region.",
                    )

            if cand.content and cand.content.parts:
                for part in cand.content.parts:
                    if getattr(part, "inline_data", None) and part.inline_data.data:
                        raw_data = part.inline_data.data
                        if isinstance(raw_data, str):
                            try:
                                out_bytes = base64.b64decode(raw_data)
                            except Exception:
                                out_bytes = raw_data.encode("latin1")
                        else:
                            out_bytes = raw_data
                        break

        if not out_bytes:
            explanation = ""
            if cand and cand.content and cand.content.parts:
                text_parts = [p.text for p in cand.content.parts if getattr(p, "text", None)]
                explanation = " ".join(filter(None, text_parts)).strip()
            detail = f"Gemini inpainting completed without returning an image. {explanation}".strip()
            raise RuntimeError(detail)

        # 5. Composite: Align border tone and feather smoothly so no patch seam appears
        gen_img = Image.open(io.BytesIO(out_bytes)).convert("RGBA")
        if gen_img.size != target_size:
            gen_img = gen_img.resize(target_size, Image.Resampling.LANCZOS)

        base_rgba = base_pil.convert("RGBA")
        composite = _seamless_inpaint_composite(gen_img, base_rgba, bw_mask)

        # Preserve alpha channel if base creative had transparency, otherwise RGB
        final_mode = "RGBA" if ("A" in base_pil.getbands() or base_mime == "image/png") else "RGB"
        final_img = composite.convert(final_mode)

        final_buf = io.BytesIO()
        final_img.save(final_buf, format="PNG")
        final_bytes = final_buf.getvalue()

        # Save to permanent Supabase Storage & local /tmp
        filename = f"edited_inpaint_{uuid.uuid4().hex}.png"
        saved_url = save_generated_media(filename, final_bytes, "image/png")

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
        cand = resp.candidates[0] if (resp.candidates and len(resp.candidates) > 0) else None
        if cand:
            if cand.finish_reason and str(cand.finish_reason) not in ("STOP", "FinishReason.STOP"):
                logger.warning(f"Background removal finish reason: {cand.finish_reason}")
                if "SAFETY" in str(cand.finish_reason).upper():
                    raise HTTPException(
                        status_code=400,
                        detail="Background removal was blocked by safety filters.",
                    )

            if cand.content and cand.content.parts:
                for part in cand.content.parts:
                    if getattr(part, "inline_data", None) and part.inline_data.data:
                        raw_data = part.inline_data.data
                        if isinstance(raw_data, str):
                            try:
                                out_bytes = base64.b64decode(raw_data)
                            except Exception:
                                out_bytes = raw_data.encode("latin1")
                        else:
                            out_bytes = raw_data
                        break

        if not out_bytes:
            explanation = ""
            if cand and cand.content and cand.content.parts:
                text_parts = [p.text for p in cand.content.parts if getattr(p, "text", None)]
                explanation = " ".join(filter(None, text_parts)).strip()
            detail = f"Gemini background removal completed without returning an image. {explanation}".strip()
            raise RuntimeError(detail)

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
