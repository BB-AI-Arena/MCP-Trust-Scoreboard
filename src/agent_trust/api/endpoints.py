"""Device-scoped enrollment and typed ingestion, separate from generic API auth."""
from datetime import datetime, timedelta, timezone
import hashlib
import json
import secrets
import uuid

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from sqlalchemy import insert, select, update

from agent_trust.api.auth import context_dependency
from agent_trust.domain.endpoint import EndpointPolicy, Enrollment, EventBatch
from agent_trust.storage.database import endpoints
from agent_trust.storage.job_ledger import JobLedger


def now():
    return datetime.now(timezone.utc).isoformat()


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


def fail(status, code):
    raise HTTPException(status_code=status, detail={'code':code})


def device(connection, endpoint_id, authorization):
    row = connection.execute(select(endpoints).where(endpoints.c.id==str(endpoint_id)).with_for_update()).mappings().first()
    supplied = authorization[7:] if authorization and authorization.startswith('Bearer ') else ''
    if not row or row['state']!='enrolled' or not supplied or not secrets.compare_digest(row['token_hash'] or '',digest(supplied)):
        fail(401,'endpoint_credential_invalid_or_revoked')
    return row


def endpoint_router(settings, engine):
    router = APIRouter(prefix='/api/v1/endpoints', tags=['endpoints'])
    read, write = context_dependency(settings,'read'), context_dependency(settings,'write')
    ledger = JobLedger(engine)

    @router.post('/provision',status_code=201)
    def provision(policy: EndpointPolicy, context=Depends(write)):
        if settings.auth_mode=='disabled':
            fail(403,'authenticated_administrator_required')
        endpoint_id, bootstrap = str(uuid.uuid4()), secrets.token_urlsafe(32)
        with engine.begin() as c:
            c.execute(insert(endpoints).values(id=endpoint_id,workspace_id=context.workspace_id,
                state='pending',bootstrap_hash=digest(bootstrap),
                bootstrap_until=(datetime.now(timezone.utc)+timedelta(minutes=15)).isoformat(),
                policy=policy.model_dump_json(),health='{}',correlation='{}',created_at=now()))
        return {'endpoint_id':endpoint_id,'bootstrap_secret':bootstrap,'expires_in':900}

    @router.post('/enroll')
    def enroll(request: Enrollment):
        with engine.begin() as c:
            row = c.execute(select(endpoints).where(endpoints.c.id==str(request.endpoint_id)).with_for_update()).mappings().first()
            if not row or row['state']!='pending' or row['bootstrap_until']<now() or not secrets.compare_digest(row['bootstrap_hash'] or '',digest(request.bootstrap_secret)):
                fail(401,'bootstrap_invalid_expired_or_consumed')
            token = secrets.token_urlsafe(32)
            c.execute(update(endpoints).where(endpoints.c.id==row['id']).values(
                state='enrolled',bootstrap_hash=None,bootstrap_until=None,
                sensor_instance_id=str(request.sensor_instance_id),token_hash=digest(token)))
        return {'endpoint_id':row['id'],'credential':token,'policy':json.loads(row['policy'])}

    @router.post('/{endpoint_id}/revoke')
    def revoke(endpoint_id: uuid.UUID, context=Depends(write)):
        with engine.begin() as c:
            row = c.execute(select(endpoints).where(endpoints.c.id==str(endpoint_id),endpoints.c.workspace_id==context.workspace_id).with_for_update()).first()
            if not row:
                fail(404,'endpoint_not_found')
            c.execute(update(endpoints).where(endpoints.c.id==str(endpoint_id)).values(state='revoked',token_hash=None,bootstrap_hash=None))
        return {'endpoint_id':str(endpoint_id),'state':'revoked'}

    @router.get('/{endpoint_id}/policy')
    def policy(endpoint_id: uuid.UUID, authorization: str | None = Header(default=None)):
        with engine.begin() as c:
            return json.loads(device(c,endpoint_id,authorization)['policy'])

    @router.post('/{endpoint_id}/events',status_code=202)
    def ingest(endpoint_id: uuid.UUID, request: EventBatch, authorization: str | None = Header(default=None)):
        ids = []
        with engine.begin() as c:
            row = device(c,endpoint_id,authorization)
            policy = json.loads(row['policy'])
            repositories = {r['id'] for r in policy['repositories']}
            for event in request.events:
                if str(event.endpoint_id)!=row['id'] or str(event.sensor_instance_id)!=row['sensor_instance_id']:
                    fail(403,'endpoint_identity_mismatch')
                if 'repository_id' in event.data and event.data['repository_id'] not in repositories:
                    fail(422,'repository_not_in_endpoint_policy')
                wire = event.model_dump(mode='json')
                input_digest = digest(json.dumps(wire,sort_keys=True,separators=(',',':')))
                payload = {**wire,'source':'windows-endpoint','workspace_id':row['workspace_id'],
                    'collector_identity':'endpoint:'+row['id'],'received_at':now(),
                    'status':'claimed','method':'authenticated_endpoint_report','verification':None,
                    'input_digest':input_digest,'policy':policy}
                job = ledger.enqueue('connector_ingest',row['workspace_id'],payload,
                    idempotency_key='endpoint:'+digest(row['id']+':'+str(event.event_id)),connection=c)
                if job['payload'].get('input_digest')!=input_digest:
                    fail(409,'event_id_conflict')
                ids.append({'event_id':str(event.event_id),'job_id':job['id']})
        return {'accepted':ids,'delivery_semantics':'at-least-once'}

    @router.get('')
    def inventory(context=Depends(read),limit: int=Query(50,ge=1,le=100),offset: int=Query(0,ge=0)):
        with engine.connect() as c:
            rows = c.execute(select(endpoints).where(endpoints.c.workspace_id==context.workspace_id).order_by(endpoints.c.created_at).limit(limit).offset(offset)).mappings()
            result = []
            for row in rows:
                health = json.loads(row['health'])
                if row['state']!='enrolled':
                    status = row['state']
                elif not row['last_seen'] or datetime.now(timezone.utc)-datetime.fromisoformat(row['last_seen'].replace('Z','+00:00'))>timedelta(minutes=3):
                    status = 'offline'
                elif health.get('events_dropped',0):
                    status = 'visibility_gap'
                elif not health.get('collectors') or any(v not in ('supported','active') for v in health.get('collectors',{}).values()):
                    status = 'degraded'
                else:
                    status = 'healthy'
                result.append({k:row[k] for k in ('id','workspace_id','sensor_instance_id','state','last_seen')} | {'health':health,'health_state':status})
        return {'items':result,'limit':limit,'offset':offset}

    return router
