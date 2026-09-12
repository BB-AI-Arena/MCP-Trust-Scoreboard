# Endpoint troubleshooting

- `enrollment required`: provision a device and enroll under the intended runtime
  account. Never copy the generic platform token into sensor configuration.
- `credential unavailable under this account`: DPAPI account/machine mismatch.
  Stop/reconcile and provision appropriately; do not disable encryption.
- `bootstrap_invalid_expired_or_consumed`: one-use 15-minute secret, possibly a
  lost enrollment response. Revoke/reconcile; no reuse bypass.
- 401 after enrollment: invalid/revoked device credential; events remain queued.
  Operator decides whether to retain/export/dispose them. Do not auto-reenroll.
- 409: an event ID has conflicting immutable data; spool remains for reconciliation.
  Do not assign replacement IDs to hide the conflict.
- `private destination not scoped`: add only the intended platform network to local
  CIDRs. Do not enable arbitrary private/link-local egress or disable TLS.
- `permission_missing`: protected processes or inaccessible registry/path metadata;
  other collectors may still work. No automatic administrator elevation.
- `degraded`: malformed/unsupported MCP JSON, out-of-scope/unavailable repository,
  snapshot cap, parser or OS-call error. Config changes do not execute discovered tools.
- Spool capacity/expiry: oldest events are removed with persisted cumulative loss
  counters; heartbeat reports the gap. These events cannot be recovered from cache.
- Spool corruption/disk-full: fail visibly and preserve files for operator action;
  the central heartbeat ages to offline. Do not reset the whole data directory.
- Healthy/degraded/offline/visibility_gap is available via authenticated
`GET /api/v1/endpoints`; sensor installation alone does not set healthy.

- Service will not start: inspect SCM state, virtual identity, owned-path ACLs
  and retained `data/status.json`; do not switch to LocalSystem.
- Service recovery: `sc.exe qfailure <name>` must show 5-second and 30-second
  delayed restarts followed by no action. A third rapid retry is not configured.
- DPAPI failure after account/name change: identity is user-bound. Reconcile and
  explicitly enroll with a fresh bootstrap; never copy `identity.dpapi`.
- Spool not draining: status reports `server_unavailable` or
  `authentication_rejected`; preserve the spool and reconcile connectivity or
  revocation rather than deleting the data directory.
- Endpoint revoked: authentication remains rejected after restart and automatic
  reenrollment does not occur. Provision and explicitly enroll a new identity.
- Uninstall removes only the owned executable and service registration; identity,
  spool and configuration remain for explicit local retention decisions.

Run native tests: `cd sensor; go test ./internal/sensor -v` on Windows. Full
acceptance is `scripts/windows_acceptance.ps1` **only in the isolated CI job**; it
requires RUNNER_TEMP and creates a uniquely named loopback-only PostgreSQL cluster.
It must never be pointed at an operator database. Evidence is retained by the
`Windows endpoint sensor` workflow, including logs on failure.

Signed installer/updater, service-account acceptance, short-lived ETW telemetry,
DNS/UDP/file-writer attribution, complete inventory, learned baselines, YARA rules,
CVE matching, DLP and enforcement are not completed capabilities.
