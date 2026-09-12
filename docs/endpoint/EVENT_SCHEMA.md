# Endpoint schema `endpoint-1`

Strict source schema; platform and sensor versions are separate. Unknown fields,
event types, schema revisions, invalid timestamps and over-limit bodies fail
explicitly; validation responses do not echo secrets or submitted telemetry.

Envelope: `schema_version`, UUID `event_id`, UUID `endpoint_id`, UUID
`sensor_instance_id`, aware `observed_at`, `collector`, `sensor_version` (`0.1.0`),
`policy_version` (`endpoint-policy-1`), `event_type`, typed `data`.
Workspace, received time, collector identity, evidence status/method and verification
are server-bound; submitted workspace/verification fields are rejected. Device
authentication proves the sender credential, not the accuracy of its observations.
Evidence remains `claimed`, verification null, method `authenticated_endpoint_report`.

| Event types | Required/selected structured data |
| --- | --- |
| endpoint_heartbeat, endpoint_capabilities, collector_health, visibility_gap | service status, collector states, spool depth, sent/dropped counters, last upload, connectivity, bounded reason |
| software_inventory | product, version when known, selected path, registry/os/extension/configured/catalog source |
| ai_tool_discovered, ai_tool_running | tool ID, path, source, version/process key when known; installed and running are separate event types |
| mcp_configuration_discovered, mcp_configuration_changed | server name, transport, executable basename, argument count, remote domain, config source, selected-metadata digest |
| process_started, process_stopped | PID/creation-time process key, PID, parent PID/key/path, executable, SID/session, bounded hash where available |
| process_network_connection | process key/PID, IP, port, TCP, direction unknown/outbound candidate |
| file_created, file_modified, file_renamed, file_deleted, repository_interaction | central repository UUID, relative path, previous relative path for rename, size, metadata-observation relationship; writer process unknown |

See executable Pydantic definitions in `src/agent_trust/domain/endpoint.py`.
No freeform `content`, command lines, prompts, environment values or source files.
Relative repository paths reject drive/absolute/traversal forms. Repository IDs
must belong to the endpoint's central policy. Approval/classification are central
policy, not device assertions. No automatic mapping to AI agents or Falcon hosts.

API: `POST /api/v1/endpoints/{id}/events`, at most 100 events/batch, bounded request
body (including chunked input). Whole-batch transaction: 202 only after jobs commit.
Response `accepted` contains event/job IDs in request order. Replays with identical
canonical typed input reuse jobs; conflicting immutable IDs return 409 without
partial batch enqueue. Event time may be up to 14 days old / five minutes ahead;
spool defaults expire earlier. Very late events persist but bounded correlation
can omit them; no historical-completeness claim. Auth/revocation/identity errors
are 401/403; schema errors 422; body limits 413. Poll existing jobs for findings
and delivery IDs. No response execution.
