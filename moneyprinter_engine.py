import os
import re
import json
import uuid
import math
import asyncio
import logging
import subprocess
import urllib.parse
from typing import List, Optional, Tuple, Dict, Any

import requests
import edge_tts
import imageio_ffmpeg
from google import genai
from google.genai import types
import shutil
import stat

logger = logging.getLogger("moneyprinter_engine")
logger.setLevel(logging.INFO)

def get_ffmpeg_binary() -> str:
    sys_ffmpeg = shutil.which("ffmpeg")
    if sys_ffmpeg:
        return sys_ffmpeg
    try:
        bin_path = imageio_ffmpeg.get_ffmpeg_exe()
        if bin_path and os.path.exists(bin_path):
            try:
                st = os.stat(bin_path)
                os.chmod(bin_path, st.st_mode | stat.S_IEXEC)
            except Exception:
                pass
            return bin_path
    except Exception as e:
        logger.error(f"Error resolving FFmpeg executable: {e}")
    return "ffmpeg"

FFMPEG_PATH = get_ffmpeg_binary()

GRADIENT_PALETTES = [
    ("0x0f172a", "0x38bdf8"), # Navy to electric cyan
    ("0x1e1b4b", "0x818cf8"), # Deep indigo to neon violet
    ("0x18181b", "0xf43f5e"), # Charcoal to vibrant rose
    ("0x064e3b", "0x10b981"), # Dark emerald to bright teal
    ("0x312e81", "0xc084fc"), # Royal purple to lilac
]

def format_srt_time(seconds: float) -> str:
    """Format seconds into HH:MM:SS,mmm for SRT subtitles."""
    millis = int((seconds - int(seconds)) * 1000)
    total_seconds = int(seconds)
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    secs = total_seconds % 60
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"

def _sync_generate_script(
    subject: str,
    custom_script: Optional[str],
    client: Optional[genai.Client]
) -> Tuple[str, List[str]]:
    """Synchronous worker to call Gemini with quick fallback."""
    default_script = (
        custom_script.strip()
        if custom_script and custom_script.strip()
        else f"Here is what you need to know about {subject}. Take action today and upgrade your results."
    )
    default_keywords = [subject, "modern technology workspace", "creative focus person", "clean sleek business"]

    if client is None:
        logger.info("No Gemini client provided, using default script template.")
        return default_script, default_keywords

    if custom_script and custom_script.strip():
        prompt = (
            f"You are a professional video ad director.\n"
            f"Here is a user-provided narration script:\n\"\"\"{custom_script.strip()}\"\"\"\n\n"
            "Analyze the script and extract 3 to 4 distinct visual search keywords for finding matching stock B-roll video clips.\n"
            "Each keyword should be 2 to 4 words in English describing cinematic stock video scenes (e.g., 'focused entrepreneur laptop', 'modern sunny office', 'city traffic night', 'happy customer smiling').\n"
            "Respond ONLY with valid JSON in this exact structure:\n"
            "{\"script\": \"<the original script>\", \"keywords\": [\"keyword 1\", \"keyword 2\", \"keyword 3\"]}"
        )
    else:
        prompt = (
            f"You are an elite short-form video ad copywriter and director.\n"
            f"Video Topic / Subject: \"{subject.strip()}\"\n\n"
            "Write a high-converting, engaging short video script (approx 45 to 65 words, roughly 20 to 30 seconds of voiceover).\n"
            "Include a powerful 3-second hook, high-value core message, and a strong call-to-action.\n"
            "Also extract 3 to 4 cinematic visual search keywords for matching stock B-roll clips (2 to 4 words each, e.g. 'businessman typing laptop', 'growth chart neon', 'smiling person mobile phone').\n"
            "Respond ONLY with valid JSON in this exact structure:\n"
            "{\"script\": \"<script text for narration>\", \"keywords\": [\"keyword 1\", \"keyword 2\", \"keyword 3\"]}"
        )

    for model_name in ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-flash"]:
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.7
                )
            )
            data = json.loads(response.text)
            script = data.get("script", default_script)
            keywords = data.get("keywords", default_keywords)
            return script, keywords
        except Exception as e:
            logger.warning(f"Gemini {model_name} failed: {e}")
            continue

    return default_script, default_keywords

async def generate_script_and_keywords(
    subject: str,
    custom_script: Optional[str],
    client: Optional[genai.Client]
) -> Tuple[str, List[str]]:
    """Non-blocking script generation with timeout."""
    try:
        return await asyncio.wait_for(
            asyncio.to_thread(_sync_generate_script, subject, custom_script, client),
            timeout=12.0
        )
    except Exception as e:
        logger.warning(f"Script generation timed out or failed ({e}), using default fallback.")
        default_script = (
            custom_script.strip()
            if custom_script and custom_script.strip()
            else f"Here is what you need to know about {subject}. Take action today and upgrade your results."
        )
        default_keywords = [subject, "modern technology workspace", "creative focus person", "clean sleek business"]
        return default_script, default_keywords

