"""
Database storage for Ad Studio user saved creatives, projects/folders, and generation history.

Synchronizes with Supabase PostgreSQL (saved_creatives and projects tables) and maintains
a local persistent SQLite store for offline development, local fast caching, and resilience.
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
    """Initialize local SQLite database tables if not exist and run migrations."""
    os.makedirs("data", exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        
        # 1. saved_creatives table
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
                reference_images TEXT,
                folder_id TEXT,
                is_favorite INTEGER DEFAULT 0,
                created_at TEXT NOT NULL
            )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_user ON saved_creatives(user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_created ON saved_creatives(created_at DESC)")

        # Ensure new columns exist on older tables
        cursor.execute("PRAGMA table_info(saved_creatives)")
        cols = [r[1] for r in cursor.fetchall()]
        if "reference_images" not in cols:
            cursor.execute("ALTER TABLE saved_creatives ADD COLUMN reference_images TEXT")
        if "folder_id" not in cols:
            cursor.execute("ALTER TABLE saved_creatives ADD COLUMN folder_id TEXT")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_creative_folder ON saved_creatives(folder_id)")

        # 2. projects / folders table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS projects (
                id TEXT PRIMARY KEY,
                user_id TEXT,
                user_email TEXT,
                name TEXT NOT NULL,
                description TEXT DEFAULT '',
                color TEXT DEFAULT '#8d3624',
                icon TEXT DEFAULT 'folder',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_projects_user ON projects(user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_projects_created ON projects(created_at DESC)")

        conn.commit()


# Initialize database on module load
init_db()


def _is_supabase_ready() -> bool:
    return bool(SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY)


# ===========================================================================
# Project / Folder Management
# ===========================================================================

async def create_project(user: Optional[Dict[str, Any]], data: Dict[str, Any]) -> Dict[str, Any]:
    """Create a new project folder for organizing creatives."""
    init_db()
    pid = str(uuid.uuid4())
    user_id = (user.get("id") or "") if user else ""
    user_email = (user.get("email") or "Guest Creator") if user else "Guest Creator"
    now_iso = datetime.now(timezone.utc).isoformat()
    name = (data.get("name") or "Untitled Project").strip()
    description = (data.get("description") or "").strip()
    color = (data.get("color") or "#8d3624").strip()
    icon = (data.get("icon") or "folder").strip()

    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO projects (id, user_id, user_email, name, description, color, icon, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (pid, user_id, user_email, name, description, color, icon, now_iso, now_iso))
        conn.commit()

    record = {
        "id": pid,
        "user_id": user_id,
        "user_email": user_email,
        "name": name,
        "description": description,
        "color": color,
        "icon": icon,
        "item_count": 0,
        "created_at": now_iso,
        "updated_at": now_iso,
    }

    if _is_supabase_ready():
        try:
            url = f"{SUPABASE_URL}/rest/v1/projects"
            headers = {
                "apikey": SUPABASE_SERVICE_ROLE_KEY,
                "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
                "Content-Type": "application/json",
                "Prefer": "return=minimal",
            }
            payload = dict(record)
            payload.pop("item_count", None)
            if not user_id:
                payload.pop("user_id", None)
            async with httpx.AsyncClient(timeout=6.0) as client:
                await client.post(url, headers=headers, json=payload)
        except Exception:
            pass

    return record


async def list_projects(user: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """List all projects for user with item counts."""
    init_db()
    user_id = (user.get("id") or "") if user else ""

    query = """
        SELECT p.id, p.user_id, p.user_email, p.name, p.description, p.color, p.icon, p.created_at, p.updated_at,
               COUNT(c.id) as item_count
        FROM projects p
        LEFT JOIN saved_creatives c ON c.folder_id = p.id
    """
    params = []
    if user_id:
        query += " WHERE (p.user_id = ? OR p.user_id = '')"
        params.append(user_id)
    query += " GROUP BY p.id ORDER BY p.updated_at DESC"

    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(query, params)
        rows = cursor.fetchall()
        return [
            {
                "id": r["id"],
                "user_id": r["user_id"],
                "user_email": r["user_email"],
                "name": r["name"],
                "description": r["description"],
                "color": r["color"],
                "icon": r["icon"],
                "item_count": r["item_count"],
                "created_at": r["created_at"],
                "updated_at": r["updated_at"],
            }
            for r in rows
        ]


async def get_project(user: Optional[Dict[str, Any]], project_id: str) -> Optional[Dict[str, Any]]:
    """Fetch project details by ID."""
    init_db()
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("""
            SELECT p.*, COUNT(c.id) as item_count
            FROM projects p
            LEFT JOIN saved_creatives c ON c.folder_id = p.id
            WHERE p.id = ?
            GROUP BY p.id
        """, (project_id,))
        r = cursor.fetchone()
        if not r:
            return None
        return {
            "id": r["id"],
            "user_id": r["user_id"],
            "user_email": r["user_email"],
            "name": r["name"],
            "description": r["description"],
            "color": r["color"],
            "icon": r["icon"],
            "item_count": r["item_count"],
            "created_at": r["created_at"],
            "updated_at": r["updated_at"],
        }


async def update_project(user: Optional[Dict[str, Any]], project_id: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Update project name, description, color, or icon."""
    init_db()
    now_iso = datetime.now(timezone.utc).isoformat()
    fields = []
    params = []
    for k in ["name", "description", "color", "icon"]:
        if k in data and data[k] is not None:
            fields.append(f"{k} = ?")
            params.append(str(data[k]).strip())
    if not fields:
        return await get_project(user, project_id)
    fields.append("updated_at = ?")
    params.append(now_iso)
    params.append(project_id)

    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute(f"UPDATE projects SET {', '.join(fields)} WHERE id = ?", params)
        conn.commit()

    if _is_supabase_ready():
        try:
            url = f"{SUPABASE_URL}/rest/v1/projects?id=eq.{project_id}"
            headers = {
                "apikey": SUPABASE_SERVICE_ROLE_KEY,
                "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
                "Content-Type": "application/json",
            }
            supa_data = {k: data[k] for k in ["name", "description", "color", "icon"] if k in data}
            supa_data["updated_at"] = now_iso
            async with httpx.AsyncClient(timeout=5.0) as client:
                await client.patch(url, headers=headers, json=supa_data)
        except Exception:
            pass

    return await get_project(user, project_id)


