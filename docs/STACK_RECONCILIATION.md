# Stack reconciliation and maintainer merge handoff

Verified 2026-09-13. Authoritative current status; earlier slice handoffs are
historical evidence. Reconciliation only: no runtime, workflow, migration or
product changes, merges, deployment, tags, publication or operator-data operations.

**NOT READY FOR PUBLICATION — awaiting maintainer merge and merged-main validation.**

GitHub Project status unverified: active authentication lacks read:project.
Project update not performed/verified because active authentication lacks read:project.
“In review” below is a recommended repository disposition, not a verified Project field.

## Main, versions and releases

Default branch main: `31887614cf49dc93c31994945e107ab8339ca3ff`.
[Main CI](https://github.com/BB-AI-Arena/MCP-Trust-Scoreboard/actions/runs/34666295534)
is failing and predates the unmerged repairs. Main is not fixed by passing PRs.
No releases exist. Platform `2.0.0-alpha.1` / Python `2.0.0a1` are equivalent;
all four frontend versions agree. Sensor `0.1.0` is a separate component version.

## Complete PR matrix

All seven PRs are **OPEN, MERGEABLE, unmerged**. Exact heads below are the
pre-reconciliation snapshot. A later documentation commit must have its own CI
readback; these results are not a substitute for that or final-main validation.

| Order / PR | Title / purpose | Base branch | Head branch | Verified head | CI / review readiness | New migration | Issues |
|---|---|---|---|---|---|---|---|
| 1 / [#15](https://github.com/BB-AI-Arena/MCP-Trust-Scoreboard/pull/15) | fix: restore runtime and validate PostgreSQL assessment lifecycle | main | fix/runtime-postgres-release-gates | `cbab41409d98fade11c2ccee316b7bebc1fab182` | 8 jobs green; maintainer review | 002, 003 | #1/#2/#3/#8/#11 |
| 2 / [#16](https://github.com/BB-AI-Arena/MCP-Trust-Scoreboard/pull/16) | test: add alpha runtime, browser and image release gates | fix/runtime-postgres-release-gates | test/alpha-release-acceptance | `6f9cdb8d8aac35b5647288200ecff16f31183fab` | 9/10 green; historical CVE gate failure superseded by #17; qualified review | none | #3/#8/#11 |
| 3 / [#17](https://github.com/BB-AI-Arena/MCP-Trust-Scoreboard/pull/17) | chore: apply owner alpha dependency-risk policy | test/alpha-release-acceptance | chore/alpha-dependency-risk-policy | `886560bb801be9c2d2a49627ea19d1ad3c5eee9d` | 10 green; maintainer review | none | #8/#11 |
| 4 / [#19](https://github.com/BB-AI-Arena/MCP-Trust-Scoreboard/pull/19) | feat: connect JSON evidence to durable webhook finding delivery | chore/alpha-dependency-risk-policy | feat/json-webhook-connectors | `e6bd77f93f7abd1aa2513a92aa146a9ecc5b5e8b` | 10 green; maintainer review | none | #18 |
| 5 / [#21](https://github.com/BB-AI-Arena/MCP-Trust-Scoreboard/pull/21) | feat: add read-only CrowdStrike Falcon evidence collection | feat/json-webhook-connectors | feat/crowdstrike-evidence-source | `9aa41c1bdbd3c81c6bdf4ba5f33bf1035d18de43` | 10 green; fixture scope ready for review | 004 | #20 |
| 6 / [#23](https://github.com/BB-AI-Arena/MCP-Trust-Scoreboard/pull/23) | feat: add observe-only Windows endpoint sensor vertical slice | feat/crowdstrike-evidence-source | feat/windows-endpoint-sensor | `e8e09f1868834a13b233817bccb0e188448fedc5` | 10 platform + Windows green; review with #24 | 005 | #22 |
| 7 / [#24](https://github.com/BB-AI-Arena/MCP-Trust-Scoreboard/pull/24) | feat: validate Windows sensor as least-privilege service | feat/windows-endpoint-sensor | feat/windows-service-acceptance | `e814ba207d243b5e0ac10e784fbf0ec102f7e205` | 10 platform + portable Go + Windows green; SCM blocker cleared | none | #22/#8 |

CI: [#15](https://github.com/BB-AI-Arena/MCP-Trust-Scoreboard/actions/runs/34667642223),
[#16 historical failure](https://github.com/BB-AI-Arena/MCP-Trust-Scoreboard/actions/runs/34670452399),
[#17](https://github.com/BB-AI-Arena/MCP-Trust-Scoreboard/actions/runs/34671405825),
[#19](https://github.com/BB-AI-Arena/MCP-Trust-Scoreboard/actions/runs/34672165101),
[#21](https://github.com/BB-AI-Arena/MCP-Trust-Scoreboard/actions/runs/34677860030),
[#23 platform](https://github.com/BB-AI-Arena/MCP-Trust-Scoreboard/actions/runs/34680383650),
[#23 Windows](https://github.com/BB-AI-Arena/MCP-Trust-Scoreboard/actions/runs/34680383651),
[#24 platform](https://github.com/BB-AI-Arena/MCP-Trust-Scoreboard/actions/runs/34738201170),
[#24 Windows](https://github.com/BB-AI-Arena/MCP-Trust-Scoreboard/actions/runs/34738201185).
Downloaded #24 platform JUnit: **19 PostgreSQL integration and 14 full-stack/browser
tests, zero failures/skips**. PR #16's old conclusion must not be relabeled green.

### Actual ancestry, duplicates and workflow differences

Fetched origin; `git merge-base --is-ancestor BASE HEAD` succeeds for every row.
`git rev-list --left-right --count BASE...HEAD` reports:

| Pair | Base-only / head-only commits | Contains all predecessor commits? |
|---|---|---|
| main → #15 | 0 / 3 | yes |
| #15 → #16 | 0 / 4 | yes |
| #16 → #17 | 0 / 1 | yes |
| #17 → #19 | 0 / 2 | yes |
| #19 → #21 | 0 / 2 | yes |
| #21 → #23 | 0 / 5 | yes |
| #23 → #24 | 0 / 24 | yes |

Every downstream head transitively includes earlier heads. No missing commits,
unexpected divergence, conflicts, stale base references or duplicate stable patch
IDs among 41 non-merge commits above main. A documentation commit increases only
the final row. No applied migration edits or version conflicts found.

Workflow differences: #15 repairs platform/release gates; #16 adds full-stack and
image gates; #17 changes CVE disposition; #19 retains gates; #21 extends runtime
artifact retention; #23 adds Windows CI and release-preparation Windows gates;
#24 adds portable Go and SCM execution. These are intentional dependency changes.

## Windows evidence and limits

[Run 34738201185](https://github.com/BB-AI-Arena/MCP-Trust-Scoreboard/actions/runs/34738201185)
passes portable Go, **nine native Windows tests**/build, foreground/PostgreSQL and
SCM/PostgreSQL. Artifact source is PR test-merge commit
`33d98a5f88b48afe0852787faa33fb01613b472e`, parents #23 head and
`e814ba207d243b5e0ac10e784fbf0ec102f7e205`. GitHub commit API confirms both
test merge and #24 head have tree `a5e2a976ae5d5660da381d3a5285fb9579677d73`.
This is not execution on main.

- Server 2022 amd64, Windows build **20348**, runner **20260907.297.1**, Go **1.26.8**.
- Binary SHA-256: `182d41f2021ad2fe124d2141b07396755e3697f2558b4b46863f4ff5c71b0215`.
- Identity: `NT SERVICE\\AgentTrustEndpoint-e1197f247361`; not elevated;
  requested privilege only `SeChangeNotifyPrivilege`.
- SCM readback: Automatic, reset 86400s, restart delays 5000/30000ms, non-crash
  failure actions enabled. Installer specifies third action “no action”.
  Readback lists two restarts, not a literal NONE row; acceptance proves the first
  unexpected-process recovery, not three consecutive crashes.
- Transient `data/bootstrap.json`: private ACL, only SYSTEM/Administrators/named
  service SID. Existing server 15-minute single-redemption policy; enrollment and
  deletion pass under SCM. No command-line/environment/registry/log/spool handoff.
- User-scope DPAPI: unrelated-user decryption rejected; stop/start and SCM recovery
  preserve identity. Enrolled service starts while platform offline and recovers.
- Spool: **2582 queued / recovered / uploaded**, **1 replay attempt / exactly 1
  persisted logical record**, **0 dropped / expired**; 5298 total uploads.
  Four findings delivered in five receiver attempts.
- Revocation rejects authentication before/after restart, same identity and history.
  No automatic reenrollment.
- Uninstall removes service/executable; preserves identity/spool/config/status/history
  and unrelated files. No implicit purge.
- Foreground: six offline events recovered, one persisted replay record, five
  findings/six receiver attempts. Both modes: zero enforcement, `executed: false`.

SCM health: **ai/mcp/filesystem/software degraded; process permission_missing;
network/runtime active; dns/udp/file_writer unsupported**. Denied-profile AI/MCP
discovery stays degraded. No LocalSystem workaround or broad user-profile grants.

Evidence caveats: generic `service/acceptance.json` collector lists are static
harness labels, not proof that every foreground assertion ran under SCM. Use
`service/scm-acceptance.json` health and conditional assertions for service claims.
Foreground proves AI/MCP fixtures, benign child/TCP/disposable file observations
and Shadow AI correlation; behavioral/hash fixtures are not live malware/C2.
Server single-redemption rejection is explicit in `tests/test_endpoint.py`;
the SCM “single_use” label is not an additional second-service redemption test.
Literal reboot and full interactive-user visibility are unverified.

Preserve [failed run 34709938220](https://github.com/BB-AI-Arena/MCP-Trust-Scoreboard/actions/runs/34709938220):
service-name-only startup had no bootstrap channel (“enrollment required”).
Protected transient handoff fixed that blocker; later success does not erase history.

## Migration audit

| Order | Exact packaged filename | Introduced | Effect |
|---|---|---|---|
| 001 | `001_initial.sql` | already main | records/job ledger |
| 002 | `002_workspace_idempotency.sql` | #15 | workspace-scoped idempotency |
| 003 | `003_assessment_results.sql` | #15 | assessment projection/backfill |
| 004 | `004_connector_checkpoints.sql` | #21 | CrowdStrike checkpoint state |
| 005 | `005_endpoints.sql` | #23 | endpoint enrollment/health/correlation |

No old migration changed; #24 and reconciliation add none. Packaged loader applies
sorted SQL transactionally with serialization. Real PostgreSQL tests cover fresh
creation, 001→current with retained records/jobs, concurrent/repeated invocation,
003→current preservation, checkpoint atomicity/revisions/replay, endpoint
persistence and restarted workers. Historical test name “003_to_004” now applies
through **005** and asserts five migration records.

Exact disposable-fixture commands:

```bash
.venv/bin/pytest --run-integration tests/integration -v --tb=short
.venv/bin/pytest --run-integration \
  tests/integration/test_postgres.py::test_fresh_and_existing_schema_migrations_preserve_data \
  tests/integration/test_falcon_runtime.py::test_upgrade_003_to_004_preserves_preexisting_records \
  tests/integration/test_falcon_runtime.py::test_postgres_page_atomicity_replay_revisions_mapping_and_delivery \
  tests/integration/test_endpoint_runtime.py -v
```

The suite does not separately snapshot populated endpoint and checkpoint tables
*together across repeat migration calls*. Additional final-main validation:
in a disposable database apply 001, seed legacy records/jobs, upgrade through 005,
enroll an endpoint and ingest a Falcon fixture page; snapshot all four tables,
call `create_schema(engine)` twice, assert identical rows and exactly five
migration filenames. This is a prepared validation extension, not an existing
result; existing tests independently cover those state paths.

Rollback: preserve applied SQL/ledger, credentials, records and checkpoints.
Stop affected writers and drain/reconcile jobs before restoring compatible code.
For incompatible rollback, restore a verified backup into a **separate** database,
reconcile newer records before an owner-approved switch. Never drop/reset operator
tables/volumes. Sensor uninstall preserves local identity/spool/config/status and
server history; preserve the profile too. Changing machine/account/service name
requires explicit enrollment reconciliation. No migration rollback was performed.

## All open issues

Implemented/tested means advertised slice on unmerged branches, not future roadmap
completion. No issue closes in this pass.

| Issue | Roadmap ID | Purpose | Implemented? | Acceptance tested? | PR(s) | Merged? | Still required / recommended action |
|---|---|---|---|---|---|---|---|
| #1 | ATP-A1 | namespace/version/provider contracts | yes | unit/import/config/provider | #12/#15 | #12 only | In review; close after stack merge + main validation |
| #2 | ATP-A2 | durable records/fenced jobs | yes | real PostgreSQL/concurrency/recovery | #15 | no | In review; close after merge + main validation |
| #3 | ATP-A3 | four legacy surfaces/truthful alpha | alpha scope yes | 14 browser/full-stack + builds | #15/#16/#17 | no | In review; close after merge + main validation |
| #5 | ATP-C2, formerly C1 | behavior/baselines/SDK/OTel | endpoint subset | not general SDK/baselines | #23/#24 subset | no | Keep open for remaining requirements |
| #6 | ATP-E1, formerly C2 | graph/artifact assurance | legacy views only | not full assurance acceptance | no completion PR | no | Keep open: multi-edge/cycle/provenance scope |
| #7 | ATP-B2 | verification/snapshots/drift | foundations only | not full acceptance | no completion PR | no | Keep open: typed evidence is not verified provenance |
| #8 | ATP-D1 | release/recovery/upgrade/packaging | alpha gates yes, broader partial | stack gates under owner policy | #15–#24 | no | Keep open: merge/main pending and future operations |
| #9 | ATP-F1 | optional enforcement/approvals | intentionally no | no | none | no | Keep open; no work authorized |
| #10 | ATP-B1 | MCP/OpenAPI protocol collectors | no complete protocol slice | no | none | no | Keep open; discovery/JSON ingestion is not protocol collection |
| #11 | ATP-A0 | foundation epic | alpha children yes | unit/runtime/legacy | #12/#15–#17 | #12 only | Close with #1/#2/#3 after main validation |
| #18 | ATP-B3 | JSON → durable webhook | yes | HTTP/TLS + PostgreSQL retries | #19 | no | Close after merge + main validation |
| #20 | ATP-B4 | read-only Falcon evidence | fixture scope yes | checkpoint/API/worker/webhook fixtures | #21 | no | Close after merge + main validation; live optional/unverified |
| #22 | ATP-C1 | Windows observe-only sensor | v0.1 yes | native/foreground + limited-visibility SCM | #23/#24 | no | CLOSE AFTER STACK MERGE + MERGED-MAIN VALIDATION |

### #22 definition of done, including original acceptance

| Requirement | Implementation / acceptance basis | Disposition |
|---|---|---|
| Unique device identity/credential, versions/policy/workspace/revocation | endpoint API/domain/storage tests | satisfied in review |
| DPAPI/no secret telemetry | native DPAPI; SCM restart/recovery, unrelated-user rejection | satisfied in review |
| AI/MCP discovery without execution | bounded configured fixture discovery, foreground Windows | supported paths; SCM profile visibility degraded |
| Software/OS inventory | native registry/OS and foreground acceptance | supported subset; service inventory degraded |
| Process lifecycle/parent/path/hash/session where practical | polling, real benign child | snapshot limits; SCM permission_missing |
| Network metadata/association where supported | native TCP fixture | TCP subset; DNS/UDP unsupported, no payload claim |
| Scoped file/repository metadata/classification | disposable sensitive repo foreground fixture | polling limits; no writer/source-read proof |
| Versioned typed telemetry/timestamps/source/correlation | endpoint schemas/contracts + PostgreSQL | satisfied in review |
| Persistent bounded spool/health/loss/replay | Go capacity/age tests + Windows outage/restart/replay | satisfied; no exactly-once transport claim |
| Shadow AI near sensitive repository | foreground signals + central positive/negative controls | co-presence/interaction, not proven exfiltration |
| Suspicious network/process, destructive metadata, hash indicator | benign deterministic fixtures/rule tests | fixture scope, not native malware/C2 validation |
| Real Windows and real SCM | Server 2022 jobs | satisfied within visibility bounds; no literal reboot |
| Integration/delivery/zero enforcement | PostgreSQL/outbox/receiver and executed=false | satisfied in review |
| Docs/privacy/install/uninstall/integrity plan | endpoint docs, binary hash, preserved-state uninstall | satisfied; signing/mTLS future |
| Existing platform regression gates | 10 platform jobs + Windows/portable | stack passes; merged main pending |
| Reviewable PR/status | #23/#24, reconciliation; owner Project exception | in review, not merged; Project unverified |

The original 15-step isolated acceptance is satisfied by **foreground** execution;
separate SCM acceptance proves service lifecycle with honest degradation, not full
interactive-user telemetry. Later DLP/prevention/mTLS/signing/Windows client
certification/macOS/Linux/learned baselines do not extend #22's v0.1 definition of done.

### Roadmap IDs and #8 release scope

A core platform; B external integrations/evidence; C endpoint security;
D release/operations; E graph/assurance; F enforcement.
#22 retains **ATP-C1 Windows Endpoint Sensor**.
#5 becomes **ATP-C2 Behavioral Detection Engine, baselines and SDKs**.
Preserve general authenticated/versioned/idempotent telemetry, dynamic registration,
agent/deployment/identity/workload baselines, warm-up/windowing, late/duplicate
events, missing telemetry, poisoning resistance, anomaly-vs-policy, bounded loss,
Python/JavaScript SDKs and tested OpenTelemetry mappings. Only endpoint-specific
delivered subsets are marked superseded by #23/#24. #6 becomes **ATP-E1**, depending
on #7 (B2) and #5 (new C2). C3 DLP and C4 vulnerability/malware intelligence remain
future labels; no duplicate issue or feature is created.

#8 separates implemented alpha gates from pending maintainer merges/main validation
and broader future production recovery/upgrade/packaging qualification. Alpha does
not require zero CVEs, mTLS, signing, all connectors, enforcement or SaaS tenancy.
Historical test counts/links are preserved and explicitly labeled historical.

## PR description reconciliation

Updated descriptions: #15's future-acceptance language; #16's
CVE-release-blocking/deferred-connector language; #23's SCM-follow-up boundary;
#24's failed/pending status. Current evidence goes first; original bodies/failed
links remain under historical headings. #17/#19/#21 remain accurate for their slice.
Issue updates preserve requirements and previous evidence; no closure or Project update.
Issues #1/#2/#3/#11/#18/#20/#22 now carry current in-review/after-main closure
recommendations; #5/#6 IDs and #8 alpha/future scope are reconciled. #7/#9/#10
were audited and remain unchanged. Deprecated Projects-classic lookup in the CLI
prevented its PR-edit command; the authorized pull-request REST endpoint was used
instead, without requesting broader permissions.

Local reconciliation verification: **105 unit/contract tests passed**, 33 explicitly
gated integration/browser skips; the separately executed disposable PostgreSQL
suite passed **19/19, zero skips**. Compileall, roadmap ID/dependency validation and
diff whitespace checks passed. No frontend/runtime/workflow code changed; prior
platform/Windows artifacts remain implementation evidence, not a Linux rerun of Windows.

## Exact maintainer merge sequence

**#15 → #16 → #17 → #19 → #21 → #23 → #24.**
Use heads above; refresh #24 for reconciliation-only changes and reread all CI.

Repository permits merge commits. Main's protection endpoint returned “Branch
not protected”; repository rulesets were empty. Refresh settings/reviews before
owner action. Prefer **merge commits preserving ancestry**, without deleting
dependency branches mid-stack. After each predecessor merges, fetch and verify
its original head is an ancestor of main; **retarget the next PR to main** and
wait for refreshed base-aware CI/mergeability. Normally no rebase is required.
Squash/rebase replaces ancestry and needs a separately reviewed transplant plan
to avoid duplicate commits; never automatically force-push.

| Merge | Target at merge | Required validation before/after owner action | Migration |
|---|---|---|---|
| #15 | main | 8 checks, installed runtime/PostgreSQL/legacy | 002/003 |
| #16 | main after #15 | functional/browser/build/secret/scanner-execution; historical CVE failure explicitly reviewed under #17 | none |
| #17 | main after #16 | all 10 checks, informational findings/raw scans/SBOMs | none |
| #19 | main after #17 | all 10 + JSON/idempotency/webhook/retry | none |
| #21 | main after #19 | all 10 + Falcon fixture/checkpoint/restart | 004 |
| #23 | main after #21 | platform + native/foreground Windows, endpoint correlation | 005 |
| #24 | main after #23 | platform + portable/native/foreground/SCM, then full final-main validation | none |

Do not demand CVE remediation for #16's old conclusion. Maintainer explicitly
accepts the superseded failure and immediately follows with #17, or approves
consolidation if merge rules change. Do not bypass protections automatically or
leave the stack at #16 as a release. No retarget/merge/auto-merge in this pass.

## Final validation on actual merged main — NOT YET RUN

After all merges, pin actual main and use the existing evidence-only workflow:

```bash
git fetch origin
merged_main_sha=$(git rev-parse origin/main)
gh api repos/BB-AI-Arena/MCP-Trust-Scoreboard/git/ref/heads/main --jq .object.sha
# Verify API SHA equals merged_main_sha before dispatch.
gh workflow run release-prepare.yml --repo BB-AI-Arena/MCP-Trust-Scoreboard \
  --ref main -f version=2.0.0-alpha.1 -f source_sha="$merged_main_sha"
gh run list --repo BB-AI-Arena/MCP-Trust-Scoreboard \
  --workflow release-prepare.yml --branch main --limit 5
# Select that dispatch; verify checked-out source SHA in both called workflows.
# gh run watch RUN_ID --repo BB-AI-Arena/MCP-Trust-Scoreboard --exit-status
# gh run download RUN_ID --repo BB-AI-Arena/MCP-Trust-Scoreboard --dir OWNED_EVIDENCE_DIRECTORY
```

`release-prepare.yml` calls `ci.yml` and `windows-sensor.yml` with exact SHA,
validates version/clean source, and prepares checksums only. Read-only permissions;
no deployment/tag/publication. No workflow change needed. Do not dispatch against
old main and call it final acceptance.

Required evidence tied to that actual main SHA:

- [ ] Python unit/contracts/compileall; no gated skips substituted for integration.
- [ ] PostgreSQL installed API/worker/assessment lifecycle/fencing/recovery;
      fresh/001→005/repeat migrations and existing job/record/checkpoint/endpoint state.
- [ ] Generic JSON, durable webhook delivery, CrowdStrike fixture connector.
- [ ] Four legacy workspaces; Compose/browser/report/upgrade/backup-restore acceptance.
- [ ] Four frontend builds/PDF tests; Compose boundaries; committed-secret checks.
- [ ] Python/npm audits, informational container CVEs, raw scans and CycloneDX SBOMs.
      Scanner execution/coverage failures remain blocking.
- [ ] Portable Go, native Windows/self-contained build, foreground acceptance.
- [ ] SCM install/virtual account/Automatic/bounded recovery; bootstrap enrollment/
      deletion, server single-redemption regression, DPAPI restart/recovery.
- [ ] Offline service startup/outage/spool/restart/replay/restoration, revocation,
      preserved identity/history, safe uninstall and honest collector health.
- [ ] Zero enforcement, source SHA/binary hash/Windows build, retained artifacts.
- [ ] Maintainer reviews evidence boundaries: no literal reboot or second-service
      token-reuse claim; additional validation recorded separately.

Local platform commands: [ALPHA_ACCEPTANCE.md](ALPHA_ACCEPTANCE.md).
Windows commands: [endpoint/SERVICE_ACCEPTANCE.md](endpoint/SERVICE_ACCEPTANCE.md).
Linux tests never substitute for Windows. Preserve artifacts before 14-day expiry;
new passing runs never erase historical failures.

## Accepted limitations and readiness

Known dependency CVEs accepted/informational under #17 and
[KNOWN_SECURITY_ISSUES.md](KNOWN_SECURITY_ISSUES.md); no hardening campaign.
No production-hardening, mTLS, signed installer/updater, client-edition certification,
literal reboot, live Falcon tenant, full interactive-user visibility, macOS/Linux,
DLP/enforcement or shared SaaS claim. These are not new alpha blockers.

**NOT READY FOR PUBLICATION.** Remaining release gates:

1. Maintainer review/merge of dependency stack.
2. Successful validation against actual merged main.

After both, reassess **READY FOR MAINTAINER REVIEW FOR 2.0.0-alpha.1 PUBLICATION**.
No tag/release/publication is authorized by this reconciliation.
