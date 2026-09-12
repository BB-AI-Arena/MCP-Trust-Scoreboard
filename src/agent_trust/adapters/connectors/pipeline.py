"""Durable normalized evidence/findings plus transactional delivery outbox jobs."""
import json

from agent_trust.storage.database import records
from agent_trust.storage.job_ledger import _insert
from .registry import SOURCES, destination


def generic_records(job):
    evidence = dict(job['payload'])
    rules = evidence.pop('rule_findings')
    evidence.pop('input_digest')
    evidence['id'] = 'evidence-' + job['id']
    findings = [{'id':'finding-' + job['id'] + '-' + rule['rule_id'],
        'workspace_id':job['workspace_id'],'subject_id':evidence['subject'],
        'title':rule['title'],'severity':rule['severity'], 'rule_id':rule['rule_id'],
        'rule_version':evidence['rule_version'],'evidence_ids':[evidence['id']],
        'schema_version':'2026-01','status':'open','source':evidence['source'],
        'description':'Deterministic rule matched collector-reported content; raw content discarded.'}
        for rule in rules]
    return evidence, findings, 'rules-only'


def complete_ingestion(ledger, job):
    source = job['payload'].get('source')
    if source not in SOURCES:
        raise ValueError('unregistered_evidence_source')
    if source == 'generic-json':
        evidence, findings, provider = generic_records(job)
    else:
        evidence, findings, provider = SOURCES[source].records(job['payload'], job['id'])
    result = {'evidence_id':evidence['id'], 'finding_ids':[f['id'] for f in findings],
              'delivery_jobs':len(findings), 'provider':provider}

    def persist(connection, completed):
        for kind, record in [('evidence',evidence)] + [('findings', f) for f in findings]:
            connection.execute(_insert(connection, records).values(id=record['id'],
                workspace_id=job['workspace_id'], kind=kind, payload=json.dumps(record),
                created_at=completed['created_at'], updated_at=completed['updated_at']))
        delivery_ids = []
        for finding in findings:
            delivery = ledger.enqueue('finding_delivery', job['workspace_id'],
                {'destination_id':'webhook','finding':finding},
                idempotency_key='webhook:' + finding['id'], connection=connection)
            delivery_ids.append(delivery['id'])
        return {'delivery_job_ids':delivery_ids}

    return ledger.complete(job['id'], job['lease_token'], result, persist=persist)


def deliver_finding(ledger, job, settings):
    receipt = destination(job['payload']['destination_id'], settings).deliver(job['payload']['finding'], job['id'])
    # HTTP acknowledgment is separate from local durable completion. A crash in
    # this gap may redeliver the same ID; the receiver must deduplicate it.
    return ledger.complete(job['id'], job['lease_token'], receipt)
