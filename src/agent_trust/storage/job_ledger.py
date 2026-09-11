"""Transactional PostgreSQL job ledger with leases and stale-worker fencing."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import insert, select, text, update

from .database import jobs


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(value: datetime) -> str:
    return value.isoformat()


def _decode(row) -> dict[str, Any]:
    result = dict(row._mapping)
    result["payload"] = json.loads(result["payload"])
    if result.get("result"):
        result["result"] = json.loads(result["result"])
    return result


class JobLedger:
    """At-least-once job state. External calls must happen outside transactions."""

    def __init__(self, engine):
        self.engine = engine

    def enqueue(self, kind: str, workspace_id: str, payload: dict[str, Any], *, idempotency_key: str | None = None, max_attempts: int = 3) -> dict[str, Any]:
        if max_attempts < 1:
            raise ValueError("max_attempts must be positive")
        job_id = str(uuid.uuid4())
        now = _now()
        values = dict(id=job_id, workspace_id=workspace_id, kind=kind, payload=json.dumps(payload), status="queued", attempts=0, max_attempts=max_attempts, available_at=_iso(now), lease_until=None, lease_token=None, result=None, error=None, idempotency_key=idempotency_key, created_at=_iso(now), updated_at=_iso(now))
        with self.engine.begin() as connection:
            if idempotency_key:
                existing = connection.execute(select(jobs).where(jobs.c.idempotency_key == idempotency_key, jobs.c.workspace_id == workspace_id)).first()
                if existing:
                    return _decode(existing)
            connection.execute(insert(jobs).values(**values))
        return values | {"payload": payload}

    def get(self, job_id: str, workspace_id: str) -> dict[str, Any] | None:
        with self.engine.connect() as connection:
            row = connection.execute(select(jobs).where(jobs.c.id == job_id, jobs.c.workspace_id == workspace_id)).first()
        return _decode(row) if row else None

    def claim(self, worker_id: str, lease_seconds: int = 60) -> dict[str, Any] | None:
        now = _now()
        expiry = _iso(now)
        with self.engine.begin() as connection:
            if connection.dialect.name == "postgresql":
                statement = text("""SELECT * FROM agent_trust_jobs
                    WHERE (status = 'queued' AND available_at <= :now)
                       OR (status = 'running' AND lease_until < :now)
                    ORDER BY created_at FOR UPDATE SKIP LOCKED LIMIT 1""")
                row = connection.execute(statement, {"now": expiry}).first()
            else:
                row = connection.execute(select(jobs).where(((jobs.c.status == "queued") & (jobs.c.available_at <= expiry)) | ((jobs.c.status == "running") & (jobs.c.lease_until < expiry))).order_by(jobs.c.created_at).limit(1)).first()
            if not row:
                return None
            job_id = row._mapping["id"]
            token = f"{worker_id}:{uuid.uuid4()}"
            updated = connection.execute(update(jobs).where(jobs.c.id == job_id).values(status="running", attempts=row._mapping["attempts"] + 1, lease_until=_iso(now + timedelta(seconds=lease_seconds)), lease_token=token, updated_at=expiry))
            if updated.rowcount != 1:
                return None
            fresh = connection.execute(select(jobs).where(jobs.c.id == job_id)).first()
        return _decode(fresh)

    def complete(self, job_id: str, lease_token: str, result: dict[str, Any]) -> bool:
        now = _iso(_now())
        with self.engine.begin() as connection:
            changed = connection.execute(update(jobs).where(jobs.c.id == job_id, jobs.c.status == "running", jobs.c.lease_token == lease_token).values(status="complete", result=json.dumps(result), error=None, lease_until=None, lease_token=None, updated_at=now)).rowcount
        return changed == 1

    def fail(self, job_id: str, lease_token: str, error: str, retry_delay_seconds: int = 5) -> bool:
        now = _now()
        with self.engine.begin() as connection:
            row = connection.execute(select(jobs.c.attempts, jobs.c.max_attempts).where(jobs.c.id == job_id, jobs.c.status == "running", jobs.c.lease_token == lease_token)).first()
            if not row:
                return False
            terminal = row.attempts >= row.max_attempts
            changed = connection.execute(update(jobs).where(jobs.c.id == job_id, jobs.c.status == "running", jobs.c.lease_token == lease_token).values(status="failed" if terminal else "queued", error=error[:4000], available_at=_iso(now if terminal else now + timedelta(seconds=retry_delay_seconds)), lease_until=None, lease_token=None, updated_at=_iso(now))).rowcount
        return changed == 1

    def recover_abandoned(self, now: datetime | None = None) -> int:
        now = now or _now()
        with self.engine.begin() as connection:
            changed = connection.execute(update(jobs).where(jobs.c.status == "running", jobs.c.lease_until < _iso(now)).values(status="queued", lease_token=None, lease_until=None, available_at=_iso(now), updated_at=_iso(now))).rowcount
        return int(changed or 0)
