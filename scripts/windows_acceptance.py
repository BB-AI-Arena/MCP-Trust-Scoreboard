"""Real Windows foreground sensor + API/worker/PostgreSQL acceptance.

Run only in the dedicated disposable CI job. No vendor credentials or operator DB.
The PostgreSQL process/cluster is created separately under RUNNER_TEMP by the job.
"""
from datetime import datetime, timedelta, timezone
from contextlib import contextmanager
from collections import Counter
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import hashlib
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import time
import uuid

import httpx

ROOT=Path(__file__).resolve().parents[1]


def free_port():
    with socket.socket() as s:
        s.bind(('127.0.0.1',0));return s.getsockname()[1]


def wait(check,seconds=120):
    deadline=time.monotonic()+seconds
    while time.monotonic()<deadline:
        try:
            result=check()
            if result:return result
        except (httpx.HTTPError,OSError,KeyError):pass
        time.sleep(.5)
    raise AssertionError('Windows acceptance condition timed out')


def persisted_event_counts(engine, workspace_id):
    """One statement snapshot, not shifting offset pages during live ingestion.

    Keep multiplicity: a genuine duplicate logical event MUST fail acceptance.
    Only used against the dedicated disposable acceptance database.
    """
    from sqlalchemy import select
    from agent_trust.storage.database import records
    with engine.connect() as connection:
        rows=connection.execute(select(records.c.payload).where(
            records.c.kind=='evidence',records.c.workspace_id==workspace_id)).scalars().all()
    return Counter(json.loads(row).get('event_id') for row in rows)


