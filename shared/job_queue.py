"""
shared/job_queue.py
Lightweight Redis queue helper used by all four API services.

In the enterprise model (AWS) this is replaced by an SQS client —
the job schema is identical.
"""

from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

_redis_client = None


def _get_redis():
    global _redis_client
    if _redis_client is not None:
        return _redis_client
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    try:
        import redis
        _redis_client = redis.from_url(redis_url, decode_responses=True)
        _redis_client.ping()
    except Exception:
        _redis_client = None
    return _redis_client


QUEUE_KEY = "koi:scan:queue"
RESULT_TTL = 3600


def enqueue_job(app: str, payload: dict) -> str:
    """
    Push a scan job onto the queue. Returns the job_id.
    If Redis is unavailable, returns a sentinel job_id with status 'unavailable'.
    """
    job_id = str(uuid.uuid4())
    job = {
        "job_id": job_id,
        "app": app,
        "payload": payload,
        "enqueued_at": datetime.now(timezone.utc).isoformat(),
    }
    r = _get_redis()
    if r is None:
        return f"sync:{job_id}"  # caller should fall back to sync processing
    r.rpush(QUEUE_KEY, json.dumps(job))
    # Write a 'queued' status immediately so polling works right away
    r.setex(
        f"koi:scan:result:{job_id}",
        RESULT_TTL,
        json.dumps({"job_id": job_id, "status": "queued", "result": None}),
    )
    return job_id


def get_job_result(job_id: str) -> Optional[dict]:
    """
    Fetch job result from Redis cache.
    Returns None if not found (expired or never queued).
    """
    r = _get_redis()
    if r is None:
        return None
    raw = r.get(f"koi:scan:result:{job_id}")
    if raw is None:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return None


def write_sync_result(job_id: str, app: str, result: dict) -> None:
    """
    Write a completed result directly (used in sync mode).
    """
    r = _get_redis()
    if r is None:
        return
    output = {
        "job_id": job_id,
        "app": app,
        "status": "complete",
        "result": result,
    }
    r.setex(f"koi:scan:result:{job_id}", RESULT_TTL, json.dumps(output))
