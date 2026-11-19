"""
The campaign builder's upgrade page, the plan list it shows, and the hand-off to checkout.

Checkout is not built yet. Until it is, set UPGRADE_URL_PRO and UPGRADE_URL_STUDIO to payment
links (a Stripe Payment Link works) and /upgrade/checkout sends people there. With no link set,
it shows a short "opening soon" page instead of a dead end.
"""

import os
from html import escape

from fastapi import APIRouter
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse

from pricing import PLANS

router = APIRouter(tags=["Upgrade"])

CHECKOUT_ENV = {"pro": "UPGRADE_URL_PRO", "studio": "UPGRADE_URL_STUDIO"}


@router.get("/upgrade/campaign", include_in_schema=False)
async def campaign_upgrade_page():
    return FileResponse("static/upgrade/campaign.html", headers={"Cache-Control": "no-cache"})


@router.get("/api/plans")
async def list_plans():
    """Public plan list for pricing displays (prices, credits, gated features)."""
    return {
        "plans": {
            key: {
                "label": p["label"],
                "price_usd_month": p["price_usd_month"],
                "credits": p["credits"],
                "renews": p["renews"],
                "features": list(p.get("features", [])),
            }
            for key, p in PLANS.items()
        }
    }


@router.get("/upgrade/checkout", include_in_schema=False)
async def upgrade_checkout(plan: str = "pro"):
    plan = plan if plan in CHECKOUT_ENV else "pro"
    url = (os.environ.get(CHECKOUT_ENV[plan]) or "").strip()
    if url.startswith("https://"):
        return RedirectResponse(url, status_code=303)
    label = escape(PLANS[plan]["label"])
    return HTMLResponse(
        status_code=503,
        content=f"""<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0"><title>Upgrades open soon · Ad Studio</title>
<style>body{{margin:0;min-height:100svh;display:grid;place-items:center;background:#000;color:#fff;font:400 18px/1.5 Inter,system-ui,sans-serif;padding:24px}}
main{{max-width:520px}}h1{{font-size:40px;letter-spacing:-.03em;line-height:1.05;margin:0 0 16px}}a{{color:#ff6b1f}}</style></head>
<body><main><h1>{label} upgrades open soon</h1>
<p>Paid plans aren't taking sign-ups yet. Your link is saved in this browser and will be waiting in the Campaign tab.</p>
<p><a href="/upgrade/campaign">Back to the campaign builder</a> · <a href="/">Back to the studio</a></p></main></body></html>""",
    )
