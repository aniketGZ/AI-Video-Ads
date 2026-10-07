"""Competitor Ad Agent Engine — Meta Ads Library Analyser
Autonomous background agent that finds and studies the competitors' live Meta ads and hands
structured research (analysis/meta_refs.json) to the campaign flow, which writes the ads.

Every output is derived from the brand's own site and the ads actually captured. When a source
is unavailable the run says so and continues with less; it never substitutes canned content.
"""

import os
import sys
import re
import json
import time
import glob
import shutil
import asyncio
import logging
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from urllib.parse import urljoin
import requests
from bs4 import BeautifulSoup

from google import genai
from google.genai import types

from media_utils import market_hints

logger = logging.getLogger("competitor_ad_agent")
logger.setLevel(logging.INFO)

# Base directories
BASE_DIR = Path(__file__).resolve().parent
RUNS_DIR = BASE_DIR / "runs"
TOOLS_DIR = BASE_DIR / "tools" / "competitor_ad_agent"
EXTRACT_CARDS_JS = TOOLS_DIR / "extract_cards.js"
VIDEO_FRAMES_PY = TOOLS_DIR / "video_frames.py"

STEPS = [
    {"index": 0, "name": "Validate & Read Brand", "desc": "Inspect product image, extract product lock and brand kit."},
    {"index": 1, "name": "Resolve Competitors", "desc": "Search & resolve competitor pages in Meta Ad Library."},
    {"index": 2, "name": "Capture Meta Ads", "desc": "Extract live ad cards, scroll, de-dupe and select top performers."},
    {"index": 3, "name": "Ingest Creatives", "desc": "Download images/videos and extract hook frames (0–3s) & scene cuts."},
    {"index": 4, "name": "Gemini Ad Analysis", "desc": "Multimodal analysis of visual angles, hooks, copy and pacing."},
    {"index": 5, "name": "Synthesize Insights", "desc": "Cross-competitor patterns, saturated angles and white space -> meta_refs.json."},
    {"index": 6, "name": "Report & Handoff", "desc": "Write report.md and handoff.json from the captured research."},
]

# The agent selects this many top competitor ads in total (across all competitors) before analysis.
DEFAULT_TARGET_SELECTED_ADS = 50
# Capture about twice each competitor's share of the target so the ranking has a pool to choose from
CAPTURE_POOL_FACTOR = 2
MAX_CARDS_PER_COMPETITOR = 80
MAX_LIBRARY_SCROLLS = 30
ANALYSIS_CONCURRENCY = 5
# Meta signal is "strong" when the competitors have at least this many ads live for LONG_RUNNING_DAYS or more
STRONG_SIGNAL_MIN_ADS = 9
LONG_RUNNING_DAYS = 14
# Ad Library country used when the brand's main market can't be read from its site
GLOBAL_COUNTRY = "ALL"


def _target_selected_ads(input_data: Dict[str, Any]) -> int:
    try:
        return max(1, int(input_data.get("settings", {}).get("target_selected_ads", DEFAULT_TARGET_SELECTED_ADS)))
    except (TypeError, ValueError):
        return DEFAULT_TARGET_SELECTED_ADS


def _capture_goal(input_data: Dict[str, Any], n_competitors: int) -> int:
    share = -(-_target_selected_ads(input_data) // max(1, n_competitors))
    return min(MAX_CARDS_PER_COMPETITOR, share * CAPTURE_POOL_FACTOR)


class AgentLogger:
    """Logs events both to memory (for UI streaming) and to run_log.md / agent_stream.jsonl"""
    def __init__(self, run_dir: Path):
        self.run_dir = run_dir
        self.log_file = run_dir / "run_log.md"
        self.stream_file = run_dir / "agent_stream.jsonl"
        self.events: List[Dict[str, Any]] = []

    def log(self, step: int, level: str, message: str, details: Optional[Any] = None, screenshot: Optional[str] = None):
        timestamp = datetime.now().strftime("%H:%M:%S")
        iso_time = datetime.now().isoformat()
        event = {
            "time": timestamp,
            "iso": iso_time,
            "step": step,
            "level": level.upper(),
            "message": message,
            "details": details,
            "screenshot": screenshot,
        }
        self.events.append(event)
        logger.info(f"[{level.upper()}] [Step {step}] {message}")

        # Append to agent_stream.jsonl
        try:
            with open(self.stream_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(event, ensure_ascii=False) + "\n")
        except Exception as e:
            logger.warning(f"Failed to append to stream file: {e}")

        # Update run_log.md summary
        self._append_markdown_log(step, timestamp, level, message)

    def _append_markdown_log(self, step: int, timestamp: str, level: str, message: str):
        try:
            if not self.log_file.exists():
                return
            content = self.log_file.read_text(encoding="utf-8", errors="replace")
            # If section exists
            entry = f"- `{timestamp}` **[{level}]** {message}\n"
            if "## Live Activity Log" not in content:
                content += "\n\n## Live Activity Log\n"
            content += entry
            self.log_file.write_text(content, encoding="utf-8")
        except Exception:
            pass

    def mark_step_complete(self, step_idx: int):
        try:
            if not self.log_file.exists():
                return
            content = self.log_file.read_text(encoding="utf-8", errors="replace")
            # replace [ ] Step {step_idx} with [x] Step {step_idx}
            pattern = re.compile(rf"- \[ \] (Step {step_idx} .*)")
            new_content = pattern.sub(r"- [x] \1", content)
            if new_content != content:
                self.log_file.write_text(new_content, encoding="utf-8")
        except Exception:
            pass


class ActiveRunState:
    """In-memory state of an active or recent run"""
    def __init__(self, run_id: str):
        self.run_id = run_id
        self.status = "idle"  # idle | running | complete | failed | stopped
        self.current_step = 0
        self.step_name = STEPS[0]["name"]
        self.progress = 0.0
        self.start_time = None
        self.error: Optional[str] = None
        self.cancel_requested = False
        self.latest_screenshot: Optional[str] = None
        self.stats = {
            "competitors_resolved": 0,
            "ads_seen": 0,
            "ads_selected": 0,
            "images_downloaded": 0,
            "videos_downloaded": 0,
            "ads_analyzed": 0,
            "image_prompts": 0,
            "video_prompts": 0,
        }
        self.logger: Optional[AgentLogger] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "run_id": self.run_id,
            "status": self.status,
            "current_step": self.current_step,
            "step_name": self.step_name,
            "progress": round(self.progress, 2),
            "start_time": self.start_time,
            "error": self.error,
            "stats": self.stats,
            "latest_screenshot": self.latest_screenshot,
            "logs_count": len(self.logger.events) if self.logger else 0,
        }


# Global store of active/monitored runs
RUN_STATES: Dict[str, ActiveRunState] = {}
RUN_TASKS: Dict[str, asyncio.Task] = {}


def get_or_create_run_state(run_id: str) -> ActiveRunState:
    if run_id not in RUN_STATES:
        state = ActiveRunState(run_id)
        run_dir = RUNS_DIR / run_id
        state.logger = AgentLogger(run_dir)
        # Check if already completed on disk
        if (run_dir / "handoff.json").exists():
            state.status = "complete"
            state.current_step = len(STEPS) - 1
            state.progress = 1.0
            state.step_name = STEPS[-1]["name"]
        RUN_STATES[run_id] = state
    return RUN_STATES[run_id]


def list_all_runs() -> List[Dict[str, Any]]:
    """List all available runs in the runs/ folder."""
    runs = []
    if not RUNS_DIR.exists():
        RUNS_DIR.mkdir(parents=True, exist_ok=True)

    for item in sorted(RUNS_DIR.iterdir()):
        if item.is_dir():
            run_id = item.name
            state = get_or_create_run_state(run_id)
            input_file = item / "input.json"
            brand_name = "Unknown"
            category = ""
            if input_file.exists():
                try:
                    data = json.loads(input_file.read_text(encoding="utf-8"))
                    brand_name = data.get("brand", {}).get("name", brand_name)
                    category = data.get("brand", {}).get("category", "")
                except Exception:
                    pass

            has_handoff = (item / "handoff.json").exists()
            has_report = (item / "report.md").exists()
            has_insights = (item / "analysis" / "insights.md").exists()
            has_product = any((item / "uploads").glob("product.*")) if (item / "uploads").exists() else False

            runs.append({
                "run_id": run_id,
                "brand_name": brand_name,
                "category": category,
                "status": "complete" if has_handoff else state.status,
                "has_handoff": has_handoff,
                "has_report": has_report,
                "has_insights": has_insights,
                "has_product": has_product,
                "current_step": state.current_step,
                "progress": state.progress,
            })
    return runs


