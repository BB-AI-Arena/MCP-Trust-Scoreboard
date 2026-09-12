# Implementation status

Updated 2026-09-11 America/Chicago (2026-09-12 UTC). Alpha acceptance slice;
new product features, integrations and cosmetic UI work remain paused.

## Source and release state

- Starting SHA: `cbab41409d98fade11c2ccee316b7bebc1fab182`, clean checkout.
- GitHub rechecked: [PR #15](https://github.com/BB-AI-Arena/MCP-Trust-Scoreboard/pull/15)
  is **OPEN**, not merged, and still has that head. Its base is main.
- Branch: `test/alpha-release-acceptance`, dependent PR base
  `fix/runtime-postgres-release-gates`, **not main**. Ending SHA/PR/remote evidence
  will be recorded after push. Main remains `31887614cf49dc93c31994945e107ab8339ca3ff`.
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
- Same-origin Nginx routes; actual behavior response/path mapping instead of hidden
  synthetic frontend success on outages. Preserve labeled backend demo examples.
- Adapt nested artifact findings/risk fields; show client-submitted snippet without
  new server retention. Freeze export-clone animations to prevent missing/dim PDF
  panels and omit export controls. No screen redesign or new workspace feature.
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
| `.venv/bin/pytest --run-integration tests/integration -v --tb=short` | 13 passed, zero skipped, 108.06s |
| `ACCEPTANCE_EVIDENCE=evidence/acceptance-round6 .venv/bin/pytest --run-acceptance tests/acceptance -v --tb=short` | 14 passed, zero skipped, 67.78s; dirty development source retained in evidence |
| `.venv/bin/python -m compileall -q src tests scripts` | Passed |
| `.venv/bin/python -m pip check` | Passed |
| `.venv/bin/python -m pip_audit` | No known third-party vulnerabilities; unpublished editable project itself cannot be audited on PyPI |
| `npm ci --ignore-scripts && npm audit --audit-level=high && node --test ../../tests/frontend/pdf-export.test.cjs && npm run build` in all four frontends | All passed; zero npm advisories, real jsPDF API checks and four builds |
| `python3 scripts/scan_images.py --output evidence/final-scan-development` | **Failed policy gate**; full findings retained, no exceptions. Final SBOM/helper changes still require rescan |
| `git diff --check` | Passed |

Starlette deprecations, Recharts maintenance warning and bundle-size warnings
remain. No tests removed, thresholds reduced or warnings suppressed. Earlier
browser failures caught real blank PDFs and routing/result defects. Harness
corrections included wrong button labels, native alert handling and 502 vs 504
gateway status. Failed development runs are not counted as passing acceptance.

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

**Release remains blocked.** Container OS/bundled-tooling HIGH/CRITICAL findings
remain despite passing source dependency audits. Final counts/source/checksums
are pending the final clean-source scan. No false-positive exceptions, metadata
deletion or blanket ignores. Maintainer review and broader alpha hardening remain
open; future-phase milestones are not complete.

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
Remote PR/issue/project updates and CI readback are pending this local handoff.

Next: resolve reported container blockers without exceptions, rerun exact-source
gates and review dependent PRs. **After release gates**, the next product milestone
is a vendor-neutral connector framework and one cross-vendor end-to-end integration.
It is not implemented in this slice.
