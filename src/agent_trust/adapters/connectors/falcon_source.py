"""Allowlisted vendor observations, not keyword analysis or AI attribution."""
import hashlib
import json
from datetime import datetime

from .falcon_client import FalconError


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',',':'), allow_nan=False).encode()).hexdigest()


def timestamp(value):
    if not isinstance(value,str) or len(value)>40:
        raise FalconError('malformed_timestamp')
    try:
        parsed = datetime.fromisoformat(value.replace('Z','+00:00'))
        if parsed.tzinfo is None:
            raise ValueError()
    except ValueError:
        raise FalconError('malformed_timestamp') from None
    return value


class CrowdStrikeSource:
    name = 'crowdstrike-falcon'
    schema_version = 'falcon-1'

    def normalize(self, envelope, context):
        """Envelope is internal collector metadata, never a submitted API dict."""
        raw, kind = envelope['resource'], envelope['resource_type']
        config, collected = envelope['config'], envelope['collected_at']
        if not isinstance(raw,dict) or raw.get('cid') != config.account_cid:
            raise FalconError('account_mismatch_or_missing')
        fields = (('device_id','cid','hostname','platform_name','agent_version','first_seen','last_seen','modified_timestamp','status')
                  if kind == 'host' else ('composite_id','id','cid','agent_id','created_timestamp','updated_timestamp','timestamp','severity','severity_name','status','product','type'))
        kept = {}
        for key in fields:
            value = raw.get(key)
            if value is None:
                continue
            if key == 'severity':
                if isinstance(value,bool) or not isinstance(value,(int,float)) or not 0<=value<=100:
                    raise FalconError('malformed_severity')
            elif not isinstance(value,str) or len(value)>512:
                raise FalconError('malformed_vendor_field')
            if key.endswith('timestamp') or key in ('first_seen','last_seen'):
                timestamp(value)
            kept[key] = value
        identifier = kept.get('device_id' if kind == 'host' else 'composite_id')
        if not identifier:
            raise FalconError('missing_vendor_identity')
        if kind == 'alert':
            timestamp(kept.get('created_timestamp'))
            timestamp(kept.get('updated_timestamp'))
            # Detect description/name revisions without retaining untrusted text.
            texts = [raw.get(k,'') for k in ('name','display_name','description')]
            if not all(isinstance(t,str) for t in texts):
                raise FalconError('malformed_vendor_text')
            kept['text_digest'] = digest(texts)
        host_id = kept.get('device_id' if kind == 'host' else 'agent_id')
        agent_id = envelope['agent_mapping'].get(host_id)
        identity = [context.workspace_id, config.connection_id, config.account_cid, kind, identifier]
        logical = 'falcon-' + digest(identity)
        revision = digest({'fields':kept,'mapped_agent_id':agent_id,'normalizer':'falcon-1'})
        return {'source':self.name,'schema_version':'2026-01','source_schema':self.schema_version,
            'workspace_id':context.workspace_id,'collector_identity':context.collector_identity,
            'connection_id':config.connection_id,'vendor_account':config.account_cid,
            'resource_type':kind,'vendor_id':identifier,'logical_id':logical,'revision':revision,
            'subject':logical,'collected_at':collected,'status':'claimed','verification':None,
            'method':'authenticated_vendor_api_read','vendor_fields':kept,
            'agent_id':agent_id,'agent_link': 'explicit_operator_mapping' if agent_id else 'unmatched_vendor_context',
            'redacted':True,'retention':'allowlisted metadata and text digest; no raw text, commands, credentials or tokens',
            'normalizer_version':'falcon-1'}

    @staticmethod
    def records(evidence, job_id):
        evidence = dict(evidence, id='evidence-' + job_id)
        findings = []
        if evidence['resource_type'] == 'alert':
            source = evidence['vendor_fields']
            severity = source.get('severity_name','unknown').lower()
            if severity not in ('informational','low','medium','high','critical'):
                severity = 'unknown'
            findings.append({'id':'finding-' + job_id, 'logical_id':evidence['logical_id'],
                'revision':evidence['revision'],'workspace_id':evidence['workspace_id'],
                'subject_id':evidence['subject'],'evidence_ids':[evidence['id']],
                'schema_version':'2026-01','source':evidence['source'],
                'origin':'vendor_alert','title':'CrowdStrike Falcon reported alert',
                'severity':severity,'status':source.get('status','unknown'),
                'source_severity':source.get('severity'), 'source_status':source.get('status'),
                'vendor_id':evidence['vendor_id'],'vendor_fields':source,
                'agent_id':evidence['agent_id'],'agent_link':evidence['agent_link'],
                'normalizer_version':evidence['normalizer_version'],
                'description':'Imported vendor conclusion; not independently verified or attributed to an AI agent.'})
        return evidence, findings, 'vendor-import'
