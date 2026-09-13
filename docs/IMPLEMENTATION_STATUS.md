# Implementation status

## Current reconciliation — 2026-09-13

The authoritative current heads, CI, migration/issue matrix, merge order and
actual-main validation instructions are in [STACK_RECONCILIATION.md](STACK_RECONCILIATION.md).
PR #24's implementation head `e814ba207d243b5e0ac10e784fbf0ec102f7e205` passes
platform, portable Go, native Windows, foreground and real SCM acceptance.
[Windows run 34738201185](https://github.com/BB-AI-Arena/MCP-Trust-Scoreboard/actions/runs/34738201185)
clears the service enrollment blocker; the report distinguishes test-merge source,
foreground fixture coverage and degraded service-account collector visibility.
New feature development is stopped. No PR merged, issue closed or release published.
**NOT READY FOR PUBLICATION — awaiting maintainer merge and merged-main validation.**
GitHub Project status unverified: active authentication lacks read:project.

## Historical Windows endpoint vertical-slice handoffs

The remaining sections preserve prior source-specific results, counts and failed
runs. Their next-step/blocker and Project statements are historical, not a current
Project verification or an instruction to restart product work.

Service follow-up source: this branch adds SCM virtual-account acceptance after
PR #23. GitHub Project status unverified: active authentication lacks read:project.

Starting SHA `9aa41c1bdbd3c81c6bdf4ba5f33bf1035d18de43`. Rechecked GitHub and clean
checkout: default main; #15/#16/#17/#19/#21 OPEN with unchanged heads; fetched safely.
Branch `feat/windows-endpoint-sensor`, dependent base `feat/crowdstrike-evidence-source`
(PR #21). No merging, deployment, publication, tags, credential changes or operator
database/volume access. Platform stays unreleased **2.0.0-alpha.1**; sensor 0.1.0.
Accepted dependency CVEs remain informational; scans/SBOMs/secret gates preserved.

Implemented native Go Windows runtime/SCM handler, Toolhelp/TCP/registry/scoped
file metadata and AI/MCP discovery, DPAPI identity, bounded persistent spool,
device enrollment/revocation and typed API. Existing PostgreSQL worker transaction
persists evidence, bounded explainable correlations, findings and webhook jobs.
Migration 005 adds one private endpoint table; 001–004 unchanged. See
[endpoint/WINDOWS.md](endpoint/WINDOWS.md) for setup, privacy, limits and rollback.

Baseline `.venv/bin/pytest -o addopts= -q -ra`: **93 passed / 32 gated skips**, 25.61s.
Initial endpoint `.venv/bin/pytest tests/test_endpoint.py -v --tb=short`: **10 passed**.
Initial `.venv/bin/pytest --run-integration tests/integration/test_endpoint_runtime.py -v --tb=short`:
**1 passed**, 10.35s, real PostgreSQL concurrent idempotency/correlation and local TLS
receiver/retry. Existing generic connector tests passed (21). Go 1.26.8 portable
spool/privacy/transport tests: **4 passed**. Windows x64 executable/tests cross-compile.
Full local `.venv/bin/pytest -o addopts= -q -ra`: **103 passed / 33 gated skips**, 27.25s.
`.venv/bin/pytest --run-integration tests/integration -v --tb=short --junitxml=evidence/endpoint-runtime/junit.xml`:
**19 passed**, 207.06s, zero skips; existing 18 retained. Compileall/diff checks passed.
Initial implementation commit **bebcaa09d8705befa83b6fa84923276591f8b2de** is pushed in
[PR #23](https://github.com/BB-AI-Arena/MCP-Trust-Scoreboard/pull/23), base PR #21.
[Existing CI 34679332603](https://github.com/BB-AI-Arena/MCP-Trust-Scoreboard/actions/runs/34679332603)
passed all ten jobs. [Windows CI 34679332513](https://github.com/BB-AI-Arena/MCP-Trust-Scoreboard/actions/runs/34679332513)
and its PR run 34679354524 passed. Downloaded artifact **10293057019** confirms:
Windows Server 2022 x64 build **20348**, runner **20260907.297.1**; six native tests,
real foreground enrollment/process/TCP/file/registry/OS collection and full pipeline;
six offline events recovered, identical replay deduplicated, five findings accepted
in six receiver attempts, zero blocking actions. Discovery and behavioral test
fixtures remain explicitly synthetic, not live Cursor/MCP/vendor validation.
Executable checksum and exact commands: [endpoint/WINDOWS.md](endpoint/WINDOWS.md).

Follow-up adds nonempty-directory/remote-hash guards, stronger TLS/scope tests and
safer Windows harness cleanup/helper timing. Final ending head and its separate
CI result must be read back on PR #23; earlier passing runs are not substituted.
The final contract clarification labels polling lifecycle observations and adds
server-derived AI approval status; older unlabeled spool records retain canonical
replay compatibility. Dedicated tests cover both, without changing migration 005.
Clarification verification: `.venv/bin/pytest -o addopts= -q -ra` **104 passed / 33
gated skips**, 28.78s; focused real PostgreSQL endpoint test **1 passed**, 11.03s;
Go portable tests **5 passed**, Windows executable cross-build and compileall/diff
checks passed. Pre-clarification head `b94f8f628d534fe6bca12eebb10b94296bd7ff2d`
passed all ten CI jobs (34679626574/34679628953) and the Windows workflow
(34679626578/34679628965). Final-head readback is recorded separately on PR #23.
Head `8dc316da700a8a1512f3d0f563fb47e57fcc629f` passed the ten-job CI run
34679870729 and Windows PR run 34679873211, but Windows push run **34679870733
failed** its replay-count assertion. Logs show telemetry arriving between offset
pages: that live listing cannot serve as an exact cardinality snapshot. The harness
now counts persisted events in one PostgreSQL statement, retaining multiplicity
(not deduplicating away real duplicate records). A regression oracle test injects
a genuine duplicate and verifies it remains visible across more than two pages.
The raw failed-run logs remain retained. A new final-head Windows run is required;
the passing sibling run does not erase this failure.
Snapshot-check repair: `.venv/bin/pytest -o addopts= -q -ra` **105 passed / 33
explicitly gated skips**, 30.54s; `.venv/bin/python -m compileall -q src tests
scripts/windows_acceptance.py` and `git diff --check` passed. No production code,
gate or assertion threshold changed for this harness repair.
All changes are in review, not merged/approved/published. No GitHub operations failed.

## Verified implementation-head handoff

Implementation ending SHA **`1a5eefa8bdf7d3d9ee2c15156270ec9bc90c64bf`**;
subsequent handoff-only documentation commits do not change the implementation.
[Push CI 34680187103](https://github.com/BB-AI-Arena/MCP-Trust-Scoreboard/actions/runs/34680187103)
and PR CI **34680189468** passed all ten existing jobs. This includes the real
PostgreSQL/runtime suite (**19 tests, zero failures/skips**, retained JUnit), four
frontend builds, full-stack/browser/report/persistence acceptance, deployment
checks, secret protections, dependency scans and container evidence generation.
[Windows push 34680187120](https://github.com/BB-AI-Arena/MCP-Trust-Scoreboard/actions/runs/34680187120)
and PR Windows **34680189435** passed. Downloaded artifact **10293223676**:
Windows Server 2022 x64 build **20348**, runner **20260907.297.1**, **eight native
tests**, full foreground pipeline; **10 offline events recovered**, replay count
**exactly one** in PostgreSQL, **five accepted findings / six receiver attempts**,
**zero blocking actions**. Sensor executable SHA-256:
`3c22332a69841751a1ee091410a4a13df3df88dbd53b2d3eb8d422a0481c9171`.

Downloaded container artifact **10293112740**: **41 checksums verified**, source
matches the implementation head, **13 service identities / 12 distinct images**,
scans completed with dependency findings still present. Raw reports and CycloneDX
SBOMs retained; findings remain accepted/informational, not described as clean.
Runtime artifact **10293478318** and dependency artifact **10293957572** are retained
on the same run. Actual final branch/PR head and its CI readback are also recorded
on [PR #23](https://github.com/BB-AI-Arena/MCP-Trust-Scoreboard/pull/23); no inherited
pass or prior SHA is substituted for that final check.

Rechecked dependency stack: #15/#16/#17/#19/#21 still OPEN; base remains PR #21,
not main. [Issue #22](https://github.com/BB-AI-Arena/MCP-Trust-Scoreboard/issues/22)
and its dedicated Project item remain In review. Platform **2.0.0-alpha.1 remains
unreleased**. No merge, deployment, tag, publication, credential change or operator
database/volume operation occurred. Backup/rollback: preserve additive migration
005 and records, stop sensor ingestion and reconcile pending endpoint jobs before
rolling code back; do not delete data/volumes. Metadata paths/SIDs remain sensitive;
private ACLs, scoped roots and retention/reconciliation are operator responsibilities.

Known limitations: polling misses short-lived activity; no file-writer association,
DNS/UDP, payloads, source-code read proof, complete inventory, learned baseline,
production signing/updater or enforcement. Dedicated-account SCM deployment was
unvalidated at this historical #23 handoff; #24 now supplies the scoped acceptance
linked above.
Issue #22 and [the private Project](https://github.com/users/BB-AI-Arena/projects/1)
remain In review, not Done. Next concrete follow-up: dedicated least-privilege SCM
account enrollment/start/recovery acceptance and a Windows client-OS test matrix;
not dependency hardening or prevention.

## Prior slice history — read-only CrowdStrike source

## Scope, source and review state

Owner priority: useful product development. Known third-party dependency CVEs are
**Accepted for development/alpha; hardening deferred.** Scans/raw reports/SBOMs and
scanner-execution/secret/functional/data-integrity checks remain. No dependency
remediation, package/base-image changes or unrelated release prerequisites.

Starting SHA: `e6bd77f93f7abd1aa2513a92aa146a9ecc5b5e8b` (PR #19).
GitHub recheck: #15, #16, #17 and #19 remain OPEN/unmerged at their reported heads;
#19's exact-head run 34672162831 remains successful. Checkout was clean, fetch
succeeded, no published tags/releases found. Canonical version stays **unreleased
2.0.0-alpha.1**. Prior evidence: [PR19_CONNECTOR_HISTORY.md](PR19_CONNECTOR_HISTORY.md).

Branch `feat/crowdstrike-evidence-source`, base `feat/json-webhook-connectors`
(PR #19), not main. Dependency order #15 → #16 → #17 → #19 → this feature.
Tracking: [ATP-B4 #20](https://github.com/BB-AI-Arena/MCP-Trust-Scoreboard/issues/20),
[dedicated private project](https://github.com/users/BB-AI-Arena/projects/1).
[Feature PR #21](https://github.com/BB-AI-Arena/MCP-Trust-Scoreboard/pull/21) is OPEN,
base `feat/json-webhook-connectors`, In review, not Done. Initial implementation
SHA `bf175ffdf16806a56ffbab5f2d240f1f82ee55f9`; exact-source CI
[34677600114](https://github.com/BB-AI-Arena/MCP-Trust-Scoreboard/actions/runs/34677600114)
passed all ten jobs. Its dependent-PR run
[34677676274](https://github.com/BB-AI-Arena/MCP-Trust-Scoreboard/actions/runs/34677676274)
also passed. The subsequent tested follow-up exposes committed ingestion-job IDs
for following persistence/delivery through the existing jobs API. The actual
ending head and its separate CI readback are recorded in the PR handoff (not
inferred from these earlier runs); no merge or publication is automatic.

## Implemented

- Operator `agent-trust-falcon check`, `sync-once`, and explicitly authorized
  optional `live-smoke`; private environment credentials, no credentials in jobs,
  checkpoints, findings or output.
- Small typed client: OAuth token issuance, Hosts READ scroll/v2 details,
  Alerts READ combined v1 (a read POST). Commercial us-1/us-2/eu-1; TLS/address
  pinning; bounded retries/bodies; token expiry/401 refresh; 403/error separation;
  Retry-After/vendor retry guidance enforced across operations and resumptions.
- Registered source/destination dispatch reuses generic JSON, the modular worker,
  PostgreSQL ledger and webhook. No new destination, broker, service or response
  adapter. Generic immutable-event 409 and assessment behavior retained.
- Host inventory context; vendor-origin alert findings, not keyword rules.
  Original IDs/timestamps/severity/status, logical IDs and immutable revisions,
  minimal metadata/text digests. Explicit registered-agent mappings or unmatched
  vendor context; no fabricated AI identity or causality.
- Additive migration 004 private checkpoints; per-connection PostgreSQL session
  advisory lock, no transaction held during vendor calls. Page enqueue/checkpoint
  atomicity, expired-cursor rewind, fixed-window replay and revision deduplication.
- Real local TLS fixture and installed collector/API/worker/PostgreSQL/receiver
  tests. Existing CI preserved; feature-base PRs trigger CI and runtime JUnit is
  retained. No frontend redesign or new unrelated release gate.

Official operations/scopes, commands, field mapping and limits:
[connectors/CROWDSTRIKE.md](connectors/CROWDSTRIKE.md). No containment, remote
commands, alert mutation, policy changes or enforcement. Authentication to Falcon
does not make vendor conclusions objectively verified.

## Commands and measured validation

- Baseline `.venv/bin/pytest -o addopts= -q -ra`: **75 passed, 28 explicitly skipped**
  integration/browser tests (separate mandatory CI suites).
- Feature `.venv/bin/pytest -o addopts= -q -ra`: **93 passed, 32 explicitly skipped**,
  25.18s on the committed-job-ID follow-up; two inherited Starlette warnings,
  not suppressed.
- `.venv/bin/pytest --run-integration tests/integration -v --tb=short --junitxml=evidence/falcon-runtime/junit.xml`:
  **18 passed, zero skipped**, 201.25s. Original 14 retained plus four Falcon tests:
  real TLS/installed runtime delivery and restart; page rollback/revisions/mapping;
  rate-limit/checkpoint recovery; migration 003→004/repeat preservation.
- Initial focused integration run: **4 passed**, 58.67s.
- Follow-up `.venv/bin/pytest --run-integration tests/integration/test_falcon_runtime.py -v --tb=short`:
  **4 passed**, 58.83s, including durable lookup of the returned job IDs.
- `.venv/bin/python -m compileall -q src tests`; `git diff --check`: passed.
- `.venv/bin/python -m pip install --no-deps --no-build-isolation -e .`: failed
  because this local environment lacks `setuptools.build_meta`. Normal isolated
  `.venv/bin/python -m pip install --no-deps -e .` and
  `.venv/bin/agent-trust-falcon --help`: passed; no application dependencies changed.
- Exact implementation-source CI 34677600114: **all ten jobs passed**. Downloaded
  JUnit confirms **18 runtime/PostgreSQL tests** and **14 full-stack/browser/report/
  persistence/backup-restore tests**, no skips/failures/errors. Four frontend
  builds/tests, Compose validation, Python/version checks and security jobs passed.

Retained evidence was downloaded with
`gh run download 34677600114 --repo BB-AI-Arena/MCP-Trust-Scoreboard --dir evidence/falcon-ci-34677600114`.
Artifact IDs: runtime **10292499026**, acceptance **10292354660**, dependencies
**10292484132**, container security **10292439475** (14-day CI retention).
All **41 container evidence checksums verified**. Trivy 0.74.0 completed at
2026-09-12T06:15:45Z using database updated 2026-09-12T01:00:32Z; 13 service
identities / 12 distinct images with CycloneDX inventories and unchanged full
reports. **Findings remain present**: each of six Python image identities has
181 package/advisory matches, including 56 HIGH/CRITICAL matches, not unique CVE
counts. No dependency/image changes or suppressions. Python/npm audits completed
with no reported findings; the unpublished first-party application is explicitly
not in the PyPI audit database. This is not a claim of vulnerability-free software.

No credentials were supplied privately for live validation: **live CrowdStrike
smoke was not run and remains pending**, not a development blocker. Tests use
synthetic data/credentials, real local TLS and named disposable Docker resources.
Only vendor-origin/trust configuration and synthetic protocol failures are fixtures;
application services are real. No operator database, volume or live account used.

## Upgrade, rollback and limits

004 adds one private table; 001–003 and existing records are preserved. Checkpoints
cannot be written via generic record APIs. Back up/test restore separately, stop
old workers before enqueueing Falcon records. Rollback: stop collection, drain/
reconcile connector jobs and restore preceding code while preserving the additive
table/records. Never delete user volumes or restore over live data. Collector
locks require direct PostgreSQL or session pooling, not transaction-mode pooling.

Bounded live-data reads are not snapshots/complete history. Initial backfill defaults
to 24h (max 30d); subsequent windows overlap five minutes. Late indexing/retention/
hidden or removed records can require explicit replay. No automatic retention,
scheduler, source UI, cross-account impersonation or current-alert projection.
Metadata/hashes can remain sensitive. Revisions may deliver out of order.

Webhooks remain at least once with stable retry IDs; receivers must deduplicate
and reconcile revisions. Acceptance is not remediation. Pending jobs use existing
destination configuration: pause/reconcile before changing URL or credentials.
Known dependency risk remains visible in [KNOWN_SECURITY_ISSUES.md](KNOWN_SECURITY_ISSUES.md).
Alpha is not production-hardened or enterprise-ready. Approval, merge, deployment
and publication are separate. Nothing merged/deployed/tagged/published; no operator
credentials/data/volumes changed.

Next: maintainer review of the dependency stack and optional purpose-authorized
bounded Falcon live smoke; do not broaden scopes or restart dependency hardening.
