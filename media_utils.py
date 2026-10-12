import os
import re
import socket
import ipaddress
import logging
from typing import List, Optional, Tuple
from urllib.parse import urlparse, urljoin

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

GENERATED_DIR = "static/generated"
GENERATED_URL_PREFIX = "/static/generated/"

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
VIDEO_EXTS = {".mp4", ".mov", ".webm"}

MAX_IMAGE_BYTES = 20 * 1024 * 1024
MAX_VIDEO_BYTES = 200 * 1024 * 1024

# Aspect ratios accepted by Gemini image models (ImageConfig.aspect_ratio)
GEMINI_IMAGE_ASPECTS = {"1:1", "2:3", "3:2", "3:4", "4:3", "4:5", "5:4", "9:16", "16:9", "21:9"}

# Resolutions accepted by Gemini image models (ImageConfig.image_size)
GEMINI_IMAGE_RESOLUTIONS = {"1K", "2K", "4K"}
DEFAULT_IMAGE_RESOLUTION = "1K"

# Selectable image models: key -> API model id, display name and how many reference images it accepts
IMAGE_MODELS = {
    "nano-banana-pro": {"id": "nano-banana-pro-preview", "label": "Nano Banana Pro", "max_refs": 6},
    "nano-banana-2.1": {"id": "gemini-nano-banana-2.1", "label": "Nano Banana 2.1", "max_refs": 14},
}
DEFAULT_IMAGE_MODEL = "nano-banana-pro"


def image_model(key: Optional[str]) -> dict:
    """Model settings for a key from IMAGE_MODELS; unknown keys fall back to the default. Env vars
    NANO_BANANA_PRO_MODEL / NANO_BANANA_21_MODEL override the API ids."""
    k = (str(key or "").strip().lower().replace(" ", "-")) if key else DEFAULT_IMAGE_MODEL
    if k not in IMAGE_MODELS:
        k = DEFAULT_IMAGE_MODEL
    env = {"nano-banana-pro": "NANO_BANANA_PRO_MODEL", "nano-banana-2.1": "NANO_BANANA_21_MODEL"}[k]
    return {**IMAGE_MODELS[k], "key": k, "id": os.environ.get(env) or IMAGE_MODELS[k]["id"]}

_EXT_MIME = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
    ".gif": "image/gif",
    ".mp4": "video/mp4",
    ".mov": "video/quicktime",
    ".webm": "video/webm",
}


def load_dotenv(env_path: str = ".env") -> None:
    """Load KEY=value lines from .env into os.environ without overwriting variables that are already set."""
    if not os.path.exists(env_path):
        return
    try:
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, val = line.split("=", 1)
                key = key.strip()
                if key and key not in os.environ:
                    os.environ[key] = val.strip().strip("'\"")
    except Exception as e:
        logger.warning(f"Could not load {env_path}: {e}")


def get_client(api_key: Optional[str] = None):
    """Initializes and returns a Google GenAI client if an API key is provided or present in the environment."""
    from google import genai

    key = api_key or os.environ.get("GEMINI_API_KEY")
    if not key or not str(key).strip():
        return None
    try:
        return genai.Client(api_key=str(key).strip())
    except Exception as e:
        logger.warning(f"Could not initialize GenAI client: {e}")
        return None


def mime_for_path(path: str, default: str = "image/jpeg") -> str:
    """MIME type from a file path or a bare extension like '.png'."""
    # os.path.splitext(".png") returns ('.png', ''), which made every upload 'application/octet-stream'
    # and left Gemini blind to the product photos
    ext = path.lower() if path.startswith(".") and "." not in path[1:] else os.path.splitext(path)[1].lower()
    return _EXT_MIME.get(ext, default)


def safe_upload_ext(filename: Optional[str], allowed: set, default: str) -> str:
    """Return the file's extension only if it is in the allow-list, so uploads can never be served as HTML/JS."""
    ext = os.path.splitext(filename or "")[1].lower()
    return ext if ext in allowed else default


def detect_image_ext(data: bytes) -> str:
    """Pick a file extension from the image's magic bytes."""
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return ".png"
    if data[:3] == b"\xff\xd8\xff":
        return ".jpg"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return ".webp"
    if data[:6] in (b"GIF87a", b"GIF89a"):
        return ".gif"
    return ".png"


