"""Disposable loopback demo receiver; not a production webhook service.

Prints each finding once per process. Deduplication is bounded/in-memory and
does not survive restart. Never expose this unauthenticated demo publicly.
"""
import argparse
from http.server import BaseHTTPRequestHandler, HTTPServer
import json


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=9099)
    args = parser.parse_args()
    seen = set()

    class Receiver(BaseHTTPRequestHandler):
        def do_POST(self):
            try:
                length = int(self.headers.get('Content-Length','0'))
                if not 0 < length <= 64000:
                    raise ValueError('body size')
                body = json.loads(self.rfile.read(length))
                delivery = body['delivery_id']
                if not isinstance(delivery,str) or len(delivery) > 128 or delivery != self.headers.get('Idempotency-Key'):
                    raise ValueError('delivery ID')
                if len(seen) >= 1000 and delivery not in seen:
                    self.send_error(503,'Demo capacity reached')
                    return
                if delivery not in seen:
                    print(json.dumps(body),flush=True)
                    seen.add(delivery)
            except (ValueError,KeyError,TypeError):
                self.send_error(400,'Invalid finding envelope')
                return
            self.send_response(204)
            self.end_headers()

    server = HTTPServer(('127.0.0.1',args.port),Receiver)
    print(f'DEMO receiver: http://127.0.0.1:{server.server_port}/findings; memory-only deduplication',flush=True)
    server.serve_forever()


if __name__ == '__main__':
    main()
