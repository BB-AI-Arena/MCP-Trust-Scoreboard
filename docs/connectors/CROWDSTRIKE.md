# CrowdStrike Falcon: read-only evidence source

Target: **unreleased 2.0.0-alpha.1**, local/self-hosted, not production-hardened.
Implementation contract `falcon-1`, reviewed against official references on
2026-09-12. **Local TLS protocol-fixture tested; live CrowdStrike validation pending.**
Accepted third-party dependency CVEs remain informational; no hardening work or
new unrelated release prerequisites are introduced here.

This source reads endpoint context and vendor alerts, commits normalized ingestion
jobs/checkpoints, and reuses the worker's evidence/finding/webhook path. Host context
does not generate a finding. Alerts become **vendor-origin findings**, not results
of keyword-scanning their descriptions. No containment, remote commands, alert
modification, policy changes, token revocation or response adapter is implemented.

## Vendor contract and permissions

A small typed Python client uses the existing address-pinned TLS transport; no
Falcon SDK dependency is installed. API operation versions are independent of
application and normalization versions. Only these operations are allowlisted:

| Operation | HTTP route | Required scope / purpose |
| --- | --- | --- |
| oauth2AccessToken | POST `/oauth2/token` | OAuth client credentials, token issuance only |
| QueryDevicesByFilterScroll | GET `/devices/queries/devices-scroll/v1` | **Hosts: READ**, host IDs |
| GetDeviceDetailsV2 | GET `/devices/entities/devices/v2` | **Hosts: READ**, host details |
| PostCombinedAlertsV1 | POST `/alerts/combined/alerts/v1` | **Alerts: READ**, cursor-based alert retrieval |

