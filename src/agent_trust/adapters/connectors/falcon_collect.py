"""Bounded sync-once with a PostgreSQL session lock and transactional checkpoints.

The dedicated session holds an advisory lock, NOT an open transaction, during
vendor calls. A lost session cannot commit a retrieved page through a new session.
"""
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
import json
import time

from sqlalchemy import select, text

from agent_trust.storage.database import connector_checkpoints, records
from agent_trust.storage.job_ledger import JobLedger, _insert
from .base import SourceContext
from .falcon_client import FalconClient, FalconConfig, FalconError
from .falcon_source import CrowdStrikeSource, digest, timestamp


def now():
    return datetime.now(timezone.utc).isoformat()


@contextmanager
def collection_session(engine, workspace, connection_id):
    if engine.dialect.name != 'postgresql':
        raise FalconError('postgresql_required')
    key = int(digest([workspace,connection_id])[:15],16)
    with engine.connect() as connection:
        acquired = connection.execute(text('SELECT pg_try_advisory_lock(:key)'), {'key':key}).scalar()
        connection.commit()
        if not acquired:
            raise FalconError('collection_already_running')
        try:
            yield connection
        finally:
            if not connection.invalidated:
                connection.rollback()
                connection.execute(text('SELECT pg_advisory_unlock(:key)'), {'key':key})
                connection.commit()


def save_state(connection, identifier, workspace, state):
    statement = _insert(connection, connector_checkpoints).values(
        id=identifier, workspace_id=workspace, payload=json.dumps(state), updated_at=now())
    connection.execute(statement.on_conflict_do_update(index_elements=['id'],
        set_={'payload':statement.excluded.payload, 'updated_at':statement.excluded.updated_at}))


def check_connection(config: FalconConfig):
    client = FalconClient(config, max_requests=12, seconds=40)
    source = CrowdStrikeSource()
    coverage = {}
    for stream in ('hosts','alerts'):
        try:
            if stream == 'hosts':
                items, _ = client.host_page(None,1)
            else:
                items, _ = client.alert_page(None,1,(datetime.now(timezone.utc)-timedelta(days=1)).isoformat(),now())
            for item in items:
                source.normalize({'resource':item,'resource_type':'host' if stream=='hosts' else 'alert',
                    'config':config,'collected_at':now(),'agent_mapping':{}}, SourceContext('check-only','operator'))
            coverage[stream] = 'read_ok_empty' if not items else 'read_ok'
        except FalconError as error:
            coverage[stream] = str(error)
    return {'connection_id':config.connection_id, 'coverage':coverage,
            'status':'complete' if all(v.startswith('read_ok') for v in coverage.values()) else 'partial',
            'transport':'local_fixture' if config.fixture_origin else 'vendor_api', 'response_capabilities':[]}


