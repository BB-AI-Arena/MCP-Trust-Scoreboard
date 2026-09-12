"""Synthetic Falcon protocol + webhook receiver, never a vendor/live account.

Shapes/operations grounded in official OAuth2, Hosts and Alerts references.
This file can also run inside a disposable fixture container. No customer data.
"""
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import ssl
from urllib.parse import parse_qs, urlsplit

CID = 'a' * 32
HOSTS = ['1' * 32, '2' * 32]


def initial_state():
    stamp = (datetime.now(timezone.utc)-timedelta(hours=1)).isoformat()
    return {'calls':[], 'tokens':0, 'plans':{}, 'received':[], 'accepted_ids':[],
        'webhook_failures':1, 'expire_cursor':False,
        'hosts':[{'device_id':i,'cid':CID,'hostname':'fixture-host','platform_name':'Linux',
                  'agent_version':'fixture-sensor','first_seen':stamp,'last_seen':stamp,'status':'normal'} for i in HOSTS],
        'alerts':[{'cid':CID,'composite_id':CID+':alert:'+str(i),'id':'alert-'+str(i),
                   'agent_id':host,'created_timestamp':stamp,'updated_timestamp':stamp,
                   'timestamp':stamp,'severity':70,'severity_name':'High','status':'new',
                   'description':'fixture untrusted text: eval(user); never execute',
                   'cmdline':'sensitive-fixture-command-not-retained','product':'epp','type':'ldt'} for i,host in enumerate(HOSTS)]}


def handler(state, state_file=None):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*_):
            pass

        def do_GET(self):
            self.handle_request()

        def do_POST(self):
            self.handle_request()

        def handle_request(self):
            if state_file and Path(state_file).exists():
                state.clear()
                state.update(json.loads(Path(state_file).read_text()))
            url = urlsplit(self.path)
            query = parse_qs(url.query)
            raw = self.rfile.read(int(self.headers.get('Content-Length',0)))
            body = parse_qs(raw.decode()) if url.path=='/oauth2/token' else json.loads(raw or b'{}')
            state['calls'].append([self.command,url.path])  # never log credentials
            status, headers, response = 200, {}, {'errors':[],'resources':[]}
            plan = state['plans'].get(url.path,[])
            if plan:
                item = plan.pop(0)
                status, headers, response = item.get('status',200), item.get('headers',{}), item.get('body',{})
            elif url.path=='/oauth2/token' and self.command=='POST':
                if not body.get('client_id') or not body.get('client_secret'):
                    status = 401
                else:
                    state['tokens'] += 1
                    response = {'access_token':'fixture-access-'+str(state['tokens']), 'expires_in':1800,'token_type':'bearer'}
            elif url.path=='/findings' and self.command=='POST':
                assert self.headers['Idempotency-Key']==body['delivery_id']
                state['received'].append(body)
                if state['webhook_failures']:
                    state['webhook_failures'] -= 1
                    status = 503
                else:
                    status = 204
                    if body['delivery_id'] not in state['accepted_ids']:
                        state['accepted_ids'].append(body['delivery_id'])
            elif self.headers.get('Authorization') != 'Bearer fixture-access-'+str(state['tokens']):
                status = 401
            elif url.path=='/devices/queries/devices-scroll/v1' and self.command=='GET':
                offset = int(query.get('offset',['h:0'])[0].split(':')[-1])
                limit = int(query['limit'][0])
                items = state['hosts'][offset:offset+limit]
                response = {'errors':[], 'resources':[i['device_id'] for i in items],
                            'meta':{'pagination':{'offset':'h:'+str(offset+len(items)),'total':len(state['hosts'])}}}
            elif url.path=='/devices/entities/devices/v2' and self.command=='GET':
                response = {'errors':[], 'resources':[i for i in state['hosts'] if i['device_id'] in query['ids']]}
            elif url.path=='/alerts/combined/alerts/v1' and self.command=='POST':
                assert body['sort']=='created_timestamp|asc'
                assert "cid:'"+CID+"'" in body['filter']
                if body.get('after') and state['expire_cursor']:
                    state['expire_cursor'] = False
                    status = 400
                else:
                    offset = int(body.get('after','a:0').split(':')[-1])
                    items = state['alerts'][offset:offset+body['limit']]
                    pagination = {'total':len(state['alerts'])}
                    if offset+len(items)<len(state['alerts']):
                        pagination['after'] = 'a:'+str(offset+len(items))
                    response = {'errors':[], 'resources':items,'meta':{'pagination':pagination}}
            else:
                status = 405
            if state_file:
                Path(state_file).write_text(json.dumps(state))
            self.send_response(status)
            self.send_header('Content-Type','application/json')
            for key,value in headers.items():
                self.send_header(key,value)
            self.end_headers()
            if status!=204:
                self.wfile.write(response.encode() if isinstance(response,str) else json.dumps(response).encode())
    return Handler


def server(state, address, certificate, key, state_file=None):
    http = ThreadingHTTPServer(address,handler(state,state_file))
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(certificate,key)
    http.socket = context.wrap_socket(http.socket, server_side=True)
    return http


if __name__=='__main__':
    instance = server(initial_state(),('0.0.0.0',8443),'/certs/cert.pem','/certs/key.pem','/tmp/state.json')
    print('fixture-ready',flush=True)
    instance.serve_forever()
