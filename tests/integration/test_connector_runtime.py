"""Installed API/worker + real PostgreSQL + real, isolated TLS webhook receiver.

Only disposable certificates/data. No live vendor calls and no HTTP mocking.
"""
import json
import subprocess

import httpx
import pytest

from .conftest import docker, eventually
from .test_container_runtime import start_api, HEADERS, TOKEN

pytestmark = pytest.mark.integration

RECEIVER = r'''
from http.server import BaseHTTPRequestHandler, HTTPServer
import json, ssl
requests = []
class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
        assert self.headers.get('Authorization') == 'Bearer fixture-destination-only'
        assert self.headers['Idempotency-Key'] == body['delivery_id']
        requests.append(body)
        with open('/tmp/received.json','w') as handle:
            json.dump(requests,handle)
        self.send_response(503 if len(requests) == 1 else 204)
        self.end_headers()
    def log_message(self, *_): pass
server = HTTPServer(('0.0.0.0',8443),Handler)
context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
context.load_cert_chain('/certs/cert.pem','/certs/key.pem')
server.socket = context.wrap_socket(server.socket,server_side=True)
print('receiver-ready',flush=True)
server.serve_forever()
'''


def test_installed_json_finding_tls_delivery_and_retry_restart(containers, postgres, platform_image, tmp_path):
    certs = tmp_path / 'certificates'
    certs.mkdir()
    subprocess.run(['openssl','req','-x509','-newkey','rsa:2048','-nodes','-days','1',
        '-keyout',str(certs / 'key.pem'),'-out',str(certs / 'cert.pem'),
        '-subj','/CN=receiver','-addext','subjectAltName=DNS:receiver'],
        capture_output=True, check=True, timeout=20)
    mount = f'type=bind,src={certs},dst=/certs,readonly'
    receiver = containers.run('receiver',platform_image,'--network-alias','receiver',
        '--mount',mount,command=('python','-u','-c',RECEIVER))
    eventually(lambda: 'receiver-ready' in docker('logs',receiver))
    # Negative TLS check: the same self-signed receiver must be rejected without
    # the explicitly mounted fixture CA. A verify=False implementation fails this.
    negative = containers.run('untrusted-tls',platform_image,command=('python','-c',
        "from agent_trust.adapters.connectors.webhook import WebhookDestination,DeliveryError; "
        "from agent_trust.config import Settings; "
        f"s=Settings(webhook_url='https://receiver:8443/findings',webhook_allowed_hosts=('receiver',),webhook_allowed_cidrs=('{containers.address(receiver)}/32',)); "
        "\ntry: WebhookDestination(s).deliver({'id':'fixture'},'negative')\n"
        "except DeliveryError as e: assert str(e)=='destination_transport_failed'; print('untrusted-certificate-rejected')\n"
        "else: raise AssertionError('untrusted TLS certificate accepted')"))
    eventually(lambda: json.loads(docker('inspect','--format','{{json .State}}',negative))['Status'] == 'exited')
    assert 'untrusted-certificate-rejected' in docker('logs',negative)
    worker = containers.run('connector-worker',platform_image,'--mount',mount,
        '-e',f'DATABASE_URL={postgres["internal"]}', '-e',f'AGENT_TRUST_API_TOKEN={TOKEN}',
        '-e','SSL_CERT_FILE=/certs/cert.pem',
        '-e','AGENT_TRUST_WEBHOOK_URL=https://receiver:8443/findings',
        '-e','AGENT_TRUST_WEBHOOK_ALLOWED_HOSTS=receiver',
        '-e',f'AGENT_TRUST_WEBHOOK_ALLOWED_CIDRS={containers.address(receiver)}/32',
        '-e','AGENT_TRUST_WEBHOOK_BEARER_TOKEN=fixture-destination-only',
        command=('agent-trust-worker',))
    api, url = start_api(containers,platform_image,postgres['internal'])
    body = {'schema_version':'1','event_id':'real-tls-event','subject':'fixture-tool',
            'reported_agent_id':'claimed-agent','observed_at':'2026-09-01T12:00:00Z',
            'content':'eval(user)'}
    with httpx.Client(base_url=url,trust_env=False,timeout=5) as client:
        route = '/api/v1/connectors/generic-json/events'
        assert client.post(route,json=body).status_code == 401
        submitted = client.post(route,json=body,headers=HEADERS)
        assert submitted.status_code == 202
        job_id = submitted.json()['job_id']
        assert client.post(route,json=body,headers=HEADERS).json()['job_id'] == job_id
        assert client.post(route,json={**body,'content':'different'},headers=HEADERS).status_code == 409
        def completed_ingestion():
            job = client.get('/api/v1/jobs/' + job_id,headers=HEADERS).json()
            return job if job.get('status') == 'complete' else None
        ingestion = eventually(completed_ingestion)
        delivery_id = ingestion['result']['delivery_job_ids'][0]
        def failed_once():
            job = client.get('/api/v1/jobs/' + delivery_id,headers=HEADERS).json()
            return job if job.get('attempts') == 1 and job.get('status') == 'queued' else None
        failed = eventually(failed_once)
        assert failed['error'] == 'destination_http_503', (failed,docker('logs',worker))
        containers.stop(worker)
        containers.restart(api)
        client.base_url = f'http://{containers.address(api)}:8080'
        eventually(lambda: client.get('/readiness').status_code == 200)
        evidence = client.get('/api/v1/evidence',headers=HEADERS).json()['items']
        findings = client.get('/api/v1/findings',headers=HEADERS).json()['items']
        assert len(evidence) == len(findings) == 1
        assert evidence[0]['collector_identity'] == 'api-token' and evidence[0]['status'] == 'claimed'
        assert findings[0]['evidence_ids'] == [evidence[0]['id']]
        assert 'content' not in evidence[0]
        containers.restart(worker)
        def delivered():
            job = client.get('/api/v1/jobs/' + delivery_id,headers=HEADERS).json()
            return job if job.get('status') == 'complete' else None
        delivery = eventually(delivered)
        assert delivery['attempts'] == 2
        assert delivery['result']['outcome'] == 'accepted_by_destination'
        assert delivery['result']['response_action'] is None
        # An assessment job still runs in the same worker after connector jobs.
        assessment = client.post('/api/v1/assessments',headers=HEADERS,
                                 json={'subject_id':'mixed-worker','content':'eval(user)'}).json()
        eventually(lambda: client.get('/api/v1/jobs/' + assessment['job_id'],headers=HEADERS).json()['status'] == 'complete')
    received = json.loads(docker('exec',receiver,'python','-c',"print(open('/tmp/received.json').read())"))
    assert len(received) == 2
    assert {r['delivery_id'] for r in received} == {delivery_id}
    assert received[1]['finding']['id'] == findings[0]['id']
