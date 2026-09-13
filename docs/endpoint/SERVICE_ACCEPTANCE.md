# Windows service acceptance follow-up

Historical starting source: e8e09f1868834a13b233817bccb0e188448fedc5 (PR #23).
PR #23/#24 and their prerequisites are now merged. Actual-main release preparation
passed; source-bound evidence is in [the reconciliation report](../STACK_RECONCILIATION.md#windows-acceptance-on-feature-merged-main).
Historical branch: feat/windows-service-acceptance; base: feat/windows-endpoint-sensor.
Windows execution initially passed at implementation head
`e814ba207d243b5e0ac10e784fbf0ec102f7e205` in
[run 34738201185](https://github.com/BB-AI-Arena/MCP-Trust-Scoreboard/actions/runs/34738201185).
See [the authoritative reconciliation](../STACK_RECONCILIATION.md#windows-acceptance-on-feature-merged-main)
for exact source, binary hash, spool counts and actual collector states.
The historical SCM enrollment blocker and feature-main validation are both complete;
the later status-only documentation merge is separately revalidated.

The development installer is `scripts/windows_service.ps1`. It creates a unique
virtual account `NT SERVICE\<service name>` through SCM, sets automatic startup,
and restricts requested token privileges to SeChangeNotifyPrivilege (traversal).
No administrator membership, debug, backup, restore or impersonation privilege is
requested. Administrator rights are needed only by the installation controller.
Read-only HKLM inventory and the service's HKCU view use existing Windows ACLs;
no registry ACL changes or interactive-user hive loading occur. No service control
rights are granted to ordinary users. SCM's default service DACL is retained and
captured in evidence.

Virtual accounts avoid a password distribution/rotation mechanism and a shared
LocalService identity. Domain managed accounts are unnecessary for the current
HTTP bearer transport; dedicated local accounts would add password/profile and
logon-right provisioning. SCM loads the service profile. User-bound DPAPI is
unchanged: encryption and decryption run inside the same SCM identity, on the
same machine. Preserve its profile; changing the account, service name or machine
requires explicit identity reconciliation. An administrator can take over a
machine; DPAPI is not protection from an administrator acting as the service.

Enrollment bootstrap input goes privately over stdin to the installer and then
into a bounded `data/bootstrap.json` handoff. The file is protected with
inheritance disabled and grants only SYSTEM, Administrators, and the named
virtual service account. It is deleted after successful enrollment; the server's
existing 15-minute bootstrap expiry and single-redemption rules remain in force.
The token is never an ImagePath/process argument, service environment value,
registry value, configuration field, log, or retained evidence. Temporary server
unavailability leaves the handoff; startup retries are bounded by the SCM recovery
policy below, not an in-process enrollment retry loop. Server-side expiry/redeemed
checks remain authoritative; the local file has no expiry scheduler. Rejected
material requires explicit operator reconciliation after bounded SCM attempts.
The token's expiry is not extended by retaining its private file. Ordinary
automatic starts and recovery consume no bootstrap when a DPAPI identity exists
and cannot silently reenroll. Endpoint credentials exist in memory and in
user-bound DPAPI ciphertext only.

Only a new, nonexistent leaf installation directory is accepted; the parent must
exist and neither it nor an ancestor may be a reparse point. Administrators/SYSTEM
control the installation. The service gets read/execute on binaries/configuration
and modify on data; the virtual-account path does not require runtime WRITE_DAC
or grant itself full control. No parent ACL changes. Configuration, identity, spool and local
status remain private. The sensor does not write arbitrary logs; `data/status.json`
is a bounded current health snapshot with no credential, including authentication
rejection when the server cannot receive heartbeats.

Recovery: restart after 5 seconds, restart after 30 seconds, then no action;
failure count resets after 86,400 seconds. Non-crash error exits also count.
No reboot or external command recovery action. Automatic-start configuration and
actual SCM crash/restart are tested. Literal machine reboot remains unverified on
GitHub-hosted runners; restart is never described as a reboot.

Install from an elevated PowerShell 7 process using a privately supplied bootstrap
on stdin (do not put it in this command):

```powershell
./scripts/windows_service.ps1 -Action Install -Name AgentTrustEndpoint -InstallRoot C:\OwnedParent\Sensor -Source .\sensor\dist\agent-trust-sensor.exe -Config C:\Private\sensor.json
./scripts/windows_service.ps1 -Action Inspect -Name AgentTrustEndpoint -InstallRoot C:\OwnedParent\Sensor
./scripts/windows_service.ps1 -Action Uninstall -Name AgentTrustEndpoint -InstallRoot C:\OwnedParent\Sensor
```

Install starts/enrolls through SCM. Subsequent Start/Stop actions use the same
helper. A failed enrollment leaves private installation state for diagnosis;
explicit Enroll with a fresh valid bootstrap can retry if no identity was saved.
A consumed bootstrap requires central reconciliation, never an automatic bypass.
Repeat installation fails before changing files. Uninstall verifies the recorded
binary checksum and exact SCM executable/argument ownership, stops the service,
removes registration and only the executable. Identity, spool, status, config and
installation marker are preserved. There is no purge command. Central history,
repositories and platform volumes are never uninstall targets.

Service discovery reads only configured accessible fixture/operator-approved
paths. Its HKCU is not the interactive user's hive. Protected processes may yield
permission_missing; unreadable profiles yield degraded AI/MCP health. TCP has only
the associations available from readable processes. No blanket profile grants,
session impersonation or user hive loading. A future per-user helper would need
separate enrollment/consent and explicit session provenance; it is not implemented.

Reproduce only in the disposable Windows CI job:
`./scripts/windows_acceptance.ps1 -Service`. Foreground uses the same script without
`-Service`; native Go and portable Go tests are separate workflow steps/jobs.
The final run reports AI/MCP/filesystem/software degraded, process
permission_missing, network/runtime active and DNS/UDP/file-writer unsupported.
Full fixture discovery/Shadow AI coverage is from foreground acceptance; static
collector labels in generic acceptance JSON do not override the SCM health report.
Server unit tests reject bootstrap reuse; the SCM scenario verifies enrollment and
deletion, not a second service instance redeeming the token. Only the first crash
recovery is exercised, not all three successive failure actions. No literal reboot,
mTLS, signed installer or attestation claim.

Evidence includes SCM readback, runtime SID/elevation, ACLs, runner/build/source,
binary hash, exact spool/replay counts, revocation and collector states. Portable
and native spool tests separately force capacity and age limits; expired is a
subset of dropped and old counters decode with expired=0. Crash-before-removal may
overcount loss conservatively. No exactly-once transport claim.

GitHub Project status unverified: active authentication lacks read:project.
