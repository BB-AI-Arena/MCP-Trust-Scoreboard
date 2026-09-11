"""Small durable repository for workspace-scoped versioned records."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import delete, insert, select, update

from .database import records


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class RecordRepository:
    def __init__(self, engine):
        self.engine = engine

    def put(self, kind: str, record: dict[str, Any], workspace_id: str) -> dict[str, Any]:
        record = dict(record)
        record["workspace_id"] = workspace_id
        record_id = str(record["id"])
        now = _now()
        with self.engine.begin() as connection:
            existing = connection.execute(select(records.c.id, records.c.workspace_id).where(records.c.id == record_id)).first()
            if existing:
                if existing.workspace_id != workspace_id:
                    raise PermissionError("record belongs to another workspace")
                connection.execute(update(records).where(records.c.id == record_id).values(payload=json.dumps(record), updated_at=now))
            else:
                connection.execute(insert(records).values(id=record_id, workspace_id=workspace_id, kind=kind, payload=json.dumps(record), created_at=now, updated_at=now))
        return record

    def get(self, kind: str, record_id: str, workspace_id: str) -> dict[str, Any] | None:
        with self.engine.connect() as connection:
            row = connection.execute(select(records.c.payload).where(records.c.id == record_id, records.c.kind == kind, records.c.workspace_id == workspace_id)).first()
        return json.loads(row[0]) if row else None

    def list(self, kind: str, workspace_id: str, limit: int = 50, offset: int = 0) -> list[dict[str, Any]]:
        limit = min(max(limit, 1), 100)
        with self.engine.connect() as connection:
            rows = connection.execute(select(records.c.payload).where(records.c.kind == kind, records.c.workspace_id == workspace_id).order_by(records.c.created_at.desc()).limit(limit).offset(max(offset, 0))).all()
        return [json.loads(row[0]) for row in rows]

    def delete_workspace(self, workspace_id: str) -> None:
        """Only for disposable test databases and retention tooling."""
        with self.engine.begin() as connection:
            connection.execute(delete(records).where(records.c.workspace_id == workspace_id))