References: [OAuth2](https://developer.crowdstrike.com/api-reference/collections/oauth2/#oauth2accesstoken),
[Hosts](https://developer.crowdstrike.com/api-reference/collections/hosts/#querydevicesbyfilterscroll),
[Alerts](https://developer.crowdstrike.com/api-reference/collections/alerts/#postcombinedalertsv1).
The selected Alerts POST reads data; it is not an alert mutation. Combined v1 is
documented without a deprecation marker; deprecated query/entity v1 alternatives
are not used. Do **not** grant Hosts WRITE, Alerts WRITE, RTR, admin or response scopes.

Host scrolling returns an opaque offset with a documented two-minute lifetime;
vendor page limit is 10,000. Alert combined retrieval returns `meta.pagination.after`
until the terminal page and allows up to 1,000 records. Its sort syntax differs
from Hosts: the adapter uses `created_timestamp|asc` for Alerts and `device_id.asc`
for Hosts. The Alerts sort field is immutable, as recommended by the vendor to
avoid skips while records change. See the [official Alerts pagination guidance](https://github.com/CrowdStrike/falconpy/wiki/Alerts#postcombinedalertsv1).
The adapter deliberately caps both page sizes at **100**, including host-detail IDs.

Explicitly configured commercial regions (no autodiscovery or redirects):

| `--region` | Origin |
| --- | --- |
| us-1 | `https://api.crowdstrike.com` |
| us-2 | `https://api.us-2.crowdstrike.com` |
| eu-1 | `https://api.eu-1.crowdstrike.com` |

These origins follow [CrowdStrike's region configuration reference](https://github.com/CrowdStrike/falconpy/wiki/Environment-Configuration).
Other clouds, Flight Control/member-CID impersonation and cross-account aggregation
are not supported by this slice. Each returned resource must carry the configured
account CID. An empty successful query does not verify that configured account
against returned data, nor does API authentication prove a vendor conclusion true.

## Installation and private configuration

Use the existing platform installation and PostgreSQL configuration. Developer
installation: `python -m pip install -e '.[postgres,test]'`. Runtime-only installation:
`python -m pip install '.[postgres]'`; the platform image also installs the command.
No test packages are required in the installed runtime.

Supply credentials privately in the collector process environment through your
existing secret manager or protected shell configuration:

- `AGENT_TRUST_FALCON_CLIENT_ID`
- `AGENT_TRUST_FALCON_CLIENT_SECRET`
- Existing `DATABASE_URL`, `AGENT_TRUST_WORKSPACE_ID`, `AGENT_TRUST_API_TOKEN` for sync.

No credentials are accepted as CLI flags, persisted in jobs/checkpoints/findings,
or printed. The collector does not automatically read `.env`; load only the private
configuration you intend for this process. Do not paste credentials into issues,
commands in shared logs, this document, or CI. Connection ID is an operator-chosen
stable identifier, **not** a client secret. Account CID is the expected Falcon tenant:
32 lowercase hexadecimal characters, not the sensor-install CID with checksum suffix.

Connection checking performs bounded reads without local writes:

```bash
agent-trust-falcon check --connection falcon-primary --account-cid "$FALCON_ACCOUNT_CID" --region us-1
```

An empty result reports `read_ok_empty`; missing credentials, unauthorized clients,
missing read permission, unavailable services and malformed/partial responses are
distinct safe error codes. Exit **0** means the requested bounded work completed;
exit **2** means partial/unavailable/configuration failure. Completion is not an
assertion of whole-estate coverage or enforcement.

## Sync once and inspect persisted results

Start the existing `agent-trust-worker` with the destination configuration from
[CONNECTORS.md](../CONNECTORS.md). It needs webhook credentials, **not** Falcon
credentials. Keep the collector's Falcon credentials out of API/worker environments.

```bash
agent-trust-falcon sync-once --connection falcon-primary --account-cid "$FALCON_ACCOUNT_CID" --region us-1 --page-size 100 --max-pages 5 --seconds 120
```

For the running README Compose stack, execute the installed command in a one-off
container on its existing network (do not publish PostgreSQL ports). With the two
Falcon variables already exported privately in the invoking shell:

```bash
docker compose run --rm --no-deps -e AGENT_TRUST_FALCON_CLIENT_ID -e AGENT_TRUST_FALCON_CLIENT_SECRET worker-platform agent-trust-falcon sync-once --connection falcon-primary --account-cid "$FALCON_ACCOUNT_CID" --region us-1
```

Use images built from this feature after maintainer review. This command is an
operator instruction, not a deployment performed by the tests or this change.

Defaults: initial previous 24 hours of **updated** alerts, up to five pages per
stream, 100 records/page, 120-second request budget. Bounds: 1–20 pages per stream,
1–100 records/page, 1–300 seconds. `--since` accepts an aware ISO timestamp within
the preceding 30 days; it sets the initial/replay backfill, not an in-progress window.
The collector has a finite request budget including retries. No scheduler/daemon
or new service is added; invoke sync-once again to continue an unfinished window.
Hosts are current inventory, not historical host inventory for the alert interval.

Summary fields include per-stream pages committed, records submitted (including
unchanged records reusing existing jobs), cursor replays, errors and coverage.
`complete` means the bounded queries reached their end. Ingestion may still be
queued, and destination delivery may be pending or failed independently.

Read normalized evidence and revision-specific findings through the existing
authenticated API:

```bash
curl --fail-with-body -H "Authorization: Bearer $AGENT_TRUST_API_TOKEN" http://127.0.0.1:8080/api/v1/connectors
curl --fail-with-body -H "Authorization: Bearer $AGENT_TRUST_API_TOKEN" 'http://127.0.0.1:8080/api/v1/evidence?limit=100'
curl --fail-with-body -H "Authorization: Bearer $AGENT_TRUST_API_TOKEN" 'http://127.0.0.1:8080/api/v1/findings?limit=100'
```

Pagination remains `limit`/`offset`, maximum 100. Delivery envelopes/receiver
acknowledgments expose a durable delivery ID; inspect `/api/v1/jobs/{id}` for
independent retry/result status. There is no new source-specific UI or filtered
job-list endpoint in this slice.

## Identity, mapping, revisions and retained fields

Logical identities hash the workspace, configured connection, vendor account,
resource type and original vendor ID; original IDs remain in evidence. Revisions
hash allowlisted fields, descriptive-text digest, explicit mapping and normalizer
version. Unchanged revisions reuse the same durable job; changed status/content
creates a new immutable revision under the same logical alert ID. Old revisions
and their collection provenance remain. Generic JSON retains its immutable-event
409 behavior; vendor revisions do not weaken that contract.

| Source fields | Retained interpretation |
| --- | --- |
| Host `device_id`, CID, hostname, platform, sensor version, timestamps, status | Endpoint inventory context, not an AI agent or automatic finding |
| Alert `composite_id`, original `id`, CID, product/type, created/updated/event timestamps | Original alert identity and provenance |
| Alert `agent_id` | Falcon endpoint/sensor identity only |
| Alert severity number/name, status | Source values retained; recognized severity names normalized, unknown stays unknown |
| Description/display name/name | SHA-256 digest only; text discarded before enqueue |
| Command lines, usernames, IPs, assignment details, other unselected fields | Not persisted or delivered |

No model, keyword rules, vendor-score probability calibration or platform rule ID
is attached to imported alerts. Findings say `origin: vendor_alert`; evidence is
`claimed`, with `verification: null` and method `authenticated_vendor_api_read`.
Metadata (especially hostnames), IDs and hashes may still be sensitive; hashes
are not anonymization. No automated retention expiry is introduced.

Optional explicit operator mapping is a private JSON file:

```json
{"<Falcon device ID>": "<existing platform agent ID>"}
```

Pass `--agent-map /absolute/path/to/private-map.json`. Every mapped agent must
already be registered in the configured workspace. The mapping links entities;
it is **not proof that an AI agent caused an alert**. Unmapped alerts remain vendor
context, with no fabricated agent identity. Mapping changes require explicit
`--replay --since <timestamp>` to avoid silently mixing mappings in one traversal.

## Checkpoint, retry and outbound delivery semantics

Migration **004_connector_checkpoints.sql** adds one private checkpoint table;
generic record APIs cannot write it. Existing tables/data/credentials/volumes/queue
names are unchanged. A PostgreSQL **session** advisory lock excludes another
collector for the same workspace/connection. Use direct PostgreSQL or session
pooling, not transaction-mode connection pooling for the collector.

The session has no open transaction during vendor calls. After a page is validated,
all its normalized ingestion jobs and its next cursor commit together. A process
death or failed commit replays that page; it cannot checkpoint unseen records.
The existing worker atomically commits evidence/findings/delivery enqueue with
ingestion completion under its lease fence. No second durable queue is introduced.

Host cursors older than 110 seconds restart that host traversal. An invalid cursor
response while resuming triggers at most one cursor rewind per stream/invocation,
persisted even when the page budget is exhausted; a repeated invalid request is
reported, not skipped. Alert cursor recovery replays the **same fixed time window**.
After both streams complete, the next alert window overlaps the previous upper
bound by five minutes. Overdue checkpoints beyond the 30-day bound require explicit
replay rather than silent truncation. `--replay` preserves data and deduplicates
existing revisions; it never deletes jobs or findings.

Falcon pagination is live data, not a snapshot. Changes/late indexing beyond the
overlap and upstream retention can limit completeness; replay an explicit window
when reconciling gaps. Deleted/hidden alerts, audit-history completeness, removed
hosts and revisions never returned by Falcon are not recovered or fabricated.

OAuth expiry follows `expires_in`; a read 401 refreshes at most once within three
attempts. A 403 does not trigger scope escalation. Transport/429/selected 5xx retry
boundedly. Standard Retry-After (seconds/date) and vendor X-Ratelimit-Retryafter
(Unix time) are respected; waits over five seconds are persisted as `not_before`
instead of sleeping or retrying early. See [CrowdStrike retry guidance](https://www.crowdstrike.com/tech-hub/ng-siem/api-pagination-strategies-for-falcon-foundry-functions-and-workflows/)
and [official PSFalcon header handling](https://github.com/CrowdStrike/psfalcon/blob/master/class/Class.ps1).
Bodies are bounded to 2 MB, socket/response operations to five seconds. DNS uses
the system resolver; the wall-clock budget is not a substitute for resolver/DB
timeouts. TLS chain/hostname validation, address pinning/private-target restrictions
and no redirects/proxies are inherited from the reference transport.

Webhooks are unchanged: at-least-once delivery with stable retry IDs and
revision-specific deduplication. Revisions may arrive out of order; receivers must
use logical ID, revision and vendor timestamps, not arrival order, to maintain
their own current view. HTTP acknowledgment means acceptance, not response execution.
Pending deliveries use existing worker destination configuration: **pause/reconcile
pending jobs before changing destination URL or credentials**. No rerouting feature
or new destination/response implementation is added.

## Upgrade, rollback and validation

Back up and verify restore separately using [RUNTIME_VALIDATION.md](../RUNTIME_VALIDATION.md).
Apply migration 004 through normal API/worker/collector startup; repeat application
is tested. Stop older workers before queueing Falcon records: they do not recognize
the new source. To roll back, stop collection, drain/reconcile connector jobs, then
restore the preceding code while preserving the additive checkpoint table and all
records. Never remove user volumes or restore over live data. Resume with the same
connection/account/region; identity changes require a new connection ID.

```bash
.venv/bin/pytest tests/test_falcon.py tests/test_connectors.py -v
.venv/bin/pytest --run-integration tests/integration -v
.venv/bin/python -m compileall -q src tests
```

Tests use synthetic documented response shapes over actual local TLS, actual
adapter/installed command, real PostgreSQL, API/worker and webhook receiver. They
cover auth expiry/errors, rate limits, malformed/partial pages, cursor replay,
transaction failure, concurrent collection exclusion, revisions, mappings,
restart/delivery dedup and migration 003→004. Existing generic JSON, assessment,
browser/report/recovery/scan/SBOM/secret checks remain required in CI.

Optional purpose-authorized **live smoke**, never run by ordinary CI:

```bash
agent-trust-falcon live-smoke --authorize-live-read --connection falcon-primary --account-cid "$FALCON_ACCOUNT_CID" --region us-1
```

This reads at most one host and one alert, with a 12-request/40-second request
budget, and persists nothing. Run only with credentials supplied privately for
that purpose. It does not validate all regional/schema variants or certify
production readiness. No such credentials were supplied for this run: **live
validation remains pending**, not a development blocker.
