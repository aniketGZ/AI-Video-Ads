"""
Plan checks for API routes.

Until user accounts exist, every request gets the plan named by the APP_PLAN environment
variable (default "studio", so nothing changes for current use). Set APP_PLAN=starter to see
what a Starter user sees. When accounts land, current_plan() reads the signed-in user's plan
instead and nothing else here changes.
"""

import os

from fastapi import Depends, HTTPException, Request

from pricing import FEATURES, PLANS, plan_has, plans_with

DEFAULT_PLAN = "studio"


def current_plan(request: Request) -> str:
    plan = (os.environ.get("APP_PLAN") or DEFAULT_PLAN).strip().lower()
    return plan if plan in PLANS else DEFAULT_PLAN


def require_feature(feature: str):
    """Route dependency: 403 with an upgrade message when the plan lacks `feature`."""
    label = FEATURES[feature]
    allowed = plans_with(feature)
    names = " and ".join(PLANS[p]["label"] for p in allowed)

    def check(plan: str = Depends(current_plan)) -> str:
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
    return {"plan": plan, "label": p["label"], "features": list(p.get("features", []))}
