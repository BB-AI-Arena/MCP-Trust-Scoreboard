# Roadmap

Stable IDs are used for issues, board items, commits, and handoffs.

| ID | Target | Scope | Acceptance gate | Status |
| --- | --- | --- | --- | --- |
| ATP-A1 | 2.0.0-alpha.1 | Neutral naming, namespace, contracts, safe config, baseline CI | Import/version/branding checks | In progress |
| ATP-A2 | 2.0.0-alpha.1 | PostgreSQL records, job ledger, authenticated migration API | Persistence, retries, fencing, auth tests | In review (repair #15) |
| ATP-A3 | 2.0.0-alpha.1 | Legacy flow compatibility and honest docs | Four services remain runnable; demo limitations labeled | In review (partial) |
| ATP-B1 | 2.0.0-alpha.2 | Real MCP stdio/Streamable HTTP and OpenAPI import | Local fixture protocol tests and safe egress | Planned |
| ATP-B2 | 2.0.0-alpha.2 | Evidence, verification, snapshots, drift | Claimed/verified/observed states and diff tests | Planned |
| ATP-C1 | 2.0.0-beta.1 | Durable behavior events and baselines | Auth, duplicates, late data, warm-up tests | Planned |
| ATP-C2 | 2.0.0-beta.1 | Graph/artifact views and Python/JS SDKs | Multi-edge/cycle and telemetry mapping tests | Planned |
| ATP-D1 | 2.0.0-rc.1 | Recovery, upgrade, compatibility, packaging, release prep | Fresh/upgrade/rollback/end-to-end gates | Alpha subset in review; dependency risk accepted, hardening deferred |
| ATP-B3 | 2.0.0-alpha.1 | Connector framework, JSON evidence source, webhook finding destination | Authenticated durable end-to-end path with local receiver and retries | Implemented for review (#18); live vendor validation not claimed |
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
Current scope: ATP-B3, a vendor-neutral connector framework and JSON-to-webhook
reference path, with sources/destinations/response capabilities kept separate.
