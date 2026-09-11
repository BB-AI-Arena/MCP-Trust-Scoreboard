"""Database engine and schema definitions.

PostgreSQL is the supported deployment database. SQLite is intentionally
supported only for isolated tests and disposable local contract checks.
"""

from __future__ import annotations

from sqlalchemy import Column, Integer, MetaData, String, Table, Text, create_engine

metadata = MetaData()

records = Table(
    "agent_trust_records", metadata,
    Column("id", String(128), primary_key=True),
    Column("workspace_id", String(128), nullable=False, index=True),
    Column("kind", String(64), nullable=False, index=True),
    Column("payload", Text, nullable=False),
    Column("created_at", String(40), nullable=False),
    Column("updated_at", String(40), nullable=False),
)

jobs = Table(
    "agent_trust_jobs", metadata,
    Column("id", String(128), primary_key=True),
    Column("workspace_id", String(128), nullable=False, index=True),
    Column("kind", String(64), nullable=False, index=True),
    Column("payload", Text, nullable=False),
    Column("status", String(24), nullable=False, index=True),
    Column("attempts", Integer, nullable=False, default=0),
    Column("max_attempts", Integer, nullable=False, default=3),
    Column("available_at", String(40), nullable=False, index=True),
    Column("lease_until", String(40), nullable=True),
    Column("lease_token", String(128), nullable=True, index=True),
    Column("result", Text, nullable=True),
    Column("error", Text, nullable=True),
    Column("idempotency_key", String(256), nullable=True, unique=True),
    Column("created_at", String(40), nullable=False),
    Column("updated_at", String(40), nullable=False),
)


def make_engine(database_url: str):
    """Create an engine without opening a connection until it is used."""
    return create_engine(database_url, future=True, pool_pre_ping=True)


def create_schema(engine) -> None:
    metadata.create_all(engine)
