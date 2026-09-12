# Agent Trust Platform v2 technical plan

Status: accepted implementation baseline for `2.0.0-alpha.1` (2026-09-11).
This plan converts the existing Palo Alto/Koi demonstration suite into a
vendor-neutral local/self-hosted product without deleting its useful flows.

## Scope and decisions

1. Keep FastAPI, Python, React, Vite, D3, and Recharts. Introduce one Python
   namespace at `src/agent_trust` and retain the old app directories as tested
   compatibility surfaces during migration.
2. PostgreSQL is the durable system of record. The new schema uses a record
   table and a transactional job ledger with indexes. SQLite is allowed only
   for isolated tests. Redis remains a disposable cache/legacy queue and is
   not a recovery source.
3. Rules-only analysis is the default and needs no API key. Gemini, an
   OpenAI-compatible endpoint, and AbuseIPDB are explicit adapters with
   capability declarations and unavailable/error states. No cloud fallback is
   implicit.
4. The API is single-tenant per deployment. Authentication owns workspace and
   collector identity; payload identity is reported data, not authorization.
   Token auth, restrictive CORS, bounded pagination, structured errors, and
   idempotency are the alpha baseline.
5. The legacy four services keep their route and response shapes. Their seeded
   examples and heuristic attribution are compatibility/demo behavior and are
   not advertised as verified security evidence.
6. No new graph database, Kafka, cloud service, enforcement gateway, or
   proprietary integration is introduced in alpha. Inline enforcement is a
   v2.1 design and remains absent.

## Dependency order and gates

| Order | Slice | Gate |
| --- | --- | --- |
| A1 | Neutral product language, version, namespace, contracts | No product/runtime claim names a vendor as the platform owner; import and version tests pass |
| A2 | Provider contracts and safe configuration | Rules work without keys; unavailable providers are visible; hosted use is opt-in |
| A3 | PostgreSQL schema, records, job ledger | Durable restart, idempotency, retry, lease recovery, and stale-worker fencing tests pass |
| A4 | Authenticated `/api/v1` migration surface | Workspace cannot be selected by body; scopes and error contract tests pass |
| A5 | Legacy adapter and UI migration | Four original route/response flows remain runnable and branded neutrally |
| B | MCP/OpenAPI collectors, evidence, snapshots | Real local stdio/HTTP fixtures and unsafe-egress/archive tests pass |
| C | Behavior, graph, artifact evidence views and SDKs | Duplicate/late events, warmup, multi-edge/cycle, and telemetry mapping tests pass |
| D | Release/recovery/upgrade gates | Disposable fresh/upgrade/rollback tests, scans, SBOM, and exact SHA release prep pass |

## Data and migration strategy

The original `koi` Postgres database and `postgres_data`/`redis_data` volumes
are not renamed or altered by this slice. `001_initial.sql` adds namespaced
tables; a later migration will backfill legacy results only after an explicit
operator backup and dry run. Legacy Redis result keys remain readable by old
services but are not copied into durable state automatically.

Before upgrade, stop writers, take a logical Postgres backup, record the
application SHA, and test restore in a disposable database. Rollback means
stop the new API/worker and restart the prior image against the preserved
legacy schema; do not roll back by deleting or resetting volumes. New records
created after a rollback need an explicit reconciliation plan. Expired Redis
cache data cannot be recovered.

## Runnable commands

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e '.[postgres,test]'
pytest
python -m compileall -q src tests
docker compose config
```

For the modular API use a PostgreSQL URL and a secret token:

```bash
AGENT_TRUST_API_TOKEN='local-only-secret' \
DATABASE_URL='postgresql+psycopg://agent_trust:password@localhost:5432/agent_trust' \
AGENT_TRUST_IMPORT_APP=1 uvicorn agent_trust.api.app:app --host 127.0.0.1 --port 8080
```

## Current acceptance boundary

This alpha slice provides the namespace, versioned models, provider contracts,
secure defaults, durable records/jobs, compatibility metadata, and API contract
tests. It does not claim real MCP protocol discovery, OpenAPI operation
execution, production telemetry SDKs, calibrated model confidence, universal
IAM resolution, shared SaaS isolation, automatic quarantine, or inline
enforcement. Those are roadmap gates, not documentation-only checkboxes.
