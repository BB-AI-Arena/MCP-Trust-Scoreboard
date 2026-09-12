# Windows Endpoint Sensor v0.1

Observe-only, **not production-hardened**, not an EDR replacement. Sensor version
0.1.0; platform remains unreleased 2.0.0-alpha.1. No prevention/response capability.

## Validation boundary

The dedicated `Windows endpoint sensor` workflow targets **windows-2022 x64**.
Verified initial source `bebcaa09d8705befa83b6fa84923276591f8b2de`: **Windows Server
2022 x64 build 20348**, runner image `20260907.297.1`, six native tests plus the full
foreground vertical scenario passed. [Windows run 34679332513](https://github.com/BB-AI-Arena/MCP-Trust-Scoreboard/actions/runs/34679332513),
artifact `windows-endpoint-34679332513-1` / `10293057019`. Downloaded
`acceptance.json` confirms six offline events recovered, one replay deduplicated,
five findings accepted in six webhook attempts, and zero blocking actions.
Initial executable SHA-256 `68206c170558c833f89502bcb46fc8460f6472651cdda46bc8ae882c63c4246e`.
Exact final-source evidence is linked in PR #23; do not infer it from this earlier
snapshot. Windows 10/11, ARM64 and other service-account configurations are not yet
validated. Cross-compilation alone is not a Windows-support claim.

Latest verified implementation source **1a5eefa8bdf7d3d9ee2c15156270ec9bc90c64bf**:
[Windows run 34680187120](https://github.com/BB-AI-Arena/MCP-Trust-Scoreboard/actions/runs/34680187120)
(artifact **10293223676**) and PR run 34680189435 passed **eight native tests**
and the foreground scenario on the same Windows build/image. Ten offline events
recovered; exactly one persisted replay record; five findings accepted after six
webhook attempts; zero blocking actions. Binary SHA-256:
`3c22332a69841751a1ee091410a4a13df3df88dbd53b2d3eb8d422a0481c9171`.
All ten existing CI jobs also passed (34680187103 / 34680189468).
An earlier run 34679870733 failed a replay-count assertion using moving offset
pages. The repaired harness verifies multiplicity in a single PostgreSQL snapshot;
a regression deliberately inserts a true duplicate and confirms it is not hidden.
Raw failure evidence remains retained. Subsequent documentation-only heads and
their exact CI results are recorded on PR #23.

The acceptance harness uses real Toolhelp, IP Helper, file identities, DPAPI,
registry/OS inventory, API, worker and disposable PostgreSQL. Cursor discovery uses
a benign helper at a fixture installation path, not an installed commercial IDE.
MCP JSON is synthetic and never executed. Network-suspicion telemetry is synthetic;
the benign child TCP connection is independently observed by the real collector.
File create/modify/rename/delete and a bounded rename burst use disposable files.

## Build and install (operator-controlled)

Install Go 1.26.8 from the official distribution. From `sensor`:

```powershell
$env:CGO_ENABLED = '0'
go mod verify
go test ./internal/sensor -v
go build -trimpath -o dist/agent-trust-sensor.exe ./cmd/agent-trust-sensor
Get-FileHash dist/agent-trust-sensor.exe -Algorithm SHA256
```

Only `agent-trust-sensor.exe` is the sensor. Never install `fixture-process.exe`.
Copy the sensor to an administrator-controlled directory. Build inventory is
available with `go version -m -json`; checksums are integrity evidence, not code
signatures. Authenticode signing and a reviewed installer/update channel remain
future packaging work; this run publishes no package or binary.

Use an HTTPS origin for the central API, with its existing restrictive ingress
configuration. The sensor verifies TLS, rejects redirects/proxies and connects to
validated addresses. Private deployments need explicit CIDRs. Only deliberate
loopback test configuration permits HTTP. Do not expose the legacy APIs as an
endpoint ingestion proxy.

## Enrollment and policy

An authenticated platform administrator (existing `write` scope) provisions a
device at `POST /api/v1/endpoints/provision`. Body is a strict endpoint policy:

```json
{
  "repositories": [{"id":"58c6b85e-3453-4e09-b07b-29aace16311a", "path":"C:\\Work\\Example", "classification":"Restricted"}],
  "approved_tools": [],
  "custom_tools": [],
  "mcp_paths": []
}
```

The centrally assigned repository UUID is stable across path-name changes in
operator records; it is not inferred from a folder name. This first version uses
an immutable enrollment policy. Updating it requires stopping collection and
reconciling/re-enrolling; fleet policy revision APIs are follow-up work. No policy
field authorizes commands, scripts or prevention. Public/Internal/Confidential/
Restricted/Regulated are supported. An empty approved list approves no AI tools.

Provisioning returns a unique endpoint ID and a **single-use 15-minute bootstrap
secret**. Keep that response private/in memory. Do not log it or write it to disk.
Set `AGENT_TRUST_ENROLLMENT_SECRET` privately in the enrollment process environment.
No generic administrator credential is copied to the endpoint.

Create a private local JSON configuration (no secrets in this file):

```json
{
  "server":"https://trust.example.internal",
  "endpoint_id":"<provisioned UUID>",
  "data_dir":"C:\\ProgramData\\AgentTrust\\Sensor",
  "allowed_roots":["C:\\Work\\Example", "C:\\Users\\assessed-user"],
  "profile_roots":["C:\\Users\\assessed-user"],
  "allowed_cidrs":["10.20.30.0/24"],
  "interval_seconds":2,
  "spool_count":10000,
  "spool_bytes":33554432,
  "spool_hours":168
}
```

The local approved roots constrain centrally selected repository/tool/config paths;
no whole-filesystem default exists. Use a dedicated restricted data directory and
protect the configuration from other users. Sensor enrollment applies an inheritable
DACL granting the enrolling user, administrators and SYSTEM only to the data path.
Enrollment refuses a nonempty preexisting data directory; it must not change
permissions on arbitrary operator data. A no-sharing lock file excludes competing
sensor processes across Windows sessions and releases on process death.

```powershell
.\agent-trust-sensor.exe enroll --config C:\Private\sensor.json
.\agent-trust-sensor.exe run --config C:\Private\sensor.json
.\agent-trust-sensor.exe version
```

The bootstrap secret is exchanged for a unique device bearer credential; server
stores SHA-256 hashes, Windows stores user-bound **DPAPI ciphertext** in
`<data_dir>\identity.dpapi`. Enroll/run under the same account on the same machine.
Do not clone identity files. Bootstrap response loss after server consumption
requires administrator reconciliation/new provisioning; there is no insecure
reusable-bootstrap fallback. mTLS/device key enrollment is the migration target,
not implemented attestation. `POST /api/v1/endpoints/{id}/revoke` revokes ingestion
and policy access immediately for subsequent requests; already committed evidence
jobs remain forensic records. The sensor does not execute a response to revocation.

## Service runtime and uninstall

The supported development service path is `scripts/windows_service.ps1`. It
creates a virtual account `NT SERVICE\<service-name>`, automatic startup, and
bounded SCM recovery: restart after 5 seconds and 30 seconds, then stop; reset
after 24 hours. Non-crash exits are included. The helper captures SCM state,
recovery, service DACL, token identity and owned-path ACLs.

The account has access only to owned installation/data paths and normal
`SeChangeNotifyPrivilege` traversal. It has no administrator, debug, backup,
restore or impersonation privilege. User-bound DPAPI is used under its own
profile. Interactive-user profile visibility is not assumed; inaccessible AI/MCP
paths report `degraded`, and protected resources report `permission_missing`.
Literal machine reboot persistence is unverified on hosted runners.

Uninstall verifies service ownership, stops the service, removes registration and
the executable, and preserves identity, spool, status, configuration and local
evidence. There is no default purge.

The executable includes an SCM handler and operator-only registration commands:

```powershell
.\agent-trust-sensor.exe install-service --config C:\Private\sensor.json
```

Registration is **manual start**, not automatic deployment. Before starting, choose
a least-privilege service account and enroll under that same account (DPAPI user
binding). SCM defaults to LocalSystem until the operator configures the account;
do not start it against another account's enrolled identity. Foreground runtime is
the first acceptance target; dedicated-account SCM startup/recovery is not yet
validated and must not be claimed production-ready. No account password is accepted
or stored by this executable. Installation alone means no telemetry is active.

Stop the owned sensor through normal service controls, then:

```powershell
.\agent-trust-sensor.exe uninstall-service --name AgentTrustEndpoint
```

Removal refuses a running/unrelated service. It preserves all local data. Revoke
the endpoint centrally, reconcile queued records, and archive/delete its exact
data directory only under separate operator policy. No global cleanup command.

## Implemented collector coverage

| Collector | Implemented | Important gaps |
| --- | --- | --- |
| AI discovery | Cursor, Ollama, LM Studio, Claude Code conventional executable paths; Codex/Gemini npm package metadata; Copilot IDE extension manifests; explicit custom paths (including OpenWebUI) | Installation is not use. Alternate/package-manager layouts need configuration. No browser history or extension APIs beyond selected IDE manifests |
| AI running | Exact discovered executable-path match in process snapshots | Interpreted CLI packages/extensions are installed-only unless separately mapped to a specific executable; no generic Node/VS Code/browser AI attribution |
| MCP | Cursor `.cursor/mcp.json`, VS Code user `mcp.json`, explicitly configured strict JSON `mcpServers`/`servers` | No JSONC/TOML, full config upload, env/argument values, command execution or tool invocation |
| Software | Windows version/build, HKLM/HKCU uninstall registry views, selected manifests | Registry/package versions may be absent; no endpoint CVE database or complete package inventory |
| Process | Toolhelp snapshots; creation-time/PID key; parent if creation ordering supports it; path, SID/session, bounded SHA-256 | Short-lived/protected processes may be missed. First eight new executables/tick, max 16 MiB each hashed; no command lines |
| Network | IPv4/IPv6 TCP owner-PID table changes | TCP only; no payload/TLS interception, DNS mapping, UDP or guaranteed outbound direction. SYN_SENT is outbound candidate; established direction is unknown |
| Repository | Up to 20 approved roots, bounded metadata snapshots, stable Windows file identity for rename, create/change/delete | Max 3,000 entries/root; skips `.git`, `node_modules`, symlinks. No content/hash/entropy scan, read audit or writer PID. Polling can miss intermediate changes |

Discovery refreshes every 30 ticks, health every 10 ticks. States are `supported`,
`active`, `degraded`, `permission_missing`, `unsupported`. Polling gaps are explicitly
reported even when active. More privileges are not automatically requested.
Lifecycle event labels explicitly mean first-seen/no-longer-visible snapshots,
not complete start/stop auditing. An inaccessible process can disappear from the
snapshot without exiting. AI evidence carries server-derived approval status.

## Spool and delivery

`<data_dir>\spool` contains metadata event files and counters. Default bounds:
10,000 events / 32 MiB / seven days, per event 16 KiB; upload batches of 50.
Atomic write/flush/rename survives normal restart. Oldest events expire/drop first;
durable counters are advanced before removal (a crash can overcount, not hide loss).
Heartbeat exposes depth/sent/dropped/last-upload and collector health. Disk-full or
corruption stops the sensor with a safe error; the central view becomes offline.
Spool is metadata, not encrypted document storage; filesystem ACLs are required.

Requests have a 10-second timeout. Errors retain events; subsequent attempts wait
at least five seconds and respect Retry-After. IDs are stable until the server
commits ingestion jobs. Acknowledgment is not finding creation or remediation.
Duplicate identical events reuse jobs; conflicting IDs fail 409 and remain queued
for explicit reconciliation. No silent cloud fallback or alternate destination.

## Central API, rules and rollback

`GET /api/v1/endpoints` (admin read scope) derives healthy/degraded/offline/visibility
gap from heartbeat age and coverage. Installation or empty findings is not health.
Normalized evidence/findings/jobs use the existing read API and webhook destination.
Shadow AI correlation uses running unapproved AI plus file activity in a classified
repository within a bounded window. It labels **temporal co-presence; file-process
association unknown**. No source-read, theft or AI-caused-incident claim.

Experimental periodic-network and metadata-burst rules use 120 seconds / at most
512 events per endpoint; not a learned baseline or complete history. They emit
suspicions, not confirmed C2/ransomware. Operator-configured hash matches are a
separate indicator rule. Real-world tuning, history baselines and richer malware
rules remain future work; normal create-only build fixtures are negative controls.

Migration **005_endpoints.sql** adds one private table for enrollment, policy,
health and bounded correlation state. 001–004 are untouched; event idempotency
reuses the existing job ledger. Concurrent worker completions serialize per endpoint
inside their existing fenced transaction. Repeated migrations preserve data.
Back up/test restore separately. Rollback: stop sensors/ingestion, drain or reconcile
new-source jobs, then revert API/worker code while preserving the table/records.
Older workers do not understand the endpoint source. Do not reset/delete volumes.

No future DLP, CVE matching, YARA execution, prevention, patching, isolation or
remote shell is enabled. Response metadata always has `executed: false` and no
requested action; any future response requires separate authority and tests.