# ==============================================================================
# GEMINI CLIENT & MULTIMODAL CALLS
# ==============================================================================

def get_gemini_client(api_key: Optional[str] = None) -> Optional[genai.Client]:
    key = (api_key or "").strip() or os.environ.get("GEMINI_API_KEY", "").strip()
    if not key:
        return None
    try:
        return genai.Client(api_key=key)
    except Exception as e:
        logger.warning(f"Could not initialize GenAI client: {e}")
        return None


def call_gemini_text(
    client: genai.Client,
    prompt: str,
    system_instruction: Optional[str] = None,
    response_mime: Optional[str] = None,
    image_parts: Optional[List[Any]] = None,
) -> str:
    """Robust helper to call Gemini with fallback across available models."""
    # Current model first; the older ones are retired on this API (404) and only cost a failed round trip
    models_to_try = ["gemini-3.6-flash"]
    contents = []
    if image_parts:
        contents.extend(image_parts)
    contents.append(prompt)

    config_kwargs = {}
    if system_instruction:
        config_kwargs["system_instruction"] = system_instruction
    if response_mime:
        config_kwargs["response_mime_type"] = response_mime

    config = types.GenerateContentConfig(**config_kwargs) if config_kwargs else None

    last_err = None
    for m in models_to_try:
        try:
            resp = client.models.generate_content(
                model=m,
                contents=contents,
                config=config,
            )
            if resp and resp.text:
                return resp.text.strip()
        except Exception as e:
            last_err = e
            logger.debug(f"Gemini model {m} failed: {e}")
            continue

    raise RuntimeError(f"All Gemini models failed: {last_err}")


def extract_json_from_text(text: str) -> Any:
    """Clean markdown codeblocks and parse JSON safely."""
    clean = re.sub(r"^```(?:json)?\s*", "", text.strip(), flags=re.MULTILINE)
    clean = re.sub(r"\s*```$", "", clean.strip(), flags=re.MULTILINE)
    return json.loads(clean.strip())


def scrape_website_info(url: str) -> Tuple[str, Optional[str]]:
    """Scrapes clean text and og:image / hero image from a brand URL."""
    text = ""
    image_url = None
    try:
        if not re.match(r"^https?://", url, re.I):
            url = "https://" + url
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        resp = requests.get(url, headers=headers, timeout=12)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        market = market_hints(soup, resp.text)

        # Extract og:image
        og_img = soup.find("meta", property="og:image") or soup.find("meta", attrs={"name": "og:image"})
        if og_img and og_img.get("content"):
            image_url = urljoin(url, og_img["content"])

        # If no og:image, look for prominent hero/product image
        if not image_url:
            for img in soup.find_all("img"):
                src = img.get("src") or img.get("data-src")
                if src and any(w in src.lower() for w in ["product", "hero", "bottle", "pack", "cdn.shopify"]):
                    image_url = urljoin(url, src)
                    break

        for tag in soup(["script", "style", "noscript", "svg", "header", "footer"]):
            tag.decompose()

        raw_text = soup.get_text(separator="\n")
        lines = [line.strip() for line in raw_text.splitlines() if line.strip()]
        text = "\n".join(lines)[:7000]
        if market:
            text = f"[Site market signals: {market}]\n{text}"
    except Exception as e:
        logger.warning(f"Error scraping {url}: {e}")
    return text, image_url


MARKET_SCHEMA_TEXT = """"market": {
    "country_code": "ISO 3166-1 alpha-2 code of the main country the brand sells in (e.g. US, GB, DE, AU), or ALL if it clearly sells worldwide or the site gives no signal",
    "country": "country name, or Global",
    "language": "main language of the site and its customers, e.g. English",
    "currency": "ISO currency code shown on the site, or empty",
    "evidence": "the site signals this is based on (store country, currency, language, shipping text)"
  }"""


def clean_market(raw: Any) -> Dict[str, str]:
    """Market read from the site, with an Ad Library-safe country code (two letters or ALL)."""
    m = raw if isinstance(raw, dict) else {}
    code = str(m.get("country_code") or "").strip().upper()
    if not re.fullmatch(r"[A-Z]{2}", code):
        code = GLOBAL_COUNTRY
    return {
        "country_code": code,
        "country": str(m.get("country") or ("Global" if code == GLOBAL_COUNTRY else code)),
        "language": str(m.get("language") or ""),
        "currency": str(m.get("currency") or ""),
        "evidence": str(m.get("evidence") or ""),
    }


def _read_site_or_fail(url: str, client: Optional[genai.Client]) -> Tuple[str, Optional[str]]:
    """Brand site text for the analyst. Raises with a user-facing reason instead of guessing."""
    if not client:
        raise RuntimeError("A Gemini API key is required to read the brand site.")
    scraped_text, site_image_url = scrape_website_info(url)
    if not scraped_text:
        raise RuntimeError(f"Could not read {url}. Check the URL is public and try again.")
    return scraped_text, site_image_url


def discover_competitors_and_demographics(
    url: str,
    client: Optional[genai.Client] = None,
) -> Dict[str, Any]:
    """Fast discovery step: reads the brand URL and returns the brand profile, its main market,
    demographics and 3-5 direct competitors for the user to confirm.

    Raises RuntimeError when the site or Gemini can't be read; the caller shows that to the user."""
    scraped_text, site_image_url = _read_site_or_fail(url, client)

    prompt = f"""You are a senior Meta advertising strategist and market analyst.
Analyze this brand URL: {url}
Website content (the first line lists market signals read from the page code, if any):
{scraped_text[:5000]}

1. Identify the brand name, product category and hero product from the site.
2. Identify the brand's main market from the site's evidence: store country, currency, language, shipping text.
   Do not assume any country without evidence.
3. Describe the target customers in that market:
   - age_range (e.g. "25-40"), gender ("All genders", "Women" or "Men")
   - geography: the countries, regions or city types they live in, within the brand's market
   - lifestyle: daily habits relevant to the product
   - cultural_context: the environment and emotional triggers around the product for these customers
4. List 3 to 5 real direct competitor brands that sell a similar product to the same customers in the same
   market and are likely to run Meta ads there. Use exact brand names as they appear on their Facebook pages.
   For each: name, a one-line reason, selected: true.

Return ONLY valid JSON:
{{
  "brand_name": "...",
  "category": "...",
  "product": "...",
  "image_url": "{site_image_url or ''}",
  {MARKET_SCHEMA_TEXT},
  "demographics": {{
    "age_range": "...",
    "gender": "...",
    "geography": "...",
    "lifestyle": "...",
    "cultural_context": "..."
  }},
  "competitors": [
    {{"name": "...", "reason": "...", "selected": true}}
  ]
}}
"""
    try:
        parsed = extract_json_from_text(call_gemini_text(client, prompt, response_mime="application/json"))
    except Exception as e:
        raise RuntimeError(f"Gemini could not analyse the site: {e}") from e
    if not isinstance(parsed, dict) or not parsed.get("competitors"):
        raise RuntimeError("Gemini returned no competitors for this site. Add competitors manually or try again.")
    parsed["market"] = clean_market(parsed.get("market"))
    parsed.setdefault("image_url", site_image_url or "")
    return parsed


