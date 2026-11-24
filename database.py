"""
Database storage for Ad Studio user saved creatives, projects/folders, and generation history.

Synchronizes with Supabase PostgreSQL (saved_creatives and projects tables) and maintains
a local persistent SQLite store for offline development, local fast caching, and resilience.
"""

import os
import sqlite3
import json
import uuid
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import httpx
try:
    from media_utils import load_dotenv
    load_dotenv()
except Exception:
    pass

logger = logging.getLogger(__name__)

if os.environ.get("VERCEL"):
    DB_DIR = "/tmp/data"
    DB_PATH = "/tmp/ad_studio.db"
else:
    DB_DIR = "data"
    DB_PATH = os.path.join("data", "ad_studio.db")


def _get_supabase_url() -> str:
    return (os.environ.get("SUPABASE_URL") or "").rstrip("/")


def _get_supabase_key() -> str:
    return os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or os.environ.get("SUPABASE_ANON_KEY") or ""


def _is_supabase_ready() -> bool:
    return bool(_get_supabase_url() and _get_supabase_key())


def _clean_uuid(val: Any) -> Optional[str]:
    """Return a clean UUID string if valid, else None (avoids PostgreSQL 22P02 invalid input syntax error)."""
    if not val:
        return None
    try:
        return str(uuid.UUID(str(val).strip()))
    except (ValueError, AttributeError, TypeError):
        return None


