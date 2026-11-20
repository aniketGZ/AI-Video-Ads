import os
import json
import time
import logging
import threading
from typing import Optional

logger = logging.getLogger(__name__)

# Kept outside /static so job prompts and scripts are not publicly downloadable.
JOBS_CACHE_FILE = "/tmp/jobs_cache.json" if os.environ.get("VERCEL") else os.path.join("data", "jobs_cache.json")
JOB_RETENTION_SECONDS = 7 * 24 * 3600

_lock = threading.Lock()


def _read_cache() -> dict:
    if not os.path.exists(JOBS_CACHE_FILE):
        return {}
    try:
        with open(JOBS_CACHE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def persist_job_update(job_id: str, data: dict, job_store: Optional[dict] = None) -> dict:
    """
    Merge `data` into the job's record (memory + disk) and stamp `updated_at`.
    Thread-safe: progress callbacks run on worker threads.
    """
    now = time.time()
    with _lock:
        cache = _read_cache()
        existing = (job_store or {}).get(job_id) or cache.get(job_id) or {}
        merged = {**existing, **data, "updated_at": now}
        merged.setdefault("created_at", now)
        if merged.get("status") == "success":
            merged.pop("error", None)
        if job_store is not None:
            job_store[job_id] = merged

        cache[job_id] = merged
        cutoff = now - JOB_RETENTION_SECONDS
        cache = {k: v for k, v in cache.items() if v.get("updated_at", v.get("created_at", now)) >= cutoff}
        try:
            os.makedirs(os.path.dirname(JOBS_CACHE_FILE), exist_ok=True)
            tmp_path = JOBS_CACHE_FILE + ".tmp"
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(cache, f)
            os.replace(tmp_path, JOBS_CACHE_FILE)
        except Exception as e:
            logger.warning(f"Failed to persist job {job_id} to cache: {e}")
    return merged


def load_job(job_id: str) -> Optional[dict]:
    with _lock:
        return _read_cache().get(job_id)
