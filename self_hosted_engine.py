import os
import time
import base64
import logging
import asyncio
from typing import Optional, Dict, Any, Tuple
import requests

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Simple .env loader (zero-dependency)
# ---------------------------------------------------------------------------
def load_dotenv(env_path: str = ".env") -> None:
    """Load key-value pairs from .env into os.environ if not already set."""
    if not os.path.exists(env_path):
        return
    try:
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    key, val = line.split("=", 1)
                    key = key.strip()
                    val = val.strip().strip("'\"")
                    # Do not overwrite if already set in environment
                    if key and key not in os.environ:
                        os.environ[key] = val
        logger.info(f"Loaded environment variables from {env_path}")
    except Exception as e:
        logger.warning(f"Could not load {env_path}: {e}")

# Load .env immediately upon import
load_dotenv()

# ---------------------------------------------------------------------------
# Server Defaults & Configuration
# ---------------------------------------------------------------------------
DEFAULT_IMAGE_API_URL = "http://35.239.44.254:8000"
DEFAULT_VIDEO_API_URL = "http://136.115.27.165:8000"

def get_image_api_url() -> str:
    return os.environ.get("IMAGE_API_URL", DEFAULT_IMAGE_API_URL).rstrip("/")

def get_image_api_key() -> str:
    return os.environ.get("IMAGE_API_KEY", "").strip()

def get_video_api_url() -> str:
    return os.environ.get("VIDEO_API_URL", DEFAULT_VIDEO_API_URL).rstrip("/")

def get_video_api_key() -> str:
    return os.environ.get("VIDEO_API_KEY", "").strip()

def is_self_hosted_enabled() -> bool:
    val = os.environ.get("USE_SELF_HOSTED", "true").strip().lower()
    return val in ("true", "1", "yes", "on")

def should_fallback_to_gemini() -> bool:
    val = os.environ.get("FALLBACK_TO_GEMINI", "true").strip().lower()
    return val in ("true", "1", "yes", "on")

# ---------------------------------------------------------------------------
# Global Concurrency Locks
# "One job at a time per server. Requests are processed sequentially."
# ---------------------------------------------------------------------------
_image_server_lock = asyncio.Lock()
_video_server_lock = asyncio.Lock()

# Cached public IP
_cached_public_ip: Optional[Tuple[str, float]] = None

def get_public_ip() -> str:
    """Fetch public IP for GCP allowlisting reference (cached 1 hour)."""
    global _cached_public_ip
    now = time.time()
    if _cached_public_ip and (now - _cached_public_ip[1] < 3600):
        return _cached_public_ip[0]
    try:
        res = requests.get("https://api.ipify.org", timeout=4)
        if res.ok:
            ip = res.text.strip()
            _cached_public_ip = (ip, now)
            return ip
    except Exception as e:
        logger.warning(f"Failed to fetch public IP: {e}")
    return "Unknown (check https://api.ipify.org)"

# ---------------------------------------------------------------------------
# Image Data Helpers
# ---------------------------------------------------------------------------
def image_file_to_data_uri(path: str) -> str:
    """Convert a local image file to base64 data URI."""
    ext = os.path.splitext(path)[1].lstrip(".").lower()
    if ext == "jpg":
        ext = "jpeg"
    elif not ext:
        ext = "png"
    with open(path, "rb") as f:
        data = f.read()
    b64 = base64.b64encode(data).decode("utf-8")
    return f"data:image/{ext};base64,{b64}"

def image_bytes_to_data_uri(img_bytes: bytes, mime_type: str = "image/png") -> str:
    """Convert raw image bytes to base64 data URI."""
    b64 = base64.b64encode(img_bytes).decode("utf-8")
    return f"data:{mime_type};base64,{b64}"

