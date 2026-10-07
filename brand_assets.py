"""
Brand assets pulled from the brand's own website: the logo used as the wordmark in ads.

find_brand_logo() ranks the page's logo images, downloads the best one, renders SVG logos to
PNG with headless Chromium, and saves a transparent PNG in static/generated.
"""
import io
import re
import uuid
import logging
from typing import List, Optional, Tuple
from urllib.parse import urljoin, urlparse, parse_qsl, urlencode, urlunparse

import requests
from bs4 import BeautifulSoup
from PIL import Image

from media_utils import GENERATED_DIR, is_public_http_url

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"
}
MAX_LOGO_BYTES = 5 * 1024 * 1024
LOGO_RENDER_WIDTH = 800


def _norm(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", (text or "").lower())


def _bigger(src: str) -> str:
    """Ask image CDNs (Shopify-style ?width/?height) for a larger rendition."""
    parts = urlparse(src)
    query = [(k, v) for k, v in parse_qsl(parts.query) if k not in ("width", "height", "crop")]
    if any(k in dict(parse_qsl(parts.query)) for k in ("width", "height")):
        query.append(("width", str(LOGO_RENDER_WIDTH)))
    return urlunparse(parts._replace(query=urlencode(query)))


def logo_candidates(page_url: str, html: str, brand_name: str = "") -> List[str]:
    """Logo image URLs on the page, best first."""
    soup = BeautifulSoup(html, "html.parser")
    brand = _norm(brand_name) or _norm(urlparse(page_url).netloc.split(".")[-2] if "." in urlparse(page_url).netloc else "")
    header = soup.find("header")
    scored: List[Tuple[int, str]] = []
    for img in soup.find_all("img"):
        src = img.get("src") or img.get("data-src") or ""
        if not src or src.startswith("data:"):
            continue
        attrs = " ".join(str(img.get(a, "")) for a in ("class", "id", "alt", "src")).lower()
        alt = _norm(img.get("alt", ""))
        score = 0
        if "logo" in attrs:
            score += 3
        if brand and (brand in alt or brand in _norm(src)):
            score += 4
        if header and header in img.parents:
            score += 2
        if alt and brand and brand not in alt and "logo" not in src.lower():
            score -= 4  # partner / marketplace logos ("Ajio", "Myntra", ...)
        if "white" in src.lower() or "light" in src.lower():
            score -= 1  # usually invisible on light backgrounds
        if score > 0:
            scored.append((score, urljoin(page_url, src)))
    og = soup.find("meta", property="og:image") or soup.find("meta", attrs={"name": "og:image"})
    if og and og.get("content"):
        scored.append((1, urljoin(page_url, og["content"])))
    seen, ordered = set(), []
    for _, u in sorted(scored, key=lambda x: -x[0]):
        u = "https:" + u if u.startswith("//") else u
        if u not in seen:
            seen.add(u)
            ordered.append(u)
    return ordered


def _render_svg(svg_bytes: bytes) -> Optional[bytes]:
    """SVG -> transparent PNG via headless Chromium (image models cannot read SVG)."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return None
    svg = svg_bytes.decode("utf-8", errors="replace")
    html = (
        "<html><body style='margin:0;background:transparent'>"
        f"<div id='l' style='display:inline-block;width:{LOGO_RENDER_WIDTH}px'>{svg}</div>"
        "<style>#l svg{width:100%;height:auto;display:block}</style></body></html>"
    )
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page(viewport={"width": LOGO_RENDER_WIDTH, "height": LOGO_RENDER_WIDTH})
            page.set_content(html)
            png = page.locator("#l").screenshot(omit_background=True)
            browser.close()
            return png
    except Exception as e:
        logger.warning(f"[brand_assets] SVG render failed: {e}")
        return None


def _visibility_on_white(img: Image.Image) -> float:
    """Share of visible pixels dark enough to read on a white background (0..1)."""
    rgba = img.convert("RGBA").resize((min(img.width, 300), max(1, int(img.height * min(img.width, 300) / img.width))))
    visible = [(r, g, b) for r, g, b, a in rgba.getdata() if a > 64]
    if not visible:
        return 0.0
    dark = sum(1 for r, g, b in visible if 0.299 * r + 0.587 * g + 0.114 * b < 200)
    return dark / len(visible)


def _download_logo(src: str) -> Optional[Image.Image]:
    if not is_public_http_url(src):
        return None
    try:
        res = requests.get(_bigger(src), headers=HEADERS, timeout=12)
        res.raise_for_status()
        data = res.content[:MAX_LOGO_BYTES]
    except Exception as e:
        logger.info(f"[brand_assets] logo download failed {src}: {e}")
        return None
    is_svg = "svg" in res.headers.get("content-type", "") or urlparse(src).path.lower().endswith(".svg")
    if is_svg:
        data = _render_svg(data)
        if not data:
            return None
    try:
        img = Image.open(io.BytesIO(data))
        img.load()
    except Exception:
        return None
    if img.width < 40 or img.height < 12:
        return None
    return img


def find_brand_logo(page_url: str, brand_name: str = "") -> Optional[dict]:
    """Best logo from the brand site, saved as PNG. Returns {path, source, tone} or None."""
    try:
        res = requests.get(page_url, headers=HEADERS, timeout=12)
        res.raise_for_status()
    except Exception as e:
        logger.info(f"[brand_assets] could not load {page_url}: {e}")
        return None
    fallback = None
    for src in logo_candidates(page_url, res.text, brand_name)[:6]:
        img = _download_logo(src)
        if not img:
            continue
        visibility = _visibility_on_white(img)
        entry = (img, src, visibility)
        if visibility >= 0.3:
            return _save_logo(*entry)
        if not fallback or visibility > fallback[2]:
            fallback = entry
    return _save_logo(*fallback) if fallback else None


def save_uploaded_logo(content: bytes) -> Optional[dict]:
    try:
        img = Image.open(io.BytesIO(content))
        img.load()
    except Exception:
        return None
    return _save_logo(img, "upload", _visibility_on_white(img))


def _save_logo(img: Image.Image, source: str, visibility: float) -> dict:
    filename = f"logo_{uuid.uuid4().hex}.png"
    img.convert("RGBA").save(f"{GENERATED_DIR}/{filename}", "PNG")
    return {
        "path": f"/static/generated/{filename}",
        "source": source,
        # light logos (white wordmarks) need a dark area of the ad to sit on
        "tone": "dark" if visibility >= 0.3 else "light",
    }
