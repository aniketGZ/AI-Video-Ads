import json, re, os, glob

BASE = os.path.dirname(os.path.dirname(__file__))
inp = json.load(open(os.path.join(BASE, "input.json"), encoding="utf-8"))
settings = inp["settings"]
groups = {g["id"]: g for g in inp["ad_groups"]}

# approved copy per group (lowercased), plus allow substrings of primary_text
def approved(gid):
    c = groups[gid]["copy"]
    strings = set()
    for k in ("headlines","primary_text","descriptions"):
        for s in c.get(k, []) or []:
            strings.add(s.strip().lower())
    if c.get("cta"): strings.add(c["cta"].strip().lower())
    pt = " ".join(c.get("primary_text", []) or []).lower()
    return strings, pt

# forbidden competitor terms
forbidden = set()
for comp in ["sanfe","bombay shaving company","bombae","plum goodness","plum bodylovin","bodylovin","fuzzoff","spotlite","pepticharge","caramello","hairess","airplay","nivea","pilgrim","nykaa","purplle","myntra","flipkart","zepto","blinkit"]:
    forbidden.add(comp)
for comp in ["sanfe","bombay-shaving-company","plum-goodness"]:
    d = json.load(open(os.path.join(BASE,"raw",comp,"ads.json"), encoding="utf-8"))
    for c in d["cards"]:
        if c.get("page_name"):
            for tok in re.split(r"\s+with\s+", c["page_name"].lower()):
                forbidden.add(tok.strip())
        if c.get("landing_domain"): forbidden.add(c["landing_domain"].lower())
forbidden = {f for f in forbidden if f and len(f) > 3 and f not in ("arriv",)}

errs, warns = [], []

def check_copy(gid, label, s):
    if not s: return
    appr, pt = approved(gid)
    sl = s.strip().lower()
    if sl in appr or sl in pt:
        return
    errs.append(f"{label}: copy not verbatim -> '{s}'")

def check_forbidden(label, text):
    tl = text.lower()
    for f in forbidden:
        if re.search(r"(?<![a-z])"+re.escape(f)+r"(?![a-z])", tl):
            errs.append(f"{label}: forbidden term '{f}' in prompt text")

# ---- images ----
imgs = json.load(open(os.path.join(BASE,"prompts","image_prompts.json"), encoding="utf-8"))
per_group = {}
for p in imgs:
    gid = p["ad_group_id"]; pid = p["id"]
    per_group.setdefault(gid, {"img":[], "concepts":[]})
    per_group[gid]["img"].append(pid); per_group[gid]["concepts"].append(p["concept_type"])
    # product ref
    if not any("product" in r["role"].lower() for r in p["reference_images"]):
        errs.append(f"{pid}: no product reference")
    if not p["prompt"].get("product_lock"): errs.append(f"{pid}: no product_lock")
    if p["aspect_ratio"] not in settings["image_aspect_ratios"]:
        errs.append(f"{pid}: aspect {p['aspect_ratio']} not in settings")
    to = p["prompt"]["text_overlay"]
    if to.get("render_in_image"):
        check_copy(gid, pid+" headline", to.get("headline"))
        check_copy(gid, pid+" cta", to.get("cta"))
    # forbidden scan over whole prompt
    check_forbidden(pid, json.dumps(p["prompt"]) + p.get("inspired_by_pattern",""))

# ---- videos ----
vids = json.load(open(os.path.join(BASE,"prompts","video_prompts.json"), encoding="utf-8"))
for p in vids:
    gid = p["ad_group_id"]; pid = p["id"]
    per_group.setdefault(gid, {"img":[], "concepts":[]})
    per_group[gid].setdefault("vid",[]).append(pid)
    per_group[gid].setdefault("vconcepts",[]).append(p["concept_type"])
    if not any("product" in r["role"].lower() for r in p["reference_images"]):
        errs.append(f"{pid}: no product reference")
    if "product" not in p["first_frame_prompt"].lower() or "unchanged" not in p["video_prompt"].lower():
        warns.append(f"{pid}: check product-lock phrasing in prompts")
    if p["aspect_ratio"] not in settings["video_aspect_ratios"]:
        errs.append(f"{pid}: aspect {p['aspect_ratio']} not in settings")
    if p["duration_s"] != settings["video_duration_s"]:
        errs.append(f"{pid}: duration {p['duration_s']} != {settings['video_duration_s']}")
    if p["model"] != settings["video_model"]:
        warns.append(f"{pid}: model {p['model']} != settings {settings['video_model']}")
    for b in p["beats"]:
        ost = b.get("on_screen_text")
        if ost and ost.lower() not in ("none",""):
            check_copy(gid, pid+f" beat {b['t']} on_screen_text", ost)
    check_copy(gid, pid+" end_card headline", re.search(r"Headline '([^']+)'", p["end_card"]).group(1) if re.search(r"Headline '([^']+)'", p["end_card"]) else None)
    # voiceover must be verbatim primary_text / approved
    check_copy(gid, pid+" voiceover", p.get("voiceover"))
    check_forbidden(pid, p["video_prompt"] + p["first_frame_prompt"] + p.get("inspired_by_pattern",""))
    # beats fit duration
    last = p["beats"][-1]["t"]
    m = re.search(r"-(\d+(?:\.\d+)?)s", last)
    if m and float(m.group(1)) > p["duration_s"]:
        errs.append(f"{pid}: beats exceed duration")

# counts
print("=== counts per group ===")
for gid, d in per_group.items():
    ni, nv = len(d.get("img",[])), len(d.get("vid",[]))
    ok_i = ni == settings["image_prompts_per_ad_group"]
    ok_v = nv == settings["video_prompts_per_ad_group"]
    ci = set(d.get("concepts",[])); cv = set(d.get("vconcepts",[]))
    print(f"  {gid}: images={ni}({'OK' if ok_i else 'BAD'}) concepts={ci} | videos={nv}({'OK' if ok_v else 'BAD'}) concepts={cv}")
    if not ({'proven','differentiator'} <= (ci|cv)):
        errs.append(f"{gid}: missing proven or differentiator concept")

print(f"\nforbidden terms scanned: {len(forbidden)}")
print("\n=== ERRORS ===")
print("\n".join(errs) if errs else "none")
print("\n=== WARNINGS ===")
print("\n".join(warns) if warns else "none")
