# Roadmap

Stable IDs are used for issues, board items, commits, and handoffs.

Current scope is reconciliation only; new feature development is stopped.
Authoritative heads, CI, issue dispositions and merge/main-validation gates:
[STACK_RECONCILIATION.md](STACK_RECONCILIATION.md). Statuses here describe repository
work, not verified Project fields. GitHub Project status unverified: active authentication lacks read:project.
Families: A core platform; B external integrations/evidence; C endpoint security;
D release/operations; E graph/assurance; F enforcement.

| ID | Target | Scope | Acceptance gate | Status |
| --- | --- | --- | --- | --- |
| ATP-A1 | 2.0.0-alpha.1 | Neutral naming, namespace, contracts, safe config, baseline CI | Import/version/branding checks | In review |
| ATP-A2 | 2.0.0-alpha.1 | PostgreSQL records, job ledger, authenticated migration API | Persistence, retries, fencing, auth tests | In review (repair #15) |
| ATP-A3 | 2.0.0-alpha.1 | Legacy flow compatibility and honest docs | Four services remain runnable; demo limitations labeled | Alpha slice in review |
| ATP-B1 | 2.0.0-alpha.2 | Real MCP stdio/Streamable HTTP and OpenAPI import | Local fixture protocol tests and safe egress | Planned |
| ATP-B2 | 2.0.0-alpha.2 | Evidence, verification, snapshots, drift | Claimed/verified/observed states and diff tests | Planned |
| ATP-C1 | 2.0.0-alpha.1 (sensor slice) | Windows observe-only sensor (#22), including SCM service acceptance | Foreground + service → offline spool → typed PostgreSQL evidence → finding → webhook | Passing stack acceptance; PR #23/#24 in review |
| ATP-C2 | 2.0.0-beta.1 | Endpoint behavioral detection, baselines, SDK/OpenTelemetry mappings (#5) | Duplicate/late telemetry, missing indicators, poisoning resistance, anomaly/policy distinction | Planned |
| ATP-C3 | 2.0.0-beta.1 | DLP / sensitive data protection | Explicit privacy and response authority gates | Planned |
| ATP-C4 | 2.0.0-beta.1 | Endpoint vulnerability / malware intelligence | Bounded inventory, matching and evidence tests | Planned |
| ATP-D1 | 2.0.0-rc.1 | Recovery, upgrade, compatibility, packaging, release prep | Fresh/upgrade/rollback/end-to-end gates | Alpha subset in review; dependency risk accepted, hardening deferred |
| ATP-B3 | 2.0.0-alpha.1 | Connector framework, JSON evidence source, webhook finding destination | Authenticated durable end-to-end path with local receiver and retries | Implemented for review (#18); live vendor validation not claimed |
| ATP-B4 | 2.0.0-alpha.1 | Read-only CrowdStrike host/alert source | TLS fixture + PostgreSQL checkpoint/revision/worker/webhook tests | In review (#20, PR #21); live validation pending |
| ATP-E1 | 2.0.0-beta.1 | Graph and artifact assurance views (#6) | Multi-edge/cycle, declared/effective/observed and provenance tests | Planned |
| ATP-E2 | 2.0.0 | Human-reviewed stable release | Maintainer review after D; no automatic release | Planned |
| ATP-F1 | 2.1.0 | Optional inline enforcement and expiring approvals | Denied calls never reach upstream; replay-proof approvals | Planned |

PR #12 is merged; the #15→#16→#17→#19→#21→#23→#24 stack remains open.
Platform and Server 2022 foreground/SCM acceptance pass on the final implementation
tree; PR #16 retains its historical CVE-only failure superseded by #17's policy.
Remaining alpha gates are maintainer merge and final validation on actual main.
Known dependency CVEs remain accepted/informational; execution, secret and
functional/data-integrity gates remain required. No production-hardening claim.

#22 owns ATP-C1. #5 moves from C1 to C2, preserving learned baselines, late/duplicate
events, missing telemetry, poisoning resistance, anomaly/policy distinction and
Python/JavaScript SDK/OpenTelemetry requirements not delivered by endpoint v0.1.
#6 moves from C2 to E1 without losing graph/artifact assurance requirements.
Sources, destinations and response authority remain separate. No new feature,
enforcement, issue closure or publication is authorized by this reconciliation.
