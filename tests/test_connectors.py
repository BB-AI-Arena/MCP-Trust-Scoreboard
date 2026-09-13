from dataclasses import replace
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import socket
from threading import Thread

from fastapi.testclient import TestClient
import pytest
from sqlalchemy import create_engine, select, update

from agent_trust.adapters.connectors.pipeline import complete_ingestion
from agent_trust.adapters.connectors.webhook import DeliveryError, WebhookDestination, resolve_target
from agent_trust.api.app import create_app
from agent_trust.config import Settings
from agent_trust.jobs.worker import process_one
from agent_trust.storage.database import jobs, records
from agent_trust.storage.job_ledger import JobLedger

BODY = {'schema_version':'1', 'event_id':'event-1', 'subject':'fixture-tool',
        'reported_agent_id':'claimed-agent','observed_at':'2026-09-01T12:00:00Z',
        'content':"eval(user); password='fixture-only-secret-value'"}
HEADERS = {'Authorization':'Bearer fixture-ingest-token'}


@pytest.fixture
def receiver():
    state = {'requests':[], 'status':204, 'body':b'', 'location':None}
    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            state['requests'].append({'headers':dict(self.headers),
                'body':json.loads(self.rfile.read(int(self.headers['Content-Length'])))})
            self.send_response(state['status'])
            if state['location']:
                self.send_header('Location',state['location'])
            self.end_headers()
            self.wfile.write(state['body'])
        def log_message(self, *_):
            pass
    server = ThreadingHTTPServer(('127.0.0.1',0), Handler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield state, f'http://127.0.0.1:{server.server_port}/findings'
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


@pytest.fixture
def platform(tmp_path, receiver):
    state, url = receiver
    settings = Settings(api_token='fixture-ingest-token', workspace_id='trusted-workspace',
        webhook_url=url, webhook_allowed_hosts=('127.0.0.1',),
        webhook_allowed_cidrs=('127.0.0.1/32',), webhook_allow_http=True,
        webhook_token='fixture-destination-token', webhook_timeout_seconds=1)
    engine = create_engine(f'sqlite:///{tmp_path / "connectors.db"}')
    client = TestClient(create_app(settings, engine))
    yield client, JobLedger(engine), settings, state
    engine.dispose()


def submit(client, body=BODY):
    return client.post('/api/v1/connectors/generic-json/events', json=body, headers=HEADERS)


def test_real_json_to_webhook_and_no_raw_content_retention(platform):
    client, ledger, settings, state = platform
    first = submit(client)
    assert first.status_code == 202
    assert submit(client).json()['job_id'] == first.json()['job_id']
    assert submit(client, {**BODY,'content':'different'}).status_code == 409
    assert process_one(ledger,'fixture', settings)
    job = ledger.get(first.json()['job_id'], settings.workspace_id)
    assert job['status'] == 'complete' and len(job['result']['delivery_job_ids']) == 2
    evidence = client.get('/api/v1/evidence', headers=HEADERS).json()['items'][0]
    assert evidence['workspace_id'] == settings.workspace_id
    assert evidence['status'] == 'claimed' and evidence['verification'] is None
    assert evidence['collector_identity'] == 'api-token'
    assert evidence['reported_agent_id'] == 'claimed-agent'
    assert 'content' not in evidence
    assert client.get('/api/v1/findings', headers=HEADERS).json()['count'] == 2
    while process_one(ledger,'fixture',settings):
        pass
    assert len(state['requests']) == 2
    for request in state['requests']:
        assert request['headers']['Authorization'] == 'Bearer fixture-destination-token'
        delivered = request['body']
        assert request['headers']['Idempotency-Key'] == delivered['delivery_id']
        result = ledger.get(delivered['delivery_id'],settings.workspace_id)['result']
        assert result['outcome'] == 'accepted_by_destination' and result['response_action'] is None
    with ledger.engine.connect() as connection:
        persisted = str(connection.execute(select(jobs.c.payload)).all()) + str(connection.execute(select(records.c.payload)).all())
    assert 'fixture-only-secret-value' not in persisted + json.dumps(state['requests'])


def test_auth_scopes_identity_and_separate_capabilities(platform):
    client, ledger, settings, _ = platform
    assert client.post('/api/v1/connectors/generic-json/events',json=BODY).status_code == 401
    for key in ('workspace_id','collector_identity','verification','destination_url'):
        assert submit(client, {**BODY,key:'forged'}).status_code == 422
    readonly = TestClient(create_app(replace(settings,api_scopes=('read',)),ledger.engine))
    assert submit(readonly).status_code == 403
    capabilities = client.get('/api/v1/connectors',headers=HEADERS).json()
    assert {a['role'] for a in capabilities['adapters']} == {'evidence_source','finding_destination'}
    assert capabilities['response_adapters'] == []
    assert all(not a['enforce'] for a in capabilities['adapters'])


def test_missing_destination_is_unavailable_not_success(platform):
    client, ledger, settings, _ = platform
    submit(client,{**BODY,'content':'eval(user)'})
    process_one(ledger,'fixture',settings)
    process_one(ledger,'fixture',replace(settings,webhook_url=''))
    with ledger.engine.connect() as connection:
        row = connection.execute(select(jobs).where(jobs.c.kind == 'finding_delivery')).one()
    assert row.status == 'queued' and row.error == 'destination_unavailable' and row.result is None


def test_receiver_failure_retries_same_durable_delivery_id(platform):
    client, ledger, settings, state = platform
    submitted = submit(client,{**BODY,'content':'eval(user)'})
    process_one(ledger,'fixture',settings)
    delivery_id = ledger.get(submitted.json()['job_id'],settings.workspace_id)['result']['delivery_job_ids'][0]
    state['status'] = 503
    process_one(ledger,'fixture',settings)
    assert ledger.get(delivery_id,settings.workspace_id)['status'] == 'queued'
    with ledger.engine.begin() as connection:
        connection.execute(update(jobs).where(jobs.c.id == delivery_id).values(available_at='2000-01-01T00:00:00+00:00'))
    state['status'] = 204
    process_one(JobLedger(ledger.engine),'restarted-worker',settings)
    assert ledger.get(delivery_id,settings.workspace_id)['attempts'] == 2
    assert [r['body']['delivery_id'] for r in state['requests']] == [delivery_id,delivery_id]


def test_no_findings_still_persists_evidence(platform):
    client, ledger, settings, state = platform
    submitted = submit(client,{**BODY,'content':'ordinary text'})
    process_one(ledger,'fixture',settings)
    result = ledger.get(submitted.json()['job_id'],settings.workspace_id)['result']
    assert result['delivery_job_ids'] == [] and result['finding_ids'] == []
    assert client.get('/api/v1/evidence',headers=HEADERS).json()['count'] == 1
    assert not state['requests']


def test_atomic_persistence_and_stale_worker_fencing(platform, monkeypatch):
    client, ledger, settings, _ = platform
    submitted = submit(client)
    job = ledger.claim('fixture')
    original = ledger.enqueue
    monkeypatch.setattr(ledger,'enqueue',lambda *a,**k: (_ for _ in ()).throw(RuntimeError('fixture transaction failure')))
    with pytest.raises(RuntimeError):
        complete_ingestion(ledger,job)
    assert ledger.get(submitted.json()['job_id'],settings.workspace_id)['status'] == 'running'
    with ledger.engine.connect() as connection:
        assert connection.execute(select(records)).first() is None
    monkeypatch.setattr(ledger,'enqueue',original)
    with ledger.engine.begin() as connection:
        connection.execute(update(jobs).where(jobs.c.id == job['id']).values(lease_until='2000-01-01T00:00:00+00:00'))
    newer = ledger.claim('new-worker')
    assert not complete_ingestion(ledger,job)
    assert complete_ingestion(ledger,newer)


@pytest.mark.parametrize('url,hosts,cidrs', [
    ('http://127.0.0.1/',('127.0.0.1',),()),
    ('https://169.254.169.254/',('169.254.169.254',),('169.254.0.0/16',)),
    ('https://[::ffff:169.254.169.254]/',('::ffff:169.254.169.254',),()),
    ('https://[::1]/',('::1',),()),
    ('https://user:secret@example.com/',('example.com',),()),
    ('https://not-allowed.example/',(),()),
])
def test_destination_scope_blocks_unsafe_targets(url, hosts, cidrs):
    with pytest.raises(DeliveryError):
        resolve_target(Settings(webhook_url=url,webhook_allowed_hosts=hosts,webhook_allowed_cidrs=cidrs))


def test_redirects_never_forward_credentials_and_large_responses_fail(platform):
    _, _, settings, state = platform
    state.update(status=302,location='http://untrusted.invalid/')
    with pytest.raises(DeliveryError,match='http_302'):
        WebhookDestination(settings).deliver({'id':'fixture'},'delivery')
    assert len(state['requests']) == 1
    state.update(status=200,body=b'x'*4097)
    with pytest.raises(DeliveryError,match='too_large'):
        WebhookDestination(settings).deliver({'id':'fixture'},'delivery')


def test_pinned_connection_does_not_resolve_twice(platform, monkeypatch):
    _, _, settings, state = platform
    original = socket.getaddrinfo
    calls = []
    def resolve(*args,**kwargs):
        calls.append(args)
        assert len(calls) == 1
        return original(*args,**kwargs)
    monkeypatch.setattr(socket,'getaddrinfo',resolve)
    WebhookDestination(settings).deliver({'id':'fixture'},'delivery')
    assert len(calls) == 1 and len(state['requests']) == 1


@pytest.mark.parametrize('change', [
    {'schema_version':'2'}, {'observed_at':'2026-09-01T12:00:00'},
    {'artifact_digest':'not-a-digest'}, {'content':'x'*100001},
])
def test_ingestion_schema_and_limits(platform, change):
    client, *_ = platform
    assert submit(client,{**BODY,**change}).status_code == 422


def test_workspace_isolation_for_same_source_event(platform):
    client, ledger, settings, _ = platform
    first = submit(client).json()['job_id']
    other = TestClient(create_app(replace(settings,workspace_id='other'),ledger.engine))
    second = submit(other).json()['job_id']
    assert first != second
    assert other.get('/api/v1/jobs/' + first,headers=HEADERS).status_code == 404
    assert client.get('/api/v1/jobs/' + second,headers=HEADERS).status_code == 404


def test_delivery_attempts_are_bounded(platform):
    client, ledger, settings, state = platform
    submitted = submit(client,{**BODY,'content':'eval(user)'}).json()
    process_one(ledger,'fixture',settings)
    delivery = ledger.get(submitted['job_id'],settings.workspace_id)['result']['delivery_job_ids'][0]
    state['status'] = 503
    for _ in range(3):
        with ledger.engine.begin() as connection:
            connection.execute(update(jobs).where(jobs.c.id == delivery).values(available_at='2000-01-01T00:00:00+00:00'))
        assert process_one(ledger,'fixture',settings)
    job = ledger.get(delivery,settings.workspace_id)
    assert job['status'] == 'failed' and job['attempts'] == 3 and job['result'] is None
    assert not process_one(ledger,'fixture',settings)


def test_acknowledgment_before_lost_lease_can_redeliver_same_id(platform):
    from agent_trust.adapters.connectors.pipeline import deliver_finding
    client, ledger, settings, state = platform
    submit(client,{**BODY,'content':'eval(user)'})
    process_one(ledger,'fixture',settings)
    delivery = ledger.claim('old-worker')
    with ledger.engine.begin() as connection:
        connection.execute(update(jobs).where(jobs.c.id == delivery['id']).values(lease_until='2000-01-01T00:00:00+00:00'))
    assert not deliver_finding(ledger,delivery,settings)
    assert process_one(ledger,'new-worker',settings)
    assert [r['body']['delivery_id'] for r in state['requests']] == [delivery['id'],delivery['id']]
    assert ledger.get(delivery['id'],settings.workspace_id)['attempts'] == 2
