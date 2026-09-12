# Implementation status

## Owner policy change — development/alpha

Known third-party dependency CVEs are **Accepted for development/alpha; hardening
deferred.** This supersedes earlier zero-HIGH/CRITICAL gate instructions. Do not
restart the container-hardening loop. Alpha is not production-hardened.

Dependency scans/raw reports/SBOMs remain; findings are informational. Scanner
execution, inventory, build, runtime, migration, data-integrity and committed-secret
failures still block. Review/approval, merge, deployment and publication remain
separate states; none are automatic.

Starting SHA: `6f9cdb8d8aac35b5647288200ecff16f31183fab`. PR #15 and #16 were
rechecked and remain open/unmerged at their previously reported heads. Policy
branch `chore/alpha-dependency-risk-policy` depends on `test/alpha-release-acceptance`
(PR #16), not main. Target remains unreleased `2.0.0-alpha.1`.

The interrupted image experiment is preserved locally on
`fix/python-runtime-images`, commit `3e2eb28`; no experimental Dockerfile changes
are carried into this policy/product branch. Its 54 unit tests passed; its full
image experiment was interrupted (exit 130), not accepted. Test-owned disposable
resources were removed after exact ownership checks; no user volumes/data changed.

Historical full acceptance (71 passing tests and nine passing CI jobs; old
vulnerability policy failed) is preserved in [PR16_ACCEPTANCE_HISTORY.md](PR16_ACCEPTANCE_HISTORY.md).
The current [known-risk register](KNOWN_SECURITY_ISSUES.md) retains all 181 distinct
advisory/package/version/severity rows across 12 images/13 services from verified
artifact 10290422302, not just high/critical findings. Raw reports remain unchanged.

## Policy slice: implemented, CI passed, awaiting review

[PR #17](https://github.com/BB-AI-Arena/MCP-Trust-Scoreboard/pull/17), head
`886560bb801be9c2d2a49627ea19d1ad3c5eee9d`, base
`test/alpha-release-acceptance`. [Exact-head CI](https://github.com/BB-AI-Arena/MCP-Trust-Scoreboard/actions/runs/34671404252)
passed all ten jobs. Container artifact `10290464773` reports
`scan_completed: true`, `findings_present: true`: this is **not a clean scan**.
Affected Python images still report 53 HIGH / 3 CRITICAL matches each; those are
package matches, not unique CVEs. Full findings and CycloneDX inventories remain
available in CI. No image composition changes were included.

Policy commands/results:

- `.venv/bin/pytest -o addopts= -q -ra`: 53 passed, 27 explicit integration/browser
  skips locally; those suites passed separately in mandatory CI.
- `.venv/bin/python scripts/dependency_audit.py python --output evidence/dependency-policy-python`:
  completed; zero known third-party findings, unpublished editable self-package
  explicitly disclosed as unauditable.
- `.venv/bin/python -m compileall -q src tests scripts`; `git diff --check`: passed.

## Connector slice: implemented, local tests passed, CI pending

Branch `feat/json-webhook-connectors` starts at policy head `886560bb801be9c2d2a49627ea19d1ad3c5eee9d`;
its review base is `chore/alpha-dependency-risk-policy` (PR #17), not main. PRs
#15/#16 remain open at their verified heads. Tracking:
[ATP-B3 #18](https://github.com/BB-AI-Arena/MCP-Trust-Scoreboard/issues/18),
[private project](https://github.com/users/BB-AI-Arena/projects/1), In review, not Done.

Implemented shared source/destination/response contracts and a working generic
JSON → normalization → PostgreSQL evidence/finding → webhook path. The existing
worker handles ingestion, delivery and assessment jobs. Evidence/findings/delivery
enqueue/completion share one fenced transaction; delivery happens outside it.
Duplicate events reuse a job; conflicting content returns 409. Destination
failures retry boundedly with a stable delivery ID. Raw content is discarded before
enqueueing. Workspace/collector are authenticated server context; reported agents
and evidence remain claims, not verified identities. No priority vendor integration
was selected; no vendor stubs or live-provider claims were added.

Local commands/results on the implemented connector tree:

- `.venv/bin/pytest -o addopts= -q -ra`: **74 passed, 28 explicit integration/browser
  skips**, two inherited Starlette warnings (not suppressed).
- `.venv/bin/pytest --run-integration tests/integration -v --tb=short`: **14 passed,
  zero skipped** in 144.27 seconds: original 13 runtime/PostgreSQL tests retained,
  plus installed API/worker JSON-to-TLS-webhook, untrusted-certificate rejection,
  failed delivery/retry across worker restart and persisted retrieval.
- `.venv/bin/python -m compileall -q src tests scripts examples`; `git diff --check`:
  passed. Local example receiver smoke: two real POSTs returned 204 with the same
  delivery ID deduplicated. Example deduplication is in-memory/demo only.
- Existing frontend/browser/report, deployment and scanner jobs remain mandatory
  CI; no cosmetic UI or dependency changes. Exact-head CI results pending.

Real services: local HTTP/TLS receiver, installed API/worker and disposable
PostgreSQL. Injected fixtures: DNS/address failures, receiver 503 responses and
temporary TLS trust. No hosted analysis/vendor calls or production validation.

Compatibility/risks: no schema change (001–003), volume rename, credential or user
data changes. Existing routes and four legacy workspaces remain. Delivery is
at least once, not exactly once or response enforcement; receivers must durably
deduplicate. One operator-configured destination, one authenticated collector
credential, no automatic retention expiry/redrive or multi-tenant claim. Pending
jobs use current destination configuration: pause/reconcile before changing it.
Before code rollback stop ingestion, reconcile new job kinds and preserve the
ledger; older workers cannot process connector jobs. Back up/test restore into
a separate database; never delete volumes. See [CONNECTORS.md](CONNECTORS.md).

Target **unreleased 2.0.0-alpha.1**, not production-hardened. Approval, reviewed
merge, deployment and publication are distinct pending states. Nothing merged,
deployed, tagged or published. Next dependency-ready product task after review:
extend the reference contracts to the selected cross-vendor source/destination
with explicit capability/schema contracts and local fixtures before live validation;
do not restart dependency hardening without an owner request.