async def generate_narration_audio(
    script: str,
    voice_name: str,
    output_audio_path: str,
    output_srt_path: str
) -> float:
    """
    Synthesizes voice narration using Microsoft Edge TTS and outputs audio + .srt timestamps.
    Returns the total duration in seconds.
    """
    communicate = edge_tts.Communicate(script, voice=voice_name)
    sub_entries = []
    
    with open(output_audio_path, "wb") as audio_file:
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio_file.write(chunk["data"])
            elif chunk["type"] == "SentenceBoundary":
                start_sec = chunk["offset"] / 10_000_000.0
                end_sec = (chunk["offset"] + chunk["duration"]) / 10_000_000.0
                text = chunk["text"].strip()
                if text:
                    sub_entries.append((start_sec, end_sec, text))

    # Calculate audio duration using ffprobe
    duration = get_media_duration(output_audio_path)
    if duration <= 0:
        duration = 15.0

    # If sentence boundaries were not captured, generate evenly spaced subtitles
    if not sub_entries:
        sentences = [s.strip() for s in re.split(r'[.!?。！？\n]+', script) if s.strip()]
        if not sentences:
            sentences = [script]
        seg_duration = duration / len(sentences)
        for i, sentence in enumerate(sentences):
            s_start = i * seg_duration
            s_end = min((i + 1) * seg_duration, duration)
            sub_entries.append((s_start, s_end, sentence))

    # Write SRT format file
    with open(output_srt_path, "w", encoding="utf-8") as srt_file:
        for idx, (start_t, end_t, text) in enumerate(sub_entries, 1):
            srt_file.write(f"{idx}\n")
            srt_file.write(f"{format_srt_time(start_t)} --> {format_srt_time(end_t)}\n")
            srt_file.write(f"{text}\n\n")

    return duration

def get_media_duration(file_path: str) -> float:
    """Get media file duration in seconds using FFmpeg."""
    try:
        cmd = [FFMPEG_PATH, "-i", file_path]
        res = subprocess.run(cmd, stderr=subprocess.PIPE, stdout=subprocess.PIPE, text=True, timeout=10)
        match = re.search(r"Duration:\s*(\d+):(\d+):(\d+\.\d+)", res.stderr)
        if match:
            hours, mins, secs = match.groups()
            return int(hours) * 3600 + int(mins) * 60 + float(secs)
    except Exception as e:
        logger.error(f"Error reading media duration: {e}")
    return 15.0

def fetch_pixabay_videos(query: str, api_key: str, aspect_ratio: str = "9:16") -> List[str]:
    """Fetch video download URLs from Pixabay API matching the search term."""
    try:
        clean_q = urllib.parse.quote(query[:60])
        url = f"https://pixabay.com/api/videos/?key={api_key}&q={clean_q}&per_page=5"
        res = requests.get(url, timeout=8)
        if res.status_code == 200:
            data = res.json()
            video_urls = []
            for hit in data.get("hits", []):
                videos = hit.get("videos", {})
                # Prioritize medium or small for fast download & encoding
                clip = videos.get("medium") or videos.get("small") or videos.get("tiny") or videos.get("large")
                if clip and clip.get("url"):
                    video_urls.append(clip["url"])
            return video_urls
    except Exception as e:
        logger.warning(f"Pixabay search failed for query '{query}': {e}")
    return []

def create_synthetic_background_clip(
    output_path: str,
    width: int,
    height: int,
    duration: float = 4.0,
    index: int = 0
) -> bool:
    """
    Creates a sleek motion animated background clip using FFmpeg if no stock clip is found.
    Ensures zero failures and ultra-fast generation with -preset ultrafast.
    """
    c0, c1 = GRADIENT_PALETTES[index % len(GRADIENT_PALETTES)]
    color_filter = f"gradients=s={width}x{height}:d={duration}:c0={c0}:c1={c1}:speed=0.6"
    cmd = [
        FFMPEG_PATH, "-y",
        "-f", "lavfi",
        "-i", color_filter,
        "-t", str(duration),
        "-c:v", "libx264",
        "-preset", "ultrafast",
        "-threads", "2",
        "-pix_fmt", "yuv420p",
        output_path
    ]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        if res.returncode == 0 and os.path.exists(output_path):
            return True
        # Fallback to simple color loop if gradients filter is unsupported
        cmd_fallback = [
            FFMPEG_PATH, "-y",
            "-f", "lavfi",
            "-i", f"color=c={c0}:s={width}x{height}:d={duration}",
            "-t", str(duration),
            "-c:v", "libx264",
            "-preset", "ultrafast",
            "-threads", "2",
            "-pix_fmt", "yuv420p",
            output_path
        ]
        res_fb = subprocess.run(cmd_fallback, capture_output=True, text=True, timeout=15)
        return res_fb.returncode == 0 and os.path.exists(output_path)
    except Exception as e:
        logger.error(f"Failed to create synthetic background clip: {e}")
        return False

