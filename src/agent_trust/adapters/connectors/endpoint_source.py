"""Endpoint evidence source; correlation participates in existing fenced commit."""
import json
from sqlalchemy import select, update
from agent_trust.storage.database import endpoints
from agent_trust.engines.endpoint import correlate


class WindowsEndpointSource:
    name = 'windows-endpoint'
    schema_version = 'endpoint-1'

    @staticmethod
    def records(payload, job_id, connection):
        evidence = {k:v for k,v in payload.items() if k not in ('input_digest','policy')}
        evidence['id'] = 'evidence-'+job_id
        if payload['event_type'] in ('ai_tool_discovered','ai_tool_running'):
            evidence['approval_status'] = ('approved' if payload['data']['tool_id'] in payload['policy']['approved_tools'] else 'unapproved')
            evidence['approval_source'] = 'server_bound_enrollment_policy'
        row = connection.execute(select(endpoints).where(endpoints.c.id==payload['endpoint_id'],
            endpoints.c.workspace_id==payload['workspace_id']).with_for_update()).mappings().one()
        state, findings = correlate(evidence,json.loads(row['correlation']),payload['policy'])
        changes = {'correlation':json.dumps(state)}
        if payload['event_type']=='endpoint_heartbeat' and (not row['last_seen'] or payload['observed_at']>row['last_seen']):
            changes.update(health=json.dumps(payload['data'] | {'sensor_version':payload['sensor_version'],'policy_version':payload['policy_version']}),last_seen=payload['observed_at'])
        connection.execute(update(endpoints).where(endpoints.c.id==row['id']).values(**changes))
        return evidence,findings,'endpoint-rules'
