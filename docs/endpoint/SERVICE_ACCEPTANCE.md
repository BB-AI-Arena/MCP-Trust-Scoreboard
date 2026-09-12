# Windows service acceptance follow-up

Starting source: e8e09f1868834a13b233817bccb0e188448fedc5 (open PR #23).
Branch: feat/windows-service-acceptance; base: feat/windows-endpoint-sensor.
Windows execution results are pending; implementation is not proof of acceptance.

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
as an ephemeral StartService argument. It is not an ImagePath/process argument,
service environment registry value or configuration field. Ordinary automatic
starts and recovery receive no bootstrap and cannot reenroll. No transcript/body
logging should wrap enrollment. Endpoint credentials exist in memory and in
user-bound DPAPI ciphertext only.

Only a new, nonexistent leaf installation directory is accepted; the parent must
exist and neither it nor an ancestor may be a reparse point. Administrators/SYSTEM
control the installation. The service gets read/execute on binaries/configuration
and modify on data (enrollment gives its own identity full control on that owned
data directory). No parent ACL changes. Configuration, identity, spool and local
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
Evidence includes SCM readback, runtime SID/elevation, ACLs, runner/build/source,
binary hash, exact spool/replay counts, revocation and collector states. Portable
and native spool tests separately force capacity and age limits; expired is a
subset of dropped and old counters decode with expired=0. Crash-before-removal may
overcount loss conservatively. No exactly-once transport claim.

GitHub Project status unverified: active authentication lacks read:project.