def analyze_and_build_input_from_url(
    url: str,
    client: Optional[genai.Client],
    run_dir: Path,
    uploaded_product_bytes: Optional[bytes] = None,
    uploaded_product_ext: str = ".png",
    custom_competitors: Optional[List[Dict[str, Any]]] = None,
    custom_demographics: Optional[Dict[str, Any]] = None,
    custom_market: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Builds input.json for a run from the brand URL, the optional product photo and the
    competitors / demographics / market the user confirmed at discovery.

    Raises RuntimeError when the site or Gemini can't be read."""
    uploads_dir = run_dir / "uploads"
    uploads_dir.mkdir(parents=True, exist_ok=True)

    scraped_text, site_image_url = _read_site_or_fail(url, client)

    # Product photo: the user's upload, otherwise the site's own hero image (never a drawn stand-in)
    p_path = uploads_dir / f"product{uploaded_product_ext}"
    if uploaded_product_bytes:
        p_path.write_bytes(uploaded_product_bytes)
    elif site_image_url:
        try:
            r = requests.get(site_image_url, timeout=15)
            if r.status_code == 200:
                p_path.write_bytes(r.content)
        except Exception as e:
            logger.warning(f"Could not download site image {site_image_url}: {e}")

    prompt = f"""You are a senior brand analyst. Analyze this brand website: {url}

Website content (the first line lists market signals read from the page code, if any):
{scraped_text[:6000]}

Use only what the site says or clearly shows. Return ONLY valid JSON:
{{
  "brand": {{
    "name": "brand name",
    "url": "{url}",
    "category": "specific product category",
    "product": "hero product name and a one-line description",
    "usp": ["3 to 4 benefits or advantages the site states"],
    "audience": "who the site is selling to",
    "tone": "how the brand writes (e.g. playful, clinical, premium)",
    "brand_colors": ["#hex of the main brand colours seen on the site"]
  }},
  {MARKET_SCHEMA_TEXT},
  "demographics": {{
    "age_range": "...",
    "gender": "...",
    "geography": "countries, regions or city types within the brand's market",
    "lifestyle": "...",
    "cultural_context": "..."
  }},
  "competitors": [{{"name": "direct competitor brand selling in the same market"}}]
}}
"""
    try:
        input_data = extract_json_from_text(call_gemini_text(client, prompt, response_mime="application/json"))
    except Exception as e:
        raise RuntimeError(f"Gemini could not analyse the site: {e}") from e
    if not isinstance(input_data, dict) or not isinstance(input_data.get("brand"), dict):
        raise RuntimeError("Gemini returned an unreadable brand analysis. Try again.")

    # The user's confirmed choices from discovery win over this second read
    if custom_competitors:
        input_data["competitors"] = custom_competitors
    if custom_demographics and isinstance(custom_demographics, dict):
        input_data["demographics"] = custom_demographics
        aud_summary = f"{custom_demographics.get('age_range', '')} {custom_demographics.get('lifestyle', '')} in {custom_demographics.get('geography', '')}".strip()
        if aud_summary:
            input_data["brand"]["audience"] = aud_summary
    market = clean_market(custom_market or input_data.get("market"))
    input_data["market"] = market
    input_data["settings"] = default_settings(market)

    (run_dir / "input.json").write_text(json.dumps(input_data, indent=2, ensure_ascii=False), encoding="utf-8")
    return input_data


def default_settings(market: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Run settings; the Ad Library is searched in the brand's main market (ALL when unknown)."""
    return {
        "ad_library_country": clean_market(market)["country_code"],
        "target_selected_ads": DEFAULT_TARGET_SELECTED_ADS,
        "video_duration_s": 8,
    }


# ==============================================================================
# PIPELINE STEP IMPLEMENTATIONS
# ==============================================================================

async def step_0_validate_and_read_brand(
    run_dir: Path,
    input_data: Dict[str, Any],
    client: Optional[genai.Client],
    agent_logger: AgentLogger,
) -> bool:
    """Step 0: Validate input.json and uploads/product.*, write product_lock.md and brand_kit.json"""
    agent_logger.log(0, "info", "Validating inputs and analyzing brand...")

    uploads_dir = run_dir / "uploads"
    brand_dir = run_dir / "brand"
    brand_dir.mkdir(parents=True, exist_ok=True)

    product_files = list(uploads_dir.glob("product.*")) if uploads_dir.exists() else []
    product_file = product_files[0] if product_files else None

    if not product_file or not product_file.exists():
        agent_logger.log(0, "warning", "Product image missing in uploads/! Prompts will mark product_reference as MISSING.")
    else:
        agent_logger.log(0, "info", f"Found product image: {product_file.name}")

    product_lock_file = brand_dir / "product_lock.md"
    brand_kit_file = brand_dir / "brand_kit.json"

    # If product lock already exists, keep or enrich
    if not product_lock_file.exists():
        if client and product_file:
            agent_logger.log(0, "info", "Calling Gemini Vision to inspect uploaded product and generate product_lock.md...")
            try:
                with open(product_file, "rb") as f:
                    pbytes = f.read()
                mime = "image/png" if product_file.suffix.lower() == ".png" else "image/jpeg"
                part = types.Part.from_bytes(data=pbytes, mime_type=mime)

                prompt = (
                    "You are a forensic packaging and industrial design QA expert.\n"
                    "Analyze this product photo with microscopic precision. Write a factual QC checklist\n"
                    "describing: Form & Silhouette, Dominant & Accent Colors (with approximate hex values),\n"
                    "Materials & Finish (matte, gloss, frosted, metallic), Label Layout & Typography,\n"
                    "Cap/Closure/Pump mechanism, and exact Proportions.\n"
                    "End with a mandatory one-line 'Product Lock Clause' that will be copy-pasted verbatim\n"
                    "into all image and video generation prompts."
                )
                lock_text = call_gemini_text(client, prompt, image_parts=[part])
                product_lock_file.write_text(lock_text, encoding="utf-8")
                agent_logger.log(0, "success", "Generated brand/product_lock.md via Gemini Vision.")
            except Exception as e:
                agent_logger.log(0, "warning", f"Gemini vision call failed: {e}. No product lock written; the campaign flow locks the product from the user's photos.")
        else:
            agent_logger.log(0, "info", "No product photo or Gemini key; skipping the product lock (the campaign flow locks the product from the user's photos).")

    # Brand kit
    if not brand_kit_file.exists():
        # Only what the site analysis found; the campaign flow builds the full brand kit from the site and logo
        brand_kit = {
            "brand_name": input_data.get("brand", {}).get("name", ""),
            "palette": input_data.get("brand", {}).get("brand_colors") or [],
            "created_at": datetime.now().isoformat(),
        }
        brand_kit_file.write_text(json.dumps(brand_kit, indent=2), encoding="utf-8")
        agent_logger.log(0, "success", "Written brand/brand_kit.json.")

    agent_logger.mark_step_complete(0)
    return True


def _scroll_and_collect(page, extract_js: str, goal: int) -> List[Dict[str, Any]]:
    """Scroll an Ad Library results page, extracting after every scroll (the page only renders part of the
    feed at a time), until `goal` unique cards are collected or the feed stops growing."""
    seen: Dict[str, Dict[str, Any]] = {}
    stale_scrolls = 0
    for _ in range(MAX_LIBRARY_SCROLLS):
        before = len(seen)
        try:
            res = page.evaluate(f"({extract_js})()")
        except Exception:
            res = None
        for c in (res.get("cards", []) if isinstance(res, dict) else []):
            key = c.get("library_id") or f"{c.get('page_name')}|{c.get('headline')}|{(c.get('primary_text') or '')[:60]}"
            seen.setdefault(key, c)
        if len(seen) >= goal:
            break
        stale_scrolls = stale_scrolls + 1 if len(seen) == before else 0
        if stale_scrolls >= 3:
            break
        page.mouse.wheel(0, 2400)
        page.wait_for_timeout(1500)
    return list(seen.values())


def _write_empty_ads_record(ads_file: Path, cname: str, url: Optional[str], reason: str) -> None:
    """Record that a competitor yielded no ads (and why). Empty records are retried on resume."""
    ads_file.parent.mkdir(parents=True, exist_ok=True)
    ads_file.write_text(json.dumps({
        "competitor": cname,
        "url": url,
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "card_count": 0,
        "cards": [],
        "no_ads_reason": reason,
    }, indent=2, ensure_ascii=False), encoding="utf-8")


def _has_cached_cards(ads_file: Path) -> bool:
    try:
        return bool(json.loads(ads_file.read_text(encoding="utf-8")).get("cards"))
    except Exception:
        return False


def _run_playwright_sync(
    competitors: List[Dict[str, Any]],
    country: str,
    capture_goal: int,
    raw_dir: Path,
    run_log_dir: Path,
    state: ActiveRunState,
    agent_logger: AgentLogger,
):
    """Synchronous worker running inside a separate thread to bypass Windows asyncio loop limitations."""
    from playwright.sync_api import sync_playwright

    extract_js = ""
    if EXTRACT_CARDS_JS.exists():
        extract_js = EXTRACT_CARDS_JS.read_text(encoding="utf-8")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            locale="en-US",
            extra_http_headers={"Accept-Language": "en-US,en;q=0.9"},
            viewport={"width": 1366, "height": 900},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        )
        page = context.new_page()

        for comp in competitors:
            if state.cancel_requested:
                agent_logger.log(1, "warning", "Run cancelled by user.")
                break

            cname = comp.get("name", "competitor")
            slug_name = _slug(cname)
            comp_dir = raw_dir / slug_name
            comp_dir.mkdir(parents=True, exist_ok=True)

            ads_file = comp_dir / "ads.json"
            if ads_file.exists():
                try:
                    existing = json.loads(ads_file.read_text(encoding="utf-8"))
                    if existing.get("cards"):
                        agent_logger.log(1, "info", f"Competitor '{cname}' already has cached ads.json ({len(existing['cards'])} cards).")
                        state.stats["competitors_resolved"] += 1
                        continue
                except Exception:
                    pass

            page_id = comp.get("facebook_page")
            if page_id and str(page_id).isdigit():
                url = f"https://www.facebook.com/ads/library/?active_status=active&ad_type=all&country={country}&view_all_page_id={page_id}&search_type=page&media_type=all"
            else:
                encoded = requests.utils.quote(cname)
                url = f"https://www.facebook.com/ads/library/?active_status=active&ad_type=all&country={country}&q={encoded}&search_type=keyword_unordered&media_type=all"

            agent_logger.log(1, "info", f"Navigating to Meta Ad Library for '{cname}' -> {url}")
            try:
                page.goto(url, timeout=35000, wait_until="networkidle")
                page.wait_for_timeout(2500)

                # Screenshot search view
                shot_path = run_log_dir / f"{slug_name}_results.png"
                page.screenshot(path=str(shot_path))
                state.latest_screenshot = f"/api/competitor-agent/runs/{state.run_id}/artifact/run_log/{shot_path.name}"
                agent_logger.log(1, "info", f"Captured browser screenshot for '{cname}'", screenshot=state.latest_screenshot)

                # Scroll and extract with extract_cards.js until this competitor's capture goal is met
                cards = []
                if extract_js:
                    agent_logger.log(1, "info", f"Scrolling '{cname}' results to collect up to {capture_goal} ads...")
                    cards = _scroll_and_collect(page, extract_js, capture_goal)

                # If country != "ALL" and 0 cards were found, try fallback to ALL countries
                if not cards and country.upper() != "ALL":
                    agent_logger.log(1, "info", f"0 local ads in '{country}' for '{cname}'. Checking global ad inventory (country=ALL)...")
                    url_all = f"https://www.facebook.com/ads/library/?active_status=active&ad_type=all&country=ALL&q={requests.utils.quote(cname)}&search_type=keyword_unordered&media_type=all"
                    try:
                        page.goto(url_all, timeout=30000, wait_until="networkidle")
                        page.wait_for_timeout(2000)
                        if extract_js:
                            cards = _scroll_and_collect(page, extract_js, capture_goal)
                    except Exception:
                        pass

                # If cards found, write ads.json
                if cards:
                    ads_record = {
                        "competitor": cname,
                        "url": page.url,
                        "captured_at": datetime.now(timezone.utc).isoformat(),
                        "card_count": len(cards),
                        "cards": cards,
                    }
                    ads_file.write_text(json.dumps(ads_record, indent=2, ensure_ascii=False), encoding="utf-8")
                    agent_logger.log(1, "success", f"Extracted {len(cards)} active ads for '{cname}' from Meta Ad Library.")
                else:
                    _write_empty_ads_record(ads_file, cname, url, "no live ads in the Ad Library")
                    agent_logger.log(1, "warning", f"No live ads found in the Ad Library for '{cname}'.")

                state.stats["competitors_resolved"] += 1
            except Exception as ex:
                _write_empty_ads_record(ads_file, cname, url, f"browser error: {ex}")
                agent_logger.log(1, "warning", f"Could not read the Ad Library for '{cname}': {ex}")

        browser.close()


async def step_1_find_competitors(
    run_dir: Path,
    input_data: Dict[str, Any],
    state: ActiveRunState,
    agent_logger: AgentLogger,
) -> bool:
    """Step 1: Discover / resolve competitors on Meta Ad Library via Playwright browser."""
    agent_logger.log(1, "info", "Checking competitor pages in Meta Ad Library...")
    competitors = input_data.get("competitors", [])
    country = input_data.get("settings", {}).get("ad_library_country") or GLOBAL_COUNTRY
    run_log_dir = run_dir / "run_log"
    run_log_dir.mkdir(parents=True, exist_ok=True)
    raw_dir = run_dir / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)

    # Skip the browser only when every competitor already has captured ads (empty records are retried)
    all_cached = all(_has_cached_cards(raw_dir / _slug(comp.get("name", "")) / "ads.json") for comp in competitors)

    if all_cached and len(competitors) > 0:
        agent_logger.log(1, "info", "All competitor raw data already cached locally. Skipping browser navigation.")
        state.stats["competitors_resolved"] = len(competitors)
        agent_logger.mark_step_complete(1)
        return True

    # Real Playwright browser session run via worker thread (safe on Windows SelectorEventLoop)
    try:
        agent_logger.log(1, "info", "Launching Playwright browser (Chromium) to inspect Meta Ad Library...")
        await asyncio.to_thread(
            _run_playwright_sync,
            competitors,
            country,
            _capture_goal(input_data, len(competitors)),
            raw_dir,
            run_log_dir,
            state,
            agent_logger,
        )
    except Exception as e:
        agent_logger.log(1, "warning", f"The Ad Library browser failed: {e}. Continuing without competitor ads.")
        for comp in competitors:
            ads_file = raw_dir / _slug(comp.get("name", "competitor")) / "ads.json"
            if not ads_file.exists():
                _write_empty_ads_record(ads_file, comp.get("name", "competitor"), None, f"browser failed to start: {e}")

    agent_logger.mark_step_complete(1)
    return True


