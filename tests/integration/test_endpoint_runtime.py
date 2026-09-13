"""Real PostgreSQL endpoint correlation/outbox; Windows collector runs separately."""
from concurrent.futures import ThreadPoolExecutor
from fastapi.testclient import TestClient
import pytest
from sqlalchemy import select, text
from agent_trust.api.app import create_app
from agent_trust.config import Settings
from agent_trust.jobs.worker import process_one
from agent_trust.storage.database import endpoints, jobs, records
from agent_trust.storage.job_ledger import JobLedger
from test_endpoint import ADMIN,enrollment,ingest,policy_fixture,signals

pytestmark=pytest.mark.integration


def test_postgres_endpoint_idempotency_fenced_correlations_and_delivery(pg_engine,falcon_server):
    state,config=falcon_server
    settings=Settings(api_token='fixture-endpoint-administrator',workspace_id='endpoint-fixture',
        webhook_url=config.fixture_origin+'/findings',webhook_allowed_hosts=('127.0.0.1',),webhook_allowed_cidrs=('127.0.0.1/32',))
    client=TestClient(create_app(settings,pg_engine));ledger=JobLedger(pg_engine)
    policy=policy_fixture();identity,_=enrollment(client,policy)
    events=[{k:v for k,v in e.items() if k not in ('workspace_id','id')}|{'endpoint_id':identity['endpoint_id'],'sensor_instance_id':identity['sensor_instance_id']} for e in signals(policy)]
    with ThreadPoolExecutor(max_workers=3) as pool:
        responses=list(pool.map(lambda _:ingest(client,identity,events),range(3)))
    assert all(r.status_code==202 for r in responses)
    assert responses[0].json()==responses[1].json()==responses[2].json()
    with ThreadPoolExecutor(max_workers=3) as pool:
        def drain(n):
            for _ in range(100):
                if not process_one(ledger,f'endpoint-worker-{n}',settings):break
        list(pool.map(drain,range(3)))
    with pg_engine.connect() as c:
        assert len(c.execute(select(records).where(records.c.kind=='evidence')).all())==len(events)
        findings=c.execute(select(records).where(records.c.kind=='findings')).all()
        assert findings and c.execute(select(endpoints.c.correlation)).scalar()!='{}'
    # Receiver's default first attempt fails; restarted ledger preserves retries.
    from sqlalchemy import update
    with pg_engine.begin() as c:c.execute(update(jobs).where(jobs.c.status=='queued').values(available_at='2000-01-01T00:00:00+00:00'))
    restarted=JobLedger(pg_engine)
    while process_one(restarted,'restarted',settings):pass
    assert state['received'] and state['accepted_ids']
    assert client.get('/api/v1/findings',headers=ADMIN).json()['items']
    with pg_engine.connect() as c:assert c.execute(text('SELECT count(*) FROM agent_trust_migrations')).scalar()==5