def init_db():
    """Initialize local SQLite database tables if not exist and run migrations."""
    try:
        os.makedirs(DB_DIR, exist_ok=True)
    except Exception:
        pass
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
                folder_id TEXT DEFAULT '',
                is_favorite INTEGER DEFAULT 0,
                created_at TEXT NOT NULL
            )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_user ON saved_creatives(user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_user_email ON saved_creatives(user_email)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_created ON saved_creatives(created_at DESC)")

        # Ensure new columns exist on older tables
        cursor.execute("PRAGMA table_info(saved_creatives)")
        cols = [r[1] for r in cursor.fetchall()]
        if "reference_images" not in cols:
            cursor.execute("ALTER TABLE saved_creatives ADD COLUMN reference_images TEXT")
        if "folder_id" not in cols:
            cursor.execute("ALTER TABLE saved_creatives ADD COLUMN folder_id TEXT DEFAULT ''")
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
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_projects_email ON projects(user_email)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_projects_created ON projects(created_at DESC)")

        conn.commit()


# Initialize database on module load
init_db()


# ===========================================================================
# Project / Folder Management
# ===========================================================================

async def create_project(user: Optional[Dict[str, Any]], data: Dict[str, Any]) -> Dict[str, Any]:
    """Create a new project folder for organizing creatives."""
    init_db()
    pid = str(uuid.uuid4())
    raw_user_id = (user.get("id") or "") if user else ""
    user_id = _clean_uuid(raw_user_id) or ""
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
            url = f"{_get_supabase_url()}/rest/v1/projects"
            headers = {
                "apikey": _get_supabase_key(),
                "Authorization": f"Bearer {_get_supabase_key()}",
                "Content-Type": "application/json",
                "Prefer": "return=minimal",
            }
            payload = dict(record)
            payload.pop("item_count", None)
            payload["user_id"] = _clean_uuid(user_id)
            async with httpx.AsyncClient(timeout=6.0) as client:
                res = await client.post(url, headers=headers, json=payload)
                if res.status_code >= 400:
                    logger.warning(f"Supabase project create notice (status {res.status_code}): {res.text}")
        except Exception as e:
            logger.warning(f"Supabase create_project non-fatal exception: {e}")

    return record


async def list_projects(user: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """List all projects for user with item counts."""
    init_db()
    raw_uid = (user.get("id") or "") if user else ""
    user_id = _clean_uuid(raw_uid) or ""
    user_email = (user.get("email") or "").strip().lower() if user else ""

    # Fail closed: an unidentified (guest) caller owns no projects — never scan the whole table.
    if not user_id and not user_email:
        return []

    projects_map: Dict[str, Dict[str, Any]] = {}

    # 1. Try fetching from Supabase if available
    if _is_supabase_ready():
        try:
            if user_id and user_email:
                _scope = f"&or=(user_id.eq.{user_id},user_email.eq.{user_email})"
            elif user_id:
                _scope = f"&user_id=eq.{user_id}"
            else:
                _scope = f"&user_email=eq.{user_email}"
            url = f"{_get_supabase_url()}/rest/v1/projects?select=*{_scope}&order=updated_at.desc"
            headers = {
                "apikey": _get_supabase_key(),
                "Authorization": f"Bearer {_get_supabase_key()}",
            }
            async with httpx.AsyncClient(timeout=6.0) as client:
                res = await client.get(url, headers=headers)
                if res.status_code == 200:
                    supa_projects = res.json()
                    # Cache fetched projects into SQLite
                    with sqlite3.connect(DB_PATH) as conn:
                        cur = conn.cursor()
                        for p in supa_projects:
                            pid = str(p.get("id"))
                            cur.execute("""
                                INSERT OR REPLACE INTO projects (id, user_id, user_email, name, description, color, icon, created_at, updated_at)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                            """, (
                                pid,
                                str(p.get("user_id") or ""),
                                str(p.get("user_email") or "Guest Creator"),
                                str(p.get("name") or "Untitled Project"),
                                str(p.get("description") or ""),
                                str(p.get("color") or "#8d3624"),
                                str(p.get("icon") or "folder"),
                                str(p.get("created_at") or datetime.now(timezone.utc).isoformat()),
                                str(p.get("updated_at") or datetime.now(timezone.utc).isoformat()),
                            ))
                            projects_map[pid] = {
                                "id": pid,
                                "user_id": p.get("user_id") or "",
                                "user_email": p.get("user_email") or "",
                                "name": p.get("name") or "Untitled Project",
                                "description": p.get("description") or "",
                                "color": p.get("color") or "#8d3624",
                                "icon": p.get("icon") or "folder",
                                "item_count": 0,
                                "created_at": p.get("created_at") or "",
                                "updated_at": p.get("updated_at") or "",
                            }
                        conn.commit()
        except Exception as e:
            logger.warning(f"Supabase list_projects fetch failed, fallback to local: {e}")

    # 2. Query local SQLite with item count join
    query = """
        SELECT p.id, p.user_id, p.user_email, p.name, p.description, p.color, p.icon, p.created_at, p.updated_at,
               COUNT(c.id) as item_count
        FROM projects p
        LEFT JOIN saved_creatives c ON c.folder_id = p.id
    """
    params = []
    if user_id and user_email:
        query += " WHERE (p.user_id = ? OR LOWER(p.user_email) = ?)"
        params.extend([user_id, user_email])
    elif user_id:
        query += " WHERE p.user_id = ?"
        params.append(user_id)
    else:
        query += " WHERE LOWER(p.user_email) = ?"
        params.append(user_email)

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
    """Fetch project details by ID, scoped to the owner."""
    init_db()
    raw_uid = (user.get("id") or "") if user else ""
    user_id = _clean_uuid(raw_uid) or ""
    user_email = (user.get("email") or "").strip().lower() if user else ""
    if not user_id and not user_email:
        return None  # guests own no projects
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("""
            SELECT p.*, COUNT(c.id) as item_count
            FROM projects p
            LEFT JOIN saved_creatives c ON c.folder_id = p.id
            WHERE p.id = ? AND (p.user_id = ? OR LOWER(p.user_email) = ?)
            GROUP BY p.id
        """, (project_id, user_id, user_email))
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
    """Update project name, description, color, or icon (owner only)."""
    init_db()
    if not await get_project(user, project_id):
        return None  # not found or not owned by this user
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
            url = f"{_get_supabase_url()}/rest/v1/projects?id=eq.{project_id}"
            headers = {
                "apikey": _get_supabase_key(),
                "Authorization": f"Bearer {_get_supabase_key()}",
                "Content-Type": "application/json",
            }
            supa_data = {k: data[k] for k in ["name", "description", "color", "icon"] if k in data}
            supa_data["updated_at"] = now_iso
            async with httpx.AsyncClient(timeout=5.0) as client:
                await client.patch(url, headers=headers, json=supa_data)
        except Exception as e:
            logger.warning(f"Supabase update_project error: {e}")

    return await get_project(user, project_id)


async def delete_project(user: Optional[Dict[str, Any]], project_id: str) -> bool:
    """Delete a project and unassign its items (owner only)."""
    init_db()
    if not await get_project(user, project_id):
        return False  # not found or not owned by this user
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE saved_creatives SET folder_id = '' WHERE folder_id = ?", (project_id,))
        cursor.execute("DELETE FROM projects WHERE id = ?", (project_id,))
        conn.commit()

    if _is_supabase_ready():
        try:
            headers = {
                "apikey": _get_supabase_key(),
                "Authorization": f"Bearer {_get_supabase_key()}",
            }
            async with httpx.AsyncClient(timeout=5.0) as client:
                await client.patch(
                    f"{_get_supabase_url()}/rest/v1/saved_creatives?folder_id=eq.{project_id}",
                    headers={**headers, "Content-Type": "application/json"},
                    json={"folder_id": ""},
                )
                await client.delete(f"{_get_supabase_url()}/rest/v1/projects?id=eq.{project_id}", headers=headers)
        except Exception as e:
            logger.warning(f"Supabase delete_project error: {e}")

    return True


async def _user_owns_creative(user: Optional[Dict[str, Any]], creative_id: str) -> bool:
    """True only if this creative belongs to the given signed-in user. Guests own nothing."""
    raw_uid = (user.get("id") or "") if user else ""
    user_id = _clean_uuid(raw_uid) or ""
    user_email = (user.get("email") or "").strip().lower() if user else ""
    if not user_id and not user_email:
        return False

    # Local cache first (list_saved_creatives syncs rows here before the UI offers any action).
    init_db()
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("SELECT user_id, user_email FROM saved_creatives WHERE id = ?", (creative_id,))
        r = cur.fetchone()
    if r is not None:
        row_uid = (r["user_id"] or "")
        row_email = (r["user_email"] or "").strip().lower()
        return (bool(user_id) and row_uid == user_id) or (bool(user_email) and row_email == user_email)

    # Not cached locally — ask Supabase, scoped to this user.
    if _is_supabase_ready():
        try:
            if user_id and user_email:
                flt = f"id=eq.{creative_id}&or=(user_id.eq.{user_id},user_email.eq.{user_email})"
            elif user_id:
                flt = f"id=eq.{creative_id}&user_id=eq.{user_id}"
            else:
                flt = f"id=eq.{creative_id}&user_email=eq.{user_email}"
            url = f"{_get_supabase_url()}/rest/v1/saved_creatives?select=id&{flt}"
            headers = {"apikey": _get_supabase_key(), "Authorization": f"Bearer {_get_supabase_key()}"}
            async with httpx.AsyncClient(timeout=5.0) as client:
                res = await client.get(url, headers=headers)
                if res.status_code == 200:
                    return bool(res.json())
        except Exception as e:
            logger.warning(f"Supabase ownership check error: {e}")
    return False


async def move_creative_to_project(user: Optional[Dict[str, Any]], creative_id: str, project_id: Optional[str]) -> bool:
    """Move a creative to a project folder (or unassign if empty) — owner only."""
    init_db()
    if not await _user_owns_creative(user, creative_id):
        return False
    p_id = (project_id or "").strip()
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE saved_creatives SET folder_id = ? WHERE id = ?", (p_id, creative_id))
        conn.commit()

    if _is_supabase_ready():
        try:
            url = f"{_get_supabase_url()}/rest/v1/saved_creatives?id=eq.{creative_id}"
            headers = {
                "apikey": _get_supabase_key(),
                "Authorization": f"Bearer {_get_supabase_key()}",
                "Content-Type": "application/json",
            }
            patch_data = {"folder_id": p_id}
            async with httpx.AsyncClient(timeout=5.0) as client:
                res = await client.patch(url, headers=headers, json=patch_data)
                # If folder_id column doesn't exist yet, patch model_params
                if res.status_code >= 400:
                    get_res = await client.get(url, headers=headers)
                    if get_res.status_code == 200 and get_res.json():
                        cur_mp = get_res.json()[0].get("model_params") or {}
                        cur_mp["folder_id"] = p_id
                        await client.patch(url, headers=headers, json={"model_params": cur_mp})
        except Exception as e:
            logger.warning(f"Supabase move_creative_to_project error: {e}")

    return True


# ===========================================================================
# User Profile Statistics
# ===========================================================================

async def get_user_stats(user: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Returns generation and storage statistics for user profile."""
    init_db()
    raw_uid = (user.get("id") or "") if user else ""
    user_id = _clean_uuid(raw_uid) or ""
    user_email = (user.get("email") or "").strip().lower() if user else ""

    # Guests have no stats of their own — never aggregate across the whole table.
    if not user_id and not user_email:
        return {
            "total_generations": 0, "total_creatives": 0, "total_images": 0,
            "total_videos": 0, "total_favorites": 0, "favorites_count": 0,
            "unassigned_count": 0, "total_projects": 0,
        }

    params = []
    user_clause = ""
    if user_id and user_email:
        user_clause = " WHERE (user_id = ? OR LOWER(user_email) = ?)"
        params.extend([user_id, user_email])
    elif user_id:
        user_clause = " WHERE user_id = ?"
        params.append(user_id)
    else:
        user_clause = " WHERE LOWER(user_email) = ?"
        params.append(user_email)

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
    cid = _clean_uuid(data.get("id")) or str(uuid.uuid4())
    raw_user_id = (user.get("id") or "") if user else (data.get("user_id") or "")
    clean_uid = _clean_uuid(raw_user_id)
    user_email = (user.get("email") or "Guest Creator") if user else (data.get("user_email") or "Guest Creator")
    now_iso = datetime.now(timezone.utc).isoformat()

    c_type = data.get("type", "image")
    title = data.get("title") or ("Video Ad" if c_type == "video" else "Image Ad")
    prompt = data.get("prompt", "")
    media_url = data.get("media_url", "")
    aspect_ratio = data.get("aspect_ratio", "9:16" if c_type == "video" else "4:5")
    model_params = dict(data.get("model_params") or {})
    tags = list(data.get("tags") or [])
    reference_images = list(data.get("reference_images") or [])
    folder_id = (data.get("folder_id") or "").strip()
    is_fav = 1 if data.get("is_favorite") else 0

    # Ensure reference_images and folder_id are also embedded in model_params for seamless compatibility
    model_params["reference_images"] = reference_images
    model_params["folder_id"] = folder_id

    # 1. Persist to local SQLite
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO saved_creatives 
            (id, user_id, user_email, type, title, prompt, media_url, aspect_ratio, model_params, tags, reference_images, folder_id, is_favorite, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            cid,
            clean_uid or "",
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
        "user_id": clean_uid or "",
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

    # 2. Persist to Supabase PostgreSQL
    if _is_supabase_ready():
        try:
            url = f"{_get_supabase_url()}/rest/v1/saved_creatives"
            headers = {
                "apikey": _get_supabase_key(),
                "Authorization": f"Bearer {_get_supabase_key()}",
                "Content-Type": "application/json",
                "Prefer": "resolution=merge-duplicates"
            }
            supabase_payload = {
                "id": cid,
                "user_id": clean_uid,  # None if not valid UUID
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

            async with httpx.AsyncClient(timeout=8.0) as client:
                res = await client.post(url, headers=headers, json=supabase_payload)

                # Fallback if folder_id or reference_images columns do not exist yet in Supabase schema
                if res.status_code >= 400 and ("folder_id" in res.text or "reference_images" in res.text):
                    logger.info("Retrying Supabase save with embedded fallback fields...")
                    fallback_payload = dict(supabase_payload)
                    fallback_payload.pop("folder_id", None)
                    fallback_payload.pop("reference_images", None)
                    res_retry = await client.post(url, headers=headers, json=fallback_payload)
                    if res_retry.status_code >= 400:
                        logger.warning(f"Supabase creative save retry notice ({res_retry.status_code}): {res_retry.text}")
                elif res.status_code >= 400:
                    logger.warning(f"Supabase creative save notice ({res.status_code}): {res.text}")
        except Exception as e:
            logger.warning(f"Supabase save_creative non-fatal exception: {e}")

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
    raw_uid = (user.get("id") or "") if user else ""
    clean_uid = _clean_uuid(raw_uid)
    user_email = (user.get("email") or "").strip().lower() if user else ""

    # Fail closed: an unidentified (guest) caller owns no creatives — never scan the whole table.
    if not clean_uid and not user_email:
        return []

    # 1. Fetch from Supabase PostgreSQL if configured
    if _is_supabase_ready():
        try:
            query_params = ["select=*", f"limit={int(limit)}", "order=created_at.desc"]

            # Filter by user if authenticated
            if clean_uid and user_email:
                query_params.append(f"or=(user_id.eq.{clean_uid},user_email.eq.{user_email})")
            elif clean_uid:
                query_params.append(f"user_id=eq.{clean_uid}")
            elif user_email:
                query_params.append(f"user_email=eq.{user_email}")

            if media_type:
                query_params.append(f"type=eq.{media_type}")

            if only_favorites:
                query_params.append("is_favorite=eq.true")

            if folder_id:
                if folder_id == "unassigned":
                    query_params.append("or=(folder_id.is.null,folder_id.eq.)")
                else:
                    query_params.append(f"folder_id=eq.{folder_id}")

            if search and search.strip():
                clean_s = search.strip().replace("*", "")
                query_params.append(f"or=(prompt.ilike.*{clean_s}*,title.ilike.*{clean_s}*)")

            url = f"{_get_supabase_url()}/rest/v1/saved_creatives?{'&'.join(query_params)}"
            headers = {
                "apikey": _get_supabase_key(),
                "Authorization": f"Bearer {_get_supabase_key()}",
            }

            async with httpx.AsyncClient(timeout=8.0) as client:
                res = await client.get(url, headers=headers)
                if res.status_code == 200:
                    supa_rows = res.json()
                    results = []
                    # Also sync into SQLite
                    with sqlite3.connect(DB_PATH) as conn:
                        cur = conn.cursor()
                        for r in supa_rows:
                            m_params = r.get("model_params") or {}
                            t_list = r.get("tags") or []
                            # Reference images can be in column or inside model_params
                            ref_list = r.get("reference_images") or m_params.get("reference_images") or []
                            f_id = r.get("folder_id") or m_params.get("folder_id") or ""

                            cur.execute("""
                                INSERT OR REPLACE INTO saved_creatives 
                                (id, user_id, user_email, type, title, prompt, media_url, aspect_ratio, model_params, tags, reference_images, folder_id, is_favorite, created_at)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                            """, (
                                str(r["id"]),
                                str(r.get("user_id") or ""),
                                str(r.get("user_email") or "Guest Creator"),
                                str(r.get("type") or "image"),
                                str(r.get("title") or "Ad"),
                                str(r.get("prompt") or ""),
                                str(r.get("media_url") or ""),
                                str(r.get("aspect_ratio") or "9:16"),
                                json.dumps(m_params),
                                json.dumps(t_list),
                                json.dumps(ref_list),
                                str(f_id),
                                1 if r.get("is_favorite") else 0,
                                str(r.get("created_at") or datetime.now(timezone.utc).isoformat())
                            ))

                            results.append({
                                "id": str(r["id"]),
                                "user_id": str(r.get("user_id") or ""),
                                "user_email": str(r.get("user_email") or ""),
                                "type": str(r.get("type") or "image"),
                                "title": str(r.get("title") or "Ad"),
                                "prompt": str(r.get("prompt") or ""),
                                "media_url": str(r.get("media_url") or ""),
                                "aspect_ratio": str(r.get("aspect_ratio") or "9:16"),
                                "model_params": m_params,
                                "tags": t_list,
                                "reference_images": ref_list,
                                "folder_id": str(f_id),
                                "is_favorite": bool(r.get("is_favorite")),
                                "created_at": str(r.get("created_at") or "")
                            })
                        conn.commit()

                    if results:
                        return results
        except Exception as e:
            logger.warning(f"Supabase list_saved_creatives query failed, fallback to SQLite: {e}")

    # 2. Local SQLite fallback
    query = """
        SELECT id, user_id, user_email, type, title, prompt, media_url, aspect_ratio, model_params, tags, reference_images, folder_id, is_favorite, created_at 
        FROM saved_creatives 
        WHERE 1=1
    """
    params = []

    if clean_uid and user_email:
        query += " AND (user_id = ? OR LOWER(user_email) = ?)"
        params.extend([clean_uid, user_email])
    elif clean_uid:
        query += " AND user_id = ?"
        params.append(clean_uid)
    else:
        query += " AND LOWER(user_email) = ?"
        params.append(user_email)

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

            f_id = r["folder_id"] or m_params.get("folder_id") or ""
            if not ref_list and m_params.get("reference_images"):
                ref_list = m_params.get("reference_images")

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
                "folder_id": f_id,
                "is_favorite": bool(r["is_favorite"]),
                "created_at": r["created_at"]
            })
        return results


async def toggle_favorite(user: Optional[Dict[str, Any]], cid: str, is_fav: bool) -> bool:
    """Toggle favorite status of a creative (owner only)."""
    if not await _user_owns_creative(user, cid):
        return False
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE saved_creatives SET is_favorite = ? WHERE id = ?", (1 if is_fav else 0, cid))
        conn.commit()

    if _is_supabase_ready():
        try:
            url = f"{_get_supabase_url()}/rest/v1/saved_creatives?id=eq.{cid}"
            headers = {
                "apikey": _get_supabase_key(),
                "Authorization": f"Bearer {_get_supabase_key()}",
                "Content-Type": "application/json"
            }
            async with httpx.AsyncClient(timeout=5.0) as client:
                await client.patch(url, headers=headers, json={"is_favorite": is_fav})
        except Exception as e:
            logger.warning(f"Supabase toggle_favorite error: {e}")

    return True


async def delete_creative(user: Optional[Dict[str, Any]], cid: str) -> bool:
    """Delete a saved creative (owner only)."""
    if not await _user_owns_creative(user, cid):
        return False
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM saved_creatives WHERE id = ?", (cid,))
        conn.commit()

    if _is_supabase_ready():
        try:
            url = f"{_get_supabase_url()}/rest/v1/saved_creatives?id=eq.{cid}"
            headers = {
                "apikey": _get_supabase_key(),
                "Authorization": f"Bearer {_get_supabase_key()}"
            }
            async with httpx.AsyncClient(timeout=5.0) as client:
                await client.delete(url, headers=headers)
        except Exception as e:
            logger.warning(f"Supabase delete_creative error: {e}")

    return True


async def sync_sqlite_to_supabase() -> int:
    """Sync all unsynced or local SQLite creatives to Supabase PostgreSQL."""
    if not _is_supabase_ready():
        return 0

    url = f"{_get_supabase_url()}/rest/v1/saved_creatives"
    headers = {
        "apikey": _get_supabase_key(),
        "Authorization": f"Bearer {_get_supabase_key()}",
        "Content-Type": "application/json",
        "Prefer": "resolution=merge-duplicates"
    }

    count = 0
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute("SELECT * FROM saved_creatives")
        rows = [dict(r) for r in c.fetchall()]

    async with httpx.AsyncClient(timeout=10.0) as client:
        for r in rows:
            try:
                mp = json.loads(r['model_params']) if r.get('model_params') else {}
                ref = json.loads(r['reference_images']) if r.get('reference_images') else []
                mp['reference_images'] = ref
                mp['folder_id'] = r.get('folder_id') or ''
                tags = json.loads(r['tags']) if r.get('tags') else []

                payload = {
                    'id': _clean_uuid(r['id']) or str(uuid.uuid4()),
                    'user_id': _clean_uuid(r.get('user_id')),
                    'user_email': r.get('user_email') or 'Guest Creator',
                    'type': r.get('type') or 'image',
                    'title': r.get('title') or 'Ad',
                    'prompt': r.get('prompt') or '',
                    'media_url': r.get('media_url') or '',
                    'aspect_ratio': r.get('aspect_ratio') or '9:16',
                    'model_params': mp,
                    'tags': tags,
                    'is_favorite': bool(r.get('is_favorite')),
                    'created_at': r.get('created_at') or datetime.now(timezone.utc).isoformat()
                }
                res = await client.post(url, headers=headers, json=payload)
                if res.status_code in (200, 201):
                    count += 1
            except Exception:
                pass

    return count
