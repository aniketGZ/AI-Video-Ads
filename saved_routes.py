"""
API routes for saving user generations, collecting images, and saving prompts.
"""

from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from access import current_user
import database

router = APIRouter(prefix="/api/saved", tags=["Saved Creatives"])


class SaveCreativePayload(BaseModel):
    type: str  # 'image' | 'video'
    title: str
    prompt: str
    media_url: str
    aspect_ratio: Optional[str] = "9:16"
    model_params: Optional[Dict[str, Any]] = None
    tags: Optional[List[str]] = None
    is_favorite: Optional[bool] = False


class FavoritePayload(BaseModel):
    id: str
    is_favorite: bool


@router.post("/create")
async def create_saved_item(payload: SaveCreativePayload, user: Optional[Dict[str, Any]] = Depends(current_user)):
    """Save an ad creative, prompt, and media item to the user's collection."""
    record = await database.save_creative(user, payload.model_dump())
    return {"status": "ok", "creative": record}


@router.get("/list")
async def get_saved_items(
    type: Optional[str] = None,
    favorites: Optional[bool] = False,
    user: Optional[Dict[str, Any]] = Depends(current_user),
):
    """Retrieve saved creatives and prompts for the user."""
    items = await database.list_saved_creatives(user, media_type=type, only_favorites=bool(favorites))
    return {"status": "ok", "creatives": items, "count": len(items)}


@router.post("/favorite")
async def set_favorite(payload: FavoritePayload, user: Optional[Dict[str, Any]] = Depends(current_user)):
    """Toggle favorite on a saved creative."""
    success = await database.toggle_favorite(payload.id, payload.is_favorite)
    return {"status": "ok" if success else "error"}


@router.delete("/{cid}")
async def remove_saved_item(cid: str, user: Optional[Dict[str, Any]] = Depends(current_user)):
    """Delete a saved creative from the user's collection."""
    success = await database.delete_creative(cid)
    return {"status": "ok" if success else "error"}
