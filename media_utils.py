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

# Video resolutions supported for Omni Flash video output
OMNI_VIDEO_RESOLUTIONS = {"720p", "1080p", "4k"}
DEFAULT_VIDEO_RESOLUTION = "1080p"

# Selectable image models: key -> API model id, display name and how many reference images it accepts
IMAGE_MODELS = {
    "nano-banana-pro": {"id": "nano-banana-pro-preview", "label": "Nano Banana Pro", "max_refs": 6},
    "nano-banana-2.1": {"id": "gemini-nano-banana-2.1", "label": "Nano Banana 2.1", "max_refs": 14},
}
DEFAULT_IMAGE_MODEL = "nano-banana-2.1"


def image_model(key: Optional[str] = None) -> dict:
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


def sanitize_device_actions(text: str) -> str:
    """
    Cleans up device actions that trigger video generation models to invert laptop screens,
    flip laptops upside-down, or render mirrored/reversed phone screens.
    """
    if not text:
        return ""

    cleaned = text
    cleaned = re.sub(
        r"\bflips (his|her|their|the) laptop( camera)? around to show\b",
        r"angles the upright laptop on the desk to show",
        cleaned,
        flags=re.IGNORECASE,
    )
    cleaned = re.sub(
        r"\bflips (his|her|their|the) (laptop|phone|screen|monitor)( around)?\b",
        r"points to the upright \2 on the desk",
        cleaned,
        flags=re.IGNORECASE,
    )
    cleaned = re.sub(
        r"\bturns laptop screen to show\b",
        r"points to the upright laptop screen to show",
        cleaned,
        flags=re.IGNORECASE,
    )
    cleaned = re.sub(
        r"\bturns (his|her|their|the) laptop( around)? to show\b",
        r"gestures toward the upright laptop screen showing",
        cleaned,
        flags=re.IGNORECASE,
    )
    cleaned = re.sub(
        r"\bholds up (two|three|multiple|\d+) (different )?device screens\b",
        r"reviews open dashboards on an upright desktop monitor",
        cleaned,
        flags=re.IGNORECASE,
    )
    cleaned = re.sub(
        r"\b(holding|holds) (the |a |his |her )?laptop in (mid-air|the air|hands)\b",
        r"seated with laptop resting flat on desk",
        cleaned,
        flags=re.IGNORECASE,
    )
    cleaned = re.sub(
        r"\bhaving laptop upside[- ]?down\b",
        r"with laptop resting upright and flat",
        cleaned,
        flags=re.IGNORECASE,
    )
    return cleaned


# ---------------------------------------------------------------------------
# Color palette mapping & video prompt sanitization (Prevents hex codes in video)
# ---------------------------------------------------------------------------
COLOR_PALETTE = {
    "black": (0, 0, 0),
    "matte black": (20, 20, 20),
    "dark charcoal": (35, 37, 40),
    "charcoal": (54, 57, 63),
    "dark grey": (75, 75, 75),
    "slate grey": (112, 128, 144),
    "cool grey": (140, 150, 160),
    "light grey": (211, 211, 211),
    "silver": (192, 192, 192),
    "soft off-white": (245, 245, 245),
    "warm off-white": (250, 248, 244),
    "cream": (255, 253, 208),
    "white": (255, 255, 255),
    "dark navy": (21, 43, 54),
    "midnight blue": (25, 25, 112),
    "navy blue": (0, 0, 128),
    "royal blue": (65, 105, 225),
    "cobalt blue": (0, 71, 171),
    "sky blue": (135, 206, 235),
    "light blue": (173, 216, 230),
    "slate blue": (106, 90, 205),
    "teal": (0, 128, 128),
    "dark teal": (0, 80, 80),
    "cyan": (0, 255, 255),
    "turquoise": (64, 224, 208),
    "mint green": (152, 255, 152),
    "seafoam green": (142, 226, 175),
    "lime green": (50, 205, 50),
    "chartreuse": (211, 233, 53),
    "olive green": (107, 142, 35),
    "forest green": (34, 139, 34),
    "emerald green": (46, 139, 87),
    "coral red": (255, 82, 82),
    "crimson": (220, 20, 60),
    "ruby red": (155, 17, 30),
    "deep red": (178, 34, 34),
    "bright red": (255, 0, 0),
    "burgundy": (128, 0, 32),
    "wine red": (114, 47, 55),
    "hot pink": (255, 105, 180),
    "blush pink": (255, 182, 193),
    "dusty rose": (216, 150, 150),
    "magenta": (255, 0, 255),
    "purple": (128, 0, 128),
    "violet": (138, 43, 226),
    "lavender": (230, 230, 250),
    "plum": (142, 69, 133),
    "dark purple": (48, 25, 52),
    "orange": (255, 140, 0),
    "burnt orange": (204, 85, 0),
    "tangerine": (242, 133, 0),
    "peach": (232, 165, 137),
    "terracotta": (204, 78, 56),
    "amber": (255, 191, 0),
    "warm gold": (218, 165, 32),
    "yellow": (255, 235, 59),
    "mustard yellow": (225, 173, 1),
    "tan": (210, 180, 140),
    "beige": (245, 245, 220),
    "warm beige": (235, 220, 195),
    "sand": (194, 178, 128),
    "taupe": (179, 139, 109),
    "warm brown": (150, 75, 0),
    "chocolate brown": (92, 51, 23),
    "espresso brown": (43, 29, 20),
}

