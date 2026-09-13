# Implementation status

Updated: 2026-09-11 (America/Chicago). New features and UI work are paused.

## Current handoff

- Repository: `BB-AI-Arena/MCP-Trust-Scoreboard`.
- Starting main SHA: `31887614cf49dc93c31994945e107ab8339ca3ff` (clean checkout).
- Ending implementation SHA: `7ad048a77f05b6faff22e4e8d5bcdc0e39d4df53`.
  Subsequent handoff-only commits do not change the tested implementation.
- Remotely validated handoff SHA: `5b175af1f94246bea604d5abf2b2ea3510c1eb9b`.
- Branch: `fix/runtime-postgres-release-gates`, based on `main`.
- **PR #12 is already merged**, at `19628da7e01603f6a35285048a86e2d7e7f9de7b`
  on 2026-09-12 00:19:57 UTC. Prior text saying it was open was stale.
  README/license PRs #13/#14 are also merged. Their appearance and MIT terms
  are unchanged by this repair.
- Proposed application version remains `2.0.0-alpha.1` (`2.0.0a1` Python).
- **Release remains blocked.** Local checks, remote CI, and exact-SHA manual
  preparation pass; review and broader release acceptance remain gates. Phase A
  and later milestones are not complete. Nothing was merged or published in
  this repair run; no tags, GitHub release, packages, or images were published.

## Actually repaired

- `Settings.from_env()` now uses concrete dataclass-instance defaults rather
  than slotted class descriptors. Tests cover unset/minimal/explicit/invalid
  environments; missing API tokens still fail closed.
- Uvicorn is a required runtime dependency. The built image runs its unchanged
  CMD, `agent-trust-api`, and `agent-trust-worker` without test extras.
  Legacy `postgresql://` URLs select the packaged psycopg driver.
- Packaged SQL migrations run transactionally under a PostgreSQL advisory
  lock, including simultaneous API/worker startup. Migration 002 makes
  idempotency workspace-scoped; 003 repairs old assessment projections from
  existing durable jobs while retaining original results/other record metadata.
- Enqueue/projection and terminal job/result/projection writes are atomic.
  Concurrent equal keys return one original job without resetting its result.
  Expired workers are fenced, including after waiting on row locks. Worker
  deaths consume bounded attempts; retry backoff is capped.
- Readiness actually queries PostgreSQL and returns 503 during an outage.
- jsPDF 4.2.1, Vite 6.4.3, and patched transitive lockfile resolutions remove
  all reported npm advisories across four apps. No UI/source design changes,
  suppressed advisories, audit exceptions, or lowered thresholds.
- CI adds actual Docker/PostgreSQL tests and PDF export API tests. Manual
  release preparation runs full exact-SHA CI before source checksums; its
  script refuses dirty/mismatched sources and records `release_ready: false`.
  Existing checkout Action SHA was verified against its official v4.2.2 tag.

## Baseline and development failures (not final results)

- `Settings.from_env()` failed with `member_descriptor ... strip`.
- The prior locally built platform image failed to start: Uvicorn was absent.
- Existing `.venv/bin/pytest -q` passed 16 tests despite these startup defects.
- Each frontend initially reported 11 advisories: 2 low, 4 moderate, 4 high,
  1 critical. The inherited CI security job failed at that audit.
- Initial new tests exposed harness issues (internal-network port publishing,
  log capture, restart address changes, a bad PNG fixture CRC) and PostgreSQL
  driver semantics (literal SQL percent formatting and INSERT rowcount).
  These were corrected and the full integration suite rerun successfully;
  the earlier failed/interrupted runs are not counted as acceptance evidence.

## Final local verification

Commands run from the repository unless a frontend directory is specified:

| Command | Result |
| --- | --- |
| `.venv/bin/python -m pip install -e '.[postgres,test]' pip-audit` | Installed local test/audit environment |
| `.venv/bin/pytest -o addopts= -q -ra` | **29 passed**, 13 integration tests explicitly skipped in this fast run |
| `.venv/bin/pytest --run-integration tests/integration -v --tb=short -x` | **13 passed**, zero skipped, 129.35s |
| `.venv/bin/python -m compileall -q src tests` | Passed |
| `.venv/bin/python -m pip check` | Passed |
| `.venv/bin/python -m pip_audit` | No known third-party vulnerabilities; local unpublished editable project not auditable on PyPI |
| `npm ci --ignore-scripts && npm audit --audit-level=high` in each of the four frontend directories | Passed, **0 vulnerabilities in each** |
| `node --test ../../tests/frontend/pdf-export.test.cjs && npm run build` in each frontend | Passed, 1 PDF API test per app and all four production builds |
| `docker compose config --quiet` | Passed (configuration validation, not a full legacy runtime test) |
| `git diff --check` and existing committed credential-pattern check | Passed |
| Workflow YAML parsed with system Python/PyYAML | Passed syntax parsing; remote Actions remains authoritative |
| `.venv/bin/python scripts/prepare_release.py --version 2.0.0-alpha.1 --sha 7ad048a77f05b6faff22e4e8d5bcdc0e39d4df53 --output <temporary-directory>/manifest.json` | Passed exact clean-source validation; local unapproved checksums only |

Warnings remain visible: Starlette/TestClient deprecations, Recharts 2 end of
maintenance notice, and large-bundle warnings for behavior/artifact frontends.
No warnings were suppressed or size thresholds relaxed. The frontend check
tests the real PDF library API, not a browser download-dialog flow.