def _safe_int(val: Any, default: int = 0) -> int:
    """Safely convert any longevity or version count value (including 'multiple' or None) to int."""
    if isinstance(val, (int, float)):
        return int(val)
    if isinstance(val, str):
        if val.isdigit():
            return int(val)
        if "multi" in val.lower():
            return 3
    return default


async def step_2_capture_ads(
    run_dir: Path,
    input_data: Dict[str, Any],
    state: ActiveRunState,
    agent_logger: AgentLogger,
) -> bool:
    """Step 2: Select the top ads across all competitors until the target (default 50) is reached."""
    agent_logger.log(2, "info", "Extracting and filtering active ad cards...")
    competitors = input_data.get("competitors", [])
    target = _target_selected_ads(input_data)
    raw_dir = run_dir / "raw"

    def rank_key(card: Dict[str, Any], cname: str):
        # Keyword searches also return other advertisers who mention the competitor; rank the competitor's own page first
        own_page = cname.lower() in (card.get("page_name") or "").lower()
        return (own_page, _safe_int(card.get("days_running")), _safe_int(card.get("versions_count")))

    total_seen = 0
    loaded = []  # (cname, ads_file, data, ranked real cards)
    for comp in competitors:
        cname = comp.get("name", "")
        ads_file = raw_dir / _slug(cname) / "ads.json"
        if not ads_file.exists():
            agent_logger.log(2, "warning", f"No ads.json found for '{cname}' in {ads_file.parent}.")
            continue
        try:
            data = json.loads(ads_file.read_text(encoding="utf-8"))
        except Exception as e:
            agent_logger.log(2, "warning", f"Error parsing ads.json for '{cname}': {e}")
            continue
        cards = data.get("cards", [])
        for c in cards:
            c.pop("selected", None)
            c.pop("selection_reason", None)
        # "inferred_" cards are placeholders that older runs wrote when the Ad Library couldn't be read
        real = [c for c in cards if not str(c.get("library_id", "")).startswith("inferred_")]
        real.sort(key=lambda c, n=cname: rank_key(c, n), reverse=True)
        total_seen += len(real)
        loaded.append((cname, ads_file, data, real))
        agent_logger.log(2, "info", f"Loaded '{cname}': {len(real)} live ads seen.")

    # Take turns across competitors (best remaining ad of each) so one advertiser cannot fill the whole target
    selected_real = 0
    queues = [(cname, list(real)) for cname, _, _, real in loaded]
    rank = 0
    while selected_real < target and any(q for _, q in queues):
        rank += 1
        for cname, queue in queues:
            if queue and selected_real < target:
                card = queue.pop(0)
                card["selected"] = True
                card["selection_reason"] = f"#{rank} for {cname} by longevity ({card.get('days_running', 0)}d)"
                selected_real += 1

    for _, ads_file, data, _ in loaded:
        ads_file.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    if selected_real == 0:
        agent_logger.log(2, "warning", "None of the competitors are running live ads that could be captured. The campaign will be built from the brand site alone.")
    elif selected_real >= target:
        agent_logger.log(2, "success", f"Target reached: {target} top ads selected across {len(loaded)} competitors.")
    else:
        agent_logger.log(2, "warning", f"Only {selected_real} live ads available across competitors (target {target}); continuing with those.")

    state.stats["ads_seen"] = total_seen
    state.stats["ads_selected"] = selected_real
    state.stats["target_selected_ads"] = target
    agent_logger.mark_step_complete(2)
    return True


