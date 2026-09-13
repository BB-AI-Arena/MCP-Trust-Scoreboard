"""Database engine and schema definitions.

PostgreSQL is the supported deployment database. SQLite is intentionally
supported only for isolated tests and disposable local contract checks.
"""

from __future__ import annotations

from importlib.resources import files

from sqlalchemy import Column, Integer, MetaData, String, Table, Text, UniqueConstraint, create_engine, text

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
    Column("idempotency_key", String(256), nullable=True),
    Column("created_at", String(40), nullable=False),
    Column("updated_at", String(40), nullable=False),
    UniqueConstraint("workspace_id", "idempotency_key", name="uq_agent_trust_jobs_workspace_key"),
)

# Operator checkpoint state is not writable via generic API records.
connector_checkpoints = Table(
    "agent_trust_connector_checkpoints", metadata,
    Column("id", String(128), primary_key=True),
    Column("workspace_id", String(128), nullable=False, index=True),
    Column("payload", Text, nullable=False),
    Column("updated_at", String(40), nullable=False),
)


def make_engine(database_url: str):
    """Create an engine without opening a connection until it is used."""
    # The original DATABASE_URL alias did not specify a driver. Use the
    # packaged psycopg runtime without requiring psycopg2 or changing aliases.
    if database_url.startswith("postgresql://"):
        database_url = database_url.replace("postgresql://", "postgresql+psycopg://", 1)
    return create_engine(database_url, future=True, pool_pre_ping=True)


def create_schema(engine) -> None:
    if engine.dialect.name != "postgresql":
        metadata.create_all(engine)
        return
    # API and worker can start simultaneously. Serialize DDL, not job work.
    with engine.begin() as connection:
        connection.execute(text("SELECT pg_advisory_xact_lock(418207, 1)"))
        connection.execute(text("CREATE TABLE IF NOT EXISTS agent_trust_migrations (version varchar(128) PRIMARY KEY)"))
        applied = set(connection.execute(text("SELECT version FROM agent_trust_migrations")).scalars())
        for migration in sorted(files("agent_trust.storage").joinpath("migrations").iterdir(), key=lambda path: path.name):
            if migration.name.endswith(".sql") and migration.name not in applied:
                # Compile literal SQL so psycopg does not interpret PL/pgSQL
                # format('%I', ...) as a client-side bind placeholder.
                connection.execute(text(migration.read_text()))
                connection.execute(text("INSERT INTO agent_trust_migrations(version) VALUES (:version)"), {"version": migration.name})
