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
    return HTMLResponse(
        status_code=200,
        content=f"""<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0"><title>{label} Plan · Ad Studio</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>
body {{
  margin: 0; min-height: 100vh; display: grid; place-items: center;
  background: #0c0807; color: #ffffff;
  font: 400 16px/1.6 'Inter', system-ui, sans-serif; padding: 24px;
  position: relative; overflow: hidden;
}}
.glow {{
  position: absolute; border-radius: 50%; filter: blur(120px); opacity: 0.16; pointer-events: none;
}}
.glow-1 {{ width: 500px; height: 500px; background: #ff6b1f; top: -100px; left: 20%; }}
.glow-2 {{ width: 450px; height: 450px; background: #9333ea; bottom: -50px; right: 20%; }}
.card {{
  position: relative; z-index: 10; max-width: 520px; width: 100%;
  background: linear-gradient(150deg, rgba(255,255,255,0.08) 0%, rgba(255,255,255,0.02) 100%), rgba(20,14,12,0.85);
  border: 1px solid rgba(255,255,255,0.12); border-radius: 20px;
  padding: 44px 36px; text-align: center;
  box-shadow: 0 24px 60px rgba(0,0,0,0.5), inset 0 1px 0 rgba(255,255,255,0.15);
  backdrop-filter: blur(24px);
}}
.logo {{ width: 40px; height: 40px; margin: 0 auto 20px; color: #ff6b1f; display: block; }}
h1 {{ font-size: 30px; font-weight: 700; letter-spacing: -0.03em; margin: 0 0 12px; line-height: 1.15; }}
p {{ color: rgba(255,255,255,0.72); margin: 0 0 28px; font-size: 15px; }}
.badge {{
  display: inline-block; padding: 4px 14px; border-radius: 999px;
  background: rgba(255,107,31,0.16); color: #ffa36b;
  font-size: 12px; font-weight: 600; text-transform: uppercase; margin-bottom: 16px;
}}
.actions {{ display: flex; gap: 12px; justify-content: center; flex-wrap: wrap; }}
.btn {{
  display: inline-flex; align-items: center; justify-content: center;
  height: 42px; padding: 0 22px; border-radius: 999px;
  font-size: 14px; font-weight: 600; text-decoration: none; transition: all 150ms ease;
}}
.btn-primary {{ background: #ff6b1f; color: #000; border: 1px solid #ff6b1f; }}
.btn-primary:hover {{ background: #ff8547; }}
.btn-ghost {{ background: rgba(255,255,255,0.06); color: #fff; border: 1px solid rgba(255,255,255,0.12); }}
.btn-ghost:hover {{ background: rgba(255,255,255,0.12); }}
</style></head>
<body>
<div class="glow glow-1"></div>
<div class="glow glow-2"></div>
<div class="card">
  <svg class="logo" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
    <circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="1.6" stroke-opacity="0.35"/>
    <circle cx="12" cy="12" r="3.2" fill="currentColor"/>
    <path d="M12 2C15.5 5.5 16.5 8.5 15.2 12M22 12C18.5 15.5 15.5 16.5 12 15.2M12 22C8.5 18.5 7.5 15.5 8.8 12M2 12C5.5 8.5 8.5 7.5 12 8.8" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/>
    <circle cx="12" cy="12" r="1.2" fill="#fff"/>
  </svg>
  <div class="badge">{label} Plan Checkout</div>
  <h1>Early Access En Route</h1>
  <p>Paid checkouts are currently opening on invite. You have full free studio credits waiting to build your next high-converting ad set.</p>
  <div class="actions">
    <a href="/app" class="btn btn-primary">Open Free Studio</a>
    <a href="/pricing" class="btn btn-ghost">Back to Pricing</a>
  </div>
</div>
</body></html>""",
    )
