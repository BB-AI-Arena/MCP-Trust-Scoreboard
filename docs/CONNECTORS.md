# Reference connector path

Target: unreleased 2.0.0-alpha.1. Local/self-hosted, **not production-hardened**.
Dependency CVEs are [accepted for development/alpha](KNOWN_SECURITY_ISSUES.md);
this is not live vendor validation or release approval.

The [read-only CrowdStrike source](connectors/CROWDSTRIKE.md) extends this same
path with Hosts/Alerts retrieval, vendor-origin revisions and an operator sync-once
command. Source/destination dispatch is registered; no response adapter is enabled.
Its additive migration 004 stores private collector checkpoints. The reference
generic JSON behavior below remains unchanged (it does not use those checkpoints).

The generic JSON evidence source and webhook finding destination implement:

```text
authenticated JSON → normalized, claimed evidence → PostgreSQL ingestion job
  → worker transaction: evidence + rule findings + delivery jobs + completion
  → webhook outside database transaction → durable acknowledgment/result
```

## Roles and implemented capabilities

`EvidenceSource.normalize`, `FindingDestination.deliver`, and `ResponseAdapter`
are separate contracts under `agent_trust.adapters.connectors`. Registered adapters
are `generic-json` (ingest schema 1), `crowdstrike-falcon` (read host/alert evidence,
normalization schema falcon-1) and `webhook` (deliver findings schema 1).
`GET /api/v1/connectors` reports these roles; **no response adapter is registered**.
Neither source ingestion nor a destination HTTP 2xx means quarantine, remediation,
enforcement, or an action confirmed by an upstream product.

The API accepts strict versioned envelopes at
`POST /api/v1/connectors/generic-json/events` (existing `write` scope). Existing
`read` scope covers connector inventory, paginated `GET /api/v1/evidence`, findings,
and jobs. Bearer authentication binds workspace and collector identity server-side.
Submitted workspace/collector/verification/destination URL fields are rejected.
Reported agent identity remains a claim. The single configured API credential
identifies `api-token`; independent per-collector credential management is not
implemented. Do not treat this as shared multi-tenant isolation.

JSON fields: schema_version (`"1"`), event_id (1–128 characters), subject (1–256),
reported_agent_id (1–128), timezone-aware observed_at, optional deployment and
subject_version (≤128), optional artifact_digest (`sha256:` plus 64 lowercase hex),
and content (≤100,000 characters). Unknown fields/schema revisions fail 422.
One envelope per submission; list pagination defaults to 50, maximum 100.

The normalizer runs existing local rules without models or network access.
It discards raw content before enqueueing, retaining metadata, SHA-256 digests,
rule identifiers and static finding descriptions. Metadata can still be sensitive:
do not submit secrets as IDs/subjects. Digests are not verification or anonymization.
Evidence is `claimed`, method `authenticated_collector_report`; verification stays
null. These rules are limited indicators, not comprehensive security assessment.
No findings means evidence persisted with no delivery jobs, not proof of safety.

## Use without vendor credentials

Install/run the modular API and worker as documented in the README. Preserve your
existing database credentials; never run examples against operator databases as
tests. For a host-local disposable setup, start the supplied demo receiver:

```bash
python examples/connectors/local_receiver.py --port 9099
```

Configure the **worker process** (the API never accepts delivery URLs):

```bash
export AGENT_TRUST_WEBHOOK_URL=http://127.0.0.1:9099/findings
export AGENT_TRUST_WEBHOOK_ALLOWED_HOSTS=127.0.0.1
export AGENT_TRUST_WEBHOOK_ALLOWED_CIDRS=127.0.0.1/32
export AGENT_TRUST_WEBHOOK_ALLOW_HTTP=true
agent-trust-worker
```

This HTTP exception works only for explicitly scoped loopback fixtures. Inside
Compose, 127.0.0.1 is the worker container, **not your host**. Use a separately
configured HTTPS receiver, hostname allowlist and explicit private CIDR if needed;
never change production networking to make this host-local example work.
The integration test supplies an isolated TLS receiver and fixture CA without
requiring public infrastructure or vendor credentials.