# ---------------------------------------------------------------------------
# Server Health Checks
# ---------------------------------------------------------------------------
def check_image_health(api_url: Optional[str] = None) -> Dict[str, Any]:
    """
    Check Qwen-Image-2.1 server health.
    GET /health (no key) -> {"loaded": true, "error": null} or {"loaded": false, ...}
    """
    url = (api_url or get_image_api_url()).rstrip("/")
    health_endpoint = f"{url}/health"
    try:
        r = requests.get(health_endpoint, timeout=4)
        if r.status_code == 200:
            data = r.json()
            return {
                "online": True,
                "loaded": data.get("loaded", True),
                "model": "Qwen-Image-2.1",
                "detail": "Ready for generation" if data.get("loaded") else "Model still loading",
                "status_code": 200,
                "url": url
            }
        elif r.status_code == 503:
            return {
                "online": True,
                "loaded": False,
                "model": "Qwen-Image-2.1",
                "detail": "Model still loading (HTTP 503)",
                "status_code": 503,
                "url": url
            }
        else:
            return {
                "online": False,
                "loaded": False,
                "model": "Qwen-Image-2.1",
                "detail": f"Unexpected HTTP status {r.status_code}: {r.text[:100]}",
                "status_code": r.status_code,
                "url": url
            }
    except requests.exceptions.ConnectTimeout:
        return {
            "online": False,
            "loaded": False,
            "model": "Qwen-Image-2.1",
            "detail": "Server is OFF or connection timed out (run .\\image-on.ps1)",
            "status_code": 0,
            "url": url
        }
    except requests.exceptions.ConnectionError:
        return {
            "online": False,
            "loaded": False,
            "model": "Qwen-Image-2.1",
            "detail": "Connection refused. Server is stopped.",
            "status_code": 0,
            "url": url
        }
    except Exception as e:
        return {
            "online": False,
            "loaded": False,
            "model": "Qwen-Image-2.1",
            "detail": str(e),
            "status_code": 0,
            "url": url
        }

def check_video_health(api_url: Optional[str] = None) -> Dict[str, Any]:
    """
    Check MiniMax-H3 server health.
    GET /health (no key) -> {"status": "ok"} when ready, 502 while loading.
    """
    url = (api_url or get_video_api_url()).rstrip("/")
    health_endpoint = f"{url}/health"
    try:
        r = requests.get(health_endpoint, timeout=4)
        if r.status_code == 200:
            return {
                "online": True,
                "loaded": True,
                "model": "MiniMax-H3",
                "detail": "Ready for generation",
                "status_code": 200,
                "url": url
            }
        elif r.status_code == 502:
            return {
                "online": True,
                "loaded": False,
                "model": "MiniMax-H3",
                "detail": "Video model is not ready yet (still loading, HTTP 502)",
                "status_code": 502,
                "url": url
            }
        else:
            return {
                "online": False,
                "loaded": False,
                "model": "MiniMax-H3",
                "detail": f"Unexpected HTTP status {r.status_code}: {r.text[:100]}",
                "status_code": r.status_code,
                "url": url
            }
    except requests.exceptions.ConnectTimeout:
        return {
            "online": False,
            "loaded": False,
            "model": "MiniMax-H3",
            "detail": "Server is OFF or connection timed out (run .\\video-on.ps1)",
            "status_code": 0,
            "url": url
        }
    except requests.exceptions.ConnectionError:
        return {
            "online": False,
            "loaded": False,
            "model": "MiniMax-H3",
            "detail": "Connection refused. Server is stopped.",
            "status_code": 0,
            "url": url
        }
    except Exception as e:
        return {
            "online": False,
            "loaded": False,
            "model": "MiniMax-H3",
            "detail": str(e),
            "status_code": 0,
            "url": url
        }

def get_diagnostics() -> Dict[str, Any]:
    """Return health status of both self-hosted servers and configuration."""
    pub_ip = get_public_ip()
    img_status = check_image_health()
    vid_status = check_video_health()
    return {
        "use_self_hosted": is_self_hosted_enabled(),
        "fallback_to_gemini": should_fallback_to_gemini(),
        "public_ip": pub_ip,
        "image_server": {
            **img_status,
            "has_api_key": bool(get_image_api_key())
        },
        "video_server": {
            **vid_status,
            "has_api_key": bool(get_video_api_key())
        }
    }

