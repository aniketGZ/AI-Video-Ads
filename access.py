"""
Plan checks and user authentication dependencies for API routes.

Reads the signed-in user's plan from Supabase Auth. Unauthenticated callers receive the
plan set by APP_PLAN (default "free" when Supabase is configured, or "studio" when in local
development mode with no auth).
"""

import os
from typing import Any, Dict, Optional

from fastapi import Depends, HTTPException, Request

from pricing import FEATURES, PLANS, plan_has, plans_with

DEFAULT_PLAN = "studio"


async def current_user(request: Request) -> Optional[Dict[str, Any]]:
    """FastAPI dependency to get the current authenticated Supabase user, or None."""
    from auth import get_current_user
    return await get_current_user(request)


async def current_plan(request: Request) -> str:
    """Resolve the active plan: authenticated user plan -> APP_PLAN -> fallback."""
    from auth import get_current_user, is_auth_configured

    user = await get_current_user(request)
    if user:
        if user.get("is_admin") or (user.get("email") or "").strip().lower() == "aniket@growthz.ai":
            return "enterprise"
        if user.get("plan"):
            plan = user["plan"].strip().lower()
            if plan in PLANS:
                return plan

    env_plan = (os.environ.get("APP_PLAN") or "").strip().lower()
    if env_plan in PLANS:
        return env_plan

    # If Supabase Auth is enabled, default guest requests to 'free' plan;
    # otherwise default to 'studio' for seamless local dev.
    return "free" if is_auth_configured() else DEFAULT_PLAN


def require_feature(feature: str):
    """Route dependency: 403 with an upgrade message when the plan lacks `feature`."""
    label = FEATURES[feature]
    allowed = plans_with(feature)
    names = " and ".join(PLANS[p]["label"] for p in allowed)

    async def check(plan: str = Depends(current_plan)) -> str:
        if not plan_has(plan, feature):
            raise HTTPException(
                status_code=403,
                detail=f"{label} is included in the {names} plans. Upgrade to use it.",
                headers={"X-Upgrade-Required": feature},
            )
        return plan

    return check


def plan_summary(plan: str) -> dict:
    p = PLANS[plan]
    return {
        "plan": plan,
        "label": p["label"],
        "credits": p.get("credits", 0),
        "features": list(p.get("features", [])),
    }
