# Roadmap

Stable IDs are used for issues, board items, commits, and handoffs.

| ID | Target | Scope | Acceptance gate | Status |
| --- | --- | --- | --- | --- |
| ATP-A1 | 2.0.0-alpha.1 | Neutral naming, namespace, contracts, safe config, baseline CI | Import/version/branding checks | In progress |
| ATP-A2 | 2.0.0-alpha.1 | PostgreSQL records, job ledger, authenticated migration API | Persistence, retries, fencing, auth tests | In progress |
| ATP-A3 | 2.0.0-alpha.1 | Legacy flow compatibility and honest docs | Four services remain runnable; demo limitations labeled | In progress |
| ATP-B1 | 2.0.0-alpha.2 | Real MCP stdio/Streamable HTTP and OpenAPI import | Local fixture protocol tests and safe egress | Planned |
| ATP-B2 | 2.0.0-alpha.2 | Evidence, verification, snapshots, drift | Claimed/verified/observed states and diff tests | Planned |
| ATP-C1 | 2.0.0-beta.1 | Durable behavior events and baselines | Auth, duplicates, late data, warm-up tests | Planned |
| ATP-C2 | 2.0.0-beta.1 | Graph/artifact views and Python/JS SDKs | Multi-edge/cycle and telemetry mapping tests | Planned |
| ATP-D1 | 2.0.0-rc.1 | Recovery, upgrade, compatibility, packaging, release prep | Fresh/upgrade/rollback/end-to-end gates | Planned |
| ATP-E1 | 2.0.0 | Human-reviewed stable release | Maintainer review after D; no automatic release | Planned |
| ATP-F1 | 2.1.0 | Optional inline enforcement and expiring approvals | Denied calls never reach upstream; replay-proof approvals | Planned |