async def read_upload(upload, allowed: set, default_ext: str, max_bytes: int) -> Tuple[bytes, str, str]:
    """Read an UploadFile, enforcing the extension allow-list and a size cap. Returns (bytes, ext, mime)."""
    from fastapi import HTTPException

    data = await upload.read()
    if len(data) > max_bytes:
        raise HTTPException(status_code=413, detail=f"File '{upload.filename}' is too large (max {max_bytes // (1024 * 1024)} MB).")
    ext = safe_upload_ext(upload.filename, allowed, default_ext)
    return data, ext, mime_for_path(ext, "application/octet-stream")


def resolve_generated_path(path: Optional[str]) -> Optional[str]:
    """
    Map a client-supplied path like '/static/generated/x.png' to a local file inside GENERATED_DIR.
    Returns None for anything outside that folder (blocks '../.env' style reads) or missing files.
    """
    if not path:
        return None
    norm = str(path).replace("\\", "/").strip()
    for prefix in (GENERATED_URL_PREFIX, GENERATED_URL_PREFIX.lstrip("/")):
        if norm.startswith(prefix):
            name = norm[len(prefix):]
            break
    else:
        return None
    if not name or "/" in name or name in (".", ".."):
        return None
    base = os.path.realpath(GENERATED_DIR)
    candidate = os.path.realpath(os.path.join(base, name))
    if os.path.dirname(candidate) != base or not os.path.isfile(candidate):
        return None
    return candidate


def is_public_http_url(url: str) -> bool:
    """True if the URL is http(s) and every address its host resolves to is publicly routable (SSRF guard)."""
    try:
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https") or not parsed.hostname:
            return False
        port = parsed.port or (443 if parsed.scheme == "https" else 80)
        infos = socket.getaddrinfo(parsed.hostname, port, proto=socket.IPPROTO_TCP)
        if not infos:
            return False
        for info in infos:
            ip = ipaddress.ip_address(info[4][0].split("%")[0])
            if not ip.is_global:
                return False
        return True
    except Exception:
        return False


def generate_gemini_image(
    client,
    contents: List,
    aspect_ratio: Optional[str] = None,
    model: Optional[str] = None,
    resolution: Optional[str] = None,
) -> Optional[bytes]:
    """
    Blocking call to a Nano Banana model (`model` is an IMAGE_MODELS key; default Nano Banana Pro).
    Passes the aspect ratio and resolution (image_size: 1K, 2K, 4K) through ImageConfig so the model
    composes for the requested format and target resolution.
    """
    from google.genai import types

    image_config_kwargs = {}
    if aspect_ratio in GEMINI_IMAGE_ASPECTS:
        image_config_kwargs["aspect_ratio"] = aspect_ratio

    res_clean = None
    if resolution:
        r = str(resolution).strip().upper()
        if r in GEMINI_IMAGE_RESOLUTIONS:
            res_clean = r
            image_config_kwargs["image_size"] = r

    config = None
    if image_config_kwargs:
        config = types.GenerateContentConfig(image_config=types.ImageConfig(**image_config_kwargs))

    try:
        response = client.models.generate_content(
            model=image_model(model)["id"],
            contents=contents,
            config=config,
        )
    except Exception as e:
        err_msg = str(e).lower()
        if res_clean and ("image_size" in err_msg or "imagesize" in err_msg or "size" in err_msg):
            logger.warning(
                f"Image generation failed with image_size={res_clean}: {e}. Retrying without resolution constraint."
            )
            fallback_kwargs = {k: v for k, v in image_config_kwargs.items() if k != "image_size"}
            fallback_config = (
                types.GenerateContentConfig(image_config=types.ImageConfig(**fallback_kwargs))
                if fallback_kwargs
                else None
            )
            response = client.models.generate_content(
                model=image_model(model)["id"],
                contents=contents,
                config=fallback_config,
            )
        else:
            raise

    if response.candidates:
        cand = response.candidates[0]
        if cand.finish_reason and str(cand.finish_reason) not in ("STOP", "FinishReason.STOP"):
            logger.warning(f"Image generation finish reason: {cand.finish_reason}")
            if "SAFETY" in str(cand.finish_reason).upper():
                raise RuntimeError("Image generation was blocked by safety filters. Please adjust prompt or references.")
        for part in (cand.content.parts if cand.content else []) or []:
            if part.inline_data and part.inline_data.data:
                data = part.inline_data.data
                return data.encode("latin1") if isinstance(data, str) else data
    return None