With the API token already supplied privately in your shell:

```bash
curl --fail-with-body http://127.0.0.1:8080/api/v1/connectors/generic-json/events \
  -H "Authorization: Bearer $AGENT_TRUST_API_TOKEN" \
  -H 'Content-Type: application/json' \
  --data '{"schema_version":"1","event_id":"example-1","subject":"internal-tool","reported_agent_id":"agent-demo","observed_at":"2026-09-01T12:00:00Z","content":"eval(user)"}'
```

Response: 202 with a durable ingestion `job_id`. Poll `/api/v1/jobs/{job_id}` using
the same token. On completion, `result` contains `evidence_id`, `finding_ids` and
`delivery_job_ids`. Poll each delivery job independently. A successful result says
`accepted_by_destination`, includes the HTTP status and `response_action: null`.
View persisted records via `/api/v1/evidence` and `/api/v1/findings`.

The same event ID, collector and workspace reuses the ingestion job. Reusing the
ID with different canonical input returns 409 without overwriting the first event.
Unauthenticated requests return 401; insufficient scope 403; invalid envelope 422.

## Destination delivery and failure behavior

- HTTPS is required except the explicit loopback fixture above. Set
  `AGENT_TRUST_WEBHOOK_ALLOWED_HOSTS`; private targets also require explicitly
  configured `AGENT_TRUST_WEBHOOK_ALLOWED_CIDRS`. Link-local/metadata, multicast,
  unspecified/reserved addresses and URL credentials are rejected. IPv4-mapped
  IPv6 is checked as IPv4. Every resolved address is checked; connection uses the
  selected validated sockaddr, with no second DNS lookup. TLS verifies the original
  hostname and trust chain. No redirects or environment proxies are used.
- Optional `AGENT_TRUST_WEBHOOK_BEARER_TOKEN` is worker configuration only: never
  persisted or forwarded across redirects. Destination responses are bounded to
  4096 bytes and never retained/interpreted. Delivery envelopes are ≤64,000 bytes.
  Socket operations and response reading are bounded by the configured timeout
  (default 5 seconds, maximum 10); DNS resolution uses the system resolver.
- No configured destination yields `destination_unavailable`, not synthetic
  success. Errors are safe codes without URL, token or response content. The
  existing durable ledger retries at most three attempts with bounded backoff;
  terminal failed jobs retain findings/evidence. There is no automatic infinite
  retry or manual redrive endpoint in this slice.
- Delivery is **at least once**. The receiver must deduplicate `Idempotency-Key`
  / `delivery_id`, including across its own restarts. Acknowledgment followed by
  worker death before commit can redeliver the same ID. The supplied demo receiver
  uses bounded in-memory deduplication only; it is not a production destination.
- Pending jobs use the worker's current configured destination. Pause the worker
  and reconcile pending jobs before changing destination URL or credentials. No
  per-workspace destination configuration or multi-destination routing is claimed.

## Storage, upgrade, rollback and tests

The generic path uses existing versioned records and PostgreSQL job ledger
(migrations 001–003); the Falcon continuation adds private checkpoints in 004.
Evidence, findings, delivery enqueue and ingestion completion
commit together under the lease fence. Network calls never hold that transaction.
Raw content is discarded; metadata/jobs remain until operator-controlled retention.
No automated retention expiry is claimed. Existing assessment and legacy routes,
volumes, queue names and credentials are unchanged.

Before upgrade, back up and test restore separately using RUNTIME_VALIDATION.md.
Do not mix older workers with connector jobs: older workers reject unfamiliar
kinds. To roll back, stop ingestion and drain/stop new workers, preserve the ledger,
then restore the preceding API/worker version only after reconciling pending new
job kinds. Never delete volumes or restore over live data to roll back code.

```bash
.venv/bin/pytest tests/test_connectors.py -v
.venv/bin/pytest --run-integration tests/integration -v
```

Tests use actual local HTTP/TLS receivers, an installed API/worker and real
PostgreSQL, plus fast isolated SQLite contracts. External DNS/address failures
are injected where needed; no live vendor integration is verified. Existing
four-workspace browser/report, recovery, build and secret gates remain in CI.