def main(service_mode=False):
    if sys.platform!='win32' or os.getenv('AGENT_TRUST_DISPOSABLE_WINDOWS_TEST')!='1':
        raise RuntimeError('requires explicit isolated Windows test environment')
    assert os.environ['DATABASE_URL'].startswith('postgresql://fixture@127.0.0.1:')
    from agent_trust.storage.database import make_engine
    engine=make_engine(os.environ['DATABASE_URL'])
    evidence=ROOT/'evidence'/'windows'/('service' if service_mode else 'foreground');evidence.mkdir(parents=True,exist_ok=True)
    executable=ROOT/'sensor'/'dist'/'agent-trust-sensor.exe'
    helper=ROOT/'sensor'/'dist'/'fixture-process.exe'
    version=json.loads(subprocess.check_output([str(executable),'version'],text=True))
    token=uuid.uuid4().hex+uuid.uuid4().hex
    api_port=free_port();origin=f'http://127.0.0.1:{api_port}'
    env={**os.environ,'AGENT_TRUST_API_TOKEN':token,'AGENT_TRUST_WORKSPACE_ID':'windows-ci',
        'AGENT_TRUST_HOST':'127.0.0.1','AGENT_TRUST_PORT':str(api_port)}
    headers={'Authorization':'Bearer '+token}
    sensor_env={k:v for k,v in os.environ.items() if k not in ('DATABASE_URL','AGENT_TRUST_API_TOKEN','AGENT_TRUST_ENROLLMENT_SECRET')}
    received=[];accepted=set()
    class Receiver(BaseHTTPRequestHandler):
        def do_POST(self):
            body=json.loads(self.rfile.read(int(self.headers['Content-Length'])))
            received.append(body)
            if len(received)==1:self.send_response(503)
            else:accepted.add(body['delivery_id']);self.send_response(204)
            self.end_headers()
        def log_message(self,*_):pass
    receiver=ThreadingHTTPServer(('127.0.0.1',0),Receiver)
    threading.Thread(target=receiver.serve_forever,daemon=True).start()
    env.update(AGENT_TRUST_WEBHOOK_URL=f'http://127.0.0.1:{receiver.server_port}/findings',
        AGENT_TRUST_WEBHOOK_ALLOWED_HOSTS='127.0.0.1',AGENT_TRUST_WEBHOOK_ALLOWED_CIDRS='127.0.0.1/32',AGENT_TRUST_WEBHOOK_ALLOW_HTTP='true')
    children=[];handles=[];scm=None
    def launch(args,role,extra=None):
        log=open(evidence/(role+'.log'),'a',encoding='utf-8');handles.append(log)
        p=subprocess.Popen(args,env=extra or env,stdout=log,stderr=log,cwd=ROOT);children.append(p);return p
    def stop(p):
        if service_mode and p is scm:
            scm.stop();return
        if p.poll() is None:
            p.terminate()
            try:p.wait(timeout=15)
            except subprocess.TimeoutExpired:p.kill();p.wait(timeout=5)
    @contextmanager
    def workspace():
        with tempfile.TemporaryDirectory(prefix='atp-windows-sensor-') as temporary:
            try:yield temporary
            finally:
                # Release Windows executable/spool handles BEFORE removing only
                # this helper-created temporary directory, including on failure.
                if scm is not None:scm.cleanup()
                for child in reversed(children):stop(child)
    api=None
    try:
        with workspace() as temporary:
            root=Path(temporary);profile=root/'profile';data=root/'sensor-data';repo=root/'repository';repo.mkdir();(repo/'src').mkdir()
            cursor=profile/'AppData'/'Local'/'Programs'/'cursor'/'Cursor.exe';cursor.parent.mkdir(parents=True);shutil.copy2(helper,cursor)
            mcp=profile/'.cursor'/'mcp.json';mcp.parent.mkdir();sentinel=root/'MCP_MUST_NOT_EXECUTE'
            mcp.write_text(json.dumps({'mcpServers':{'fixture':{'command':'cmd.exe','args':['/c',f'echo unexpected>{sentinel}'],'env':{'SECRET':'synthetic-never-upload-token'}}}}))
            # A repository UUID is centrally assigned, not inferred from its name.
            repo_id=str(uuid.uuid4());policy={'repositories':[{'id':repo_id,'path':str(repo),'classification':'Restricted'}]}
            api=launch([sys.executable,'-c','from agent_trust.api.app import run; run()'],'api')
            wait(lambda:httpx.get(origin+'/readiness').status_code==200)
            worker=launch([sys.executable,'-c','from agent_trust.jobs.worker import run; run()'],'worker')
            provision=httpx.post(origin+'/api/v1/endpoints/provision',headers=headers,json=policy).json()
            config={'server':origin,'endpoint_id':provision['endpoint_id'],'data_dir':str(data),
                'allowed_roots':[str(root)],'profile_roots':[str(profile)],'allowed_cidrs':['127.0.0.1/32'],
                'allow_loopback_http':True,'interval_seconds':1,'spool_count':10000,'spool_bytes':32<<20,'spool_hours':24}
            config_path=root/'sensor.json';config_path.write_text(json.dumps(config))
            if service_mode:
                from windows_service_acceptance import ServiceAcceptance
                scm=ServiceAcceptance(root,executable,config_path,provision['bootstrap_secret'],evidence,sensor_env)
                data=scm.data
            else:
                enroll_env={**sensor_env,'AGENT_TRUST_ENROLLMENT_SECRET':provision['bootstrap_secret']}
                enrolled=subprocess.run([str(executable),'enroll','--config',str(config_path)],env=enroll_env,capture_output=True,text=True,timeout=30)
                assert enrolled.returncode==0,'enrollment failed (no private response logged)'
            secret=provision.pop('bootstrap_secret');assert secret.encode() not in (data/'identity.dpapi').read_bytes()
            def start_sensor(seconds):
                if service_mode:return scm.start()
                return launch([str(executable),'run','--config',str(config_path),'--seconds',str(seconds)],'sensor',sensor_env)
            sensor=scm if service_mode else start_sensor(300)
            def all_records(kind):
                out=[]
                for offset in range(0,4000,100):
                    page=httpx.get(origin+'/api/v1/'+kind,headers=headers,params={'limit':100,'offset':offset},timeout=15).json()['items'];out.extend(page)
                    if len(page)<100:break
                return out
            def observed(kind):return [e for e in all_records('evidence') if e.get('event_type')==kind]
            wait(lambda:observed('endpoint_heartbeat'),150)
            wait(lambda:observed('ai_tool_discovered'))
            wait(lambda:observed('mcp_configuration_discovered'))
            assert observed('software_inventory')
            if scm:scm.validate_lifecycle()
            listener=socket.socket();listener.settimeout(15);listener.bind(('127.0.0.1',0));listener.listen()
            actor=launch([str(cursor),f'127.0.0.1:{listener.getsockname()[1]}'],'fixture-process',sensor_env)
            connection,_=listener.accept()
            wait(lambda:any(e['data']['pid']==actor.pid for e in observed('process_started')))
            wait(lambda:any(e['data']['pid']==actor.pid for e in observed('process_network_connection')))
            wait(lambda:observed('ai_tool_running'))
            file=repo/'src'/'benign.txt';file.write_text('benign repository fixture')
            wait(lambda:observed('file_created'))
            file.write_text('changed benign repository fixture')
            wait(lambda:observed('file_modified'))
            file.rename(repo/'src'/'renamed.txt');wait(lambda:observed('file_renamed'))
            (repo/'src'/'renamed.txt').unlink();wait(lambda:observed('file_deleted'))
            wait(lambda:any(f['rule_id']=='shadow-ai-sensitive-repository' for f in all_records('findings')))
            stop(api)
            before=len(list((data/'spool').glob('*.event')))
            (repo/'src'/'offline.txt').write_text('offline disposable fixture')
            wait(lambda:len(list((data/'spool').glob('*.event')))>before,30)
            stop(sensor)
            persisted={json.loads(p.read_text())['event_id'] for p in (data/'spool').glob('*.event')}
            assert persisted,'offline spool did not persist'
            # Retain one exact event and replay it after central acknowledgment.
            replay_path=next((data/'spool').glob('*.event'));replay_name=replay_path.name;replay_bytes=replay_path.read_bytes()
            sensor=start_sensor(180)
            assert len(list((data/'spool').glob('*.event')))>=len(persisted)
            if scm:scm.assert_preserved(persisted)
            api=launch([sys.executable,'-c','from agent_trust.api.app import run; run()'],'api')
            wait(lambda:httpx.get(origin+'/readiness').status_code==200)
            wait(lambda:persisted <= persisted_event_counts(engine,'windows-ci').keys(),150)
            stop(sensor)
            (data/'spool'/replay_name).write_bytes(replay_bytes)
            sensor=start_sensor(120)
            wait(lambda:not (data/'spool'/replay_name).exists(),60)
            replay_id=json.loads(replay_bytes)['event_id']
            replay_count=persisted_event_counts(engine,'windows-ci')[replay_id]
            assert replay_count==1,f'persisted replay count must be exactly one, got {replay_count}'
            if scm:
                scm.summary.update(queued_count=len(persisted),recovered_count=len(persisted),uploaded_count=len(persisted),persisted_replay_count=replay_count,replay_attempts=1)
                assert all(persisted_event_counts(engine,'windows-ci')[event_id]==1 for event_id in persisted)
                wait(lambda:scm.health()['spool_depth']==0,120)
            # Separate synthetic network/behavior fixtures exercise central rules;
            # real collector activity above is not called malicious or attributed.
            from agent_trust.api.app import create_app
            from agent_trust.config import Settings
            from fastapi.testclient import TestClient
            sys.path.insert(0,str(ROOT/'tests'))
            from test_endpoint import ADMIN,enrollment,ingest,signals
            client=TestClient(create_app(Settings(api_token='fixture-endpoint-administrator',workspace_id='windows-ci'),engine))
            synthetic,_=enrollment(client,policy)
            fixture_policy=httpx.get(origin+'/api/v1/endpoints/'+synthetic['endpoint_id']+'/policy',headers={'Authorization':'Bearer '+synthetic['credential']}).json()
            events=[{k:v for k,v in e.items() if k not in ('workspace_id','id')}|{'endpoint_id':synthetic['endpoint_id'],'sensor_instance_id':synthetic['sensor_instance_id']} for e in signals(fixture_policy)]
            assert ingest(client,synthetic,events).status_code==202
            # Actual controlled rename/modification burst in disposable files.
            for n in range(24):
                folder=repo/f'burst{n%3}';folder.mkdir(exist_ok=True);(folder/f'file{n}.txt').write_text('benign test bytes')
            time.sleep(3)
            for n in range(24):
                p=repo/f'burst{n%3}'/f'file{n}.txt';p.write_text('changed benign test bytes');p.rename(p.with_suffix('.renamed'))
            wait(lambda:{'periodic-unlisted-destination','destructive-file-pattern'} <= {f['rule_id'] for f in all_records('findings')},120)
            wait(lambda:len(accepted)>=3,90)
            stop(worker);worker=launch([sys.executable,'-c','from agent_trust.jobs.worker import run; run()'],'worker')
            wait(lambda:len(received)>len(accepted),30) # first transient receiver failure retried
            findings=all_records('findings');assert all(not f['response']['executed'] for f in findings)
            assert not sentinel.exists() and actor.poll() is None,'no MCP execution or blocking'
            assert 'synthetic-never-upload-token' not in json.dumps(all_records('evidence'))
            if scm:
                # Restart both central processes with the SCM sensor still active.
                old_pid=scm.health()['pid']
                stop(api);api=launch([sys.executable,'-c','from agent_trust.api.app import run; run()'],'api')
                wait(lambda:httpx.get(origin+'/readiness').status_code==200)
                wait(lambda:scm.health()['online'])
                assert scm.health()['pid']==old_pid
                history=persisted_event_counts(engine,'windows-ci')
                revoked=httpx.post(origin+'/api/v1/endpoints/'+provision['endpoint_id']+'/revoke',headers=headers)
                assert revoked.status_code==200
                scm.validate_revocation()
                after=persisted_event_counts(engine,'windows-ci')
                assert all(after[k]==v for k,v in history.items())
                scm.validate_uninstall()
                scm.summary.update(historical_evidence_preserved=True,findings_delivered=len(accepted),receiver_attempts=len(received),zero_enforcement_actions=True)
                scm.save()
            connection.close();listener.close();stop(actor)
            # Stop all owned processes before disposable directory cleanup.
            for p in reversed(children):stop(p)
            summary={'source_sha':os.getenv('SENSOR_SOURCE_SHA',os.getenv('GITHUB_SHA','local')),'version':version,'runner_os':os.getenv('ImageOS'),
                'runner_image_version':os.getenv('ImageVersion'),'real_windows_collectors':['process','tcp_ipv4_loopback','filesystem_create_modify_rename_delete','registry_os'],
                'fixture_discovery':['Cursor path with benign helper','MCP JSON without execution'],
                'synthetic_detections':['periodic network pattern','destructive metadata pattern'],
                'persisted_offline_events':len(persisted),'deduplicated_replay':True,'finding_count':len(findings),
                'persisted_replay_count':replay_count,'replay_verification':'single PostgreSQL statement snapshot',
                'receiver_attempts':len(received),'accepted_deliveries':len(accepted),'blocking_actions':0,
                'service_mode':'SCM virtual account' if service_mode else 'foreground',
                'binary_sha256':hashlib.sha256(executable.read_bytes()).hexdigest(),'result':'passed'}
            (evidence/'acceptance.json').write_text(json.dumps(summary,indent=2))
    finally:
        for p in reversed(children):stop(p)
        for h in handles:h.close()
        receiver.shutdown();receiver.server_close()
        engine.dispose()


if __name__=='__main__':main('--service' in sys.argv)