async def step_3_ingest_creatives(
    run_dir: Path,
    input_data: Dict[str, Any],
    state: ActiveRunState,
    agent_logger: AgentLogger,
) -> bool:
    """Step 3: Download media and extract hook frames (0–3s) + scene frames."""
    agent_logger.log(3, "info", "Ingesting creative media and extracting video frames...")
    raw_dir = run_dir / "raw"
    media_dir = run_dir / "media"
    frames_dir = run_dir / "frames"
    transcripts_dir = run_dir / "transcripts"

    media_dir.mkdir(parents=True, exist_ok=True)
    frames_dir.mkdir(parents=True, exist_ok=True)
    transcripts_dir.mkdir(parents=True, exist_ok=True)

    competitors = input_data.get("competitors", [])

    for comp in competitors:
        slug_name = _slug(comp.get("name", ""))
        comp_media_dir = media_dir / slug_name
        comp_media_dir.mkdir(parents=True, exist_ok=True)

        ads_file = raw_dir / slug_name / "ads.json"
        if not ads_file.exists():
            continue

        try:
            data = json.loads(ads_file.read_text(encoding="utf-8"))
            cards = data.get("cards", [])
            selected_cards = [c for c in cards if c.get("selected")]

            for card in selected_cards:
                if state.cancel_requested:
                    return False

                lid = card.get("library_id")
                fmt = card.get("format", "unknown")

                # Video extraction
                if fmt == "video":
                    v_file = comp_media_dir / f"{lid}.mp4"
                    # If not downloaded yet and video_urls exist, try download
                    if not v_file.exists():
                        v_urls = card.get("video_urls", [])
                        if v_urls and v_urls[0].get("src"):
                            src = v_urls[0]["src"]
                            try:
                                r = requests.get(src, timeout=20, stream=True)
                                if r.status_code == 200:
                                    with open(v_file, "wb") as f:
                                        for chunk in r.iter_content(chunk_size=65536):
                                            f.write(chunk)
                                    agent_logger.log(3, "info", f"Downloaded video {lid}.mp4 ({slug_name})")
                                    state.stats["videos_downloaded"] += 1
                            except Exception as ex:
                                agent_logger.log(3, "warning", f"Failed to download video {lid}: {ex}")

                    # Frame extraction via video_frames.py or imageio_ffmpeg
                    ad_frames_dir = frames_dir / lid
                    if v_file.exists() and not (ad_frames_dir / "meta.json").exists():
                        ad_frames_dir.mkdir(parents=True, exist_ok=True)
                        cmd = [sys.executable, str(VIDEO_FRAMES_PY), str(v_file), str(ad_frames_dir)]
                        def _extract_frames_sync():
                            return subprocess.run(
                                cmd,
                                capture_output=True,
                                text=True,
                                encoding="utf-8",
                                errors="replace",
                            )
                        proc_res = await asyncio.to_thread(_extract_frames_sync)
                        if proc_res.returncode == 0:
                            agent_logger.log(3, "info", f"Extracted hook & scene frames for video {lid}")
                        else:
                            agent_logger.log(3, "warning", f"Frame extraction for {lid} notice: {proc_res.stderr[:120]}")

                # Image extraction
                elif fmt in ("image", "carousel"):
                    img_urls = card.get("image_urls", [])
                    for i_idx, i_url in enumerate(img_urls):
                        i_file = comp_media_dir / f"{lid}_{i_idx}_.jpg"
                        if not i_file.exists() and i_url:
                            try:
                                r = requests.get(i_url, timeout=15)
                                if r.status_code == 200:
                                    i_file.write_bytes(r.content)
                                    state.stats["images_downloaded"] += 1
                            except Exception:
                                pass
        except Exception as e:
            agent_logger.log(3, "warning", f"Error ingesting creatives for {slug_name}: {e}")

    # Update latest frame preview for UI spy view
    all_hook_frames = list(frames_dir.glob("*/hook_00_0s.jpg"))
    if all_hook_frames:
        rel = all_hook_frames[0].relative_to(run_dir)
        state.latest_screenshot = f"/api/competitor-agent/runs/{state.run_id}/artifact/{rel.as_posix()}"

    agent_logger.mark_step_complete(3)
    return True


async def step_4_gemini_ad_analysis(
    run_dir: Path,
    input_data: Dict[str, Any],
    client: Optional[genai.Client],
    state: ActiveRunState,
    agent_logger: AgentLogger,
) -> bool:
    """Step 4: Multimodal analysis of each selected ad using Gemini."""
    agent_logger.log(4, "info", "Starting Gemini Multimodal Ad Analysis...")
    analysis_dir = run_dir / "analysis"
    analysis_dir.mkdir(parents=True, exist_ok=True)
    jsonl_file = analysis_dir / "ads.jsonl"

    existing_ids = set()
    if jsonl_file.exists():
        for line in jsonl_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line:
                try:
                    existing_ids.add(json.loads(line).get("library_id"))
                except Exception:
                    pass

    # Collect selected ads
    raw_dir = run_dir / "raw"
    media_dir = run_dir / "media"
    frames_dir = run_dir / "frames"
    competitors = input_data.get("competitors", [])

    ads_to_analyze = []
    for comp in competitors:
        cname = comp.get("name", "")
        slug_name = _slug(cname)
        ads_file = raw_dir / slug_name / "ads.json"
        if not ads_file.exists():
            continue
        try:
            data = json.loads(ads_file.read_text(encoding="utf-8"))
            for c in data.get("cards", []):
                if c.get("selected") and c.get("library_id") not in existing_ids:
                    ads_to_analyze.append((cname, slug_name, c))
        except Exception:
            pass

    agent_logger.log(4, "info", f"Found {len(ads_to_analyze)} new ad creatives to analyze with Gemini.")
    if ads_to_analyze and not client:
        agent_logger.log(4, "warning", "No Gemini API key, so the captured ads can't be analysed.")
        ads_to_analyze = []

    analyzed_count = len(existing_ids)

    # Analyse ads in parallel (each is an independent Gemini call); results are written as they finish
    semaphore = asyncio.Semaphore(ANALYSIS_CONCURRENCY)

    async def analyze_one(cname: str, slug_name: str, card: Dict[str, Any]):
        async with semaphore:
            if state.cancel_requested:
                return None

            lid = card.get("library_id")
            fmt = card.get("format", "unknown")
            primary_text = card.get("primary_text") or ""
            headline = card.get("headline") or ""
            cta = card.get("cta_button") or ""
            days = card.get("days_running") or 0
            versions = card.get("versions_count") or 1

            agent_logger.log(4, "info", f"Analyzing ad {lid} ({cname}) with Gemini: '{headline[:35]}'...")

            image_parts = []
            # Attach visual evidence
            if fmt == "video":
                hook_frames = sorted(list((frames_dir / lid).glob("hook_*.jpg")))
                for hf in hook_frames[:4]:  # send first 4 hook frames
                    try:
                        with open(hf, "rb") as f:
                            image_parts.append(types.Part.from_bytes(data=f.read(), mime_type="image/jpeg"))
                    except Exception:
                        pass
            else:
                img_files = sorted(list((media_dir / slug_name).glob(f"{lid}_*.jpg")))
                for img in img_files[:2]:
                    try:
                        with open(img, "rb") as f:
                            image_parts.append(types.Part.from_bytes(data=f.read(), mime_type="image/jpeg"))
                    except Exception:
                        pass

            analysis_record = None
            if client:
                prompt = f"""You are a senior Meta direct-response ad strategist.
Analyze this competitor ad thoroughly based on the creative imagery and metadata.

Metadata:
- Competitor: {cname}
- Format: {fmt}
- Days Active: {days} days
- Versions Count: {versions}
- Headline: "{headline}"
- Primary Text: "{primary_text}"
- CTA: "{cta}"

Output ONLY a valid JSON object matching this schema exactly:
{{
  "library_id": "{lid}",
  "competitor": "{cname}",
  "format": "{fmt}",
  "aspect_ratio": "9:16",
  "duration_s": {card.get('video_urls', [{}])[0].get('duration_s', 0) if fmt == 'video' else 0},
  "days_running": {days},
  "versions_count": {versions if isinstance(versions, int) else 2},
  "performance_signal": "strong | medium | weak (inferred)",
  "media_status": "full",
  "angle": "pain-point | benefit | social-proof | offer | comparison | demo | UGC/testimonial | lifestyle | founder/story | education",
  "hook": "Specific attention grabber in the first frame / 1–3s in your own words",
  "copy": {{
    "headline": "{headline}",
    "primary_text_summary": "{primary_text[:120]}",
    "cta": "{cta}"
  }},
  "visual": {{
    "composition": "focal point, camera distance, typography layout",
    "product_presence": "hero | in-use | in-hand | absent",
    "people": "none | hands | face-to-camera | lifestyle group",
    "setting": "bathroom / gym / bedroom / studio / outdoors",
    "lighting": "bright high-key / warm natural / dramatic moody",
    "palette": ["#hex1", "#hex2"],
    "text_overlay_density": "none | light | heavy",
    "typography_feel": "bold condensed sans / playful script / clean modern"
  }},
  "video_structure": [
    {{ "t": "0–1.5s", "beat": "hook", "shot": "opening visual", "on_screen_text": "text hook", "audio": "VO/sfx" }},
    {{ "t": "1.5–5s", "beat": "problem/demo", "shot": "demonstration", "on_screen_text": "demo text", "audio": "VO" }},
    {{ "t": "5–8s", "beat": "solution/CTA", "shot": "packshot and offer", "on_screen_text": "{cta}", "audio": "call to action" }}
  ],
  "why_it_likely_works": "1–2 sentences explaining performance signal",
  "weaknesses": "what it misses or does poorly"
}}"""
                for attempt in (1, 2):
                    try:
                        raw_json_str = await asyncio.to_thread(
                            call_gemini_text,
                            client,
                            prompt,
                            image_parts=image_parts if image_parts else None,
                            response_mime="application/json",
                        )
                        analysis_record = extract_json_from_text(raw_json_str)
                        break
                    except Exception as ex:
                        if attempt == 2:
                            agent_logger.log(4, "warning", f"Gemini could not analyse ad {lid}: {ex}. Skipping it.")

            if not isinstance(analysis_record, dict):
                return None
            # Facts from the Ad Library card win over whatever the model echoed back
            analysis_record.update({"library_id": lid, "competitor": cname, "format": fmt,
                                    "days_running": _safe_int(days), "versions_count": _safe_int(versions, 1)})
            return analysis_record, image_parts, lid, fmt

    tasks = [asyncio.create_task(analyze_one(cname, slug_name, card)) for cname, slug_name, card in ads_to_analyze]
    for finished in asyncio.as_completed(tasks):
        outcome = await finished
        if outcome is None:
            continue
        analysis_record, image_parts, lid, fmt = outcome

        # Append to jsonl
        with open(jsonl_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(analysis_record, ensure_ascii=False) + "\n")

        analyzed_count += 1
        state.stats["ads_analyzed"] = analyzed_count

        # Update preview frame in UI
        if image_parts and fmt == "video":
            hf = frames_dir / lid / "hook_00_0s.jpg"
            if hf.exists():
                state.latest_screenshot = f"/api/competitor-agent/runs/{state.run_id}/artifact/frames/{lid}/hook_00_0s.jpg"

    if state.cancel_requested:
        return False

    agent_logger.log(4, "success", f"Step 4 complete: {analyzed_count} ads analyzed.")
    agent_logger.mark_step_complete(4)
    return True


