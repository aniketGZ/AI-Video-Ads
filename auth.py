"""
Supabase Authentication helper and API routes.

Provides user verification, token caching, plan extraction from user_metadata,
and frontend auth configuration.
"""

import os
import time
from typing import Any, Dict, Optional

import httpx
from fastapi import APIRouter, Header, HTTPException, Request
from pydantic import BaseModel

from pricing import PLANS

SUPABASE_URL = (os.environ.get("SUPABASE_URL") or "").rstrip("/")
SUPABASE_ANON_KEY = os.environ.get("SUPABASE_ANON_KEY") or ""
SUPABASE_SERVICE_ROLE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or ""

# In-memory TTL cache for verified tokens to keep latency near 0ms for active users
_USER_CACHE: Dict[str, tuple[float, Dict[str, Any]]] = {}
CACHE_TTL_SECONDS = 60.0

router = APIRouter(prefix="/api/auth", tags=["Auth"])


def is_auth_configured() -> bool:
    """Return True if Supabase URL and anon key are present."""
    return bool(SUPABASE_URL and SUPABASE_ANON_KEY)


def _clean_token_cache() -> None:
    now = time.time()
    expired = [t for t, (exp, _) in _USER_CACHE.items() if exp <= now]
    for t in expired:
        _USER_CACHE.pop(t, None)


async def verify_supabase_token(token: str) -> Optional[Dict[str, Any]]:
    """Validate a JWT token against Supabase Auth API, returning user details or None."""
    if not is_auth_configured() or not token:
        return None

    now = time.time()
    cached = _USER_CACHE.get(token)
    if cached and cached[0] > now:
        return cached[1]

    _clean_token_cache()

    url = f"{SUPABASE_URL}/auth/v1/user"
    headers = {
        "apikey": SUPABASE_ANON_KEY,
        "Authorization": f"Bearer {token}",
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            res = await client.get(url, headers=headers)
            if res.status_code == 200:
                data = res.json()
                metadata = data.get("user_metadata") or {}
                user_info = {
                    "id": data.get("id"),
                    "email": data.get("email"),
                    "role": data.get("role", "authenticated"),
                    "plan": (metadata.get("plan") or "free").strip().lower(),
                    "user_metadata": metadata,
                    "created_at": data.get("created_at"),
                }
                if user_info["plan"] not in PLANS:
                    user_info["plan"] = "free"
                _USER_CACHE[token] = (now + CACHE_TTL_SECONDS, user_info)
                return user_info
    except Exception:
        pass

    return None


async def get_current_user(request: Request) -> Optional[Dict[str, Any]]:
    """Extract and verify user from Authorization header or cookie."""
    auth_header = request.headers.get("Authorization") or ""
    token = None
    if auth_header.startswith("Bearer "):
        token = auth_header[7:].strip()
    elif "sb-access-token" in request.cookies:
        token = request.cookies.get("sb-access-token")

    if not token:
        return None

    return await verify_supabase_token(token)


@router.get("/config")
async def get_auth_config():
    """Public Supabase endpoint & anon key for client-side Supabase JS SDK."""
    return {
        "supabase_url": SUPABASE_URL,
        "supabase_anon_key": SUPABASE_ANON_KEY,
        "enabled": is_auth_configured(),
    }


@router.get("/me")
async def get_current_user_profile(request: Request):
    """Return profile and active plan for the current session."""
    user = await get_current_user(request)
    if not user:
        return {
            "authenticated": False,
            "user": None,
            "plan": (os.environ.get("APP_PLAN") or ("free" if is_auth_configured() else "studio")).strip().lower(),
        }
    return {
        "authenticated": True,
        "user": user,
        "plan": user["plan"],
    }


class UpdatePlanPayload(BaseModel):
    plan: str


@router.post("/update-plan")
async def update_user_plan(payload: UpdatePlanPayload, request: Request):
    """Update a user's plan in Supabase user metadata."""
    if payload.plan not in PLANS:
        raise HTTPException(status_code=400, detail=f"Invalid plan. Must be one of: {list(PLANS.keys())}")

    user = await get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Sign in required to update plan")

    if not SUPABASE_SERVICE_ROLE_KEY:
        # Fallback local update if service role key is not configured
        user["plan"] = payload.plan
        return {"status": "ok", "plan": payload.plan, "note": "Updated in-session"}

    # Use Supabase Admin API to update user metadata
    url = f"{SUPABASE_URL}/auth/v1/admin/users/{user['id']}"
    headers = {
        "apikey": SUPABASE_SERVICE_ROLE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
        "Content-Type": "application/json",
    }
    updated_metadata = dict(user.get("user_metadata", {}))
    updated_metadata["plan"] = payload.plan

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            res = await client.put(url, headers=headers, json={"user_metadata": updated_metadata})
            if res.status_code == 200:
                # Invalidate user cache
                _clean_token_cache()
                return {"status": "ok", "plan": payload.plan}
            else:
                raise HTTPException(status_code=res.status_code, detail="Failed to update plan in Supabase")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