# ---------------------------------------------------------------------------
# Synchronous Core Adapters
# ---------------------------------------------------------------------------
def _sync_generate_image(
    prompt: str,
    width: Optional[int] = None,
    height: Optional[int] = None,
    steps: int = 40,
    seed: Optional[int] = None,
    image_uri: Optional[str] = None,
    api_url: Optional[str] = None,
    api_key: Optional[str] = None,
    timeout: int = 600
) -> bytes:
    """
    Call Qwen-Image-2.1 POST /generate. Returns PNG bytes.
    `image_uri` can be a base64 data URI or an https URL for image editing.
    """
    url = (api_url or get_image_api_url()).rstrip("/")
    key = api_key or get_image_api_key()

    body: Dict[str, Any] = {"prompt": prompt, "steps": steps}
    if width is not None:
        body["width"] = int(width)
    if height is not None:
        body["height"] = int(height)
    if seed is not None:
        body["seed"] = int(seed)
    if image_uri:
        body["image"] = image_uri

    headers = {"Content-Type": "application/json"}
    if key:
        headers["X-API-Key"] = key

    logger.info(
        f"[Self-Hosted Image] Sending request to {url}/generate "
        f"(steps={steps}, size={width}x{height}, has_image={bool(image_uri)})..."
    )

    try:
        r = requests.post(f"{url}/generate", headers=headers, json=body, timeout=timeout)
    except requests.exceptions.ConnectTimeout as e:
        pub_ip = get_public_ip()
        raise TimeoutError(
            f"Image server connection timed out at {url}. The server is likely OFF or your IP ({pub_ip}) is not allowlisted. "
            f"Ask the server owner to start the server (run .\\image-on.ps1) and verify your IP is allowlisted on GCP firewall."
        ) from e
    except requests.exceptions.ConnectionError as e:
        pub_ip = get_public_ip()
        raise ConnectionError(
            f"Image server connection refused at {url}. The server is currently stopped. "
            f"Ask the server owner to start the server (run .\\image-on.ps1). Your public IP: {pub_ip}"
        ) from e

    if not r.ok:
        err_msg = r.text
        try:
            err_json = r.json()
            if "detail" in err_json:
                err_msg = str(err_json["detail"])
        except Exception:
            pass
        raise RuntimeError(f"Self-hosted Image API error (HTTP {r.status_code}): {err_msg}")

    return r.content  # PNG bytes


def _sync_generate_video(
    prompt: str,
    seconds: int = 5,
    aspect: str = "16:9",
    short_edge: int = 768,
    steps: int = 30,
    seed: Optional[int] = None,
    first_frame_uri: Optional[str] = None,
    last_frame_uri: Optional[str] = None,
    api_url: Optional[str] = None,
    api_key: Optional[str] = None,
    poll_every: int = 10,
    max_wait: int = 3600,
    progress_callback: Optional[callable] = None
) -> bytes:
    """
    Call MiniMax-H3 3-step job:
    1. POST /v1/videos
    2. Poll GET /v1/videos/{id}
    3. GET /v1/videos/{id}/content -> MP4 bytes
    """
    url = (api_url or get_video_api_url()).rstrip("/")
    key = api_key or get_video_api_key()

    headers = {"Content-Type": "application/json"}
    if key:
        headers["X-API-Key"] = key

    # Clamp seconds between 4 and 15
    duration_sec = max(4, min(15, int(seconds)))
    
    # Supported short_edge values: 480, 768, 1344
    if short_edge not in (480, 768, 1344):
        short_edge = 768 if short_edge < 1000 else 1344

    # Build conditions
    conditions = []
    task = "t2va"
    aspect_ratio_param = aspect

    if first_frame_uri:
        task = "fl2va"
        conditions.append({
            "type": "image",
            "uri": first_frame_uri,
            "role": "keyframe",
            "frame_index": 0
        })
        if last_frame_uri:
            conditions.append({
                "type": "image",
                "uri": last_frame_uri,
                "role": "keyframe",
                "frame_index": -1
            })
        aspect_ratio_param = "auto" if not last_frame_uri else aspect

    body = {
        "model": "MiniMaxAI/MiniMax-H3",
        "prompt": prompt,
        "seconds": duration_sec,
        "task": task,
        "conditions": conditions,
        "target": {
            "short_edge": short_edge,
            "aspect_ratio": aspect_ratio_param,
            "duration_seconds": duration_sec
        },
        "num_outputs_per_prompt": 1,
        "num_inference_steps": steps,
    }
    if seed is not None:
        body["seed"] = int(seed)

    logger.info(
        f"[Self-Hosted Video] Creating video job on {url}/v1/videos "
        f"(task={task}, seconds={duration_sec}, short_edge={short_edge}, aspect={aspect_ratio_param})..."
    )

    try:
        job_res = requests.post(f"{url}/v1/videos", headers=headers, json=body, timeout=120)
    except requests.exceptions.ConnectTimeout as e:
        pub_ip = get_public_ip()
        raise TimeoutError(
            f"Video server connection timed out at {url}. The server is likely OFF or your IP ({pub_ip}) is not allowlisted. "
            f"Ask the server owner to start the server (run .\\video-on.ps1) and verify your IP is allowlisted on GCP firewall."
        ) from e
    except requests.exceptions.ConnectionError as e:
        pub_ip = get_public_ip()
        raise ConnectionError(
            f"Video server connection refused at {url}. The server is currently stopped. "
            f"Ask the server owner to start the server (run .\\video-on.ps1). Your public IP: {pub_ip}"
        ) from e

    if not job_res.ok:
        err_msg = job_res.text
        try:
            err_json = job_res.json()
            if "error" in err_json:
                err_msg = str(err_json["error"])
        except Exception:
            pass
        raise RuntimeError(f"Video job creation failed (HTTP {job_res.status_code}): {err_msg}")

    job_data = job_res.json()
    vid_id = job_data.get("id")
    if not vid_id:
        raise RuntimeError(f"Video server returned no job ID: {job_data}")

    logger.info(f"[Self-Hosted Video] Job created successfully. Job ID: {vid_id}. Starting polling...")

    # Step 2: Poll status
    deadline = time.time() + max_wait
    poll_count = 0

    while time.time() < deadline:
        poll_count += 1
        try:
            st_res = requests.get(f"{url}/v1/videos/{vid_id}", headers=headers, timeout=30)
            if st_res.ok:
                st = st_res.json()
                status = st.get("status")
                logger.info(f"[Self-Hosted Video] Job {vid_id} status (poll #{poll_count}): {status}")

                if progress_callback:
                    progress_callback(st, poll_count)

                if status == "completed":
                    logger.info(f"[Self-Hosted Video] Job {vid_id} completed! Downloading MP4...")
                    # Step 3: Download content
                    content_res = requests.get(f"{url}/v1/videos/{vid_id}/content", headers=headers, timeout=300)
                    content_res.raise_for_status()
                    logger.info(f"[Self-Hosted Video] Successfully downloaded {len(content_res.content)} bytes of MP4.")
                    return content_res.content

                if status in ("failed", "error"):
                    err = st.get("error") or "Unknown error"
                    raise RuntimeError(f"Video generation job failed on MiniMax-H3 server: {err}")

        except (requests.exceptions.RequestException, requests.exceptions.Timeout) as poll_err:
            logger.warning(f"[Self-Hosted Video] Transient polling error: {poll_err}")

        time.sleep(poll_every)

    raise TimeoutError(f"Video job {vid_id} timed out after {max_wait}s.")


