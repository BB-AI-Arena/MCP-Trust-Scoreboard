# Stack and issue reconciliation

This report is based on the verified preflight on 2026-09-12 and the service
follow-up branch. No PR is merged by this work. GitHub Project status unverified:
active authentication lacks read:project. Project update not performed/verified
because active authentication lacks read:project.

## Merge order

| Order | PR | Current head | Base | Recommendation |
|---:|---:|---|---|---|
| 1 | #15 | `cbab41409d98fade11c2ccee316b7bebc1fab182` | `main` | Maintainer review; platform/runtime repair is ready apart from inherited review state |
| 2 | #16 | `6f9cdb8d8aac35b5647288200ecff16f31183fab` | #15 branch | Review after #15; functional gates pass, historical container findings are informational under #17 |
| 3 | #17 | `886560bb801be9c2d2a49627ea19d1ad3c5eee9d` | #16 branch | Review/accept risk policy; do not restart hardening |
| 4 | #19 | `e6bd77f93f7abd1aa2513a92aa146a9ecc5b5e8b` | #17 branch | Review generic JSON/webhook path |
| 5 | #21 | `9aa41c1bdbd3c81c6bdf4ba5f33bf1035d18de43` | #19 branch | Review read-only Falcon adapter; live vendor validation remains pending |
| 6 | #23 | `e8e09f1868834a13b233817bccb0e188448fedc5` | #21 branch | Add this service follow-up, then rerun exact-head Windows/platform CI |

All six PRs were open at preflight. Mergeability and final CI must be refreshed
after this branch is pushed; no dependent PR should be rebased automatically.

## Migration reconciliation

The repository contains additive migrations 001, 002, 003, 004 and 005. Existing
integration tests exercise fresh creation, concurrent/repeated migration calls,
003→004 upgrade, and endpoint state retention through migration 005. The service
slice adds no migration. Rollback remains: stop endpoint ingestion, drain or
reconcile endpoint jobs, restore preceding API/worker code while preserving
records and migration state; never reset a volume or rewrite applied SQL.

## Open issue audit

| Issue | Roadmap | Implemented / tested | Merged | Still needed / recommendation |
|---:|---|---|---|---|
| #1 | ATP-A1 | Namespace/contracts implemented and covered | No | Keep open until stack is merged and main validation passes |
| #2 | ATP-A2 | Durable PostgreSQL ledger, fencing and migrations tested | No | Keep open pending merge/main validation |
| #3 | ATP-A3 | Four legacy surfaces and acceptance tested | No | Keep open pending merge/main validation |
| #5 | ATP-C1 collision source | Requirements remain for future behavioral baselines/SDK/OpenTelemetry | No | Keep open; re-ID to ATP-C2, preserve telemetry/baseline/poisoning requirements |
| #6 | ATP-E1 (re-ID from ATP-C2) | Graph/artifact scope planned | No | Keep open; preserve graph, artifact, provenance, cycle and declared/effective/observed requirements |
| #7 | ATP-B2 | Evidence verification/snapshots/drift not complete | No | Keep open |
| #8 | ATP-D1 | Alpha subset implemented; broader release work remains | No | Keep open |
| #9 | ATP-F1 | Enforcement intentionally absent | No | Keep open |
| #10 | ATP-B1 | MCP/OpenAPI protocol collectors not complete | No | Keep open |
| #11 | ATP-A0 | Foundation children remain in review | No | Keep open until dependent stack is accepted |
| #18 | ATP-B3 | Generic JSON/webhook path tested in #19 | No | Keep open until #19 merges |
| #20 | ATP-B4 | Falcon adapter fixture-tested; live validation pending | No | Keep open |
| #22 | ATP-C1 | Foreground slice passes; SCM follow-up is this branch | No | Keep open until service CI and merged-main validation pass |

No issue should be closed while its implementation remains in review unless the
maintainer's repository convention explicitly permits that transition.

## Alpha recommendation

NOT READY. Concrete blockers in advertised alpha scope are maintainer acceptance
of the stacked PRs, exact-source reruns after merge, and completion of the Windows
SCM acceptance workflow. Known dependency CVEs are not blockers under the accepted
development/alpha policy. Literal reboot persistence, Windows client editions,
signing, mTLS, DLP, enforcement, other endpoint OSes and broader vendor coverage
remain documented limitations rather than newly invented release gates.
