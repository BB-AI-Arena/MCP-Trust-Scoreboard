"""Real TLS vendor fixture + PostgreSQL + installed runtime; no live accounts."""
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import subprocess

from fastapi.testclient import TestClient
import httpx
import pytest
from sqlalchemy import select, text, update

from agent_trust.adapters.connectors.falcon_client import FalconClient, FalconError, ALERTS
from agent_trust.adapters.connectors.falcon_collect import collection_session, sync_once
from agent_trust.api.app import create_app
from agent_trust.config import Settings
from agent_trust.jobs.worker import process_one
from agent_trust.storage.database import create_schema, connector_checkpoints, jobs, records
from agent_trust.storage.job_ledger import JobLedger
from agent_trust.storage.repository import RecordRepository
from falcon_fixture import CID, HOSTS
from .conftest import docker, eventually
from .test_container_runtime import HEADERS, TOKEN, start_api

pytestmark = pytest.mark.integration


def test_postgres_page_atomicity_replay_revisions_mapping_and_delivery(pg_engine,falcon_server,monkeypatch):
    state, config = falcon_server
    create_schema(pg_engine)
    workspace = 'falcon-fixture'
    RecordRepository(pg_engine).put('agents',{'id':'registered-agent'},workspace)
    kwargs = dict(since=(datetime.now(timezone.utc)-timedelta(days=1)).isoformat(),
                  agent_mapping={HOSTS[0]:'registered-agent'},page_size=1,max_pages=1)
    original = JobLedger.enqueue
    def crash_after_enqueue(self,*args,**kwargs):
        original(self,*args,**kwargs)
        raise RuntimeError('fixture death before page commit')
    monkeypatch.setattr(JobLedger,'enqueue',crash_after_enqueue)
    with pytest.raises(RuntimeError,match='before page commit'):
        sync_once(pg_engine,config,workspace,**kwargs)
    with pg_engine.connect() as c:
        assert c.execute(select(jobs)).first() is None
        assert c.execute(select(connector_checkpoints)).first() is None
    monkeypatch.setattr(JobLedger,'enqueue',original)
    first = sync_once(pg_engine,config,workspace,**kwargs)
    assert first['status']=='partial'
    for stream in ('hosts','alerts'):
        ids = first['streams'][stream]['ingestion_job_ids']
        assert len(ids)==1 and JobLedger(pg_engine).get(ids[0],workspace)['kind']=='connector_ingest'
    with pg_engine.connect() as c:
        saved = json.loads(c.execute(select(connector_checkpoints.c.payload)).scalar_one())
        assert saved['alerts']['cursor'] and saved['hosts']['cursor']
        assert 'fixture-only' not in json.dumps(saved)
    with collection_session(pg_engine,workspace,config.connection_id):
        with pytest.raises(FalconError,match='already_running'):
            sync_once(pg_engine,config,workspace,**kwargs)
    state['expire_cursor'] = True
    second = sync_once(pg_engine,config,workspace,**kwargs)
    assert second['status']=='partial' and second['streams']['alerts']['cursor_replays']==1
    with pg_engine.connect() as c:
        saved = json.loads(c.execute(select(connector_checkpoints.c.payload)).scalar_one())
        assert saved['alerts']['cursor'] is None
    assert sync_once(pg_engine,config,workspace,**{**kwargs,'max_pages':5})['status']=='complete'
    settings = Settings(api_token=TOKEN,workspace_id=workspace,webhook_url=config.fixture_origin+'/findings',
        webhook_allowed_hosts=('127.0.0.1',),webhook_allowed_cidrs=('127.0.0.1/32',))
    ledger = JobLedger(pg_engine)
    while process_one(ledger,'first-worker',settings):
        pass
    with pg_engine.begin() as c:
        waiting = c.execute(select(jobs).where(jobs.c.kind=='finding_delivery',jobs.c.status=='queued')).one()
        assert waiting.error=='destination_http_503'
        c.execute(update(jobs).where(jobs.c.id==waiting.id).values(available_at='2000-01-01T00:00:00+00:00'))
    assert process_one(JobLedger(pg_engine),'restarted-worker',settings)
    assert [r['delivery_id'] for r in state['received']].count(waiting.id)==2
    assert state['accepted_ids'].count(waiting.id)==1
    client = TestClient(create_app(settings,pg_engine))
    findings = client.get('/api/v1/findings',headers=HEADERS).json()['items']
    assert len(findings)==2 and {f['agent_id'] for f in findings}=={None,'registered-agent'}
    assert all(f['origin']=='vendor_alert' and 'rule_id' not in f for f in findings)
    # Same alert ID updated legitimately: old revision retained, new delivery ID.
    state['alerts'][0]['status'] = 'closed'
    result = sync_once(pg_engine,config,workspace,**{**kwargs,'max_pages':5,'replay':True})
    assert result['status']=='complete'
    while process_one(ledger,'worker',settings):
        pass
    findings = client.get('/api/v1/findings',headers=HEADERS).json()['items']
    assert len(findings)==3 and len({f['logical_id'] for f in findings})==2
    assert {f['source_status'] for f in findings}=={'new','closed'}
    with pg_engine.connect() as c:
        assert len(c.execute(select(jobs).where(jobs.c.kind=='connector_ingest')).all())==5
        stored = str(c.execute(select(records.c.payload)).all()) + str(c.execute(select(jobs.c.payload)).all())
        assert 'sensitive-fixture-command' not in stored and 'fixture-only' not in stored
    with pytest.raises(FalconError,match='mapping_changed'):
        sync_once(pg_engine,config,workspace,**{**kwargs,'agent_mapping':{}})


