"""
Brand site crawl and claim checks for the Brand & Product Analyser.

The analyser only knows what the brand's own site says (plus review snippets found by search), so
this module gathers it carefully:

  - crawl_brand_site: the given page, the homepage and up to MAX_EXTRA_PAGES key pages (about, FAQ,
    reviews, ingredients/how it works, a product page), with JSON-LD ratings, reviews and FAQs and
    the market signals each page carries
  - check_proof_bank: keeps a claim only when its words are actually on a crawled page
  - voice_flags: copy that breaks the brand's voice rules
"""
import re
import json
import logging
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse, urljoin, urldefrag

from bs4 import BeautifulSoup

from media_utils import fetch_public_html, page_text, market_hints

logger = logging.getLogger(__name__)

MAX_EXTRA_PAGES = 5
PAGE_TEXT_LIMIT = 3500
MAX_JSONLD_REVIEWS = 25
MAX_FAQS = 12

# Which internal links are worth reading, in priority order (first match per kind wins)
PAGE_KINDS: List[Tuple[str, Tuple[str, ...]]] = [
    ("about", ("about", "our-story", "story", "who-we-are", "mission", "founder")),
    ("faq", ("faq", "faqs", "questions", "help")),
    ("reviews", ("review", "testimonial", "wall-of-love", "results")),
    ("how_it_works", ("ingredient", "how-it-works", "science", "technology", "clinical", "formula", "features")),
    ("product", ("/products/", "/product/", "/p/", "/shop/", "/collections/")),
]


def _site_key(url: str) -> str:
    return urlparse(url).netloc.lower().removeprefix("www.")


def _walk_jsonld(node: Any, out: Dict[str, Any]) -> None:
    """Collect ratings, reviews and FAQs from any JSON-LD shape (lists, @graph, nesting)."""
    if isinstance(node, list):
        for item in node:
            _walk_jsonld(item, out)
        return
    if not isinstance(node, dict):
        return
    types_ = node.get("@type")
    types_ = types_ if isinstance(types_, list) else [types_]
    rating = node.get("aggregateRating")
    if isinstance(rating, dict) and rating.get("ratingValue"):
        name = node.get("name") or "the product"
        count = rating.get("reviewCount") or rating.get("ratingCount")
        out["ratings"].append(f"{rating.get('ratingValue')}/{rating.get('bestRating') or 5} for {name}"
                              + (f" from {count} reviews" if count else ""))
    if "Review" in types_ and node.get("reviewBody"):
        out["reviews"].append(str(node["reviewBody"]).strip()[:400])
    if "Question" in types_:
        answer = node.get("acceptedAnswer") or {}
        text = answer.get("text") if isinstance(answer, dict) else ""
        if node.get("name"):
            out["faqs"].append({"q": str(node["name"]).strip()[:200],
                                "a": BeautifulSoup(str(text or ""), "html.parser").get_text(" ").strip()[:400]})
    for key, value in node.items():
        if key != "aggregateRating" and isinstance(value, (dict, list)):
            _walk_jsonld(value, out)


def _read_page(url: str) -> Optional[Dict[str, Any]]:
    try:
        final_url, html = fetch_public_html(url)
    except Exception as e:
        logger.info(f"[brand_research] skip {url}: {e}")
        return None
    soup = BeautifulSoup(html, "html.parser")
    data: Dict[str, Any] = {"ratings": [], "reviews": [], "faqs": []}
    for tag in soup.find_all("script", type="application/ld+json"):
        try:
            _walk_jsonld(json.loads(tag.string or tag.get_text() or "{}"), data)
        except ValueError:
            continue
    links = []
    for a in soup.find_all("a", href=True):
        href = urldefrag(urljoin(final_url, a["href"]))[0]
        if href.startswith("http"):
            links.append(href)
    hints = market_hints(soup, html)
    return {
        "url": final_url,
        "text": page_text(soup, PAGE_TEXT_LIMIT),
        "market_hints": hints,
        "links": links,
        **data,
    }


def _pick_key_pages(pages: List[Dict[str, Any]], site: str, seen: set) -> List[Tuple[str, str]]:
    links = [l for p in pages for l in p["links"] if _site_key(l) == site]
    picked: List[Tuple[str, str]] = []
    for kind, words in PAGE_KINDS:
        for link in links:
            path = urlparse(link).path.lower()
            if link not in seen and any(w in path for w in words):
                picked.append((kind, link))
                seen.add(link)
                break
        if len(picked) >= MAX_EXTRA_PAGES:
            break
    return picked


