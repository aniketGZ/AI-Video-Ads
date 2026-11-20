"""
Database storage for Ad Studio user saved creatives and prompt history.

Synchronizes with Supabase PostgreSQL (saved_creatives table) and maintains
a local persistent SQLite store for offline development and fast caching.
"""

import os
import sqlite3
import json
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import httpx

SUPABASE_URL = (os.environ.get("SUPABASE_URL") or "").rstrip("/")
SUPABASE_SERVICE_ROLE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or os.environ.get("SUPABASE_ANON_KEY") or ""

DB_PATH = os.path.join("data", "ad_studio.db")


def init_db():
    """Initialize local SQLite database table if not exists."""
    os.makedirs("data", exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS saved_creatives (
                id TEXT PRIMARY KEY,
                user_id TEXT,
                user_email TEXT,
                type TEXT NOT NULL,
                title TEXT NOT NULL,
                prompt TEXT NOT NULL,
                media_url TEXT NOT NULL,
                aspect_ratio TEXT DEFAULT '9:16',
                model_params TEXT,
                tags TEXT,
                is_favorite INTEGER DEFAULT 0,
                created_at TEXT NOT NULL
            )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_user ON saved_creatives(user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_created ON saved_creatives(created_at DESC)")
        conn.commit()


# Initialize database on module load
init_db()


def _is_supabase_ready() -> bool:
    return bool(SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY)


async def save_creative(user: Optional[Dict[str, Any]], data: Dict[str, Any]) -> Dict[str, Any]:
    """Save an image or video generation with prompt and metadata."""
    init_db()
    cid = str(uuid.uuid4())
    user_id = (user.get("id") or "") if user else ""
    user_email = (user.get("email") or "Guest Creator") if user else "Guest Creator"
    now_iso = datetime.now(timezone.utc).isoformat()

    c_type = data.get("type", "image")
    title = data.get("title") or ("Video Ad" if c_type == "video" else "Image Ad")
    prompt = data.get("prompt", "")
    media_url = data.get("media_url", "")
    aspect_ratio = data.get("aspect_ratio", "9:16" if c_type == "video" else "4:5")
    model_params = data.get("model_params") or {}
    tags = data.get("tags") or []
    is_fav = 1 if data.get("is_favorite") else 0

    # 1. Save to local SQLite
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO saved_creatives 
            (id, user_id, user_email, type, title, prompt, media_url, aspect_ratio, model_params, tags, is_favorite, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            cid,
            user_id,
            user_email,
            c_type,
            title,
            prompt,
            media_url,
            aspect_ratio,
            json.dumps(model_params),
            json.dumps(tags),
            is_fav,
            now_iso
        ))
        conn.commit()

    record = {
        "id": cid,
        "user_id": user_id,
        "user_email": user_email,
        "type": c_type,
        "title": title,
        "prompt": prompt,
        "media_url": media_url,
        "aspect_ratio": aspect_ratio,
        "model_params": model_params,
        "tags": tags,
        "is_favorite": bool(is_fav),
        "created_at": now_iso
    }

    # 2. Sync to Supabase if configured
    if _is_supabase_ready():
        try:
            url = f"{SUPABASE_URL}/rest/v1/saved_creatives"
            headers = {
                "apikey": SUPABASE_SERVICE_ROLE_KEY,
                "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
                "Content-Type": "application/json",
                "Prefer": "return=minimal"
            }
            supabase_payload = dict(record)
            if not user_id:
                supabase_payload.pop("user_id", None)
            async with httpx.AsyncClient(timeout=8.0) as client:
                await client.post(url, headers=headers, json=supabase_payload)
        except Exception:
            pass  # Resilient fallback: local copy is already saved

    return record


async def list_saved_creatives(user: Optional[Dict[str, Any]], media_type: Optional[str] = None, only_favorites: bool = False) -> List[Dict[str, Any]]:
    """List saved creatives for the current user or session."""
    init_db()
    user_id = (user.get("id") or "") if user else ""

    # If Supabase is available and user is authenticated, query Supabase
    if _is_supabase_ready() and user_id:
        try:
            url = f"{SUPABASE_URL}/rest/v1/saved_creatives"
            params = {
                "user_id": f"eq.{user_id}",
                "order": "created_at.desc",
                "select": "*"
            }
            if media_type:
                params["type"] = f"eq.{media_type}"
            if only_favorites:
                params["is_favorite"] = "eq.true"
            headers = {
                "apikey": SUPABASE_SERVICE_ROLE_KEY,
                "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}"
            }
            async with httpx.AsyncClient(timeout=8.0) as client:
                res = await client.get(url, headers=headers, params=params)
                if res.status_code == 200:
                    return res.json()
        except Exception:
            pass

    # Query local SQLite
    query = "SELECT id, user_id, user_email, type, title, prompt, media_url, aspect_ratio, model_params, tags, is_favorite, created_at FROM saved_creatives WHERE 1=1"
    params = []

    if user_id:
        query += " AND (user_id = ? OR user_id = '')"
        params.append(user_id)
    if media_type:
        query += " AND type = ?"
        params.append(media_type)
    if only_favorites:
        query += " AND is_favorite = 1"

    query += " ORDER BY created_at DESC LIMIT 100"

    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(query, params)
        rows = cursor.fetchall()
        results = []
        for r in rows:
            m_params = {}
            t_list = []
            try:
                m_params = json.loads(r["model_params"]) if r["model_params"] else {}
            except Exception:
                pass
            try:
                t_list = json.loads(r["tags"]) if r["tags"] else []
            except Exception:
                pass

            results.append({
                "id": r["id"],
                "user_id": r["user_id"],
                "user_email": r["user_email"],
                "type": r["type"],
                "title": r["title"],
                "prompt": r["prompt"],
                "media_url": r["media_url"],
                "aspect_ratio": r["aspect_ratio"],
                "model_params": m_params,
                "tags": t_list,
                "is_favorite": bool(r["is_favorite"]),
                "created_at": r["created_at"]
            })
        return results


async def toggle_favorite(cid: str, is_fav: bool) -> bool:
    """Toggle favorite status of a creative."""
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE saved_creatives SET is_favorite = ? WHERE id = ?", (1 if is_fav else 0, cid))
        conn.commit()

    if _is_supabase_ready():
        try:
            url = f"{SUPABASE_URL}/rest/v1/saved_creatives?id=eq.{cid}"
            headers = {
                "apikey": SUPABASE_SERVICE_ROLE_KEY,
                "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
                "Content-Type": "application/json"
            }
            async with httpx.AsyncClient(timeout=5.0) as client:
                await client.patch(url, headers=headers, json={"is_favorite": is_fav})
        except Exception:
            pass

    return True


async def delete_creative(cid: str) -> bool:
    """Delete a saved creative."""
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM saved_creatives WHERE id = ?", (cid,))
        conn.commit()

    if _is_supabase_ready():
        try:
            url = f"{SUPABASE_URL}/rest/v1/saved_creatives?id=eq.{cid}"
            headers = {
                "apikey": SUPABASE_SERVICE_ROLE_KEY,
                "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}"
            }
            async with httpx.AsyncClient(timeout=5.0) as client:
                await client.delete(url, headers=headers)
        except Exception:
            pass

    return True