def test_checkpoint_rate_limit_partial_page_and_expired_host_cursor(pg_engine,falcon_server):
    state, config = falcon_server
    create_schema(pg_engine)
    kwargs = dict(since=(datetime.now(timezone.utc)-timedelta(days=1)).isoformat(),page_size=1,max_pages=1)
    sync_once(pg_engine,config,'workspace',**kwargs)
    with pg_engine.begin() as c:
        row = c.execute(select(connector_checkpoints)).one()
        saved = json.loads(row.payload)
        saved['hosts']['cursor_time'] = 0
        c.execute(update(connector_checkpoints).values(payload=json.dumps(saved)))
    state['plans'][ALERTS] = [{'status':429,'headers':{'Retry-After':'60'}}]
    result = sync_once(pg_engine,config,'workspace',**kwargs)
    assert result['streams']['hosts']['cursor_replays']==1
    assert result['streams']['alerts']['error']=='rate_limited'
    calls = len(state['calls'])
    assert sync_once(pg_engine,config,'workspace',**kwargs)['error']=='retry_not_before'
    assert len(state['calls'])==calls
    with pg_engine.begin() as c:
        row = c.execute(select(connector_checkpoints)).one()
        saved = json.loads(row.payload)
        assert saved['alerts']['cursor']=='a:1'
        saved['not_before'] = 0
        c.execute(update(connector_checkpoints).values(payload=json.dumps(saved)))
    state['plans'][ALERTS] = [{'body':{'resources':state['alerts'], 'errors':[{'message':'fixture partial error'}]}}]
    result = sync_once(pg_engine,config,'workspace',**kwargs)
    assert result['streams']['alerts']['error']=='partial_response'
    with pg_engine.connect() as c:
        saved = json.loads(c.execute(select(connector_checkpoints.c.payload)).scalar_one())
        assert saved['alerts']['cursor']=='a:1' and not saved['alerts']['done']


