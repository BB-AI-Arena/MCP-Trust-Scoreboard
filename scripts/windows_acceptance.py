"""Real Windows foreground sensor + API/worker/PostgreSQL acceptance.

Run only in the dedicated disposable CI job. No vendor credentials or operator DB.
The PostgreSQL process/cluster is created separately under RUNNER_TEMP by the job.
"""
from datetime import datetime, timedelta, timezone
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


def main():
    if sys.platform!='win32' or os.getenv('AGENT_TRUST_DISPOSABLE_WINDOWS_TEST')!='1':
        raise RuntimeError('requires explicit isolated Windows test environment')
    assert os.environ['DATABASE_URL'].startswith('postgresql://fixture@127.0.0.1:')
    evidence=ROOT/'evidence'/'windows';evidence.mkdir(parents=True,exist_ok=True)
    executable=ROOT/'sensor'/'dist'/'agent-trust-sensor.exe'
    helper=ROOT/'sensor'/'dist'/'fixture-process.exe'
    version=json.loads(subprocess.check_output([str(executable),'version'],text=True))
    token=uuid.uuid4().hex+uuid.uuid4().hex
    api_port=free_port();origin=f'http://127.0.0.1:{api_port}'
    env={**os.environ,'AGENT_TRUST_API_TOKEN':token,'AGENT_TRUST_WORKSPACE_ID':'windows-ci',
        'AGENT_TRUST_HOST':'127.0.0.1','AGENT_TRUST_PORT':str(api_port)}
    headers={'Authorization':'Bearer '+token}
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
    children=[];handles=[]
    def launch(args,role,extra=None):
        log=open(evidence/(role+'.log'),'a',encoding='utf-8');handles.append(log)
        p=subprocess.Popen(args,env=extra or env,stdout=log,stderr=log,cwd=ROOT);children.append(p);return p
    def stop(p):
        if p.poll() is None:
            p.terminate()
            try:p.wait(timeout=15)
            except subprocess.TimeoutExpired:p.kill();p.wait(timeout=5)
    api=None
    try:
        with tempfile.TemporaryDirectory(prefix='atp-windows-sensor-') as temporary:
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
            enroll_env={**env,'AGENT_TRUST_ENROLLMENT_SECRET':provision['bootstrap_secret']}
            enrolled=subprocess.run([str(executable),'enroll','--config',str(config_path)],env=enroll_env,capture_output=True,text=True,timeout=30)
            assert enrolled.returncode==0,'enrollment failed (no private response logged)'
            secret=provision.pop('bootstrap_secret');assert secret.encode() not in (data/'identity.dpapi').read_bytes()
            sensor=launch([str(executable),'run','--config',str(config_path),'--seconds','300'],'sensor')
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
            listener=socket.socket();listener.bind(('127.0.0.1',0));listener.listen()
            actor=launch([str(cursor),f'127.0.0.1:{listener.getsockname()[1]}'],'fixture-process')
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
            sensor=launch([str(executable),'run','--config',str(config_path),'--seconds','180'],'sensor')
            assert len(list((data/'spool').glob('*.event')))>=len(persisted)
            api=launch([sys.executable,'-c','from agent_trust.api.app import run; run()'],'api')
            wait(lambda:httpx.get(origin+'/readiness').status_code==200)
            wait(lambda:persisted <= {e.get('event_id') for e in all_records('evidence')},150)
            stop(sensor)
            (data/'spool'/replay_name).write_bytes(replay_bytes)
            sensor=launch([str(executable),'run','--config',str(config_path),'--seconds','120'],'sensor')
            wait(lambda:not (data/'spool'/replay_name).exists(),60)
            replay_id=json.loads(replay_bytes)['event_id'];assert sum(e.get('event_id')==replay_id for e in all_records('evidence'))==1
            # Separate synthetic network/behavior fixtures exercise central rules;
            # real collector activity above is not called malicious or attributed.
            from agent_trust.api.app import create_app
            from agent_trust.config import Settings
            from agent_trust.storage.database import make_engine
            from fastapi.testclient import TestClient
            sys.path.insert(0,str(ROOT/'tests'))
            from test_endpoint import ADMIN,enrollment,ingest,signals
            engine=make_engine(env['DATABASE_URL']);client=TestClient(create_app(Settings(api_token='fixture-endpoint-administrator',workspace_id='windows-ci'),engine))
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
            connection.close();listener.close();stop(actor);engine.dispose()
            # Stop all owned processes before disposable directory cleanup.
            for p in reversed(children):stop(p)
            summary={'source_sha':os.getenv('SENSOR_SOURCE_SHA',os.getenv('GITHUB_SHA','local')),'version':version,'runner_os':os.getenv('ImageOS'),
                'runner_image_version':os.getenv('ImageVersion'),'real_windows_collectors':['process','tcp_ipv4_loopback','filesystem_create_modify_rename_delete','registry_os'],
                'fixture_discovery':['Cursor path with benign helper','MCP JSON without execution'],
                'synthetic_detections':['periodic network pattern','destructive metadata pattern'],
                'persisted_offline_events':len(persisted),'deduplicated_replay':True,'finding_count':len(findings),
                'receiver_attempts':len(received),'accepted_deliveries':len(accepted),'blocking_actions':0,
                'service_mode':'foreground runtime tested; SCM deployment under chosen service account not exercised',
                'binary_sha256':hashlib.sha256(executable.read_bytes()).hexdigest(),'result':'passed'}
            (evidence/'acceptance.json').write_text(json.dumps(summary,indent=2))
    finally:
        for p in reversed(children):stop(p)
        for h in handles:h.close()
        receiver.shutdown();receiver.server_close()


if __name__=='__main__':main()