### Real end-to-end evidence

The test builds the actual platform wheel/image, starts PostgreSQL 15 plus API
and worker with only the two required environment values, submits an
authenticated assessment (202), and sees a real rules-only worker result in
both the durable job and assessment listing. It restarts all three containers,
retrieves the same result, and resubmits the same key without changing terminal
state. No Redis service, hosted key, or submitted-code execution is used.

Additional PostgreSQL cases exercise old-schema upgrade, concurrent migrations,
six simultaneous equal keys, separate workspaces, seven independent claims
past a held row lock, atomic rollback fault injection, a killed worker process,
lease expiry/recovery/attempt limits, lock-wait expiry, retry backoff, and no
open claim transaction during analysis. Auth tests cover 401/403/404 boundaries.
The internal **test** network is isolated; this is not certification of the
production stack's egress controls.

## Migration, rollback, and remaining risks

No user database, deployment, or volume was modified. Only test-created
containers, private networks and unique image tags were removed; their dummy
data is intentionally disposable. Existing volumes and database/environment
names remain unchanged. No legacy Redis data is imported or recovered.

Before deployment, stop modular writers, take a PostgreSQL backup and test a
restore separately. Startup requires DDL privileges and applies migrations
001–003. Do not mix old/new workers. Old code assumes global idempotency and
has the fixed startup/result defects; prefer a forward fix. If reverting,
preserve current data, restore the pre-upgrade backup into a separate database,
and reconcile new results before switching. Never delete/reset volumes.
See [RUNTIME_VALIDATION.md](RUNTIME_VALIDATION.md) for commands and constraints.

Working and tested here: rules-only authenticated durable assessment lifecycle,
workspace/scoped access, real PostgreSQL startup/migration/recovery, legacy
route contracts, four frontend builds, PDF library exports.
Still demo/experimental: seeded behavior, stylistic artifact-origin guesses.
Still unsupported/unverified: MCP/OpenAPI collectors, real behavior baselines/
SDKs, inline enforcement, live hosted providers, proprietary integrations,
shared SaaS isolation, production egress/retention hardening. Only assessment
jobs are implemented; unsupported kinds retry/fail, not successful engines.
PostgreSQL 15/Linux Docker was tested; Desktop/remote Docker and other database
majors were not. No container vulnerability scan, SBOM generation, full legacy
Compose/browser acceptance, or live-user backup/restore was performed.
Those release-wide gaps are not replaced by a green checksum manifest.

## GitHub tracking and next task

- Merged foundation: https://github.com/BB-AI-Arena/MCP-Trust-Scoreboard/pull/12
- Phase A epic (reopened because acceptance is incomplete):
  https://github.com/BB-AI-Arena/MCP-Trust-Scoreboard/issues/11
- Related open work: [ATP-A2 #2](https://github.com/BB-AI-Arena/MCP-Trust-Scoreboard/issues/2),
  [ATP-A3 #3](https://github.com/BB-AI-Arena/MCP-Trust-Scoreboard/issues/3),
  [ATP-D1 #8](https://github.com/BB-AI-Arena/MCP-Trust-Scoreboard/issues/8).
- Existing private project: https://github.com/users/BB-AI-Arena/projects/1
  PR #12 is Done; the epic is Blocked rather than implicitly complete.
- Repair PR: https://github.com/BB-AI-Arena/MCP-Trust-Scoreboard/pull/15
  **Open / In review**, head `fix/runtime-postgres-release-gates`, base `main`.
  Branch: https://github.com/BB-AI-Arena/MCP-Trust-Scoreboard/tree/fix/runtime-postgres-release-gates
- `git push -u origin fix/runtime-postgres-release-gates`: passed; remote head
  and PR base/head were read back. Main remains at the starting SHA. Related
  issue comments, reopened epic, and board mutations were also read back.
- [Push CI](https://github.com/BB-AI-Arena/MCP-Trust-Scoreboard/actions/runs/34667430426)
  and [PR CI](https://github.com/BB-AI-Arena/MCP-Trust-Scoreboard/actions/runs/34667466073):
  **all eight jobs passed** at `5b175af1f94246bea604d5abf2b2ea3510c1eb9b`.
  The remote runtime job independently reports **13 passed**, no skips.
- `gh workflow run release-prepare.yml --repo BB-AI-Arena/MCP-Trust-Scoreboard --ref fix/runtime-postgres-release-gates -f version=2.0.0-alpha.1 -f source_sha=5b175af1f94246bea604d5abf2b2ea3510c1eb9b`:
  [manual preparation](https://github.com/BB-AI-Arena/MCP-Trust-Scoreboard/actions/runs/34667511352)
  **passed**, including exact-SHA validation, all eight reusable CI jobs and
  checksum preparation. The manifest was generated locally on that runner;
  it is not a published release, SBOM, uploaded artifact, or approval.
- No failed/pending GitHub mutations, permission requests, or access-scope
  changes. PR review is pending. Handoff-only tip commits can retrigger CI;
  current results are visible on the PR without rewriting the exact tested SHA
  recorded above. No merge/publication was requested by these workflows.

Next dependency-ready task: review this runtime repair with its passing CI, then
complete ATP-A3's full legacy runtime/browser acceptance and ATP-D1's
container-scan/SBOM/release gates. Keep new features/UI work paused.