def sync_once(engine, config: FalconConfig, workspace: str, *, since: str,
              agent_mapping=None, page_size=100, max_pages=5, seconds=120, replay=False,
              client=None):
    config.validate()
    start = datetime.fromisoformat(timestamp(since).replace('Z','+00:00'))
    if not datetime.now(timezone.utc)-timedelta(days=30) <= start <= datetime.now(timezone.utc):
        raise FalconError('backfill_must_be_within_last_30_days')
    if not 1<=page_size<=100 or not 1<=max_pages<=20 or not 1<=seconds<=300:
        raise FalconError('invalid_collection_limits')
    mapping = agent_mapping or {}
    if not isinstance(mapping,dict) or len(mapping)>10000 or any(not isinstance(k,str) or not isinstance(v,str) for k,v in mapping.items()):
        raise FalconError('invalid_agent_mapping')
    client = client or FalconClient(config, max_requests=max_pages*12+12, seconds=seconds)
    source = CrowdStrikeSource()
    context = SourceContext(workspace, 'operator:crowdstrike:' + config.connection_id)
    identifier = 'falcon-checkpoint-' + digest([workspace,config.connection_id])
    binding = {'cid':config.account_cid,'region':config.region,'origin':client.origin}
    mapping_digest = digest(mapping)
    ledger = JobLedger(engine)
    output = {'connection_id':config.connection_id, 'status':'partial','streams':{},
              'delivery':'queued independently; acknowledgment is not remediation',
              'transport':'local_fixture' if config.fixture_origin else 'vendor_api'}
    with collection_session(engine,workspace,config.connection_id) as connection:
        with connection.begin():
            row = connection.execute(select(connector_checkpoints.c.payload).where(
                connector_checkpoints.c.id==identifier)).first()
            state = json.loads(row[0]) if row else {}
            if state and state['binding'] != binding:
                raise FalconError('connection_identity_changed_use_new_connection_id')
            if state and state['mapping_digest'] != mapping_digest and not replay:
                raise FalconError('mapping_changed_explicit_replay_required')
            for agent in set(mapping.values()):
                if connection.execute(select(records.c.id).where(records.c.id==agent,
                        records.c.workspace_id==workspace,records.c.kind=='agents')).first() is None:
                    raise FalconError('mapping_agent_not_registered_in_workspace')
        if state.get('not_before',0)>time.time():
            return {**output,'error':'retry_not_before','retry_after_seconds':int(state['not_before']-time.time())+1}
        if not state or replay or all(state[s]['done'] for s in ('hosts','alerts')):
            lower = since if not state or replay else (datetime.fromisoformat(state['until'])-timedelta(minutes=5)).isoformat()
            # Never silently clamp an overdue checkpoint and skip the missing interval.
            if datetime.fromisoformat(lower.replace('Z','+00:00')) < datetime.now(timezone.utc)-timedelta(days=30):
                raise FalconError('checkpoint_older_than_backfill_limit_explicit_replay_required')
            state = {'binding':binding, 'mapping_digest':mapping_digest, 'since':lower, 'until':now(),
                     'hosts':{'cursor':None,'done':False},'alerts':{'cursor':None,'done':False},'not_before':0}
        for stream in ('hosts','alerts'):
            position = state[stream]
            stats = {'pages_committed':0,'records_submitted':0,'cursor_replays':0,
                     'coverage':'previously_completed' if position['done'] else 'partial'}
            output['streams'][stream] = stats
            if position['done']:
                continue
            if stream=='hosts' and position['cursor'] and time.time()-position.get('cursor_time',0)>110:
                position['cursor'] = None
                stats['cursor_replays'] += 1
            for _ in range(max_pages):
                try:
                    if stream=='hosts':
                        items, cursor = client.host_page(position['cursor'],page_size)
                    else:
                        items, cursor = client.alert_page(position['cursor'],page_size,state['since'],state['until'])
                    if cursor and cursor == position['cursor']:
                        raise FalconError('nonadvancing_cursor')
                    normalized = [source.normalize({'resource':item,'resource_type':'host' if stream=='hosts' else 'alert',
                        'config':config,'collected_at':now(),'agent_mapping':mapping},context) for item in items]
                    updated = {**position,'cursor':cursor,'done':not cursor,'cursor_time':time.time()}
                    # Page enqueue and checkpoint share one transaction on the
                    # SAME session holding the collection lock. No external calls.
                    with connection.begin():
                        for payload in normalized:
                            key = 'falcon:' + digest([payload['logical_id'],payload['revision']])
                            job = ledger.enqueue('connector_ingest',workspace,payload,
                                                 idempotency_key=key,connection=connection)
                            if job['kind']!='connector_ingest' or job['payload'].get('revision')!=payload['revision'] or job['payload'].get('logical_id')!=payload['logical_id']:
                                raise FalconError('ingestion_key_conflict')
                        save_state(connection,identifier,workspace,{**state,stream:updated,'not_before':0})
                    state[stream] = position = updated
                    stats['pages_committed'] += 1
                    stats['records_submitted'] += len(normalized)
                    if not cursor:
                        stats['coverage'] = 'bounded_query_completed'
                        break
                except FalconError as error:
                    if str(error)=='invalid_request_or_cursor' and position['cursor'] and stats['cursor_replays']<1:
                        # Replay the same fixed window, never jump beyond it.
                        position['cursor'] = None
                        stats['cursor_replays'] += 1
                        # Persist the rewind even if this invocation's page
                        # budget is exhausted. Never move the window forward.
                        with connection.begin():
                            save_state(connection,identifier,workspace,state)
                        continue
                    stats['error'] = str(error)
                    state['not_before'] = max(state.get('not_before',0),time.time()+error.retry_after)
                    with connection.begin():
                        save_state(connection,identifier,workspace,state)
                    break
        if all(state[s]['done'] for s in ('hosts','alerts')):
            output['status'] = 'complete'
        output['window'] = {'since':state['since'],'until':state['until']}
        output['coverage_note'] = 'Bounded live-data reads, not a snapshot or complete historical coverage; 5 minute overlap on subsequent windows.'
        return output
