"""Typed endpoint contracts/rules; these are NOT Windows collector validation."""
from datetime import datetime, timedelta, timezone
from dataclasses import replace
import json
import uuid

from fastapi.testclient import TestClient
import pytest
from sqlalchemy import create_engine, select, update

from agent_trust.api.app import create_app
from agent_trust.config import Settings
from agent_trust.domain.endpoint import DATA, EndpointEvent, EndpointPolicy
from agent_trust.engines.endpoint import correlate
from agent_trust.jobs.worker import process_one
from agent_trust.storage.database import endpoints, jobs
from agent_trust.storage.job_ledger import JobLedger

ADMIN={'Authorization':'Bearer fixture-endpoint-administrator'}


def enrollment(client,policy=None):
    response=client.post('/api/v1/endpoints/provision',headers=ADMIN,json=policy or {})
    assert response.status_code==201,response.text
    provision=response.json()
    body={**{k:provision[k] for k in ('endpoint_id','bootstrap_secret')},'sensor_instance_id':str(uuid.uuid4())}
    result=client.post('/api/v1/endpoints/enroll',json=body)
    assert result.status_code==200,result.text
    identity={**result.json(),'sensor_instance_id':body['sensor_instance_id']}
    return identity,body


def event(identity,kind='endpoint_heartbeat',data=None,when=None):
    return {'schema_version':'endpoint-1','event_id':str(uuid.uuid4()),'endpoint_id':identity['endpoint_id'],
        'sensor_instance_id':identity['sensor_instance_id'],'observed_at':(when or datetime.now(timezone.utc)).isoformat(),
        'collector':'runtime','sensor_version':'0.1.0','policy_version':'endpoint-policy-1','event_type':kind,'data':data or {}}


def ingest(client,identity,events):
    return client.post('/api/v1/endpoints/'+identity['endpoint_id']+'/events',
        headers={'Authorization':'Bearer '+identity['credential']},json={'events':events})


@pytest.fixture
def endpoint_platform(tmp_path):
    engine=create_engine(f'sqlite:///{tmp_path / "endpoint.db"}')
    settings=Settings(api_token='fixture-endpoint-administrator',workspace_id='endpoint-fixture')
    client=TestClient(create_app(settings,engine))
    yield client,JobLedger(engine),settings
    engine.dispose()


def test_device_enrollment_revocation_and_credentials_not_persisted(endpoint_platform):
    client,ledger,settings=endpoint_platform
    identity,body=enrollment(client)
    assert client.post('/api/v1/endpoints/enroll',json=body).status_code==401
    assert client.post('/api/v1/endpoints/enroll',json={**body,'bootstrap_secret':'secret-short'}).status_code==422
    assert 'secret-short' not in client.post('/api/v1/endpoints/enroll',json={**body,'bootstrap_secret':'secret-short'}).text
    with ledger.engine.connect() as c:
        stored=str(c.execute(select(endpoints)).all())
    assert body['bootstrap_secret'] not in stored and identity['credential'] not in stored
    route='/api/v1/endpoints/'+identity['endpoint_id']+'/events'
    ev=event(identity)
    assert client.post(route,headers=ADMIN,json={'events':[ev]}).status_code==401
    accepted=ingest(client,identity,[ev]);assert accepted.status_code==202
    assert ingest(client,identity,[ev]).json()==accepted.json()
    assert ingest(client,identity,[{**ev,'data':{'spool_depth':1}}]).status_code==409
    assert ingest(client,identity,[{**ev,'endpoint_id':str(uuid.uuid4())}]).status_code==403
    assert ingest(client,identity,[{**ev,'workspace_id':'forged'}]).status_code==422
    assert client.post('/api/v1/endpoints/'+identity['endpoint_id']+'/revoke',headers=ADMIN).status_code==200
    assert ingest(client,identity,[ev]).status_code==401


@pytest.mark.parametrize('change',[{'schema_version':'future'},{'event_type':'remote_shell'},{'data':{'command':'secret'}},{'observed_at':'2020-01-01T00:00:00Z'}])
def test_unknown_schema_unsafe_fields_and_old_data_rejected(endpoint_platform,change):
    client,_,_=endpoint_platform;identity,_=enrollment(client)
    response=ingest(client,identity,[{**event(identity),**change}]);assert response.status_code==422
    assert 'secret' not in response.text