COLOR_WORDS = set()
for c in COLOR_PALETTE.keys():
    for word in c.split():
        COLOR_WORDS.add(word.lower())
COLOR_WORDS.update({
    "neon", "matte", "metallic", "glossy", "satin", "pastel", "vibrant", "bright",
    "dark", "light", "deep", "soft", "warm", "cool", "pale", "tinted", "shimmering"
})


def hex_to_rgb(hex_str: str) -> Tuple[int, int, int]:
    """Parses a hex color string into an (r, g, b) tuple."""
    if not hex_str:
        return (128, 128, 128)
    h = str(hex_str).lstrip("#").strip()
    if len(h) == 3:
        h = "".join([c * 2 for c in h])
    elif len(h) == 8:
        h = h[:6]
    if len(h) != 6:
        return (128, 128, 128)
    try:
        return tuple(int(h[i : i + 2], 16) for i in (0, 2, 4))
    except ValueError:
        return (128, 128, 128)


def hex_to_color_name(hex_str: str) -> str:
    """
    Maps any hex color string to its closest natural language English color descriptor.
    Prevents video generation models from seeing raw hex strings and rendering them on screen.
    """
    if not hex_str:
        return ""
    r, g, b = hex_to_rgb(hex_str)
    best_name = "neutral tone"
    best_dist = float("inf")
    for name, (cr, cg, cb) in COLOR_PALETTE.items():
        dr, dg, db = r - cr, g - cg, b - cb
        # Weighted Euclidean distance approximating human perceptual color difference
        dist = 2 * (dr**2) + 4 * (dg**2) + 3 * (db**2)
        if dist < best_dist:
            best_dist = dist
            best_name = name
    return best_name


# Video ads end inside the live scene; the CTA is Meta's button, never a screen rendered in the clip.
NO_END_SCREEN_LINE = (
    "ENDING: The video ends inside the live scene on the final beat's action, with no cut away. "
    "No end screen, end card, logo slate, title card, CTA card or button, packshot on a plain background, "
    "or fade to a brand-colour screen."
)
NO_END_SCREEN_AVOID = (
    "end screens, end cards, logo slates or logo reveals, title cards, CTA cards or buttons, "
    "plain-background packshot outros, fades to a solid brand-colour screen"
)


def sanitize_video_prompt(text: str) -> str:
    """
    Cleans video generation prompts of all raw hexadecimal color codes (e.g. #FF5252, #FFFFFF).
    Video diffusion/multimodal models (e.g. Omni Flash, Veo) treat hex codes as literal text tokens
    and render them visibly on props, wardrobe, surfaces, or overlay titles.
    This function converts hex codes into descriptive English color names and eliminates redundant tags.
    """
    if not text:
        return ""
    cleaned = text

    # Step 1: Strip parenthesized or bracketed hex following a color word: e.g. 'chartreuse (#D3E935)' -> 'chartreuse'
    def strip_redundant_paren_hex(match):
        preceding = match.group(1)
        recent_words = [w.lower().strip(",.;:") for w in preceding.split()[-3:]]
        if any(w in COLOR_WORDS for w in recent_words):
            return preceding
        hex_code = match.group(2)
        return f"{preceding} ({hex_to_color_name(hex_code)})"

    cleaned = re.sub(
        r"(\b[a-zA-Z\-]+(?:\s+[a-zA-Z\-]+){0,2})\s*[\(\[]\s*(#[0-9a-fA-F]{3,8})\s*[\)\]]",
        strip_redundant_paren_hex,
        cleaned,
    )

    # Step 2: Strip unparenthesized hex immediately following a color word: e.g. 'dark navy #152B36 with' -> 'dark navy with'
    def strip_redundant_hex(match):
        preceding = match.group(1)
        recent_words = [w.lower().strip(",.;:") for w in preceding.split()[-2:]]
        if any(w in COLOR_WORDS for w in recent_words):
            return preceding
        hex_code = match.group(2)
        return f"{preceding} {hex_to_color_name(hex_code)}"

    cleaned = re.sub(
        r"(\b[a-zA-Z\-]+(?:\s+[a-zA-Z\-]+)?)\s+(#[0-9a-fA-F]{3,8})(?=\s|[.,;:\)]|$)",
        strip_redundant_hex,
        cleaned,
    )

    # Step 3: Any remaining hex codes (e.g. standalone '#FF5252' or '(#FF5252)') -> replace with descriptive color name
    def replace_remaining_hex(match):
        return hex_to_color_name(match.group(0))

    cleaned = re.sub(r"#[0-9a-fA-F]{3,8}\b", replace_remaining_hex, cleaned)

    # Step 4: Clean up repetitive 'color accents in brand palette ...'
    def clean_palette_line(match):
        colors_part = match.group(1).strip()
        parts = [c.strip() for c in re.split(r"[,;]|\band\b", colors_part) if c.strip()]
        unique_colors = list(dict.fromkeys(parts))
        if len(unique_colors) > 1:
            joined = ", ".join(unique_colors[:-1]) + " and " + unique_colors[-1]
        elif unique_colors:
            joined = unique_colors[0]
        else:
            joined = "brand accent tones"
        return f"color accents in brand palette {joined} "

    cleaned = re.sub(
        r"colou?r accents in (?:the )?brand palette ([^(\n]+?)\s*(?=\()",
        clean_palette_line,
        cleaned,
        flags=re.IGNORECASE,
    )

    # Normalize double spaces
    cleaned = re.sub(r"[ \t]{2,}", " ", cleaned)
    return cleaned