def crawl_brand_site(url: str) -> Dict[str, Any]:
    """The brand's own words: the given page, its homepage and key pages, with JSON-LD ratings,
    reviews and FAQs and the market signals they carry. Pages that fail are skipped."""
    site = _site_key(url)
    root = f"{urlparse(url).scheme}://{urlparse(url).netloc}/"
    start = [("given", url)] + ([("home", root)] if url.rstrip("/") != root.rstrip("/") else [])
    with ThreadPoolExecutor(max_workers=6) as pool:
        first = [dict(p, kind=k) for (k, _), p in zip(start, pool.map(_read_page, [u for _, u in start])) if p]
        seen = {u for _, u in start} | {p["url"] for p in first}
        extra = _pick_key_pages(first, site, seen)
        more = [dict(p, kind=k) for (k, _), p in zip(extra, pool.map(_read_page, [u for _, u in extra])) if p]
    pages = first + more
    for p in pages:
        p.pop("links", None)
    return {
        "site": site,
        "pages": pages,
        "market_hints": "; ".join(dict.fromkeys(h for p in pages for h in p["market_hints"].split("; ") if h)),
        "ratings": list(dict.fromkeys(r for p in pages for r in p["ratings"])),
        "reviews": list(dict.fromkeys(r for p in pages for r in p["reviews"]))[:MAX_JSONLD_REVIEWS],
        "faqs": [f for p in pages for f in p["faqs"]][:MAX_FAQS],
    }


def crawl_digest(crawl: Dict[str, Any]) -> str:
    """Crawl as prompt text, every page labelled with its URL so claims can cite it."""
    parts = []
    if crawl.get("market_hints"):
        parts.append(f"SITE MARKET SIGNALS: {crawl['market_hints']}")
    for p in crawl.get("pages", []):
        parts.append(f"=== PAGE [{p['kind']}] {p['url']} ===\n{p['text']}")
    if crawl.get("ratings"):
        parts.append("ON-SITE RATINGS (structured data): " + "; ".join(crawl["ratings"]))
    if crawl.get("reviews"):
        parts.append("ON-SITE REVIEWS (structured data, verbatim):\n" + "\n".join(f"- {r}" for r in crawl["reviews"]))
    if crawl.get("faqs"):
        parts.append("ON-SITE FAQ:\n" + "\n".join(f"- Q: {f['q']} A: {f['a']}" for f in crawl["faqs"]))
    return "\n\n".join(parts)


_WORD = re.compile(r"[a-z0-9%$€£¥₹.,/+-]+")


def _norm(text: str) -> str:
    return " ".join(_WORD.findall((text or "").lower()))


def appears_in(claim: str, page: str) -> bool:
    """A claim counts as on the page when it appears verbatim, or when nearly all of its words and
    every one of its numbers do (the model may trim punctuation or reorder slightly)."""
    c, p = _norm(claim), _norm(page)
    if not c:
        return False
    if c in p:
        return True
    words = [w for w in c.split() if len(w) > 2 or any(ch.isdigit() for ch in w)]
    page_words = set(p.split())
    numbers = [w for w in words if any(ch.isdigit() for ch in w)]
    if any(n not in page_words for n in numbers):
        return False
    return bool(words) and sum(w in page_words for w in words) / len(words) >= 0.85


def check_proof_bank(claims: List[Dict[str, Any]], crawl: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """(verified, unverified). A claim is verified when it is found on a crawled page (or in the
    site's structured ratings/reviews/FAQ); its source_url is set to that page. Verified claims get
    ids P1, P2, ... for prompts to cite."""
    sources = [(p["url"], p["text"]) for p in crawl.get("pages", [])]
    structured = " ".join(crawl.get("ratings", []) + crawl.get("reviews", [])
                          + [f"{f['q']} {f['a']}" for f in crawl.get("faqs", [])])
    if structured:
        sources.append((crawl.get("pages", [{}])[0].get("url", ""), structured))
    verified, unverified, seen = [], [], set()
    for c in claims or []:
        text = (c.get("claim") or "").strip()
        if not text or _norm(text) in seen:
            continue
        seen.add(_norm(text))
        hit = next((u for u, t in sources if appears_in(text, t)), None)
        if hit:
            verified.append({**c, "id": f"P{len(verified) + 1}", "claim": text, "source_url": hit, "verified": True})
        else:
            unverified.append({**c, "claim": text, "verified": False})
    return verified, unverified


def voice_flags(text: str, avoid_words: List[str]) -> List[str]:
    """Avoid-list words or phrases that appear in a piece of copy (whole-word, case-insensitive)."""
    low = (text or "").lower()
    return [w for w in avoid_words or [] if w and re.search(rf"(?<![a-z0-9]){re.escape(w.lower())}(?![a-z0-9])", low)]