def test_atomic_batch_health_and_server_bound_workspace(endpoint_platform):
    client,ledger,settings=endpoint_platform;identity,_=enrollment(client)
    first=event(identity,data={'collectors':{'process':'degraded'},'events_dropped':2})
    bad={**event(identity),'endpoint_id':str(uuid.uuid4())}
    assert ingest(client,identity,[first,bad]).status_code==403
    with ledger.engine.connect() as c:assert not c.execute(select(jobs)).first()
    assert ingest(client,identity,[first]).status_code==202
    process_one(ledger,'test',settings)
    health=client.get('/api/v1/endpoints',headers=ADMIN).json()['items'][0]
    assert health['health_state']=='visibility_gap'
    evidence=client.get('/api/v1/evidence',headers=ADMIN).json()['items'][0]
    assert evidence['workspace_id']==settings.workspace_id and evidence['verification'] is None
    assert evidence['source']=='windows-endpoint' and 'credential' not in json.dumps(evidence)
    with ledger.engine.begin() as c:c.execute(update(endpoints).values(last_seen=(datetime.now(timezone.utc)-timedelta(minutes=5)).isoformat()))
    assert client.get('/api/v1/endpoints',headers=ADMIN).json()['items'][0]['health_state']=='offline'


def policy_fixture():
    return EndpointPolicy(repositories=[{'id':str(uuid.uuid4()),'path':'C:\\disposable','classification':'Restricted'}]).model_dump(mode='json')


def signals(policy):
    identity={'endpoint_id':str(uuid.uuid4()),'sensor_instance_id':str(uuid.uuid4())}
    t=datetime.now(timezone.utc)-timedelta(seconds=30)
    specs=[('ai_tool_running',{'tool_id':'fixture-ai','path':'C:\\fixture.exe','source':'process_snapshot','process_key':'10:100'}),
        ('file_modified',{'repository_id':policy['repositories'][0]['id'],'relative_path':'src\\benign.txt'}),
        ('process_started',{'process_key':'10:100','pid':10,'parent_pid':9,'parent_key':'9:99','executable':'C:\\fixture.exe'})]
    specs.extend(('process_network_connection',{'process_key':'10:100','pid':10,'destination_ip':'192.0.2.40','destination_port':443,'direction':'outbound_candidate'}) for _ in range(5))
    specs.extend(('file_renamed',{'repository_id':policy['repositories'][0]['id'],'relative_path':f'dir{n%3}\\new{n}.txt','previous_relative_path':f'dir{n%3}\\old{n}.txt'}) for n in range(20))
    return [EndpointEvent.model_validate(event(identity,k,d,t+timedelta(seconds=n))).model_dump(mode='json')|{'id':f'evidence-{n}','workspace_id':'fixture'} for n,(k,d) in enumerate(specs)]


def test_rules_shadow_network_destructive_and_negative_controls():
    policy=policy_fixture();state={};findings=[]
    for e in signals(policy):state,fs=correlate(e,state,policy);findings.extend(fs)
    assert {f['rule_id'] for f in findings}=={'shadow-ai-sensitive-repository','periodic-unlisted-destination','destructive-file-pattern'}
    assert all(not f['response']['executed'] and f['response']['requested_action'] is None for f in findings)
    assert all(f['evidence_ids'] and f['limitations'] for f in findings)
    # Normal build/create-only and explicitly approved tool/known destination.
    policy['approved_tools']=['fixture-ai'];policy['known_destinations']=['192.0.2.40']
    state={};findings=[]
    for e in signals(policy):
        if e['event_type']=='file_renamed':e['event_type']='file_created'
        state,fs=correlate(e,state,policy);findings.extend(fs)
    assert not findings


def test_indicator_match_is_separate_and_history_bounded():
    policy=policy_fixture();policy['indicator_sha256']=['a'*64]
    e=signals(policy)[2];e['data']['sha256']='a'*64
    state,findings=correlate(e,{},policy)
    assert findings[0]['rule_id']=='configured-hash-indicator'
    for n in range(520):state,_=correlate({**e,'id':str(n)},state,policy)
    assert len(state['events'])==512


def test_shadow_requires_running_and_repository_activity():
    policy=policy_fixture();items=signals(policy)[:2];items[0]['event_type']='ai_tool_discovered'
    state={}
    for e in items:state,findings=correlate(e,state,policy);assert not findings


def test_enrollment_expiry_and_other_workspace(endpoint_platform):
    client,ledger,settings=endpoint_platform
    provision=client.post('/api/v1/endpoints/provision',json={},headers=ADMIN).json()
    with ledger.engine.begin() as c:c.execute(update(endpoints).values(bootstrap_until='2000-01-01T00:00:00+00:00'))
    response=client.post('/api/v1/endpoints/enroll',json={k:v for k,v in provision.items() if k!='expires_in'}|{'sensor_instance_id':str(uuid.uuid4())})
    assert response.status_code==401
    other=TestClient(create_app(replace(settings,workspace_id='other'),ledger.engine))
    assert other.get('/api/v1/endpoints',headers=ADMIN).json()['items']==[]
    assert other.post('/api/v1/endpoints/'+provision['endpoint_id']+'/revoke',headers=ADMIN).status_code==404
