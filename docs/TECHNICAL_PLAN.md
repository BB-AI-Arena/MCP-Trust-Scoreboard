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

The original `koi` Postgres database and `postgres_data`/`redis_data` volume
names are unchanged. API/worker startup applies packaged, transactional SQL
migrations under a PostgreSQL advisory lock. `001_initial.sql` adds namespaced
tables; `002_workspace_idempotency.sql` replaces global job-key uniqueness
with `(workspace_id, idempotency_key)` uniqueness; `003_assessment_results.sql`
repairs namespaced assessment projections from existing jobs, preserving job
results and unrelated record metadata. Applied filenames are recorded in
`agent_trust_migrations`. No legacy Redis data is imported or recovered.

Before upgrade, stop writers, take a logical Postgres backup, record the
application SHA, and test restore in a disposable database. Rollback means
stop the new API/worker and restart the prior image against the preserved
legacy schema; do not roll back by deleting or resetting volumes. New records
created after a rollback need explicit reconciliation. Do not run old and new
modular workers together during migration. The old code's global idempotency
assumption is incompatible with new cross-workspace duplicate keys; prefer a
forward fix. Restore backups into a separate database and reconcile post-backup
data, never restore over live data. Expired Redis cache data cannot be recovered.

## Runnable commands

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e '.[postgres,test]'
pytest
pytest --run-integration tests/integration -v
python -m compileall -q src tests
docker compose config
```

For the modular API use a PostgreSQL URL and a secret token:

```bash
AGENT_TRUST_API_TOKEN='local-only-secret' \
DATABASE_URL='postgresql+psycopg://agent_trust:password@localhost:5432/agent_trust' \
agent-trust-api
```

## Current acceptance boundary

This alpha slice provides the namespace, versioned models, provider contracts,
secure defaults, durable records/jobs, compatibility metadata, and API contract
tests. It does not claim real MCP protocol discovery, OpenAPI operation
execution, production telemetry SDKs, calibrated model confidence, universal
IAM resolution, shared SaaS isolation, automatic quarantine, or inline
enforcement. Those are roadmap gates, not documentation-only checkboxes.

## Runtime remediation decisions (ATP-A2, ATP-A3, ATP-D1)

- New features and UI changes are paused. PR #12 merged at
  `19628da7e01603f6a35285048a86e2d7e7f9de7b`; merging did not certify release readiness.
- `Settings.from_env()` reads defaults from a dataclass instance, not slotted
  class descriptors. Uvicorn is a required runtime dependency, not a test extra.
  The unchanged `DATABASE_URL=postgresql://...` alias uses packaged psycopg.
- Enqueue and the public assessment record share one transaction. Completion,
  retry, and abandoned-job recovery synchronize the result/status atomically.
  Duplicate keys return the original job and never reset completed results.
- Job execution remains at least once. Claims use short `SKIP LOCKED` row locks;
  external analysis runs after commit. Expired lease tokens cannot complete or
  fail an attempt, including after waiting on a lock. Attempt limits apply to
  worker death as well as explicit failures; retry backoff is capped at 300s.
  Leases currently use process UTC clocks; deployments require synchronized
  clocks, and this is not a cross-region scheduler. Only assessment jobs are
  implemented; unsupported kinds fail within their retry budget.
- Readiness executes `SELECT 1` rather than merely opening a pooled connection.
- Remediate npm advisories with jsPDF 4.2.1, Vite 6.4.3, and refreshed lockfiles;
  keep all existing audit gates and test the real PDF export API and four builds.
- Manual release preparation validates the exact version/SHA, runs the full CI
  (including Docker/PostgreSQL), and only then calculates checksums. It never
  publishes. Checksums are not an SBOM, a review, or a production-readiness claim.

Runtime test details and safe upgrade procedure: [RUNTIME_VALIDATION.md](RUNTIME_VALIDATION.md).
