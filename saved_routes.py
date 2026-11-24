"""
API routes for saving user generations, organizing projects/folders, and user profile stats.
"""

from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from access import current_user, current_plan
from pricing import PLANS
import database

router = APIRouter(tags=["Saved Creatives & Projects"])


# ===========================================================================
# Pydantic Request Schemas
# ===========================================================================

class SaveCreativePayload(BaseModel):
    type: str  # 'image' | 'video'
    title: str
    prompt: str
    media_url: str
    aspect_ratio: Optional[str] = "9:16"
    model_params: Optional[Dict[str, Any]] = None
    tags: Optional[List[str]] = None
    reference_images: Optional[List[str]] = None
    folder_id: Optional[str] = None
    is_favorite: Optional[bool] = False


class FavoritePayload(BaseModel):
    id: str
    is_favorite: bool


class MoveCreativePayload(BaseModel):
    folder_id: Optional[str] = None


class ProjectPayload(BaseModel):
    name: str
    description: Optional[str] = ""
    color: Optional[str] = "#8d3624"
    icon: Optional[str] = "folder"


class UpdateProfilePayload(BaseModel):
    name: Optional[str] = None


# ===========================================================================
# Project / Folder Endpoints
# ===========================================================================

@router.get("/api/projects")
async def get_projects(user: Optional[Dict[str, Any]] = Depends(current_user)):
    """List all projects/folders for current user."""
    projects = await database.list_projects(user)
    return {"status": "ok", "projects": projects, "count": len(projects)}


@router.post("/api/projects")
async def create_new_project(payload: ProjectPayload, user: Optional[Dict[str, Any]] = Depends(current_user)):
    """Create a new project folder."""
    if not payload.name.strip():
        raise HTTPException(status_code=400, detail="Project name is required")
    record = await database.create_project(user, payload.model_dump())
    return {"status": "ok", "project": record}


@router.patch("/api/projects/{project_id}")
async def update_existing_project(
    project_id: str,
    payload: ProjectPayload,
    user: Optional[Dict[str, Any]] = Depends(current_user),
):
    """Update project name, description, color, or icon."""
    updated = await database.update_project(user, project_id, payload.model_dump())
    if not updated:
        raise HTTPException(status_code=404, detail="Project not found")
    return {"status": "ok", "project": updated}


@router.delete("/api/projects/{project_id}")
async def remove_project(project_id: str, user: Optional[Dict[str, Any]] = Depends(current_user)):
    """Delete a project folder and unassign its items."""
    success = await database.delete_project(user, project_id)
    return {"status": "ok" if success else "error"}


# ===========================================================================
# Saved Creatives Endpoints
# ===========================================================================

@router.post("/api/saved/create")
async def create_saved_item(payload: SaveCreativePayload, user: Optional[Dict[str, Any]] = Depends(current_user)):
    """Save an ad creative, prompt, uploaded references, and folder metadata."""
    record = await database.save_creative(user, payload.model_dump())
    return {"status": "ok", "creative": record}


@router.get("/api/saved/list")
async def get_saved_items(
    type: Optional[str] = None,
    favorites: Optional[bool] = False,
    folder_id: Optional[str] = None,
    q: Optional[str] = None,
    user: Optional[Dict[str, Any]] = Depends(current_user),
):
    """Retrieve saved creatives and prompts filtered by type, folder, favorites, or search query."""
    items = await database.list_saved_creatives(
        user,
        media_type=type,
        only_favorites=bool(favorites),
        folder_id=folder_id,
        search=q,
    )
    return {"status": "ok", "creatives": items, "count": len(items)}


@router.post("/api/saved/{cid}/move")
async def move_creative_folder(
    cid: str,
    payload: MoveCreativePayload,
    user: Optional[Dict[str, Any]] = Depends(current_user),
):
    """Move a creative into a project folder or unassign it."""
    success = await database.move_creative_to_project(user, cid, payload.folder_id)
    return {"status": "ok" if success else "error"}


@router.post("/api/saved/favorite")
async def set_favorite(payload: FavoritePayload, user: Optional[Dict[str, Any]] = Depends(current_user)):
    """Toggle favorite on a saved creative."""
    success = await database.toggle_favorite(user, payload.id, payload.is_favorite)
    return {"status": "ok" if success else "error"}


@router.delete("/api/saved/{cid}")
async def remove_saved_item(cid: str, user: Optional[Dict[str, Any]] = Depends(current_user)):
    """Delete a saved creative from the user's collection."""
    success = await database.delete_creative(user, cid)
    return {"status": "ok" if success else "error"}


# ===========================================================================
# User Profile & Stats Endpoints
# ===========================================================================

@router.get("/api/user/profile")
async def get_user_profile_data(
    user: Optional[Dict[str, Any]] = Depends(current_user),
    plan: str = Depends(current_plan),
):
    """Get complete user profile, membership tier, usage stats, and credits."""
    stats = await database.get_user_stats(user)
    plan_info = PLANS.get(plan, PLANS["free"])
    
    # Calculate credits based on plan
    plan_credits = {
        "free": 500,
        "starter": 3000,
        "pro": 10000,
        "studio": 20000,
        "enterprise": 100000,
    }.get(plan, 100000 if plan == "enterprise" else 500)

    is_admin_or_top = bool(
        plan == "enterprise"
        or (user and ((user.get("email") or "").strip().lower() == "aniket@growthz.ai" or user.get("is_admin")))
    )

    if is_admin_or_top:
        plan_credits = 100000
        used_credits = (stats["total_images"] * 10) + (stats["total_videos"] * 50)
        remaining_credits = max(100000 - used_credits, 99000)
    else:
        # Estimate used credits based on generations (images = 10, videos = 50)
        used_credits = min(plan_credits, (stats["total_images"] * 10) + (stats["total_videos"] * 50))
        remaining_credits = max(0, plan_credits - used_credits)

    user_data = {
        "id": user.get("id") if user else None,
        "email": user.get("email") if user else "Guest Creator",
        "name": (user.get("user_metadata") or {}).get("name") if user else "Guest Creator",
        "plan": plan,
        "plan_label": "Enterprise (Max Access)" if is_admin_or_top else plan_info.get("label", plan.title()),
        "is_authenticated": bool(user),
        "is_admin": is_admin_or_top,
        "created_at": user.get("created_at") if user else None,
    }

    return {
        "status": "ok",
        "user": user_data,
        "stats": stats,
        "credits": {
            "total": plan_credits,
            "used": used_credits,
            "remaining": remaining_credits,
        },
    }