def download_and_normalize_clip(
    video_url: str,
    output_path: str,
    width: int,
    height: int,
    target_duration: float = 4.0
) -> bool:
    """Downloads an external MP4 clip, scales, center-crops, and trims it with ultrafast encoding."""
    temp_raw = output_path + ".raw.mp4"
    try:
        r = requests.get(video_url, stream=True, timeout=20)
        r.raise_for_status()
        with open(temp_raw, "wb") as f:
            for chunk in r.iter_content(chunk_size=131072):
                f.write(chunk)

        filter_str = f"scale={width}:{height}:force_original_aspect_ratio=increase,crop={width}:{height},setsar=1,fps=30"
        cmd = [
            FFMPEG_PATH, "-y",
            "-t", str(target_duration),
            "-i", temp_raw,
            "-vf", filter_str,
            "-c:v", "libx264",
            "-preset", "ultrafast",
            "-threads", "2",
            "-pix_fmt", "yuv420p",
            "-an",
            output_path
        ]
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
        return res.returncode == 0 and os.path.exists(output_path)
    except Exception as e:
        logger.warning(f"Could not normalize clip {video_url}: {e}")
        return False
    finally:
        if os.path.exists(temp_raw):
            try:
                os.remove(temp_raw)
            except Exception:
                pass

def render_final_mpt_video(
    normalized_clip_paths: List[str],
    audio_path: str,
    srt_path: str,
    output_video_path: str,
    total_duration: float,
    burn_subtitles: bool = True
) -> bool:
    """
    Concatenates normalized B-roll clips, adds narration audio, burns styled subtitles,
    and exports the final high-definition MP4 with ultrafast encoding.
    """
    working_dir = os.path.dirname(output_video_path)
    concat_list_file = os.path.join(working_dir, f"concat_{uuid.uuid4().hex}.txt")
    
    try:
        # Build concat list repeated as necessary to cover total duration
        with open(concat_list_file, "w", encoding="utf-8") as f:
            repeats = max(1, math.ceil(total_duration / (len(normalized_clip_paths) * 3.5))) + 1
            for _ in range(repeats):
                for p in normalized_clip_paths:
                    filename = os.path.basename(p)
                    f.write(f"file '{filename}'\n")

        srt_filename = os.path.basename(srt_path)
        audio_filename = os.path.basename(audio_path)
        out_filename = os.path.basename(output_video_path)

        def _run_render(with_subs: bool) -> bool:
            cmd = [
                FFMPEG_PATH, "-y",
                "-f", "concat",
                "-safe", "0",
                "-i", os.path.basename(concat_list_file),
                "-i", audio_filename
            ]
            if with_subs and os.path.exists(srt_path):
                # Styling: clear yellow/white text, bold, outlined, bottom aligned
                style = "FontSize=22,FontName=Arial,Bold=1,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,BorderStyle=1,Outline=2.5,Alignment=2,MarginV=50"
                cmd.extend(["-vf", f"subtitles={srt_filename}:force_style='{style}'"])

            cmd.extend([
                "-c:v", "libx264",
                "-preset", "ultrafast",
                "-threads", "2",
                "-pix_fmt", "yuv420p",
                "-c:a", "aac",
                "-b:a", "128k",
                "-shortest",
                out_filename
            ])
            res = subprocess.run(cmd, cwd=working_dir, capture_output=True, text=True, timeout=60)
            if res.returncode == 0 and os.path.exists(output_video_path):
                return True
            logger.warning(f"FFmpeg render (with_subs={with_subs}) failed: {res.stderr}")
            return False

        # Attempt 1: with subtitles (if requested)
        if burn_subtitles and os.path.exists(srt_path):
            if _run_render(with_subs=True):
                return True
            logger.warning("Subtitle burn-in failed; falling back to clean render without subtitles...")

        # Attempt 2: clean render without subtitles (guaranteed fallback)
        return _run_render(with_subs=False)

    except Exception as e:
        logger.error(f"Render pipeline failed: {e}", exc_info=True)
        return False
    finally:
        if os.path.exists(concat_list_file):
            try:
                os.remove(concat_list_file)
            except Exception:
                pass

