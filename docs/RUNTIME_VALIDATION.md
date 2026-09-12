# Runtime and PostgreSQL validation

This is a regression gate, not new product functionality. See
[IMPLEMENTATION_STATUS.md](IMPLEMENTATION_STATUS.md) for actual results and SHAs.
The continuation adds [full Compose/browser and image acceptance](ALPHA_ACCEPTANCE.md)
without replacing any of the tests below.

## Run the gates

Use a Linux host with Docker Engine, Python 3.11+ and Node 20/22. Docker Desktop
and remote Docker daemons are not validated: the tests reach private bridge IPs
from the Docker host. Install dependencies in an isolated virtual environment.

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e '.[postgres,test]' pip-audit
.venv/bin/pytest -q -ra
.venv/bin/pytest --run-integration tests/integration -v
.venv/bin/python -m compileall -q src tests
.venv/bin/python -m pip check
.venv/bin/python -m pip_audit
docker compose config --quiet
for d in app1-blast-radius/frontend app2-behavior-baseline/frontend app3-code-provenance/frontend app4-mcp-scorecard/frontend; do
  (cd "$d" && npm ci --ignore-scripts && node --test ../../tests/frontend/pdf-export.test.cjs && npm run build) || exit 1
  python3 scripts/dependency_audit.py npm --directory "$d" --output "evidence/dependencies/$(dirname "$d")" || exit 1
done
```

The short pytest command explicitly skips Docker tests. It is **not** the full
gate. CI runs the second command in a mandatory `runtime-postgres` job; missing
Docker, startup errors, or unreachable PostgreSQL fail rather than skip.

The integration fixtures build `Dockerfile.platform` with the runtime extras
only (no editable install or test packages inside that image), pull the official
`postgres:15-alpine` image, freeze its image ID for the session, and create uniquely
labeled private networks/containers. Each case gets a fresh database. PostgreSQL
data lives in that disposable container's writable layer, surviving restart.
An unused image-declared volume is covered by tmpfs; no host volumes are mounted
or deleted. API/worker containers have no host Docker socket, source mounts, or
provider credentials. Tests never connect to the operator's `DATABASE_URL`.
Only the test runner talks to Docker. Fixture teardown removes only its exact
created containers/network/image tag. No `compose down -v`, volume pruning, or
changes to existing stacks are performed. Killed test runners may leave labeled
resources: inspect their exact IDs before removing them; never prune globally.

## What is exercised

- Concrete typed configuration defaults and all environment overrides; missing
  tokens fail closed. Uvicorn is installed as a runtime requirement.
- Actual image CMD and both installed CLI entrypoints; API and worker start
  against fresh PostgreSQL, including serialized migration startup.
- Real authenticated HTTP: missing/wrong bearer token (401), insufficient
  assessment scope (403), server-bound workspace, cross-workspace job lookup
  (404), concurrent idempotent submission (202).
- A real worker finds `execution_authority` in the fixture `eval(user)` **without
  executing it**; completed jobs and assessment listings carry the same result.
- Restart API, worker and PostgreSQL; retrieve the same stored result and retry
  the same submission without resetting it. No Redis/cache service is present.
- Database outage makes readiness fail (503); restoration returns it to ready.
- Upgrade the old schema with retained records/results; backfill previously
  stuck assessment projections; repeated/concurrent migration calls are safe.
- Six concurrent equal keys converge to one job; identical keys in different
  workspaces are independent. Locked rows are skipped by independent claimers.
- An actual claimed worker subprocess is killed. Its lease expires; another
  worker may recover it only within the attempt budget. Stale completion/failure
  is rejected, including when the writer waited on a row lock until expiry.
- Injected projection-write failure rolls back enqueue/completion together.
  Provider analysis happens outside the claim transaction; retry delay/limits
  apply to unsupported kinds. Unsupported kinds are not implemented engines.
- All four real locked jsPDF copies serialize text/image/multipage PDFs; four
  Vite builds verify imports. This is API compatibility coverage, not browser
  screenshot or download-dialog end-to-end coverage.

## Upgrade and rollback

1. Record the deployed SHA/image and stop **modular** API/worker writers during a
   maintenance window. Keep all existing database/environment/volume names.
2. Use `pg_dump --format=custom --file=agent-trust-before-runtime.dump` with your
   existing PG environment/credential mechanism (never commit the dump or put
   a password in shell history). Test `pg_restore --dbname=<disposable-database>`
   on a separate database. This procedure is guidance; no user backup was taken
   by this run and no user database was upgraded.
3. Start the new API and worker against the preserved database. Startup applies
   `001`, `002`, `003` atomically under an advisory lock and records them in
   `agent_trust_migrations`. This requires DDL permission. Stop if migration
   fails; do not erase data or mark migrations manually to bypass an error.
4. Check readiness, submit an authenticated disposable assessment, and check
   both `/api/v1/jobs/{id}` and `/api/v1/assessments` after worker execution.
5. Prefer a forward fix. Rolling back to the previous modular code reintroduces
   startup/result bugs and its global key assumption. Keep the new services
   stopped if rollback is needed; restore a pre-upgrade backup into a **separate**
   database and reconcile post-backup results before changing the configured
   database. Do not drop tables, restore over live data, or delete volumes.

Legacy Redis key names and TTLs are unchanged. Expired Redis results cannot be
recovered. These original integration tests do not migrate legacy Redis history
or prove hosted-provider compatibility, production egress safety,
retention enforcement, or release-wide security readiness.

## Release remains a separate decision

Manual release preparation runs exact-SHA validation and the full CI before
generating source checksums. The script refuses dirty/mismatched sources and
explicitly records `release_ready: false`. No publishing job was added. SBOM,
container scanning, complete legacy runtime/browser acceptance, and maintainer
release review remain gates. The continuation now implements scans/SBOM and full
stack acceptance. Dependency findings are now informational under explicit owner
development/alpha risk acceptance; hardening is deferred. Scanner execution,
inventory, runtime/data-integrity and secret checks still block. Retain findings;
passing tests is not stable-release certification or publication approval.
