# Windows Endpoint Sensor v0.1 — implementation decision

Issue #22 / ATP-C1. Observe-only, unreleased alpha; no response adapter.
Branch from PR #21 (`9aa41c1bdbd3c81c6bdf4ba5f33bf1035d18de43`), which remains open.

## Language and runtime

Use Go 1.26.8 and `golang.org/x/sys/windows`: a native, CGO-free Windows x64
executable with Windows Service Control Manager integration. Go offers bounded
concurrency, memory safety, standard TLS and straightforward cross-compilation.
Compared with Python it avoids a separately managed endpoint interpreter; compared
with C# it avoids framework-dependent installation; compared with Rust it reduces
FFI/service implementation overhead for this initial supported user-mode slice.
This is an engineering choice, not a performance benchmark. No kernel driver.

Collectors use Toolhelp process snapshots, IP Helper TCP tables, registry/software
metadata, explicitly scoped AI/MCP discovery, and bounded repository metadata
snapshots. Polling misses short-lived activity and cannot assign a file write to a
process; report these gaps. Temporal co-presence is not causality or source exposure.

Endpoint enrollment uses a single-use expiring bootstrap secret created by the
authenticated administrator and exchanged for a device-specific bearer token.
Server stores hashes only. Windows stores the credential using user-bound DPAPI;
enroll and run under the same service account. Device revocation is server-side.
This is not hardware attestation or mTLS; future device key/certificate enrollment
replaces bearer authentication while retaining endpoint IDs and revocation state.

Typed events enter the existing PostgreSQL job ledger, not a new event backend.
The worker serializes per-endpoint correlation and commits evidence, state,
findings, delivery enqueue and job completion under its existing lease fence.
Existing webhook semantics and pending-destination reconciliation are unchanged.

The local spool stores bounded, atomic event files and durable loss counters.
Stable event IDs plus server idempotency provide at-least-once delivery. Installation
is operator-controlled; no driver, updater, remote shell or prevention mechanism.

References: [Go releases](https://go.dev/doc/devel/release),
[Windows services](https://pkg.go.dev/golang.org/x/sys/windows/svc),
[Toolhelp](https://learn.microsoft.com/en-us/windows/win32/toolhelp/taking-a-snapshot-and-viewing-processes),
[IP Helper](https://learn.microsoft.com/en-us/windows/win32/api/iphlpapi/nf-iphlpapi-getextendedtcptable),
[DPAPI](https://learn.microsoft.com/en-us/windows/win32/api/dpapi/nf-dpapi-cryptprotectdata).