def test_installed_falcon_collector_worker_api_webhook_restart(containers,postgres,platform_image,tmp_path):
    certs = tmp_path/'certs'
    certs.mkdir()
    subprocess.run(['openssl','req','-x509','-newkey','rsa:2048','-nodes','-days','1',
        '-keyout',str(certs/'key.pem'),'-out',str(certs/'cert.pem'),'-subj','/CN=falcon-fixture',
        '-addext','subjectAltName=DNS:falcon-fixture'],capture_output=True,check=True,timeout=20)
    mount = f'type=bind,src={certs},dst=/certs,readonly'
    fixture_code = Path(__file__).parents[1]/'falcon_fixture.py'
    fixture = containers.run('falcon',platform_image,'--network-alias','falcon-fixture','--mount',mount,
        '--mount',f'type=bind,src={fixture_code},dst=/fixture.py,readonly',command=('python','-u','/fixture.py'))
    eventually(lambda:'fixture-ready' in docker('logs',fixture))
    fixture_ip = containers.address(fixture)
    # Only fixture origin/config is substituted; installed CLI/client/storage run.
    command = (
        "from dataclasses import replace; import sys; "
        "from agent_trust.adapters.connectors.falcon_client import FalconConfig; "
        "original=FalconConfig.from_env; "
        f"FalconConfig.from_env=classmethod(lambda cls,*args: replace(original(*args),fixture_origin='https://falcon-fixture:8443',fixture_cidrs=('{fixture_ip}/32',))); "
        "from agent_trust.adapters.connectors.falcon_cli import main; "
        f"sys.argv=['agent-trust-falcon','sync-once','--connection','fixture','--account-cid','{CID}','--max-pages','3']; sys.exit(main())")
    collector = containers.run('collector',platform_image,'--mount',mount,
        '-e',f'DATABASE_URL={postgres["internal"]}','-e',f'AGENT_TRUST_API_TOKEN={TOKEN}',
        '-e','AGENT_TRUST_FALCON_CLIENT_ID=fixture-client','-e','AGENT_TRUST_FALCON_CLIENT_SECRET=fixture-only',
        '-e','SSL_CERT_FILE=/certs/cert.pem',command=('python','-c',command))
    eventually(lambda:json.loads(docker('inspect','--format','{{json .State}}',collector))['Status']=='exited')
    assert json.loads(docker('inspect','--format','{{json .State}}',collector))['ExitCode']==0, docker('logs',collector)
    assert json.loads(docker('logs',collector))['status']=='complete'
    api, url = start_api(containers,platform_image,postgres['internal'])
    assert 'sync-once' in docker('exec',api,'agent-trust-falcon','--help')
    worker = containers.run('worker',platform_image,'--mount',mount,
        '-e',f'DATABASE_URL={postgres["internal"]}','-e',f'AGENT_TRUST_API_TOKEN={TOKEN}',
        '-e','SSL_CERT_FILE=/certs/cert.pem','-e','AGENT_TRUST_WEBHOOK_URL=https://falcon-fixture:8443/findings',
        '-e','AGENT_TRUST_WEBHOOK_ALLOWED_HOSTS=falcon-fixture','-e',f'AGENT_TRUST_WEBHOOK_ALLOWED_CIDRS={fixture_ip}/32',
        command=('agent-trust-worker',))
    with httpx.Client(base_url=url,headers=HEADERS,trust_env=False,timeout=5) as client:
        def pending_retry():
            receipt = json.loads(docker('exec',fixture,'python','-c',"print(open('/tmp/state.json').read())"))
            if not receipt['received']:
                return None
            job = client.get('/api/v1/jobs/'+receipt['received'][0]['delivery_id']).json()
            return job if job['status']=='queued' and job['attempts']==1 else None
        failed = eventually(pending_retry)
        containers.stop(worker)
        containers.restart(api)
        client.base_url = f'http://{containers.address(api)}:8080'
        eventually(lambda:client.get('/readiness').status_code==200)
        assert client.get('/api/v1/findings').json()['count']==2
        containers.restart(worker)
        eventually(lambda:client.get('/api/v1/jobs/'+failed['id']).json()['status']=='complete')
        assert client.get('/api/v1/jobs/'+failed['id']).json()['result']['response_action'] is None
        for route, body in [('/api/v1/assessments',{'subject_id':'regression','content':'eval(user)'}),
            ('/api/v1/connectors/generic-json/events',{'schema_version':'1','event_id':'regression',
            'subject':'test','reported_agent_id':'claimed','observed_at':datetime.now(timezone.utc).isoformat(),'content':'ordinary'})]:
            response = client.post(route,json=body)
            assert response.status_code==202
            eventually(lambda:client.get('/api/v1/jobs/'+response.json()['job_id']).json()['status']=='complete')
    receipt = json.loads(docker('exec',fixture,'python','-c',"print(open('/tmp/state.json').read())"))
    assert [r['delivery_id'] for r in receipt['received']].count(failed['id'])==2
    assert receipt['accepted_ids'].count(failed['id'])==1


def test_upgrade_003_to_004_preserves_preexisting_records(pg_engine):
    from importlib.resources import files
    root = files('agent_trust.storage').joinpath('migrations')
    with pg_engine.begin() as c:
        c.execute(text('CREATE TABLE agent_trust_migrations (version varchar(128) PRIMARY KEY)'))
        for name in ('001_initial.sql','002_workspace_idempotency.sql','003_assessment_results.sql'):
            c.execute(text(root.joinpath(name).read_text()))
            c.execute(text('INSERT INTO agent_trust_migrations VALUES (:name)'),{'name':name})
    RecordRepository(pg_engine).put('agents',{'id':'preexisting-agent','marker':'preserve'},'workspace')
    create_schema(pg_engine)
    create_schema(pg_engine)
    assert RecordRepository(pg_engine).get('agents','preexisting-agent','workspace')['marker']=='preserve'
    with pg_engine.connect() as c:
        assert c.execute(select(connector_checkpoints)).first() is None
        assert c.execute(text('SELECT count(*) FROM agent_trust_migrations')).scalar()==4