async def execute_moneyprinter_job(
    job_id: str,
    subject: str,
    custom_script: Optional[str],
    aspect_ratio: str,
    voice_name: str,
    pixabay_key: Optional[str],
    burn_subtitles: bool,
    client: genai.Client,
    job_store: dict
):
    """
    Main asynchronous job execution pipeline with non-blocking threads and live progress updates.
    """
    try:
        job_store[job_id] = {
            "status": "processing",
            "progress_step": "1/4",
            "progress_msg": "Analyzing topic & crafting viral narration script..."
        }

        # Step 1: Script & Keywords
        script, keywords = await generate_script_and_keywords(subject, custom_script, client)
        job_store[job_id]["script"] = script
        job_store[job_id]["keywords"] = keywords
        logger.info(f"[{job_id}] Script generated ({len(script)} chars): {script[:60]}... Keywords: {keywords}")

        # Step 2: Voiceover Narration (Edge TTS)
        job_store[job_id]["progress_step"] = "2/4"
        job_store[job_id]["progress_msg"] = f"Synthesizing voiceover narration with {voice_name}..."

        os.makedirs("static/generated", exist_ok=True)
        audio_path = os.path.join("static/generated", f"mpt_audio_{job_id}.mp3")
        srt_path = os.path.join("static/generated", f"mpt_sub_{job_id}.srt")
        
        duration = await generate_narration_audio(script, voice_name, audio_path, srt_path)
        logger.info(f"[{job_id}] Audio narration generated: {duration:.1f}s")

        # Step 3: Fetching Footage (720p HD: 720x1280 or 1280x720 for ultrafast rendering)
        job_store[job_id]["progress_step"] = "3/4"
        job_store[job_id]["progress_msg"] = "Preparing HD B-roll visual clips..."

        if aspect_ratio == "16:9":
            target_w, target_h = 1280, 720
        else:
            target_w, target_h = 720, 1280

        normalized_clips = []
        clip_duration = 3.5 # Fast cuts for high engagement
        total_needed = min(4, max(3, len(keywords)))
        
        for idx in range(total_needed):
            kw = keywords[idx] if idx < len(keywords) else subject
            clip_path = os.path.join("static/generated", f"clip_{job_id}_{idx}.mp4")
            found = False
            
            job_store[job_id]["progress_msg"] = f"Preparing HD B-roll scene ({idx + 1}/{total_needed}): {kw}..."

            # Try fetching from Pixabay if key provided
            if pixabay_key:
                urls = await asyncio.to_thread(fetch_pixabay_videos, kw, pixabay_key, aspect_ratio)
                if urls:
                    ok = await asyncio.to_thread(
                        download_and_normalize_clip, urls[0], clip_path, target_w, target_h, clip_duration
                    )
                    if ok:
                        normalized_clips.append(clip_path)
                        found = True
                        
            # If not found or no key, create a high-quality aesthetic synthetic background
            if not found:
                ok = await asyncio.to_thread(
                    create_synthetic_background_clip, clip_path, target_w, target_h, clip_duration, idx
                )
                if ok:
                    normalized_clips.append(clip_path)

        if not normalized_clips:
            # Emergency fallback: at least one clip
            fallback_clip = os.path.join("static/generated", f"clip_{job_id}_main.mp4")
            await asyncio.to_thread(create_synthetic_background_clip, fallback_clip, target_w, target_h, duration, 0)
            normalized_clips.append(fallback_clip)

        # Step 4: Final Assembly & Subtitles
        job_store[job_id]["progress_step"] = "4/4"
        job_store[job_id]["progress_msg"] = "Assembling B-roll cuts, voiceover, and burning subtitles..."

        final_video_name = f"mpt_final_{job_id}.mp4"
        final_video_path = os.path.join("static/generated", final_video_name)

        success = await asyncio.to_thread(
            render_final_mpt_video,
            normalized_clip_paths=normalized_clips,
            audio_path=audio_path,
            srt_path=srt_path,
            output_video_path=final_video_path,
            total_duration=duration,
            burn_subtitles=burn_subtitles
        )

        if not success or not os.path.exists(final_video_path):
            raise RuntimeError("Final video rendering failed in FFmpeg assembly.")

        # Cleanup intermediate clip files
        for p in normalized_clips:
            try:
                if os.path.exists(p):
                    os.remove(p)
            except Exception:
                pass

        job_store[job_id] = {
            "status": "success",
            "video_url": f"/static/generated/{final_video_name}",
            "script": script,
            "duration": round(duration, 1),
            "keywords": keywords
        }
        logger.info(f"[{job_id}] Video generation complete! URL: /static/generated/{final_video_name}")

    except Exception as e:
        logger.error(f"[{job_id}] Execution failed: {e}", exc_info=True)
        job_store[job_id] = {
            "status": "failed",
            "error": str(e)
        }