# ---------------------------------------------------------------------------
# Async Thread-Pooled & Sequential Locked Wrappers
# ---------------------------------------------------------------------------
async def generate_image_async(
    prompt: str,
    width: Optional[int] = None,
    height: Optional[int] = None,
    steps: int = 40,
    seed: Optional[int] = None,
    image_uri: Optional[str] = None,
    api_url: Optional[str] = None,
    api_key: Optional[str] = None,
    timeout: int = 600
) -> bytes:
    """
    Queue and execute image generation sequentially on Qwen-Image-2.1.
    Respects one-job-at-a-time restriction via _image_server_lock.
    """
    async with _image_server_lock:
        return await asyncio.to_thread(
            _sync_generate_image,
            prompt=prompt,
            width=width,
            height=height,
            steps=steps,
            seed=seed,
            image_uri=image_uri,
            api_url=api_url,
            api_key=api_key,
            timeout=timeout
        )


async def generate_video_async(
    prompt: str,
    seconds: int = 5,
    aspect: str = "16:9",
    short_edge: int = 768,
    steps: int = 30,
    seed: Optional[int] = None,
    first_frame_uri: Optional[str] = None,
    last_frame_uri: Optional[str] = None,
    api_url: Optional[str] = None,
    api_key: Optional[str] = None,
    poll_every: int = 10,
    max_wait: int = 3600,
    progress_callback: Optional[callable] = None
) -> bytes:
    """
    Queue and execute video generation sequentially on MiniMax-H3.
    Respects one-job-at-a-time restriction via _video_server_lock.
    """
    async with _video_server_lock:
        return await asyncio.to_thread(
            _sync_generate_video,
            prompt=prompt,
            seconds=seconds,
            aspect=aspect,
            short_edge=short_edge,
            steps=steps,
            seed=seed,
            first_frame_uri=first_frame_uri,
            last_frame_uri=last_frame_uri,
            api_url=api_url,
            api_key=api_key,
            poll_every=poll_every,
            max_wait=max_wait,
            progress_callback=progress_callback
        )