# Basic web scraper helper (follows redirects manually so each hop is checked against private addresses)
BROWSER_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "en;q=0.9",
}


def fetch_public_html(url: str, timeout: int = 10) -> Tuple[str, str]:
    """(final_url, html) of a public web page, following up to 5 redirects and refusing any hop to a
    non-public address. Raises on network/HTTP errors."""
    current = url
    for _ in range(5):
        if not is_public_http_url(current):
            raise ValueError(f"Refusing to fetch non-public URL: {current}")
        res = requests.get(current, headers=BROWSER_HEADERS, timeout=timeout, allow_redirects=False)
        location = res.headers.get("location")
        if res.is_redirect and location:
            current = urljoin(current, location)
            continue
        res.raise_for_status()
        return current, res.text
    raise ValueError(f"Too many redirects: {url}")


def page_text(soup: BeautifulSoup, limit: int = 8000) -> str:
    """Readable text of a parsed page (scripts, styles and meta removed). Mutates the soup."""
    for s in soup(["script", "style", "meta", "noscript", "svg"]):
        s.decompose()
    lines = (line.strip() for line in soup.get_text(separator="\n").splitlines())
    chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
    return "\n".join(chunk for chunk in chunks if chunk)[:limit]


_CURRENCY_TOKEN = r"(?:US\$|A\$|C\$|S\$|[$€£¥₹]|\b(?:USD|EUR|GBP|AUD|CAD|INR|AED|SGD|JPY|NZD|CHF|SEK|ZAR|BRL|MXN)\b)"


def market_hints(soup: BeautifulSoup, html: str) -> str:
    """Where the brand sells, as the page itself signals it: page language, locale, hreflang targets,
    store currency/country and the currencies printed next to prices. Call before page_text()."""
    hints = []
    html_tag = soup.find("html")
    if html_tag and html_tag.get("lang"):
        hints.append(f"page language: {html_tag.get('lang')}")
    og_locale = soup.find("meta", property="og:locale")
    if og_locale and og_locale.get("content"):
        hints.append(f"og:locale: {og_locale['content']}")
    hreflangs = sorted({l.get("hreflang") for l in soup.find_all("link", hreflang=True)} - {None, "", "x-default"})
    if hreflangs:
        hints.append(f"hreflang versions: {', '.join(hreflangs[:12])}")
    m = re.search(r'"currency"\s*:\s*\{\s*"active"\s*:\s*"([A-Z]{3})"', html)
    if m:
        hints.append(f"store currency: {m.group(1)}")
    m = re.search(r'Shopify\.country\s*=\s*"([A-Z]{2})"', html)
    if m:
        hints.append(f"store country: {m.group(1)}")
    counts = {}
    for token in re.findall(rf"({_CURRENCY_TOKEN})\s?\d", soup.get_text(" ")):
        counts[token] = counts.get(token, 0) + 1
    if counts:
        top = sorted(counts.items(), key=lambda kv: -kv[1])[:3]
        hints.append("currencies next to prices: " + ", ".join(f"{k} x{v}" for k, v in top))
    return "; ".join(hints)


def scrape_url(url: str) -> str:
    try:
        _, html = fetch_public_html(url)
        return page_text(BeautifulSoup(html, "html.parser"))
    except Exception as e:
        logger.error(f"Web scraping failed: {e}")
        return ""


def sanitize_visual_prompt(text: str, forbidden_names: Optional[List[str]] = None) -> str:
    """
    Strips proper personal names and celebrity cues from visual prompts/scenes so that
    image/video generation models do not produce celebrity lookalikes or repeat individuals.
    """
    if not text:
        return ""

    cleaned = text
    names_to_strip = []
    if forbidden_names:
        for name in forbidden_names:
            if not name:
                continue
            name = name.strip()
            if len(name) >= 3:
                names_to_strip.append(name)
                parts = name.split()
                if len(parts) > 1 and len(parts[0]) >= 3:
                    names_to_strip.append(parts[0])

    names_to_strip.sort(key=len, reverse=True)
    for n in names_to_strip:
        pattern = rf"\b{re.escape(n)}\b"
        cleaned = re.sub(pattern, "a relatable customer", cleaned, flags=re.IGNORECASE)

    cleaned = re.sub(r"\ba relatable customer\'s\b", "the customer's", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\ba relatable customer is\b", "a customer is", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"^a relatable customer\b", "A relatable customer", cleaned)
    return cleaned