def _load_analysis_records(run_dir: Path) -> List[Dict[str, Any]]:
    """Analysed ads of a run, longest-running first (placeholder cards from older runs left out)."""
    jsonl_file = run_dir / "analysis" / "ads.jsonl"
    records = []
    if jsonl_file.exists():
        for line in jsonl_file.read_text(encoding="utf-8", errors="replace").splitlines():
            try:
                rec = json.loads(line)
            except ValueError:
                continue
            if isinstance(rec, dict) and rec.get("library_id") and not str(rec["library_id"]).startswith("inferred_"):
                records.append(rec)
    records.sort(key=lambda r: (_safe_int(r.get("days_running")), _safe_int(r.get("versions_count"))), reverse=True)
    return records


def _ref_fields(rec: Dict[str, Any]) -> Dict[str, Any]:
    visual = rec.get("visual") or {}
    return {
        "library_id": str(rec.get("library_id")),
        "competitor": rec.get("competitor") or "",
        "days_running": _safe_int(rec.get("days_running")),
        "versions_count": _safe_int(rec.get("versions_count"), 1),
        "angle": rec.get("angle") or "",
        "hook": rec.get("hook") or "",
        "composition": visual.get("composition") or "",
        "product_presence": visual.get("product_presence") or "",
        "people": visual.get("people") or "",
        "setting": visual.get("setting") or "",
        "lighting": visual.get("lighting") or "",
        "palette": visual.get("palette") or [],
        "text_overlay_density": visual.get("text_overlay_density") or "",
        "typography_feel": visual.get("typography_feel") or "",
        "copy": rec.get("copy") or {},
        "why_it_works": rec.get("why_it_likely_works") or "",
        "weaknesses": rec.get("weaknesses") or "",
    }


