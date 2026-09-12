"""Transactional jobs and assessment results with leases and stale-worker fencing."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from .database import jobs, records


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _decode(row) -> dict[str, Any]:
    result = dict(row._mapping)
    result["payload"] = json.loads(result["payload"])
    if result.get("result"):
        result["result"] = json.loads(result["result"])
    return result


def _insert(connection, table):
    return (pg_insert if connection.dialect.name == "postgresql" else sqlite_insert)(table)


def _sync_assessment(connection, job) -> None:
    """Maintain the public assessment projection in the job's transaction."""
    if job["kind"] != "assessment":
        return
    payload = {
        "id": job["id"], "job_id": job["id"], "workspace_id": job["workspace_id"],
        "subject_id": job["payload"].get("subject_id"),
        "profile": job["payload"].get("profile", "default"),
        "schema_version": "2026-01", "status": job["status"],
        "result": job.get("result"), "error": job.get("error"),
    }
    statement = _insert(connection, records).values(
        id=job["id"], workspace_id=job["workspace_id"], kind="assessments",
        payload=json.dumps(payload), created_at=job["created_at"], updated_at=job["updated_at"],
    )
    updated = connection.execute(statement.on_conflict_do_update(
        index_elements=[records.c.id],
        set_={"payload": statement.excluded.payload, "updated_at": statement.excluded.updated_at},
        where=(records.c.workspace_id == job["workspace_id"]) & (records.c.kind == "assessments"),
    ).returning(records.c.id))
    if updated.first() is None:
        raise PermissionError("assessment record identity conflicts with another record")


class JobLedger:
    """At-least-once state. External calls always happen outside transactions."""

    def __init__(self, engine):
        self.engine = engine

    def enqueue(self, kind: str, workspace_id: str, payload: dict[str, Any], *, idempotency_key: str | None = None, max_attempts: int = 3) -> dict[str, Any]:
        if max_attempts < 1:
            raise ValueError("max_attempts must be positive")
        now = _now().isoformat()
        values = dict(id=str(uuid.uuid4()), workspace_id=workspace_id, kind=kind,
                      payload=json.dumps(payload), status="queued", attempts=0,
                      max_attempts=max_attempts, available_at=now, lease_until=None,
                      lease_token=None, result=None, error=None,
                      idempotency_key=idempotency_key or None, created_at=now, updated_at=now)
        with self.engine.begin() as connection:
            statement = _insert(connection, jobs).values(**values).on_conflict_do_nothing(
                index_elements=[jobs.c.workspace_id, jobs.c.idempotency_key],
            ).returning(jobs)
            row = connection.execute(statement).first()
            if row is None:
                # ON CONFLICT waits for the other submission's commit. The
                # next statement sees it under PostgreSQL READ COMMITTED.
                row = connection.execute(select(jobs).where(
                    jobs.c.workspace_id == workspace_id, jobs.c.idempotency_key == idempotency_key,
                )).one()
                return _decode(row)
            job = _decode(row)
            _sync_assessment(connection, job)
        return job

    def get(self, job_id: str, workspace_id: str) -> dict[str, Any] | None:
        with self.engine.connect() as connection:
            row = connection.execute(select(jobs).where(jobs.c.id == job_id, jobs.c.workspace_id == workspace_id)).first()
        return _decode(row) if row else None

    def _expire_exhausted(self, connection, now: str) -> int:
        rows = connection.execute(update(jobs).where(
            jobs.c.attempts >= jobs.c.max_attempts,
            ((jobs.c.status == "running") & (jobs.c.lease_until <= now)) | (jobs.c.status == "queued"),
        ).values(status="failed", error="job attempt limit exhausted", lease_until=None,
                 lease_token=None, updated_at=now).returning(jobs)).all()
        for row in rows:
            _sync_assessment(connection, _decode(row))
        return len(rows)

    def claim(self, worker_id: str, lease_seconds: int = 60) -> dict[str, Any] | None:
        if lease_seconds <= 0:
            raise ValueError("lease_seconds must be positive")
        now = _now()
        with self.engine.begin() as connection:
            self._expire_exhausted(connection, now.isoformat())
            statement = select(jobs).where(
                jobs.c.attempts < jobs.c.max_attempts,
                ((jobs.c.status == "queued") & (jobs.c.available_at <= now.isoformat())) |
                ((jobs.c.status == "running") & (jobs.c.lease_until <= now.isoformat())),
            ).order_by(jobs.c.created_at, jobs.c.id).limit(1)
            if connection.dialect.name == "postgresql":
                statement = statement.with_for_update(skip_locked=True)
            row = connection.execute(statement).first()
            if not row:
                return None
            row = connection.execute(update(jobs).where(jobs.c.id == row.id).values(
                status="running", attempts=row.attempts + 1,
                lease_until=(now + timedelta(seconds=lease_seconds)).isoformat(),
                lease_token=f"{worker_id}:{uuid.uuid4()}", updated_at=now.isoformat(),
            ).returning(jobs)).one()
            job = _decode(row)
            _sync_assessment(connection, job)
        return job

    def complete(self, job_id: str, lease_token: str, result: dict[str, Any]) -> bool:
        with self.engine.begin() as connection:
            current = connection.execute(select(jobs).where(
                jobs.c.id == job_id, jobs.c.status == "running", jobs.c.lease_token == lease_token,
            ).with_for_update()).first()
            # Recheck time AFTER obtaining the lock. A blocked writer may have
            # held a valid lease when it arrived but lost it while waiting.
            now = _now().isoformat()
            if current is None or current.lease_until <= now:
                return False
            row = connection.execute(update(jobs).where(
                jobs.c.id == job_id, jobs.c.status == "running",
                jobs.c.lease_token == lease_token, jobs.c.lease_until > now,
            ).values(status="complete", result=json.dumps(result), error=None,
                     lease_until=None, lease_token=None, updated_at=now).returning(jobs)).first()
            if row is None:
                return False
            _sync_assessment(connection, _decode(row))
        return True

    def fail(self, job_id: str, lease_token: str, error: str, retry_delay_seconds: int = 5) -> bool:
        with self.engine.begin() as connection:
            predicate = (jobs.c.id == job_id, jobs.c.status == "running",
                         jobs.c.lease_token == lease_token)
            row = connection.execute(select(jobs).where(*predicate).with_for_update()).first()
            now = _now()
            if not row or row.lease_until <= now.isoformat():
                return False
            terminal = row.attempts >= row.max_attempts
            delay = min(300, max(0, retry_delay_seconds) * 2 ** min(row.attempts - 1, 10))
            row = connection.execute(update(jobs).where(*predicate).values(
                status="failed" if terminal else "queued", error=error[:4000],
                available_at=(now if terminal else now + timedelta(seconds=delay)).isoformat(),
                lease_until=None, lease_token=None, updated_at=now.isoformat(),
            ).returning(jobs)).one()
            _sync_assessment(connection, _decode(row))
        return True

    def recover_abandoned(self, now: datetime | None = None) -> int:
        now = (now or _now()).isoformat()
        with self.engine.begin() as connection:
            exhausted = self._expire_exhausted(connection, now)
            rows = connection.execute(update(jobs).where(
                jobs.c.status == "running", jobs.c.lease_until <= now,
            ).values(status="queued", lease_token=None, lease_until=None,
                     available_at=now, updated_at=now).returning(jobs)).all()
            for row in rows:
                _sync_assessment(connection, _decode(row))
        return exhausted + len(rows)
