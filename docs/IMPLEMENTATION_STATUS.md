# Implementation status

Updated 2026-09-11 America/Chicago (2026-09-12 UTC). Alpha acceptance slice;
new product features, integrations and cosmetic UI work remain paused.

## Source and release state

- Starting SHA: `cbab41409d98fade11c2ccee316b7bebc1fab182`, clean checkout.
- GitHub rechecked: [PR #15](https://github.com/BB-AI-Arena/MCP-Trust-Scoreboard/pull/15)
  is **OPEN**, not merged, and still has that head. Its base is main.
- Branch: [test/alpha-release-acceptance](https://github.com/BB-AI-Arena/MCP-Trust-Scoreboard/tree/test/alpha-release-acceptance),
  [PR #16](https://github.com/BB-AI-Arena/MCP-Trust-Scoreboard/pull/16), base
  `fix/runtime-postgres-release-gates`, **not main**. Initial implementation SHA
  `a911f422cf75f672346a0a70d407a16c7105b39a`; final repair SHA recorded after commit.
  Main remains `31887614cf49dc93c31994945e107ab8339ca3ff`.
- PR #12 is already merged at `19628da7e01603f6a35285048a86e2d7e7f9de7b`;
  README/license PRs #13/#14 are also merged. MIT/license/badges/history preserved.
- Proposed `2.0.0-alpha.1` / Python `2.0.0a1` remains **unreleased and blocked**.
  No tags/releases existed on inspection. No merge, deployment, tag, release,
  package, image or attestation publication in this slice.
- Code implementation, CI success, maintainer approval, deployment and release
  publication are separate states. Passing runtime tests is not release approval.

## Actual changes

- Real thirteen-service Compose/Chromium acceptance with unique resources and
  private dummy configuration: four workspaces, submissions, validation, real
  backend outages, demo/experimental labels, graphs, ZIP results and PDF downloads.
- Repair backend Docker contexts/shared helper placement and worker paths; await
  artifact analysis in the compatibility worker. Atomically publish legacy Redis
  initial status/queue item to avoid overwriting a fast result. Preserve keys/TTL.
- PostgreSQL health waits for the final TCP listener, not the temporary Unix
  socket initialization server. A slow-init SQL fixture reproduces this startup
  window, which caused an intermittent worker connection-refused exit.
- Same-origin Nginx routes; actual behavior response/path mapping instead of hidden
  synthetic frontend success on outages. Preserve labeled backend demo examples.
- Adapt nested artifact findings/risk fields; show client-submitted snippet without
  new server retention. Freeze export-clone animations to prevent missing/dim PDF
  panels and omit export controls. No screen redesign or new workspace feature.
- Manual PDF inspection also caught Unknown files counted as 100% AI-generated
  and clipped summary values. Preserve unknown authorship, label model signals
  experimental, and relax only the export clone's truncated text boxes.
- Loopback publication; no host PostgreSQL/Redis ports. Private random fresh-install
  credentials, required explicit database password/API token, placeholder rejection
  and deployment preflight. Legacy `SECRET_KEY` does not authenticate legacy routes.
- Require hosted-provider opt-in even with legacy keys. Remove remote font requests;
  browser acceptance asserts all requests are local. Live hosted providers untested.
- Patch Nginx/Alpine packages and Python build tooling. Replace PostgreSQL's obsolete
  Go privilege helper with Alpine su-exec, preserving PG15 entrypoint/data paths.
- Actual image scans and CycloneDX OS/application inventories; frontend npm build
  dependency closure SBOMs. Record source/image IDs, scanner/digest/database age,
  commands/findings/checksums. Any HIGH/CRITICAL (including unfixed) fails unchanged.
- CI retains complete non-sensitive findings/SBOMs and browser evidence for 14 days.
  Existing gates remain; exact-SHA release preparation depends on the new gates.

## Measured checks

Commands from the checkout unless a frontend directory is specified. Final
clean-source evidence will supersede development runs; dirty builds are not exact
release artifacts.

| Command | Result |
| --- | --- |
| `.venv/bin/pytest -o addopts= -q -ra` | 44 passed; 27 explicit integration/acceptance skips, separately executed |
| `ACCEPTANCE_EVIDENCE=evidence/acceptance-b542a0a .venv/bin/pytest --run-integration --run-acceptance -o addopts= -q tests --junitxml=evidence/acceptance-b542a0a/junit.xml` | **71 passed**, zero skips, 182.37s on `b542a0af18720df17718b57870f8d83e509d04b1` before the final unknown-authorship/export and CI-owner fixes |
| `ACCEPTANCE_EVIDENCE=evidence/acceptance-unknown-report .venv/bin/pytest --run-acceptance tests/acceptance -v --tb=short` | 14 passed, zero skips, 72.35s; unknown-authorship regression and visually inspected unclipped report |
| `.venv/bin/pytest --run-integration tests/integration -v --tb=short` | 13 passed, zero skipped, 108.06s |
| `ACCEPTANCE_EVIDENCE=evidence/acceptance-final-repairs .venv/bin/pytest --run-acceptance tests/acceptance -v --tb=short` | 14 passed, zero skipped, 70.56s, including delayed init and final report fixes; dirty development source retained |
| `.venv/bin/python -m compileall -q src tests scripts` | Passed |
| `.venv/bin/python -m pip check` | Passed |
| `.venv/bin/python -m pip_audit` | No known third-party vulnerabilities; unpublished editable project itself cannot be audited on PyPI |
| `npm ci --ignore-scripts && npm audit --audit-level=high && node --test ../../tests/frontend/pdf-export.test.cjs && npm run build` in all four frontends | All passed; zero npm advisories, real jsPDF API checks and four builds |
| `python3 scripts/scan_images.py --output evidence/containers-a911f42` | **Failed policy gate** on clean `a911f42`; full findings, image IDs and CycloneDX/checksums retained |
| `python3 scripts/scan_images.py --output evidence/containers-os-update` | **Failed policy gate** after apt upgrade; 56 HIGH/CRITICAL matches per Python image, no exceptions |
| `python3 scripts/scan_images.py --output evidence/containers-b542a0a` | **Failed policy gate** on clean `b542a0a`; same findings; all 44 evidence file checksums verified with `jq -r 'to_entries[] \u007c "\(.value)  \(.key)"' checksums.json \u007c sha256sum -c -` in that evidence directory |
| `git diff --check` | Passed |

Starlette deprecations, Recharts maintenance warning and bundle-size warnings
remain. No tests removed, thresholds reduced or warnings suppressed. Earlier
browser failures caught real blank PDFs and routing/result defects. Harness
corrections included wrong button labels, native alert handling and 502 vs 504
gateway status. Failed development runs are not counted as passing acceptance.
Clean-source `a911f42` local acceptance failed during startup (14 setup errors)
before the TCP health repair; its passing remote run did not invalidate that race.

Runtime: 401 without token → authenticated 202 → real rules-only worker → persisted
job/assessment result. Force-recreating API/worker/PostgreSQL retains result and
attempt count through unique named test volumes. Installed site-packages runtime
has no pytest/Playwright. `pg_dump -Fc` / `pg_restore --exit-on-error` into a separate
disposable database retains results. Upgrade original 001 → 003 twice, preserving
completed/unrelated records and repairing projections. Original integration tests
still cover restarts, killed workers, fencing, concurrent claims and atomicity.

All four legacy engines run in one real Redis compatibility worker. Browser tests
exercise graph circles/edges, charts/timeline, ZIP treemap and actual downloaded
PDFs with findings/limitations. Page images are reviewed as well as structurally
checked. Behavior has no report export or submission form: those are unsupported,
not invented coverage. Optional external-provider errors are mocked only in
contracts; full-stack application services are real, with hosted providers disabled.

## Risks, migration and remaining gates

**Release remains blocked.** Trivy 0.74.0 reports **56 HIGH/CRITICAL package matches
in each of seven Python service images** (53 high, 3 critical). Of these, 54 are
Debian OS matches with no fixed version listed, including perl-base critical
CVE-2026-13221, CVE-2026-42496 and CVE-2026-8376. Two Python matches originate in
pip's bundled dependency SBOM: msgpack 1.1.2 (GHSA-6v7p-g79w-8964, fixed 1.2.1)
and setuptools 70.3.0 (CVE-2025-47273, fixed 78.1.1), despite installed setuptools
84.0.0. Updating top-level tooling does not update pip's vendored contents/SBOM.
No false-positive exception, metadata deletion, downgrade or blanket ignore is
applied. Root dependency audit success does not cover these image findings.

Four frontend images, derived PostgreSQL and Redis scan with zero findings in the
measured runs. Frontend SBOM component counts: 269 (blast), 264 (behavior), 294
(artifact), 231 (connector), including npm build dependency closures. PostgreSQL
has 47 and Redis 20. Database UpdatedAt: `2026-09-12T01:00:32.340244017Z`;
os-update download: `2026-09-12T03:09:32.411087404Z`. Full image identities,
scanner digest, commands and file SHA-256 checksums are in CI/local evidence.
Maintainer review and broader alpha hardening remain open; future phases incomplete.

Working: local rules-only authenticated PostgreSQL assessment lifecycle, legacy
flows/visualizations/reports where present, installed startup/recreation/upgrade/
restore. Demo: seeded behavior and legacy heuristic scoring. Experimental:
stylistic authorship guesses, never verified authorship or an approval gate.
Untested/unsupported: live hosted providers, remote deployments, other browsers,
architectures/Desktop/remote Docker, shared SaaS, production egress/retention
certification, SDKs, MCP/OpenAPI collectors and enforcement. No enterprise claim.

No operator deployment/database/volume changed. Only exact test-owned resources
were removed and their disposable dummy data discarded; no global cleanup.
Existing names/aliases/Redis TTL remain, no new schema beyond 003. Preserve existing
database passwords; changing environment values does not rotate initialized PG.
No Redis-history import or expired-result recovery. Stop writers, back up/test
restore separately, upgrade and verify results. Rollback preserves current data,
restores the old backup separately and reconciles later results before switching;
never restore over live data/delete user volumes. Runnable commands and constraints:
[ALPHA_ACCEPTANCE.md](ALPHA_ACCEPTANCE.md), [RUNTIME_VALIDATION.md](RUNTIME_VALIDATION.md).

## Tracking and next task

Reuse [ATP-A3 #3](https://github.com/BB-AI-Arena/MCP-Trust-Scoreboard/issues/3),
[ATP-D1 #8](https://github.com/BB-AI-Arena/MCP-Trust-Scoreboard/issues/8),
[ATP-A2 #2](https://github.com/BB-AI-Arena/MCP-Trust-Scoreboard/issues/2),
[epic #11](https://github.com/BB-AI-Arena/MCP-Trust-Scoreboard/issues/11).
Private project: https://github.com/users/BB-AI-Arena/projects/1.
Implementation awaiting acceptance stays In review; release/epic Blocked.
Push/PR creation and issue #3/#8 updates succeeded and were read back. PR #16 is
in the private project, Workflow **In review**, Phase A, Area Release, P0, target
alpha. Epic #11 and ATP-D1 remain Blocked; no duplicate issues/projects.
[Initial PR CI](https://github.com/BB-AI-Arena/MCP-Trust-Scoreboard/actions/runs/34669486730)
at clean `a911f42`: **nine jobs passed, container-security failed**. Acceptance
and scan artifacts verified present (IDs 10290941392 and 10290077354), retained
14 days. Later repairs require their own exact-source validation; the initial run
did not test later repairs. No failed GitHub mutations or access escalations.

[Second PR CI](https://github.com/BB-AI-Arena/MCP-Trust-Scoreboard/actions/runs/34669756761)
on `b542a0a`: eight jobs passed; acceptance build failed on an Alpine CDN TLS
error, and scanner teardown failed on root-owned cache permissions (its findings
also failed the vulnerability policy). Evidence was retained. Remediation: at
most three package-update retries, **no TLS/stale-repository bypass**, and scanner
containers run with the invoking UID/GID. Latest CI must verify those repairs.

Clean `b542a0a` local scanner evidence: database downloaded
`2026-09-12T03:13:23.190054656Z`; scan-summary SHA-256
`bb24ceefc69c2a03ecea283d0a90d6ce3242f455caefb00f507ea73a8ad296df`;
checksums.json SHA-256 `097b5c5980cd0a7a13ac8ba63697792161def4fbd77ec3d6436b2f0648446ef1`.

Next: resolve reported container blockers without exceptions, rerun exact-source
gates and review dependent PRs. **After release gates**, the next product milestone
is a vendor-neutral connector framework and one cross-vendor end-to-end integration.
It is not implemented in this slice.
