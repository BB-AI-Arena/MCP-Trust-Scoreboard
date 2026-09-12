# Roadmap

Stable IDs are used for issues, board items, commits, and handoffs.

| ID | Target | Scope | Acceptance gate | Status |
| --- | --- | --- | --- | --- |
| ATP-A1 | 2.0.0-alpha.1 | Neutral naming, namespace, contracts, safe config, baseline CI | Import/version/branding checks | In progress |
| ATP-A2 | 2.0.0-alpha.1 | PostgreSQL records, job ledger, authenticated migration API | Persistence, retries, fencing, auth tests | In review (repair #15) |
| ATP-A3 | 2.0.0-alpha.1 | Legacy flow compatibility and honest docs | Four services remain runnable; demo limitations labeled | In review (partial) |
| ATP-B1 | 2.0.0-alpha.2 | Real MCP stdio/Streamable HTTP and OpenAPI import | Local fixture protocol tests and safe egress | Planned |
| ATP-B2 | 2.0.0-alpha.2 | Evidence, verification, snapshots, drift | Claimed/verified/observed states and diff tests | Planned |
| ATP-C1 | 2.0.0-alpha.1 (sensor slice) | Windows observe-only endpoint sensor (#22); broader baselines remain future | Real Windows → offline spool → typed PostgreSQL evidence → finding → webhook | In progress; Windows CI pending |
| ATP-C2 | 2.0.0-beta.1 | Graph/artifact views and Python/JS SDKs | Multi-edge/cycle and telemetry mapping tests | Planned |
| ATP-D1 | 2.0.0-rc.1 | Recovery, upgrade, compatibility, packaging, release prep | Fresh/upgrade/rollback/end-to-end gates | Alpha subset in review; dependency risk accepted, hardening deferred |
| ATP-B3 | 2.0.0-alpha.1 | Connector framework, JSON evidence source, webhook finding destination | Authenticated durable end-to-end path with local receiver and retries | Implemented for review (#18); live vendor validation not claimed |
| ATP-B4 | 2.0.0-alpha.1 | Read-only CrowdStrike host/alert source | TLS fixture + PostgreSQL checkpoint/revision/worker/webhook tests | In review (#20, PR #21); live validation pending |
| ATP-E1 | 2.0.0 | Human-reviewed stable release | Maintainer review after D; no automatic release | Planned |
| ATP-F1 | 2.1.0 | Optional inline enforcement and expiring approvals | Denied calls never reach upstream; replay-proof approvals | Planned |

Runtime repair continuation: PR #12 is merged, but Phase A is not complete.
UI work remains paused; owner-authorized connector development has resumed in
PR #19 (base PR #17, which depends on #16/#15). ATP-A2 persistence and the inherited
ATP-A3 source dependency repairs passed local and remote CI. The alpha acceptance
subset passes under the owner risk policy; maintainer review and broader roadmap
completion remain separate from those measured checks.
See [implementation status](IMPLEMENTATION_STATUS.md) for measured results.

Alpha acceptance continuation: `test/alpha-release-acceptance` depends on open
PR #15. Full Compose/browser/report, recreation/upgrade/restore and scan/SBOM CI
gates are implemented, not automatically accepted or released. ATP-A3 remains
In review; dependency CVEs no longer block development or alpha preparation.
Scanner execution and functional/data-integrity checks plus maintainer review
remain required. No future-phase issue is complete from interfaces alone.
Current scope: owner-selected ATP-C1 / #22 Windows Endpoint Sensor v0.1, based on
open PR #21. ATP-B4 remains in review with live Falcon validation pending. Sources,
destinations and response authority remain separate; this endpoint slice adds no
enforcement and does not complete learned baselines or the whole C milestone.
