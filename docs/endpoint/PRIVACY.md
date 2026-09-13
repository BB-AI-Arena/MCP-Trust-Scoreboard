# Endpoint privacy boundary

Observe-only security metadata. No keystrokes, screenshots, clipboard, personal
browsing history, prompt text, full documents/repositories, or arbitrary execution.
No MCP command runs. Configuration parsing extracts only a server label, transport,
executable basename, argument count and remote domain; URL userinfo/path/query,
headers, credential fields and environment/argument values are discarded.
The config digest covers selected metadata only, not secrets.

Repository observation is opt-in and metadata-only. File/path/user SID/host software
metadata and hashes can still be sensitive; they are not anonymized. Configure
the smallest scope and control access to central evidence, database backups and
the local spool. Spool ACLs restrict other users; administrator access is not a
protected boundary. Local malware with the enrolled account's rights can impersonate
the sensor: no hardware attestation, tamper protection or mTLS is claimed.

Plaintext bootstrap/device secrets are never stored as telemetry, jobs or logs.
The database stores token hashes; endpoint identity is DPAPI-encrypted and bound to
the enrolling Windows account. Bootstrap issuance/exchange returns secrets only to
the authorized caller; keep HTTP access/body logging disabled at any reverse proxy.
Central raw validation errors do not echo request data.

Service bootstrap is transient plaintext in an ACL-protected owned handoff file,
readable only by SYSTEM, Administrators and the named service identity. Successful
enrollment deletes it; this is ordinary deletion, not cryptographic secure erasure
of SSD storage. It is never copied into configuration, SCM arguments, persistent
environment, registry, logs, spool or retained diagnostic artifacts. Server expiry
and single redemption limit its usability; credentials remain user-scope DPAPI.

No package/URL is fetched during discovery and no hosted analysis provider is used.
Only the configured platform origin receives telemetry. HTTPS is verified; private
IP ranges require local configuration. Loopback HTTP is an explicit fixture exception.
No automatic retry to another origin or credential forwarding through redirects.

Service mode uses `NT SERVICE\<service-name>` with its own profile. It cannot see
an interactive user's HKCU configuration or desktop state, and process visibility
is limited by Windows access checks rather than guaranteed across sessions;
those collectors report `degraded` or `permission_missing`. The service requests
no broad profile ACLs or session impersonation. A future per-user helper requires
separate enrollment and explicit session provenance.

Local event count/bytes/time are bounded and drops are reported. Central evidence
and jobs have no automatic expiry in this slice: apply separately reviewed retention
and backup policy. Do not describe missing telemetry as no suspicious activity.
Later DLP, malware rule execution and prevention require separate privacy/authority
decisions; they are not dormant remote commands in this build.
