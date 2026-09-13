# Merged stack and alpha acceptance

Verified 2026-09-13. This is the authoritative source-bound acceptance report.
New feature development remains stopped. No release/tag/package/image publication,
deployment, branch deletion, force-push or operator database/volume operation occurred.

**READY FOR MAINTAINER REVIEW FOR 2.0.0-alpha.1 PUBLICATION**

This recommendation is supported by actual merged-main validation, not inherited
PR or synthetic-merge results. Publication still needs separate owner authorization.

## Source and final documentation follow-up

Main before the sequence: `31887614cf49dc93c31994945e107ab8339ca3ff`.
Main after all seven implementation/reconciliation PRs:
**`14378a27e96c7c8f5451f4698820f696a4e8c2c1`**.

[Release preparation 34740514148](https://github.com/BB-AI-Arena/MCP-Trust-Scoreboard/actions/runs/34740514148)
passed all **14 jobs**, including both called platform/Windows workflows and the
final manifest-preparation job, against that exact actual-main SHA.
Separate main [platform 34740499121](https://github.com/BB-AI-Arena/MCP-Trust-Scoreboard/actions/runs/34740499121)
and [Windows 34740499134](https://github.com/BB-AI-Arena/MCP-Trust-Scoreboard/actions/runs/34740499134)
also passed.

The owner additionally authorized a **status-only documentation merge followed by
another exact-main release-preparation run**. This report freezes the feature-merge
evidence above rather than pretending its hash is the later documentation merge.
The subsequent main SHA, run links and final readback are recorded in the
documentation PR and [release gate issue #8](https://github.com/BB-AI-Arena/MCP-Trust-Scoreboard/issues/8).
The post-documentation run must pass before the final publication-readiness handoff.
It adds no runtime, schema, dependency, workflow or product changes.

GitHub Project status unverified: active authentication lacks read:project.
No Project update was performed or verified; Project access is not a release gate.

## Completed normal-merge sequence

All seven expected heads were verified unchanged immediately before merging.
#16/#17/#19/#21/#23/#24 were retargeted from their predecessor's branch to main.
Every merge used GitHub's normal merge method and exact-head SHA protection:
no squash, rebase-and-merge, forced push or automatic branch deletion.

| PR | Expected head retained | Resulting merge / main SHA | Target |
|---|---|---|---|
| #15 | `cbab41409d98fade11c2ccee316b7bebc1fab182` | `ab7344c10957a11a88b83739a48a2ba0b5a96a2e` | main |
| #16 | `6f9cdb8d8aac35b5647288200ecff16f31183fab` | `9872b7fa4578c7610391f616f0deb1e6032e513b` | main |
| #17 | `886560bb801be9c2d2a49627ea19d1ad3c5eee9d` | `97f12eb5904317f631654d1e2705e9fab8efd227` | main |
| #19 | `e6bd77f93f7abd1aa2513a92aa146a9ecc5b5e8b` | `8b9b0517d1dbcd843c39116fc8288a4e5f34920b` | main |
| #21 | `9aa41c1bdbd3c81c6bdf4ba5f33bf1035d18de43` | `5a133bb2caad51a3e0a94cb5bb7f8c2f6ef4d4fd` | main |
| #23 | `e8e09f1868834a13b233817bccb0e188448fedc5` | `96c5e996f59154b550e055c3443522d82549555c` | main |
| #24 | `0de996a7f573edcb9d85eccd0eede51cf6305662` | `14378a27e96c7c8f5451f4698820f696a4e8c2c1` | main |

Actual Git ancestry includes every original head. At each retarget, merge-base was
the intended predecessor head; computed merge tree equaled the already-tested PR
head tree. After each merge, main was refreshed, ancestry checked and full tree
equality verified. Thus no duplicated upstream delta, missing commit, migration
rewrite, unexpected file change or conflict was introduced.

Base edits did not trigger new CI under the existing workflow event types.
All relevant exact-head platform/Windows checks were already complete; their tested
content matched the computed merge content. Repository rulesets were empty and
main's protection endpoint reported “Branch not protected”; none was weakened.
#15's resulting main CI was awaited and passed before #16. Subsequent main runs
were monitored; all passed except the explicitly accepted intermediate #16 CVE gate.

## Failure history and dependency policy

[Intermediate #16 main run 34740410219](https://github.com/BB-AI-Arena/MCP-Trust-Scoreboard/actions/runs/34740410219)
at `9872b7fa4578c7610391f616f0deb1e6032e513b` failed only
`container-security` under its old HIGH/CRITICAL policy. Logs explicitly identify
dependency findings; retained scans/SBOMs cover 13 service identities / 12 images.
Classification **D: accepted dependency finding**, not application/merge/scanner
execution failure. #17's [main run](https://github.com/BB-AI-Arena/MCP-Trust-Scoreboard/actions/runs/34740420826)
and the final feature-main runs passed under the superseding policy.

Known third-party dependency CVEs remain **accepted/informational for development/
alpha; hardening deferred**. Raw findings are retained, not called clean.
Scanner execution/inventory, secret, build, runtime, functional, migration and
data-integrity failures remain blocking. See [KNOWN_SECURITY_ISSUES.md](KNOWN_SECURITY_ISSUES.md).

Historical [SCM failure 34709938220](https://github.com/BB-AI-Arena/MCP-Trust-Scoreboard/actions/runs/34709938220),
[original #16 failure](https://github.com/BB-AI-Arena/MCP-Trust-Scoreboard/actions/runs/34670452399),
and [passing pre-merge SCM 34739821303](https://github.com/BB-AI-Arena/MCP-Trust-Scoreboard/actions/runs/34739821303)
remain evidence; no failed run/reference was deleted or assertion weakened.
Previous detailed reconciliation is preserved in
[the pre-merge report](https://github.com/BB-AI-Arena/MCP-Trust-Scoreboard/blob/0de996a7f573edcb9d85eccd0eede51cf6305662/docs/STACK_RECONCILIATION.md).

## Platform acceptance on feature-merged main

- Canonical platform version `2.0.0-alpha.1`, Python packaging `2.0.0a1`;
  four frontend versions agree. Sensor version `0.1.0`.
- **105 unit/contract tests passed**; default 33 gated skips are not substituted
  for the separate runtime/browser jobs.
- **19 installed-runtime/PostgreSQL integration tests**, zero failures/skips:
  API/worker, assessment jobs, fencing/recovery, migrations, JSON connector,
  durable webhook, Falcon fixture and endpoint persistence/correlation.
- **14 browser/full-stack tests**, zero failures/skips: four legacy workspaces,
  real submissions where supported, PDF/report downloads, recreation/upgrade/restore.
- Four frontend builds/PDF checks; Compose deployment boundaries; secret checks;
  Python/npm dependency audits; informational container scanning and CycloneDX SBOMs.
- Downloaded container evidence verifies **all 41 checksums**, actual source SHA,
  clean source and 13 service identities / 12 distinct images. Findings remain present.
- Local clean feature-main checkout independently passed 105 unit tests, compileall
  and a supplemental real PostgreSQL repeat-migration audit (below).

Run 34740514148 artifacts: runtime **10311879822**, acceptance **10312333784**,
containers **10311949637**, dependencies **10312363491**, Windows **10312024608**.
Artifacts are non-secret and have 14-day configured retention; preserve them before
expiry. Source checksums/manifest preparation are not signing or publication.

## Windows acceptance on feature-merged main

The release-preparation artifact records source
`14378a27e96c7c8f5451f4698820f696a4e8c2c1` directly, not a PR test merge.

| Evidence | Actual result |
|---|---|
| OS / runner / Go | Server 2022 amd64, build 20348; image 20260907.297.1; Go 1.26.8 |
| Native / portable | Nine native Windows tests/build; separate portable Go job passed |
| Sensor SHA-256 | `8d6259b931ac7c7690227fc5db0c80fbcca340afbcb41925b3a49757384e1ff8` |
| Identity | `NT SERVICE\\AgentTrustEndpoint-8a9b74573d55`, virtual account, non-elevated |
| Privilege / startup | SeChangeNotifyPrivilege; Automatic |
| Recovery | restart 5s / 30s / configured no action; reset 86400s; non-crash failures included |
| Bootstrap | protected transient data/bootstrap.json, SYSTEM/Admin/service SID ACL, successful enrollment and deletion |
| DPAPI | existing user scope; unrelated-user decryption rejected; identity survives stop/start and SCM crash recovery |
| Offline SCM spool | **2382 queued / 2382 recovered / 2382 uploaded** |
| Replay / loss | one replay attempt, exactly one persisted logical replay record; **0 dropped / 0 expired** |
| Revocation | authentication rejected before/after restart; same identity, no automatic reenrollment, history preserved |
| Uninstall | registration/executable removed; identity/spool/config/status/history/unrelated files preserved |
| Findings / receiver | SCM four delivered / five attempts; foreground five / six |
| Foreground offline | six recovered events, exactly one persisted replay record |
| Enforcement | **zero**, response executed=false |

Actual service health: AI/MCP/filesystem/software **degraded**, process
**permission_missing**, network/runtime **active**, DNS/UDP/file-writer **unsupported**.
No broad user-profile grants or LocalSystem workaround. Existing foreground
discovery/benign process/TCP/repository and Shadow AI acceptance still passes.

Evidence boundaries remain explicit: service JSON's static collector labels do not
override real health/conditional assertions. Full interactive-user fixture discovery
is foreground coverage, not proven virtual-account visibility. Behavioral/hash
fixtures are benign/synthetic, not live malware/C2. Server tests reject bootstrap
reuse; SCM enrollment/deletion is not a separate second-service redemption test.
SCM readback prints restart delays/reset but may omit the NONE row; first crash
recovery was exercised, not three consecutive failures. Literal reboot is unverified.
No mTLS, attestation, production signing, client-edition or non-Windows certification.

## Migrations and rollback

| Order | Exact file | Introduced |
|---|---|---|
| 001 | `001_initial.sql` | already on original main |
| 002 | `002_workspace_idempotency.sql` | #15 |
| 003 | `003_assessment_results.sql` | #15 |
| 004 | `004_connector_checkpoints.sql` | #21 |
| 005 | `005_endpoints.sql` | #23 |

No existing migration was rewritten. #24 and status documentation add none.
Fresh creation, 001→current with retained records/jobs, concurrent/repeated calls,
003→current, Falcon checkpoint and endpoint state are covered by the real suite.
The historical test name “003_to_004” applies through 005 and asserts five versions.

Supplemental clean-main disposable audit applied 001→005, ingested a real Falcon
fixture page and enrolled an endpoint, then repeated `create_schema` twice:
all **3 records, 5 jobs, 1 checkpoint, 1 endpoint** and exactly five migration
ledger entries were preserved. It passed separately; not included in the 19-test count.

Rollback preserves applied SQL/ledger, records, jobs, checkpoints and credentials.
Stop affected writers and reconcile/drain jobs before restoring compatible code.
For incompatible rollback use a verified backup restored to a separate database
and reconcile newer records before an owner-approved switch. Never reset operator
databases/volumes. Sensor uninstall preserves identity/spool/config/status/profile
and server history; account/machine/service-name changes need explicit reconciliation.

## Issue completion and remaining roadmap

After all seven merges and green actual-main release preparation, current issue
criteria were rechecked. Completion comments link PRs, source SHA, runs and limits;
only then were the seven completed issues closed with reason “completed”.

| Issue | Roadmap | State / disposition |
|---|---|---|
| #1 | ATP-A1 | completed: namespace/version/provider contracts (#12/#15) |
| #2 | ATP-A2 | completed: durable PostgreSQL/fenced jobs (#15) |
| #3 | ATP-A3 | completed: four legacy compatibility/alpha acceptance (#15/#16/#17) |
| #11 | ATP-A0 | completed: foundation children #1/#2/#3 |
| #18 | ATP-B3 | completed: generic JSON → durable webhook (#19) |
| #20 | ATP-B4 | completed: read-only Falcon fixture scope (#21); live tenant unverified |
| #22 | ATP-C1 | completed: original Windows v0.1 scope (#23/#24), with documented SCM limits |
| #5 | ATP-C2 | open: learned baselines, late/missing telemetry, poisoning resistance, anomaly/policy distinction, SDKs/OTel |
| #6 | ATP-E1 | open: multi-edge/cycle/provenance graph and artifact assurance |
| #7 | ATP-B2 | open: verification/snapshots/drift |
| #8 | ATP-D1 | open: future production/release operations and separate publication approval; alpha gates completed |
| #9 | ATP-F1 | open: optional enforcement/expiring approvals; not implemented |
| #10 | ATP-B1 | open: MCP/OpenAPI protocol collectors; discovery is not protocol collection |

The ID collision is resolved: #22 retains C1, #5 is C2 with all unfinished
baseline/SDK requirements preserved, and graph issue #6 is E1. C3 DLP and C4
vulnerability/malware intelligence remain future roadmap labels, not added features.
A core; B integrations/evidence; C endpoint; D release/operations; E graph/assurance;
F enforcement. Project statuses were not read or guessed.

## Revalidate a later reviewed main without publishing

```bash
git fetch origin
reviewed_main_sha=$(git rev-parse origin/main)
gh workflow run release-prepare.yml --repo BB-AI-Arena/MCP-Trust-Scoreboard \
  --ref main -f version=2.0.0-alpha.1 -f source_sha="$reviewed_main_sha"
```

Verify live main still equals the reviewed SHA before dispatch. Both reusable
workflows check out that input. Wait for every gate and the final prepare job;
download artifacts and verify source/hash/counts. Never substitute an earlier PR,
test-merge or source SHA. No release/tag/deployment action exists in this workflow.

If validation fails: A application regression, B merge defect, or E scanner/tool
execution failure blocks readiness. C environmental/harness failure needs concrete
evidence before rerun; preserve failure. D accepted dependency findings do not
block. Never weaken assertions to obtain green.

## Recommendation and accepted limits

**READY FOR MAINTAINER REVIEW FOR 2.0.0-alpha.1 PUBLICATION**, source-bound to the
passing actual-main evidence above and subject to the authorized documentation
merge's fresh final-main validation. No advertised-scope functional blocker remains.

Not production-hardened; accepted CVEs, no mTLS/signed installer, no Windows client
certification or literal reboot proof, no macOS/Linux sensor, DLP/enforcement/
quarantine, live Falcon production validation or enterprise SaaS certification.
Limited SCM interactive-user visibility is documented. These are limitations,
not newly invented alpha prerequisites. No release exists and nothing is published.
