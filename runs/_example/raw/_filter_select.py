import json, re, os

BASE = os.path.dirname(__file__)
# brand page regex per competitor
BRAND_RE = {
    "sanfe": re.compile(r"sanfe", re.I),
    "bombay-shaving-company": re.compile(r"bombay shaving|bombae", re.I),
    "plum-goodness": re.compile(r"\bplum\b|plum bodylovin", re.I),
}
# exclude page names that are retailers even if they match (none needed now, but keep Flipkart/Nykaa out)
EXCLUDE_RE = re.compile(r"flipkart|nykaa|myntra|zepto|blinkit|purplle|amazon", re.I)

# relevance keywords to Arriv (body / sweat / odor / deo / chafing / fragrance / body care)
REL_RE = re.compile(r"sweat|odou?r|deo|body\b|whole body|chaf|fragrance|mist|perfume|wash|underarm|armpit|fresh|smell|moistur|skin|summer|heat|hygiene", re.I)

def score(c):
    s = 0
    dr = c.get("days_running") or 0
    s += min(dr, 120) / 10.0            # longevity up to 12
    vc = c.get("versions_count")
    if isinstance(vc, int) and vc > 1: s += vc * 2
    if vc == "multiple": s += 3
    txt = " ".join(str(c.get(k) or "") for k in ("primary_text","headline","link_description"))
    if REL_RE.search(txt): s += 6       # relevance bonus
    if c.get("is_partnership"): s += 2   # UGC signal
    return round(s, 1)

for comp, brx in BRAND_RE.items():
    fp = os.path.join(BASE, comp, "ads.json")
    data = json.load(open(fp, encoding="utf-8"))
    cards = data["cards"]
    kept = [c for c in cards if c.get("page_name") and brx.search(c["page_name"]) and not EXCLUDE_RE.search(c["page_name"])]
    for c in kept:
        c["relevance_score"] = score(c)
    kept.sort(key=lambda c: c["relevance_score"], reverse=True)
    # ensure format mix: take top by score but guarantee >=1 image and >=1 video if available
    sel, seen_fmt = [], set()
    for c in kept:
        if len(sel) >= 8: break
        sel.append(c)
    # guarantee an image present
    if not any(c["format"] in ("image","carousel") for c in sel):
        img = next((c for c in kept if c["format"] in ("image","carousel")), None)
        if img and img not in sel: sel[-1] = img
    sel_ids = {c["library_id"] for c in sel}
    for c in cards:
        c["selected"] = c["library_id"] in sel_ids
        if c["library_id"] in sel_ids:
            c["selection_reason"] = f"score {c.get('relevance_score')} | {c.get('days_running')}d live | {c['format']} | " + ("relevant-theme" if REL_RE.search(' '.join(str(c.get(k) or '') for k in ('primary_text','headline'))) else "format/longevity")
    data["kept_brand_cards"] = len(kept)
    data["selected_ids"] = list(sel_ids)
    json.dump(data, open(fp, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    print(f"\n=== {comp}: {len(cards)} total, {len(kept)} brand, {len(sel)} selected ===")
    for c in sel:
        print(f"  {c['library_id']} | {c['format']:8} | {c.get('days_running')}d | sc={c['relevance_score']} | {c['page_name'][:28]:28} | {(c.get('headline') or (c.get('primary_text') or '')[:40])[:45]}")
