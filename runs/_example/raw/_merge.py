import json, sys, glob, os
from datetime import date

comp = sys.argv[1]
page_meta = json.loads(sys.argv[2]) if len(sys.argv) > 2 else {}
d = os.path.join(os.path.dirname(__file__), comp)
cards = {}
for fp in sorted(glob.glob(os.path.join(d, "_batch*.json"))):
    data = json.load(open(fp, encoding="utf-8"))
    for c in data.get("cards", []):
        lid = c["library_id"]
        # keep the richest record (more image/video urls / details)
        if lid not in cards or len(json.dumps(c)) > len(json.dumps(cards[lid])):
            cards[lid] = c
cards = list(cards.values())
out = {"competitor": comp, "page_meta": page_meta, "captured_on": str(date.today()),
       "total_cards": len(cards), "cards": cards}
json.dump(out, open(os.path.join(d, "ads.json"), "w", encoding="utf-8"), indent=2, ensure_ascii=False)
# quick stats
from collections import Counter
fmt = Counter(c["format"] for c in cards)
pages = Counter(c["page_name"] for c in cards)
print("total:", len(cards), "| formats:", dict(fmt))
print("pages:", dict(pages))