def get_video_dimensions(file_path: str) -> Tuple[Optional[int], Optional[int]]:
    """Probes the width and height of an MP4/video file using ffmpeg."""
    if not file_path or not os.path.isfile(file_path):
        return None, None
    try:
        import imageio_ffmpeg
        import subprocess

        exe = imageio_ffmpeg.get_ffmpeg_exe()
        res = subprocess.run([exe, "-i", file_path], capture_output=True, text=True, errors="replace")
        m = re.search(r"Video:.*?,\s*(\d{3,4})x(\d{3,4})", res.stderr)
        if m:
            return int(m.group(1)), int(m.group(2))
    except Exception as e:
        logger.warning(f"Failed to probe video dimensions for {file_path}: {e}")
    return None, None


def target_video_dimensions(
    current_w: int,
    current_h: int,
    target_resolution: str,
    aspect_ratio: Optional[str] = None,
) -> Tuple[int, int]:
    """Calculates the target pixel width and height for a desired resolution tier (720p, 1080p, 4k)."""
    res = (target_resolution or "1080p").strip().lower()
    if res in ("4k", "2160p", "uhd"):
        base = 2160
    elif res in ("1080p", "fhd"):
        base = 1080
    else:
        base = 720

    ratio = (aspect_ratio or "").strip()
    if ratio == "9:16":
        return base, int(round((base * 16 / 9) / 2.0) * 2)
    elif ratio == "16:9":
        return int(round((base * 16 / 9) / 2.0) * 2), base
    elif ratio == "1:1":
        return base, base
    elif ratio == "4:5":
        return base, int(round((base * 5 / 4) / 2.0) * 2)

    # Fallback to current aspect ratio if not specified
    if current_w < current_h:
        tw = base
        th = int(round((base * current_h / current_w) / 2.0) * 2)
    elif current_w > current_h:
        th = base
        tw = int(round((base * current_w / current_h) / 2.0) * 2)
    else:
        tw = base
        th = base
    return tw, th


def ensure_video_resolution(
    file_path: str,
    target_resolution: str,
    aspect_ratio: Optional[str] = None,
) -> str:
    """
    Ensures the video file matches the target resolution (720p, 1080p, 4k).
    If the video output from the model is lower resolution (e.g. native 720p base frames
    when 1080p or 4k was requested), upscales using high-fidelity Lanczos filtering.
    """
    if not file_path or not os.path.isfile(file_path):
        return file_path

    res_norm = (target_resolution or "1080p").strip().lower()
    if res_norm not in OMNI_VIDEO_RESOLUTIONS:
        res_norm = "1080p"

    w, h = get_video_dimensions(file_path)
    if not w or not h:
        return file_path

    tw, th = target_video_dimensions(w, h, res_norm, aspect_ratio)

    # If the video is already at or exceeding target dimensions, keep as-is
    if w >= tw and h >= th:
        logger.info(f"Video {file_path} already at {w}x{h} (meets target {tw}x{th}). No upscale needed.")
        return file_path

    logger.info(f"Upscaling video {file_path} from {w}x{h} to {tw}x{th} ({res_norm})...")
    try:
        import imageio_ffmpeg
        import subprocess

        exe = imageio_ffmpeg.get_ffmpeg_exe()
        out_path = file_path.rsplit(".", 1)[0] + f"_{res_norm}.mp4"
        cmd = [
            exe,
            "-y",
            "-i",
            file_path,
            "-vf",
            f"scale={tw}:{th}:flags=lanczos",
            "-c:v",
            "libx264",
            "-crf",
            "18",
            "-preset",
            "fast",
            "-c:a",
            "copy",
            out_path,
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True)
        if proc.returncode == 0 and os.path.isfile(out_path) and os.path.getsize(out_path) > 0:
            os.replace(out_path, file_path)
            logger.info(f"Successfully scaled video to {tw}x{th} ({res_norm}).")
            return file_path
        else:
            logger.warning(f"ffmpeg upscale failed (code {proc.returncode}): {proc.stderr[:300]}")
    except Exception as e:
        logger.error(f"Error ensuring video resolution: {e}")

    return file_path