async def delete_project(user: Optional[Dict[str, Any]], project_id: str) -> bool:
    """Delete a project and unassign its items."""
    init_db()
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE saved_creatives SET folder_id = '' WHERE folder_id = ?", (project_id,))
        cursor.execute("DELETE FROM projects WHERE id = ?", (project_id,))
        conn.commit()

    if _is_supabase_ready():
        try:
            url = f"{SUPABASE_URL}/rest/v1/projects?id=eq.{project_id}"
            headers = {
                "apikey": SUPABASE_SERVICE_ROLE_KEY,
                "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
            }
            async with httpx.AsyncClient(timeout=5.0) as client:
                await client.delete(url, headers=headers)
        except Exception:
            pass

    return True


async def move_creative_to_project(user: Optional[Dict[str, Any]], creative_id: str, project_id: Optional[str]) -> bool:
    """Move a creative to a project folder (or unassign if empty)."""
    init_db()
    p_id = (project_id or "").strip()
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE saved_creatives SET folder_id = ? WHERE id = ?", (p_id, creative_id))
        conn.commit()

    if _is_supabase_ready():
        try:
            url = f"{SUPABASE_URL}/rest/v1/saved_creatives?id=eq.{creative_id}"
            headers = {
                "apikey": SUPABASE_SERVICE_ROLE_KEY,
                "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
                "Content-Type": "application/json",
            }
            async with httpx.AsyncClient(timeout=5.0) as client:
                await client.patch(url, headers=headers, json={"folder_id": p_id})
        except Exception:
            pass

    return True


# ===========================================================================
# User Profile Statistics
# ===========================================================================

