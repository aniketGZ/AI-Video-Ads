"""
Credit prices and plans for AI Ad Studio. This file is the only place prices live.

1 credit is roughly $0.01 at the top-up price. Each action costs about 4x what it costs us
in Gemini (standard paid tier, from ai.google.dev pricing, checked 2026-11-19), so even the
cheapest credits on the Studio plan keep about a 3x markup.

Gemini costs behind each number:
  Nano Banana 2.1 (gemini-nano-banana-2.1):  1K $0.0336, 2K $0.0504, 4K $0.113 per image
  Nano Banana Pro (gemini-3-pro-image):      1K/2K $0.134, 4K $0.24 per image
  Omni 1.2 Flash video (gemini-omni-1.2-flash): 720p ~$0.07/s, 1080p $0.104/s, 4K $0.209/s
  gemini-3.6-flash text: $1.50 in / $7.50 out per 1M tokens from 2027-01-01 (half that until then),
                         Google Search grounding $14 per 1,000 after 5,000 free a month
Text steps are estimates (few traces logged so far). Check them against real usage once
token counts are recorded per generation.

Nothing calls this yet. The credit check (hold -> confirm -> refund on failure) will use it.
"""

import math

# --- What each action costs, in credits -------------------------------------------------

IMAGE_CREDITS = {
    # model key (media_utils.IMAGE_MODELS) -> resolution -> credits per image
    "nano-banana-2.1": {"1K": 15, "2K": 25, "4K": 50},
    "nano-banana-pro": {"1K": 55, "2K": 55, "4K": 100},
}

VIDEO_CREDITS_PER_SECOND = {
    # Omni Flash resolution -> credits per second of video (videos are 4-15 s)
    "720p": 30,
    "1080p": 45,
    "4k": 85,
}

TEXT_ACTION_CREDITS = {
    "brand_analysis": 60,        # /api/campaign/analyze: 2 calls + Google Search
    "campaign_strategy": 30,     # /api/campaign/strategy
    "ad_prompt": 10,             # /api/campaign/prompts, per ad written
    "competitor_research": 300,  # competitor agent run (/start); estimate, verify on real runs
}


def image_credits(model: str, resolution: str, count: int = 1) -> int:
    table = IMAGE_CREDITS.get(model) or IMAGE_CREDITS["nano-banana-2.1"]
    per = table.get((resolution or "1K").upper(), table["1K"])
    return per * max(1, int(count))


def video_credits(resolution: str, duration_s: int) -> int:
    per_s = VIDEO_CREDITS_PER_SECOND.get((resolution or "1080p").lower(), VIDEO_CREDITS_PER_SECOND["1080p"])
    seconds = max(4, min(15, int(duration_s)))  # same clamp as /api/studio/generate-video
    return per_s * seconds


def text_credits(action: str, count: int = 1) -> int:
    return TEXT_ACTION_CREDITS[action] * max(1, int(count))


# --- Plans --------------------------------------------------------------------------------

PLANS = {
    "free": {
        "label": "Free",
        "price_usd_month": 0,
        "credits": 300,          # one-time, on sign-up; does not renew
        "renews": False,
        "features": [],
        "limits": {"image_models": ["nano-banana-2.1"], "max_image_res": "2K", "max_video_res": "720p"},
    },
    "starter": {
        "label": "Starter",
        "price_usd_month": 19,
        "credits": 2000,
        "renews": True,
        "features": [],
        "limits": {"max_video_res": "1080p"},
    },
    "pro": {
        "label": "Pro",
        "price_usd_month": 49,
        "credits": 6000,
        "renews": True,
        "features": ["campaign_manager"],
        "limits": {},
    },
    "studio": {
        "label": "Studio",
        "price_usd_month": 149,
        "credits": 20000,
        "renews": True,
        "features": ["campaign_manager"],
        "limits": {},
    },
    "enterprise": {
        "label": "Enterprise",
        "price_usd_month": 499,
        "credits": 100000,
        "renews": True,
        "features": ["campaign_manager"],
        "limits": {},
    },
}

# Features some plans leave out. Image, Video and Batch studios are open to every plan.
FEATURES = {
    # The Campaign tab: brand analysis, strategy, ad prompts, competitor research and
    # campaign image renders (/api/flow/*, /api/competitor-agent/*, /api/campaign/*).
    # Campaign videos go through /api/studio/generate-video, which stays open to all plans.
    "campaign_manager": "Campaign manager",
}


def plan_has(plan: str, feature: str) -> bool:
    return feature in (PLANS.get(plan) or {}).get("features", [])


def plans_with(feature: str) -> list:
    return [k for k, p in PLANS.items() if feature in p.get("features", [])]

TOP_UPS = [
    # Only for paying plans; priced above subscription credits so plans stay the better deal.
    {"credits": 1000, "price_usd": 12},
    {"credits": 5000, "price_usd": 55},
]

YEARLY_DISCOUNT = 0.20  # yearly billing = 12 months for the price of ~9.6


def usd_per_credit(plan: str) -> float:
    p = PLANS[plan]
    return p["price_usd_month"] / p["credits"] if p["credits"] else math.inf
