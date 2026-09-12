"""Operator-configured webhook with pinned-address connection and no redirects.

No URL/credentials from evidence; no environment proxies or credential forwarding.
The receiver must deduplicate Idempotency-Key: execution is at least once.
"""
import http.client
import ipaddress
import json
import socket
import ssl
from threading import Timer
from urllib.parse import urlsplit

from agent_trust.config import Settings


class DeliveryError(RuntimeError):
    """Safe error codes only: URLs, response bodies and credentials stay private."""


def resolve_target(settings: Settings):
    if not settings.webhook_url:
        raise DeliveryError('destination_unavailable')
    url = urlsplit(settings.webhook_url)
    if url.scheme not in {'http','https'} or not url.hostname or url.username or url.password or url.fragment:
        raise DeliveryError('destination_url_invalid')
    host = url.hostname.lower().rstrip('.')
    if host not in settings.webhook_allowed_hosts:
        raise DeliveryError('destination_host_not_allowed')
    try:
        port = url.port or (443 if url.scheme == 'https' else 80)
        networks = [ipaddress.ip_network(n, strict=True) for n in settings.webhook_allowed_cidrs]
        targets = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
        if not targets:
            raise ValueError('no addresses')
        for target in targets:
            address = ipaddress.ip_address(target[4][0])
            if getattr(address, 'ipv4_mapped', None):
                address = address.ipv4_mapped
            if address.is_link_local or address.is_multicast or address.is_unspecified or address.is_reserved:
                raise ValueError('prohibited address')
            if not address.is_global and not any(address in network for network in networks):
                raise ValueError('private collector scope required')
            if url.scheme == 'http' and not (settings.webhook_allow_http and address.is_loopback):
                raise ValueError('TLS required except explicit loopback fixtures')
    except (OSError, ValueError) as exc:
        raise DeliveryError('destination_resolution_or_scope_failed') from exc
    return url, host, port, targets[0]


def request_bytes(settings: Settings, method: str, body: bytes | None, headers: dict,
                  max_response_bytes: int = 4096):
    """Shared bounded transport; callers independently authorize operations.

    Returns status/headers/bytes, never follows redirects or uses proxies.
    Kept here to preserve the reference connector's tested address pinning.
    """
    url, host, port, target = resolve_target(settings)
    connection = http.client.HTTPConnection(host, port, timeout=settings.webhook_timeout_seconds)
    sock = socket.socket(target[0], target[1], target[2])
    sock.settimeout(settings.webhook_timeout_seconds)
    timer = None
    try:
        # Connect directly to the validated sockaddr: no second DNS lookup.
        sock.connect(target[4])
        if url.scheme == 'https':
            sock = ssl.create_default_context().wrap_socket(sock, server_hostname=host)
        connection.sock = sock
        def abort():
            try:
                sock.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
        timer = Timer(settings.webhook_timeout_seconds, abort)
        timer.daemon = True
        timer.start()
        path = url.path or '/'
        if url.query:
            path += '?' + url.query
        connection.request(method, path, body=body, headers=headers)
        response = connection.getresponse()
        status = response.status
        # Response content is not retained or interpreted as instructions.
        data = response.read(max_response_bytes + 1)
        if len(data) > max_response_bytes:
            raise DeliveryError('destination_response_too_large')
        return status, {k.lower():v for k,v in response.getheaders()}, data
    except DeliveryError:
        raise
    except (OSError, ValueError, http.client.HTTPException) as exc:
        raise DeliveryError('destination_transport_failed') from exc
    finally:
        if timer:
            timer.cancel()
        connection.close()
        sock.close()


class WebhookDestination:
    name = 'webhook'

    def __init__(self, settings: Settings):
        self.settings = settings

    def deliver(self, finding: dict, delivery_id: str) -> dict:
        body = json.dumps({'schema_version':'1','delivery_id':delivery_id,'finding':finding},
                          sort_keys=True, separators=(',',':')).encode()
        if len(body) > 64_000:
            raise DeliveryError('delivery_body_too_large')
        headers = {'Content-Type':'application/json','Idempotency-Key':delivery_id,
                   'User-Agent':'agent-trust-webhook/1'}
        if self.settings.webhook_token:
            headers['Authorization'] = 'Bearer ' + self.settings.webhook_token
        status, _, _ = request_bytes(self.settings, 'POST', body, headers)
        if not 200 <= status < 300:
            raise DeliveryError(f'destination_http_{status}')
        return {'destination':'webhook','outcome':'accepted_by_destination',
                'http_status':status,'delivery_id':delivery_id,'response_action':None}
