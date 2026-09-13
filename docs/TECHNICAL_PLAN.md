# Agent Trust Platform v2 technical plan

Status: accepted implementation baseline for `2.0.0-alpha.1` (2026-09-11).
This plan converts the existing Palo Alto/Koi demonstration suite into a
vendor-neutral local/self-hosted product without deleting its useful flows.

## Scope and decisions

Owner-selected ATP-C1 / issue #22 now implements the Windows observe-only endpoint
vertical slice on PR #21. Go user-mode sensor → strict per-device ingestion →
existing PostgreSQL evidence/correlation/job/outbox path. Migration 005 adds private
device enrollment/health/policy state; 001–004 remain intact. No kernel driver or
response adapter. Real Windows CI is required, not inferred from Linux fixtures.
Decision, scope, privacy and acceptance: [endpoint/ARCHITECTURE.md](endpoint/ARCHITECTURE.md)
and [endpoint/WINDOWS.md](endpoint/WINDOWS.md). This owner priority supersedes the
older runtime-only pause; other planned C-phase capabilities are not marked done.

Owner override (development/alpha): known third-party dependency CVEs are accepted
and hardening deferred. Scans/raw findings/SBOMs remain; findings do not block
development, reviewed merges or approved alpha preparation/publication. Scanner
execution, secrets, functional and data-integrity gates remain. Do not restart a
CVE-remediation loop. Approval is still required; alpha is not production-hardened.

Reference slice (ATP-B3, implemented in PR #19, awaiting review): separate EvidenceSource, FindingDestination
and ResponseAdapter contracts. No selected vendor priority exists, so implement
generic JSON ingestion and a configured webhook destination first. Authenticate
ingestion, normalize/redact evidence, persist it and deterministic findings with
transactional delivery jobs. Test real local endpoints, duplicates, failures and
retry persistence. No vendor stubs or enforcement claims. Keep schemas versioned
and use the existing PostgreSQL ledger; destination delivery is at least once.
The working reference path and tested limits are in [CONNECTORS.md](CONNECTORS.md).
Local HTTP/TLS fixture success is not live vendor validation; response contracts
have no registered enforcement implementation. Follow this slice with a selected
source/destination adapter using the same contracts, not a new CVE-hardening loop.

Owner-selected next source (ATP-B4): read-only CrowdStrike Falcon. Reuse registered
source/destination dispatch and the existing worker/outbox. A small typed client
allowlists OAuth token issuance, Hosts scroll/v2 details, and Alerts combined v1
(read POST). Durable page enqueue/checkpoint transactions plus a per-connection
PostgreSQL session advisory lock provide bounded resumable sync-once. Migration
004 adds a private checkpoint table, not a public record kind. Imported alerts are
vendor findings with immutable revisions; inventory remains context. Explicit
registered-agent mappings never prove causality. No response capabilities, live
compatibility claims, SDK dependency, new service or CVE-remediation work. Contract,
limits and executable acceptance: [CROWDSTRIKE.md](connectors/CROWDSTRIKE.md).

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
6. No new graph database, Kafka, cloud service or enforcement gateway is
   introduced in alpha. The owner explicitly authorized the bounded read-only
   Falcon source above, without proprietary integration breadth claims. Inline enforcement is a
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
  keep audit execution and test the real PDF export API and four builds. Dependency
  findings are now informational under the subsequent owner policy above.
- Manual release preparation validates the exact version/SHA, runs the full CI
  (including Docker/PostgreSQL), and only then calculates checksums. It never
  publishes. Checksums are not an SBOM, a review, or a production-readiness claim.

Runtime test details and safe upgrade procedure: [RUNTIME_VALIDATION.md](RUNTIME_VALIDATION.md).

## Alpha acceptance continuation (ATP-A3 / ATP-D1)

PR #15 remains open at `cbab41409d98fade11c2ccee316b7bebc1fab182` on
inspection. Work branches from that head, with a dependent PR targeting
`fix/runtime-postgres-release-gates`, not main. This records the earlier acceptance
slice; the owner override above resumes connector development.

1. Build the actual root Compose services, replacing only test resource names,
   resource limits and loopback host ports. Generate a fresh private configuration;
   never inherit operator credentials or volumes. Retain errors/traces/screenshots.
2. Repair confirmed routing, response-mapping, queue and export defects; test
   real browser submissions, rendered graphs, absence/error paths and downloaded
   PDFs. Preserve service contracts and existing unit/PostgreSQL tests. Behavior
   has no report-export feature; explicitly report that gap rather than add one.
3. Prove installed API/worker operation, container recreation with preserved
   disposable volumes, migrations 001 to 003 (twice), and separate backup restore.
4. Bind legacy interfaces to loopback, unpublish database/cache ports, generate
   random fresh-install credentials, reject placeholder platform tokens, require
   hosted opt-in even for legacy providers, and remove remote font requests.
   A Compose validator is a preflight guard, not an authentication/TLS proxy.
5. Scan every built image plus Redis, retaining all severities and real CycloneDX
   inventories. Include npm's installed build dependency closure in each frontend
   image (a conservative superset of bundled JavaScript, not exact bundle tracing).
   Upgrade patched base packages/build tooling. Replace PostgreSQL's bundled Go
   privilege helper with maintained Alpine su-exec while retaining PG15 entrypoint,
   UID and volume paths; fresh/recreation/backup/upgrade tests must pass.
6. CI adds acceptance and container-security as failing gates, preserves existing
   jobs, retains non-sensitive evidence even on failure, uses pinned Actions and
   read-only permissions. The owner's later policy accepts dependency findings
   for alpha; retain them without ignores or scanner-metadata deletion. Scanner
   execution and all non-dependency security/functional gates still block.

No schema migration beyond 003 in this slice. Legacy Redis stays a TTL-only
compatibility queue, never the durable result store. Rules-only checks and mocked
provider contracts do not verify live integrations. Linux amd64 Docker/Chromium
is the acceptance target; other platforms/browsers require separate validation.
Code completion, CI success, review, deployment and publication are distinct.
The owner has authorized the connector framework/reference integration now;
dependency CVEs do not delay it. Live vendor validation remains a separate claim.
