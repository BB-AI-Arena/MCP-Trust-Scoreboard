# Historical PR #19 connector handoff

This preserves the prior slice's measured evidence. Current work is recorded in
IMPLEMENTATION_STATUS.md; the owner-accepted alpha dependency-risk policy remains
authoritative. Do not restart historical container-remediation work.

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
The historical baseline artifact 10290422302 was downloaded and all 41 checksums
verified. The current [known-risk register](KNOWN_SECURITY_ISSUES.md) retains all
181 distinct advisory/package/version/severity rows across 12 images/13 services
from connector CI artifact 10291645171. Its advisory/package/version/severity set
is identical to that baseline. Raw reports remain unchanged; this is not a clean scan.

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

## Connector slice: implemented, CI passed, awaiting review

Branch `feat/json-webhook-connectors` starts at policy head `886560bb801be9c2d2a49627ea19d1ad3c5eee9d`;
its review base is `chore/alpha-dependency-risk-policy` (PR #17), not main. PRs
#15/#16 remain open at their verified heads. Tracking:
[PR #19](https://github.com/BB-AI-Arena/MCP-Trust-Scoreboard/pull/19),
[ATP-B3 #18](https://github.com/BB-AI-Arena/MCP-Trust-Scoreboard/issues/18),
[private project](https://github.com/users/BB-AI-Arena/projects/1), In review, not Done.
Ending product implementation SHA: `5fb6f0a9d5c7fd89a406afb95f1ede05de1c6406`.
The following handoff commit changes documentation, the risk-register generator
and its regression test only, not application behavior. Its ending SHA is the
PR head (`git rev-parse HEAD`); the exact implementation source is preserved here
so evidence is not misattributed to a later documentation commit.

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

- `.venv/bin/pytest -o addopts= -q -ra`: **75 passed, 28 explicit integration/browser
  skips**, two inherited Starlette warnings (not suppressed). This includes one
  additional risk-register artifact-provenance/corrupt-checksum regression beyond
  the 74 tests at the product implementation SHA.
- `.venv/bin/pytest --run-integration tests/integration -v --tb=short`: **14 passed,
  zero skipped** in 144.27 seconds: original 13 runtime/PostgreSQL tests retained,
  plus installed API/worker JSON-to-TLS-webhook, untrusted-certificate rejection,
  failed delivery/retry across worker restart and persisted retrieval.
- `.venv/bin/python -m compileall -q src tests scripts examples`; `git diff --check`:
  passed. Local example receiver smoke: two real POSTs returned 204 with the same
  delivery ID deduplicated. Example deduplication is in-memory/demo only.
- [Exact implementation CI 34671947014](https://github.com/BB-AI-Arena/MCP-Trust-Scoreboard/actions/runs/34671947014):
  **all ten jobs passed**. `pytest`/compile/version checks passed; installed runtime
  `pytest --run-integration tests/integration -v`: 14 passed, zero skips (77.89s).
  `pytest --run-acceptance tests/acceptance -v --junitxml=evidence/acceptance/junit.xml`:
  **14 passed, zero skipped/failed/errors**, 149.433s. Includes all four real browser
  workspaces, downloaded PDF content/layout, backend failures, demo/experimental
  labels, no-provider behavior, mixed legacy worker, recreation, upgrade and
  separate database backup/restore. No extra local repeat of that unchanged suite.
- For each of the four frontend directories CI ran `npm ci && node --test
  ../../tests/frontend/pdf-export.test.cjs && npm run build`: passed. Python and
  four npm audit wrappers completed; zero known top-level findings, editable
  self-package unauditable and disclosed. This does **not** negate container CVEs.
- CI `python3 scripts/scan_images.py`: completed with findings informational.
  Compose preflight and committed-secret protections passed unchanged. No frontend,
  application dependency, base image or production changes in the connector slice.

### Retained evidence and remote state

From exact implementation run 34671947014 (downloaded/read back):

| Artifact | ID | Verified observations |
| --- | --- | --- |
| container-security-34671947014-1 | 10291645171 | 41 SHA-256 checksums; 12 image IDs, 13 services; 181 distinct advisory/package/version/severity rows; no dropped findings |
| acceptance-34671947014-1 | 10290513697 | JUnit 14/14; traces/screenshots; four actual downloaded PDF reports and layout/content checks; zero browser external requests |
| dependencies-34671947014-1 | 10291026577 | Python plus four npm raw JSON/summary reports; executions completed |

Scan source `5fb6f0a9d5c7fd89a406afb95f1ede05de1c6406`, Trivy 0.74.0,
scan `2026-09-12T04:03:49.405735+00:00`, DB UpdatedAt
`2026-09-12T01:00:32.340244017Z`. All six affected Python images (seven services)
still have 53 HIGH + 3 CRITICAL package matches each. Complete image IDs, packages,
fixes when reported, accepted status and scanner digest are in
[known_security_issues.json](known_security_issues.json); full inventories/SBOMs in
the artifact. No CVE applicability investigation or remediation was resumed.
The downloaded artifact-assurance report was also visually inspected: experimental
warning, submitted fixture code and shell-injection finding are present; this is
not an assertion of verified provenance. Behavior has no report download feature.

Evidence commands (downloads are into ignored, separate evidence folders):

```bash
gh run download 34671947014 --name container-security-34671947014-1 --dir evidence/connector-ci-containers
gh run download 34671947014 --name acceptance-34671947014-1 --dir evidence/connector-ci-acceptance
gh run download 34671947014 --name dependencies-34671947014-1 --dir evidence/connector-ci-dependencies
.venv/bin/python scripts/record_security_findings.py --evidence evidence/connector-ci-containers --run-id 34671947014 --artifact-id 10291645171
gh run view 34671947014 --json status,conclusion,headSha,jobs
```

GitHub mutations were read back: PRs #17/#19 OPEN on their documented bases,
issues #8/#11/#18 and dedicated project items In review, no duplicate issues.
`gh pr edit 17` hit the installed CLI's deprecated Projects-classic query; the
same authorized body update succeeded through `gh api --method PATCH` and was
verified. No pending authentication/permission recovery or failed write remains.
The stack must be reviewed in dependency order #15 → #16 → #17 → #19.

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
