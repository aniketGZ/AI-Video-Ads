"""
The campaign builder's upgrade page, the plan list it shows, and the hand-off to checkout.

Checkout is not built yet. Until it is, set UPGRADE_URL_STARTER, UPGRADE_URL_PRO and
UPGRADE_URL_STUDIO to payment links (a Stripe Payment Link works), and optionally the same names
ending in _ANNUAL for yearly billing; /upgrade/checkout sends people there. With no link set, it
shows a short "opening soon" page instead of a dead end.
"""

import os
from html import escape

from fastapi import APIRouter
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse

from pricing import (
    IMAGE_CREDITS, PLANS, TEXT_ACTION_CREDITS, TOP_UPS, VIDEO_CREDITS_PER_SECOND, YEARLY_DISCOUNT,
)

router = APIRouter(tags=["Upgrade"])

CHECKOUT_ENV = {"starter": "UPGRADE_URL_STARTER", "pro": "UPGRADE_URL_PRO", "studio": "UPGRADE_URL_STUDIO"}


@router.get("/upgrade/campaign", include_in_schema=False)
async def campaign_upgrade_page():
    return FileResponse("static/upgrade/campaign.html", headers={"Cache-Control": "no-cache"})


@router.get("/pricing", include_in_schema=False)
async def pricing_page():
    return FileResponse("static/pricing/pricing.html", headers={"Cache-Control": "no-cache"})


@router.get("/api/plans")
async def list_plans():
    """Public plan list for pricing displays: prices, credits, limits, gated features, what each
    action costs in credits, top-ups and the yearly discount. Everything comes from pricing.py."""
    return {
        "plans": {
            key: {
                "label": p["label"],
                "price_usd_month": p["price_usd_month"],
                "credits": p["credits"],
                "renews": p["renews"],
                "features": list(p.get("features", [])),
                "limits": dict(p.get("limits", {})),
            }
            for key, p in PLANS.items()
        },
        "costs": {
            "image": IMAGE_CREDITS,
            "video_per_second": VIDEO_CREDITS_PER_SECOND,
            "text": TEXT_ACTION_CREDITS,
        },
        "top_ups": TOP_UPS,
        "yearly_discount": YEARLY_DISCOUNT,
    }


@router.get("/upgrade/checkout", include_in_schema=False)
async def upgrade_checkout(plan: str = "pro", billing: str = "monthly"):
    plan = plan if plan in CHECKOUT_ENV else "pro"
    env = CHECKOUT_ENV[plan]
    url = ""
    if billing == "annual":
        url = (os.environ.get(env + "_ANNUAL") or "").strip()
    url = url or (os.environ.get(env) or "").strip()
    if url.startswith("https://"):
        return RedirectResponse(url, status_code=303)
    label = escape(PLANS[plan]["label"])
    price = PLANS[plan]["price_usd_month"]
    credits = f'{PLANS[plan]["credits"]:,}'
    # Same design system as every other page: system.css + site.css, one board of tiles.
    return HTMLResponse(
        status_code=200,
        content=f"""<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0"><title>{label} plan · Ad Studio</title>
<link rel="icon" href="/static/brand/favicon.svg" type="image/svg+xml">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Stack+Sans+Headline:wght@300&family=Stack+Sans+Text:wght@400;500&display=swap" rel="stylesheet">
<link rel="stylesheet" href="/static/css/system.css?v=2.0.0">
<link rel="stylesheet" href="/static/css/site.css?v=3.0.0">
<style>
.checkout {{ min-height: calc(100svh - var(--bar) - 8px); grid-template-rows: 1fr; }}
.checkout .title-main {{ grid-column: 1 / 8; }}
.checkout .title-main h1 {{ font-size: clamp(3rem, 1.5rem + 5vw, 6.5rem); }}
.checkout .side {{ grid-column: 8 / 13; display: flex; flex-direction: column; justify-content: space-between; gap: 24px; padding: 32px; }}
.checkout .side p {{ margin: 0; }}
.checkout .plan {{ font-family: var(--font-display); font-weight: 300; font-size: var(--step-head); line-height: 1; letter-spacing: -0.022em; }}
.checkout .actions {{ display: flex; flex-wrap: wrap; gap: 8px; }}
@media (max-width: 760px) {{ .checkout .title-main, .checkout .side {{ grid-column: 1 / -1; }} }}
</style></head>
<body class="site">
<header class="bar">
  <a href="/" class="logo" aria-label="Ad Studio home"><svg class="logo-mark" viewBox="0 0 24 24" aria-hidden="true"><path class="f-video" fill-rule="evenodd" d="M3.75 1.5h6.75a2.25 2.25 0 0 1 2.25 2.25v16.5a2.25 2.25 0 0 1-2.25 2.25H3.75A2.25 2.25 0 0 1 1.5 20.25V3.75A2.25 2.25 0 0 1 3.75 1.5ZM5.4 8.7v6.6l5.2-3.3Z"/><rect class="f-image" x="14.5" y="12.5" width="8" height="10" rx="2"/></svg><span>Ad Studio</span></a>
  <nav class="bar-links" aria-label="Main"><a href="/pricing">Pricing</a></nav>
  <div class="bar-actions"><a href="/app" class="btn btn-primary">Open the studio</a></div>
</header>
<main class="board page-title checkout">
  <div class="tile title-main">
    <h1 class="t-display">Checkout opens by invite</h1>
    <p>Paid plans are opening a few accounts at a time while billing is finished. Your free credits work in every studio today.</p>
  </div>
  <div class="tile tile-red side">
    <div><p class="plan">{label}</p><p>${price} a month, {credits} credits</p></div>
    <div class="actions">
      <a href="/app" class="btn btn-primary">Open the studio</a>
      <a href="/pricing" class="btn">Back to pricing</a>
    </div>
  </div>
</main>
</body></html>""",
    )