def _source_coverage(run_dir: Path, input_data: Dict[str, Any], records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Per competitor: ads found, how many ran LONG_RUNNING_DAYS+, how many were analysed, and why none if none."""
    analysed: Dict[str, int] = {}
    for r in records:
        analysed[r.get("competitor") or ""] = analysed.get(r.get("competitor") or "", 0) + 1
    out = []
    for comp in input_data.get("competitors", []):
        cname = comp.get("name", "")
        row = {"brand": cname, "relation": "competitor", "ads_found": 0, "ads_long_running": 0,
               "ads_analysed": analysed.get(cname, 0), "no_ads_reason": ""}
        ads_file = run_dir / "raw" / _slug(cname) / "ads.json"
        if ads_file.exists():
            try:
                data = json.loads(ads_file.read_text(encoding="utf-8"))
                real = [c for c in data.get("cards", []) if not str(c.get("library_id", "")).startswith("inferred_")]
                row["ads_found"] = len(real)
                row["ads_long_running"] = sum(1 for c in real if _safe_int(c.get("days_running")) >= LONG_RUNNING_DAYS)
                row["no_ads_reason"] = data.get("no_ads_reason") or ("" if real else "no live ads captured")
            except Exception:
                row["no_ads_reason"] = "ads.json unreadable"
        else:
            row["no_ads_reason"] = "not searched"
        out.append(row)
    return out


def _synthesis_prompt(brand: Dict[str, Any], market: Dict[str, Any], refs: Dict[str, List[Dict[str, Any]]]) -> str:
    rows = []
    for ref in refs["image_refs"] + refs["video_refs"]:
        row = {k: ref[k] for k in ("id", "competitor", "days_running", "versions_count", "angle", "hook", "composition",
                                   "product_presence", "people", "setting", "lighting", "text_overlay_density",
                                   "typography_feel", "why_it_works", "weaknesses")}
        row["headline"] = (ref.get("copy") or {}).get("headline", "")
        if ref.get("structure"):
            row["beats"] = [f"{b.get('t')} {b.get('beat')}: {b.get('shot')}" for b in ref["structure"] if isinstance(b, dict)]
        rows.append(row)
    return f"""You are a creative strategist studying the live Meta ads of {brand.get('name') or 'a brand'}'s competitors
({brand.get('category') or 'same category'}; market: {market.get('country') or 'global'}).
Below are ALL {len(rows)} analysed ads, longest-running first. Ids starting with R are image ads, V are video ads.
Days running is the only performance signal: an ad that has run longer has very likely kept earning its spend.

{json.dumps(rows, ensure_ascii=False)}

Return ONLY valid JSON:
{{
  "per_competitor": [{{"competitor": "...", "dominant_angles": ["..."], "formats": ["..."], "visual_signature": "one sentence"}}],
  "winning_patterns": [{{"kind": "hook | layout | beat_structure | copy | offer", "pattern": "a reusable pattern in your own words, specific enough to brief a designer",
                         "evidence": ["ids of the ads showing it"], "why": "why it likely works, tied to days running"}}],
  "saturated": ["angles or visuals most competitors repeat"],
  "whitespace": ["angles, audiences or visual treatments none of these ads use"]
}}
Rules: every pattern cites at least one id from the list; weight patterns by the days running of their evidence;
describe patterns generically (never copy a competitor's wording, people or brand assets); 5 to 12 winning_patterns."""


def _render_insights_md(meta_refs: Dict[str, Any]) -> str:
    """Human-readable view of meta_refs.json for the run page and report."""
    lines = [f"# Competitor ad insights — {meta_refs.get('brand') or ''}", "",
             f"Market: {(meta_refs.get('market') or {}).get('country') or 'Global'} · Meta signal: **{meta_refs.get('signal')}**", ""]
    lines.append("## Coverage")
    for src in meta_refs.get("sources", []):
        note = f" ({src['no_ads_reason']})" if src.get("no_ads_reason") else ""
        lines.append(f"- **{src['brand']}**: {src['ads_found']} live ads, {src['ads_long_running']} running {LONG_RUNNING_DAYS}+ days, {src['ads_analysed']} analysed{note}")
    syn = meta_refs.get("synthesis") or {}
    if not syn:
        lines += ["", "_No cross-competitor synthesis for this run (no analysed ads, or Gemini was unavailable)._"]
        return "\n".join(lines) + "\n"
    if syn.get("per_competitor"):
        lines += ["", "## Per competitor"]
        for c in syn["per_competitor"]:
            lines.append(f"- **{c.get('competitor')}**: {', '.join(c.get('dominant_angles') or [])} · formats: {', '.join(c.get('formats') or [])} · {c.get('visual_signature') or ''}")
    if syn.get("winning_patterns"):
        lines += ["", "## Winning patterns"]
        for w in syn["winning_patterns"]:
            lines.append(f"- [{w.get('kind')}] {w.get('pattern')} — {w.get('why')} (seen in {', '.join(w.get('evidence') or [])})")
    for title, key in (("Saturated territory", "saturated"), ("White space", "whitespace")):
        if syn.get(key):
            lines += ["", f"## {title}"] + [f"- {x}" for x in syn[key]]
    return "\n".join(lines) + "\n"


async def step_5_synthesize_insights(
    run_dir: Path,
    input_data: Dict[str, Any],
    client: Optional[genai.Client],
    agent_logger: AgentLogger,
) -> bool:
    """Step 5: structured handoff of every analysed ad + cross-competitor synthesis -> analysis/meta_refs.json
    (and analysis/insights.md, a readable view of it)."""
    agent_logger.log(5, "info", "Synthesizing cross-competitor patterns...")
    analysis_dir = run_dir / "analysis"
    analysis_dir.mkdir(parents=True, exist_ok=True)

    records = _load_analysis_records(run_dir)
    brand = input_data.get("brand", {})
    market = input_data.get("market") or {"country_code": input_data.get("settings", {}).get("ad_library_country", GLOBAL_COUNTRY)}
    sources = _source_coverage(run_dir, input_data, records)
    long_running = sum(s["ads_long_running"] for s in sources)

    image_refs, video_refs = [], []
    for rec in records:
        ref = _ref_fields(rec)
        if rec.get("format") == "video":
            ref["id"] = f"V{len(video_refs) + 1}"
            ref["structure"] = rec.get("video_structure") or []
            video_refs.append(ref)
        else:
            ref["id"] = f"R{len(image_refs) + 1}"
            media = sorted((run_dir / "media").glob(f"*/{ref['library_id']}_*.jpg"))
            ref["media"] = media[0].relative_to(run_dir).as_posix() if media else ""
            image_refs.append(ref)

    meta_refs: Dict[str, Any] = {
        "brand": brand.get("name", ""),
        "category": brand.get("category", ""),
        "market": market,
        "signal": "none" if not records else ("strong" if long_running >= STRONG_SIGNAL_MIN_ADS else "thin"),
        "signal_rule": f">= {STRONG_SIGNAL_MIN_ADS} competitor ads live {LONG_RUNNING_DAYS}+ days is strong",
        "sources": sources,
        "image_refs": image_refs,
        "video_refs": video_refs,
        "synthesis": {},
        "created_at": datetime.now().isoformat(),
    }

    if records and client:
        prompt = _synthesis_prompt(brand, market, meta_refs)
        for attempt in (1, 2):
            try:
                syn = extract_json_from_text(await asyncio.to_thread(call_gemini_text, client, prompt, response_mime="application/json"))
                if isinstance(syn, dict):
                    meta_refs["synthesis"] = {k: syn.get(k) or [] for k in ("per_competitor", "winning_patterns", "saturated", "whitespace")}
                    break
            except Exception as e:
                if attempt == 2:
                    agent_logger.log(5, "warning", f"Gemini synthesis failed: {e}. The analysed ads are still handed over individually.")
    elif records:
        agent_logger.log(5, "warning", "No Gemini API key, so no cross-competitor synthesis was written.")

    (analysis_dir / "meta_refs.json").write_text(json.dumps(meta_refs, indent=2, ensure_ascii=False), encoding="utf-8")
    (analysis_dir / "insights.md").write_text(_render_insights_md(meta_refs), encoding="utf-8")
    agent_logger.log(5, "success" if records else "warning",
                     f"Wrote analysis/meta_refs.json: {len(image_refs)} image and {len(video_refs)} video references, signal {meta_refs['signal']}.")
    agent_logger.mark_step_complete(5)
    return True


# Marks insights.md files that older runs filled with canned text; load_competitor_run_summary ignores them
FALLBACK_INSIGHTS_MARKER = "<!-- fallback-insights: generic template, not derived from this run's ads -->"


async def step_6_report_and_handoff(
    run_dir: Path,
    input_data: Dict[str, Any],
    state: ActiveRunState,
    agent_logger: AgentLogger,
) -> bool:
    """Step 6: report.md and handoff.json, written only from what this run captured."""
    agent_logger.log(6, "info", "Compiling report and handoff...")
    meta_refs_file = run_dir / "analysis" / "meta_refs.json"
    meta_refs = json.loads(meta_refs_file.read_text(encoding="utf-8")) if meta_refs_file.exists() else {}
    brand = input_data.get("brand", {})

    report = [
        "# Competitor Ad Research Report", "",
        f"**Run:** `{state.run_id}` · **Date:** {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        f"**Brand:** {brand.get('name', '')} ({brand.get('category', '')})", "",
        "## Coverage",
        f"- Ad cards scanned: {state.stats['ads_seen']}",
        f"- Top ads selected (by days running): {state.stats['ads_selected']}",
        f"- Ads analysed: {state.stats['ads_analyzed']}",
        f"- Media downloaded: {state.stats['images_downloaded']} images, {state.stats['videos_downloaded']} videos", "",
    ]
    insights_file = run_dir / "analysis" / "insights.md"
    if insights_file.exists():
        report.append(insights_file.read_text(encoding="utf-8").split("\n", 1)[-1])
    (run_dir / "report.md").write_text("\n".join(report), encoding="utf-8")

    handoff = {
        "run_id": state.run_id,
        "status": "complete",
        "timestamp": datetime.now().isoformat(),
        "signal": meta_refs.get("signal", "none"),
        "coverage": {
            "ads_seen": state.stats["ads_seen"],
            "ads_selected": state.stats["ads_selected"],
            "ads_analysed": state.stats["ads_analyzed"],
            "images": state.stats["images_downloaded"],
            "videos": state.stats["videos_downloaded"],
            "source": "meta_ad_library_browser",
        },
        "outputs": {
            "meta_refs": "analysis/meta_refs.json",
            "insights": "analysis/insights.md",
            "report": "report.md",
        },
        "consumer": "campaign_flow (/api/flow/analyze, then /api/flow/prompts)",
    }
    (run_dir / "handoff.json").write_text(json.dumps(handoff, indent=2), encoding="utf-8")

    agent_logger.log(6, "success", "Research complete; handed over to the campaign builder.", details=handoff)
    agent_logger.mark_step_complete(6)
    return True


# ==============================================================================
# MAIN BACKGROUND RUNNER
# ==============================================================================

async def run_competitor_agent_pipeline(
    run_id: str,
    api_key: Optional[str] = None,
    from_step: int = 0,
):
    """Main background pipeline runner."""
    state = get_or_create_run_state(run_id)
    run_dir = RUNS_DIR / run_id
    agent_logger = state.logger or AgentLogger(run_dir)
    state.logger = agent_logger

    state.status = "running"
    state.start_time = datetime.now().isoformat()
    state.error = None
    state.cancel_requested = False

    agent_logger.log(0, "info", f"Competitor Ad Agent started for run '{run_id}' (from step {from_step}).")

    try:
        # Load input.json
        input_file = run_dir / "input.json"
        if not input_file.exists():
            raise FileNotFoundError(f"Missing input.json in {run_dir}")

        input_data = json.loads(input_file.read_text(encoding="utf-8"))
        client = get_gemini_client(api_key)
        if not client:
            agent_logger.log(0, "warning", "No Gemini API key supplied. Agent will run with template & heuristic models.")
        else:
            agent_logger.log(0, "info", "Gemini client initialized successfully.")

        async def run_step(idx: int) -> bool:
            if idx == 0:
                return await step_0_validate_and_read_brand(run_dir, input_data, client, agent_logger)
            elif idx == 1:
                return await step_1_find_competitors(run_dir, input_data, state, agent_logger)
            elif idx == 2:
                return await step_2_capture_ads(run_dir, input_data, state, agent_logger)
            elif idx == 3:
                return await step_3_ingest_creatives(run_dir, input_data, state, agent_logger)
            elif idx == 4:
                return await step_4_gemini_ad_analysis(run_dir, input_data, client, state, agent_logger)
            elif idx == 5:
                return await step_5_synthesize_insights(run_dir, input_data, client, agent_logger)
            elif idx == 6:
                return await step_6_report_and_handoff(run_dir, input_data, state, agent_logger)
            return True

        last_step = len(STEPS) - 1
        for s_idx in range(from_step, len(STEPS)):
            if state.cancel_requested:
                state.status = "stopped"
                agent_logger.log(s_idx, "warning", "Run was stopped by user.")
                return

            state.current_step = s_idx
            state.step_name = STEPS[s_idx]["name"]
            state.progress = s_idx / len(STEPS)

            success = await run_step(s_idx)
            # Once meta_refs.json exists (step 5), the campaign builder can start; the report keeps running alongside it
            if s_idx >= 5 and success:
                state.stats["campaign_ready"] = True
            if not success and state.cancel_requested:
                state.status = "stopped"
                return

        state.current_step = last_step
        state.progress = 1.0
        state.status = "complete"
        agent_logger.log(last_step, "success", f"Competitor Ad Agent run '{run_id}' finished successfully.")

    except Exception as e:
        logger.exception("Competitor Ad Agent execution failed")
        state.status = "failed"
        state.error = str(e)
        agent_logger.log(state.current_step, "error", f"Agent failed with error: {e}")


def _slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def load_reference_ads(run_id: str, image_limit: int = 12, video_limit: int = 8) -> Dict[str, List[dict]]:
    """The analysed competitor ads of a run, longest-running first, as concept/layout references.

    Image references carry the saved creative (`media_path`, relative to the run folder) so it can be
    attached to the image model as a layout reference; video references carry their beat structure."""
    out: Dict[str, List[dict]] = {"image": [], "video": []}
    if not run_id or not re.fullmatch(r"[A-Za-z0-9_\-]+", run_id):
        return out
    r_dir = RUNS_DIR / run_id
    for rec in _load_analysis_records(r_dir):
        lid = str(rec["library_id"])
        visual = rec.get("visual") or {}
        base = {
            "ref_id": lid,
            "competitor": rec.get("competitor") or "",
            "angle": rec.get("angle") or "",
            "hook": rec.get("hook") or "",
            "why_it_works": rec.get("why_it_likely_works") or "",
            "days_running": rec.get("days_running") or 0,
            "performance_signal": rec.get("performance_signal") or "",
            "composition": visual.get("composition") or "",
            "product_presence": visual.get("product_presence") or "",
            "people": visual.get("people") or "",
            "setting": visual.get("setting") or "",
            "lighting": visual.get("lighting") or "",
            "text_overlay_density": visual.get("text_overlay_density") or "",
            "typography_feel": visual.get("typography_feel") or "",
        }
        if rec.get("format") == "video":
            out["video"].append({**base, "structure": rec.get("video_structure") or []})
            continue
        media = sorted((r_dir / "media").glob(f"*/{lid}_*.jpg"))
        if not media:
            continue
        rel = media[0].relative_to(r_dir).as_posix()
        out["image"].append({
            **base,
            "run_id": run_id,
            "media_path": rel,
            "image_url": f"/api/competitor-agent/runs/{run_id}/artifact/{rel}",
        })
    out["image"] = _round_robin_by_competitor(out["image"], image_limit)
    out["video"] = _round_robin_by_competitor(out["video"], video_limit)
    return out


def _round_robin_by_competitor(refs: List[dict], limit: int) -> List[dict]:
    """Keep each competitor's best-first order but alternate competitors, so the references vary."""
    by_comp: Dict[str, List[dict]] = {}
    for r in refs:
        by_comp.setdefault(r["competitor"], []).append(r)
    picked: List[dict] = []
    while len(picked) < limit and any(by_comp.values()):
        for comp in list(by_comp):
            if by_comp[comp] and len(picked) < limit:
                picked.append(by_comp[comp].pop(0))
    return picked


def resolve_reference_media(run_id: str, media_path: str) -> Optional[Path]:
    """Safe local path of a reference creative inside runs/<run_id>/media, or None."""
    if not run_id or not re.fullmatch(r"[A-Za-z0-9_\-]+", run_id) or not media_path:
        return None
    media_root = (RUNS_DIR / run_id / "media").resolve()
    target = (RUNS_DIR / run_id / media_path).resolve()
    if media_root not in target.parents or not target.is_file():
        return None
    return target


def load_competitor_run_summary(run_id: str) -> Optional[dict]:
    """Extract competitor intelligence summary from a completed or running agent run."""
    if not run_id or not re.fullmatch(r"[A-Za-z0-9_\-]+", run_id):
        return None
    r_dir = RUNS_DIR / run_id
    if not r_dir.exists():
        return None

    comp_names = []
    total_ads = 0
    winning_hooks = []

    # Read raw ads
    raw_dir = r_dir / "raw"
    if raw_dir.exists():
        for comp_dir in raw_dir.iterdir():
            if comp_dir.is_dir():
                ads_json = comp_dir / "ads.json"
                if ads_json.exists():
                    try:
                        data = json.loads(ads_json.read_text(encoding="utf-8"))
                        c_name = data.get("competitor") or comp_dir.name
                        if c_name not in comp_names:
                            comp_names.append(c_name)
                        # "inferred_" cards are placeholders written when the Ad Library could not be read
                        cards = [c for c in data.get("cards", []) if not str(c.get("library_id", "")).startswith("inferred_")]
                        total_ads += len(cards)
                        for c in cards:
                            hl = c.get("headline") or ""
                            hook = c.get("hook") or ""
                            if hl and hl not in winning_hooks:
                                winning_hooks.append(hl)
                            elif hook and hook not in winning_hooks:
                                winning_hooks.append(hook)
                    except Exception:
                        pass

    demographics = {}
    input_file = r_dir / "input.json"
    if input_file.exists():
        try:
            demographics = json.loads(input_file.read_text(encoding="utf-8")).get("demographics") or {}
        except Exception:
            pass

    insights_text = ""
    insights_file = r_dir / "analysis" / "insights.md"
    if insights_file.exists():
        try:
            insights_text = insights_file.read_text(encoding="utf-8", errors="replace")
        except Exception:
            pass
    # Structured research from step 5 (runs before meta_refs.json existed only have insights.md)
    meta_refs = {}
    meta_refs_file = r_dir / "analysis" / "meta_refs.json"
    if meta_refs_file.exists():
        try:
            meta_refs = json.loads(meta_refs_file.read_text(encoding="utf-8"))
        except Exception:
            pass

    # Older runs filled insights.md with canned personal-care text; never pass that on as research.
    # Runs written before the marker existed are recognised by the canned Sanfe line.
    canned_for_other_market = (
        "**Sanfe:** Heavy focus on dark spot removal" in insights_text
        and not any("sanfe" in c.lower() for c in comp_names)
    )
    if FALLBACK_INSIGHTS_MARKER in insights_text or canned_for_other_market:
        insights_text = ""

    product_lock = ""
    lock_file = r_dir / "brand" / "product_lock.md"
    if lock_file.exists():
        try:
            product_lock = lock_file.read_text(encoding="utf-8", errors="replace")
        except Exception:
            pass

    return {
        "run_id": run_id,
        "competitors": comp_names,
        "total_ads": total_ads,
        "insights_text": insights_text,
        "winning_hooks": winning_hooks[:8],
        "product_lock": product_lock,
        "demographics": demographics,
        "market": meta_refs.get("market") or {},
        "signal": meta_refs.get("signal") or ("thin" if total_ads else "none"),
        "synthesis": meta_refs.get("synthesis") or {},
        # With no captured ads, insights.md is generic fallback text (not about this brand's market)
        "reliable": total_ads > 0,
        "report_url": f"/api/competitor-agent/runs/{run_id}/artifact/report.md"
    }