async def get_user_stats(user: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Returns generation and storage statistics for user profile."""
    init_db()
    user_id = (user.get("id") or "") if user else ""
    params = [user_id] if user_id else []
    user_clause = " WHERE (user_id = ? OR user_id = '')" if user_id else ""

    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute(f"SELECT COUNT(*) FROM saved_creatives{user_clause}", params)
        total_generations = cursor.fetchone()[0]

        cursor.execute(f"SELECT COUNT(*) FROM saved_creatives{user_clause}{' AND' if user_clause else ' WHERE'} type = 'image'", params)
        total_images = cursor.fetchone()[0]

        cursor.execute(f"SELECT COUNT(*) FROM saved_creatives{user_clause}{' AND' if user_clause else ' WHERE'} type = 'video'", params)
        total_videos = cursor.fetchone()[0]

        cursor.execute(f"SELECT COUNT(*) FROM saved_creatives{user_clause}{' AND' if user_clause else ' WHERE'} is_favorite = 1", params)
        total_favorites = cursor.fetchone()[0]

        cursor.execute(f"SELECT COUNT(*) FROM saved_creatives{user_clause}{' AND' if user_clause else ' WHERE'} (folder_id IS NULL OR folder_id = '')", params)
        unassigned_count = cursor.fetchone()[0]

        cursor.execute(f"SELECT COUNT(*) FROM projects{user_clause}", params)
        total_projects = cursor.fetchone()[0]

        return {
            "total_generations": total_generations,
            "total_creatives": total_generations,
            "total_images": total_images,
            "total_videos": total_videos,
            "total_favorites": total_favorites,
            "favorites_count": total_favorites,
            "unassigned_count": unassigned_count,
            "total_projects": total_projects,
        }


# ===========================================================================
# Saved Creatives & Generation Storage
# ===========================================================================

async def save_creative(user: Optional[Dict[str, Any]], data: Dict[str, Any]) -> Dict[str, Any]:
    """Save an image or video generation with prompt, uploaded references, and folder metadata."""
    init_db()
    cid = data.get("id") or str(uuid.uuid4())
    user_id = (user.get("id") or "") if user else (data.get("user_id") or "")
    user_email = (user.get("email") or "Guest Creator") if user else (data.get("user_email") or "Guest Creator")
    now_iso = datetime.now(timezone.utc).isoformat()

    c_type = data.get("type", "image")
    title = data.get("title") or ("Video Ad" if c_type == "video" else "Image Ad")
    prompt = data.get("prompt", "")
    media_url = data.get("media_url", "")
    aspect_ratio = data.get("aspect_ratio", "9:16" if c_type == "video" else "4:5")
    model_params = data.get("model_params") or {}
    tags = data.get("tags") or []
    reference_images = data.get("reference_images") or []
    folder_id = (data.get("folder_id") or "").strip()
    is_fav = 1 if data.get("is_favorite") else 0

    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO saved_creatives 
            (id, user_id, user_email, type, title, prompt, media_url, aspect_ratio, model_params, tags, reference_images, folder_id, is_favorite, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
            json.dumps(reference_images),
            folder_id,
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
        "reference_images": reference_images,
        "folder_id": folder_id,
        "is_favorite": bool(is_fav),
        "created_at": now_iso
    }

    if _is_supabase_ready():
        try:
            url = f"{SUPABASE_URL}/rest/v1/saved_creatives"
            headers = {
                "apikey": SUPABASE_SERVICE_ROLE_KEY,
                "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
                "Content-Type": "application/json",
                "Prefer": "resolution=merge-duplicates"
            }
            supabase_payload = dict(record)
            if not user_id:
                supabase_payload.pop("user_id", None)
            async with httpx.AsyncClient(timeout=8.0) as client:
                await client.post(url, headers=headers, json=supabase_payload)
        except Exception:
            pass

    return record


async def list_saved_creatives(
    user: Optional[Dict[str, Any]],
    media_type: Optional[str] = None,
    only_favorites: bool = False,
    folder_id: Optional[str] = None,
    search: Optional[str] = None,
    limit: int = 150,
) -> List[Dict[str, Any]]:
    """List saved creatives with filtering by media type, favorite, folder, and search keyword."""
    init_db()
    user_id = (user.get("id") or "") if user else ""

    query = """
        SELECT id, user_id, user_email, type, title, prompt, media_url, aspect_ratio, model_params, tags, reference_images, folder_id, is_favorite, created_at 
        FROM saved_creatives 
        WHERE 1=1
    """
    params = []

    if user_id:
        query += " AND (user_id = ? OR user_id = '')"
        params.append(user_id)
    if media_type:
        query += " AND type = ?"
        params.append(media_type)
    if only_favorites:
        query += " AND is_favorite = 1"
    if folder_id:
        if folder_id == "unassigned":
            query += " AND (folder_id IS NULL OR folder_id = '')"
        else:
            query += " AND folder_id = ?"
            params.append(folder_id)
    if search:
        s = f"%{search.strip().lower()}%"
        query += " AND (LOWER(prompt) LIKE ? OR LOWER(title) LIKE ?)"
        params.extend([s, s])

    query += f" ORDER BY created_at DESC LIMIT {int(limit)}"

    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(query, params)
        rows = cursor.fetchall()
        results = []
        for r in rows:
            m_params = {}
            t_list = []
            ref_list = []
            try:
                m_params = json.loads(r["model_params"]) if r["model_params"] else {}
            except Exception:
                pass
            try:
                t_list = json.loads(r["tags"]) if r["tags"] else []
            except Exception:
                pass
            try:
                ref_list = json.loads(r["reference_images"]) if r["reference_images"] else []
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
                "reference_images": ref_list,
                "folder_id": r["folder_id"] or "",
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
