"""Small read-operation allowlisted Falcon client, contract snapshot 2026-09-12.

No SDK dependency, redirects, region autodiscovery, customer write operations,
debug response logging, or credentials in serializable models.
"""
from dataclasses import dataclass, field, replace
from email.utils import parsedate_to_datetime
import json
import math
import os
import re
import time
from urllib.parse import urlencode, urlsplit
from typing import Any

from agent_trust.config import Settings
from .webhook import DeliveryError, request_bytes

REGIONS = {'us-1':'https://api.crowdstrike.com',
           'us-2':'https://api.us-2.crowdstrike.com',
           'eu-1':'https://api.eu-1.crowdstrike.com'}
TOKEN = '/oauth2/token'
HOSTS = '/devices/queries/devices-scroll/v1'
HOST_DETAILS = '/devices/entities/devices/v2'
ALERTS = '/alerts/combined/alerts/v1'
OPERATIONS = {('POST',TOKEN), ('GET',HOSTS), ('GET',HOST_DETAILS), ('POST',ALERTS)}


class FalconError(RuntimeError):
    def __init__(self, code: str, retry_after: float = 0):
        super().__init__(code)
        self.retry_after = retry_after


@dataclass(frozen=True)
class FalconConfig:
    connection_id: str
    account_cid: str
    region: str = 'us-1'
    client_id: str = field(default='', repr=False)
    client_secret: str = field(default='', repr=False)
    fixture_origin: str = ''
    fixture_cidrs: tuple[str, ...] = ()

    @classmethod
    def from_env(cls, connection_id, account_cid, region):
        return cls(connection_id, account_cid, region,
                   os.getenv('AGENT_TRUST_FALCON_CLIENT_ID',''),
                   os.getenv('AGENT_TRUST_FALCON_CLIENT_SECRET',''))

    def validate(self):
        if not re.fullmatch(r'[A-Za-z0-9_-]{1,64}', self.connection_id):
            raise FalconError('invalid_connection_id')
        if not re.fullmatch(r'[a-f0-9]{32}', self.account_cid):
            raise FalconError('invalid_account_cid')
        if self.region not in REGIONS:
            raise FalconError('unsupported_region')
        if not self.client_id or not self.client_secret:
            raise FalconError('credentials_unavailable')
        if self.fixture_origin:
            url = urlsplit(self.fixture_origin)
            if url.scheme != 'https' or url.path not in ('','/') or url.query or url.fragment or url.username or url.password:
                raise FalconError('invalid_tls_fixture_origin')


class FalconClient:
    def __init__(self, config: FalconConfig, *, max_requests=100, seconds=120,
                 sleep=time.sleep):
        config.validate()
        self.config = config
        self.origin = (config.fixture_origin or REGIONS[config.region]).rstrip('/')
        self.transport = Settings(webhook_url=self.origin,
            webhook_allowed_hosts=(urlsplit(self.origin).hostname,),
            webhook_allowed_cidrs=config.fixture_cidrs,
            webhook_timeout_seconds=5)
        self.remaining = max_requests
        self.deadline = time.monotonic() + seconds
        self.sleep = sleep
        self._token = ''
        self._expires = 0
        self._not_before = 0

    @staticmethod
    def retry_delay(headers, attempt):
        delays = [float(2 ** attempt)]
        try:
            value = headers.get('retry-after')
            if value:
                delays.append(float(value) if value.isdigit() else
                              parsedate_to_datetime(value).timestamp() - time.time())
            value = headers.get('x-ratelimit-retryafter')
            if value:
                delays.append(float(value) - time.time())  # vendor Unix timestamp
        except (ValueError, TypeError, OverflowError):
            raise FalconError('malformed_retry_guidance') from None
        if not all(math.isfinite(d) for d in delays):
            raise FalconError('malformed_retry_guidance')
        return max(delays)

    def _wire(self, method, path, body, headers):
        if time.time() < self._not_before:
            raise FalconError('retry_not_before', self._not_before - time.time())
        if self.remaining <= 0 or time.monotonic() >= self.deadline:
            raise FalconError('collection_budget_exhausted')
        self.remaining -= 1
        try:
            return request_bytes(replace(self.transport, webhook_url=self.origin + path),
                                 method, body, headers, max_response_bytes=2_000_000)
        except DeliveryError:
            raise FalconError('transport_unavailable') from None

    def _request(self, method: str, path: str, *, query=None, payload=None, token=False) -> dict[str, Any]:
        if (method,path) not in OPERATIONS:
            raise FalconError('operation_not_allowed')
        endpoint = path + ('?' + urlencode(query, doseq=True) if query else '')
        body = (urlencode(payload).encode() if token else json.dumps(payload).encode()) if payload is not None else None
        refreshed = False
        for attempt in range(3):
            if not token and (not self._token or time.monotonic() >= self._expires):
                self.authenticate()
            headers = {'Content-Type':'application/x-www-form-urlencoded' if token else 'application/json',
                       'Accept':'application/json','User-Agent':'agent-trust-falcon/1'}
            if not token:
                headers['Authorization'] = 'Bearer ' + self._token
            try:
                status, response_headers, raw = self._wire(method, endpoint, body, headers)
            except FalconError as error:
                if str(error) != 'transport_unavailable' or attempt == 2:
                    raise
                self._wait(2 ** attempt)
                continue
            if status == 401:
                if token or refreshed or attempt == 2:
                    raise FalconError('unauthorized')
                self._token = ''
                refreshed = True
                continue
            if status == 403:
                raise FalconError('permission_denied')
            if status == 429 or status in (500,502,503,504):
                delay = self.retry_delay(response_headers, attempt)
                code = 'rate_limited' if status == 429 else 'temporarily_unavailable'
                if attempt == 2 or delay > 5 or time.monotonic() + delay >= self.deadline:
                    self._not_before = time.time() + delay
                    raise FalconError(code, retry_after=delay)
                self._wait(delay)
                continue
            if status in (400,404,410) and not token:
                raise FalconError('invalid_request_or_cursor')
            if not 200 <= status < 300:
                raise FalconError('unauthorized' if token and status == 400 else 'unexpected_http_status')
            try:
                result = json.loads(raw)
                if not isinstance(result,dict):
                    raise ValueError()
            except (ValueError, UnicodeError):
                raise FalconError('malformed_response') from None
            if result.get('errors'):
                raise FalconError('partial_response')
            return result
        raise FalconError('request_attempts_exhausted')

    def _wait(self, seconds):
        if time.monotonic() + seconds >= self.deadline:
            raise FalconError('collection_budget_exhausted')
        self.sleep(seconds)

    def authenticate(self) -> None:
        result = self._request('POST', TOKEN, payload={
            'client_id':self.config.client_id,'client_secret':self.config.client_secret}, token=True)
        value, expiry = result.get('access_token'), result.get('expires_in')
        if not isinstance(value,str) or not value or len(value)>8192 or not isinstance(expiry,(int,float)) or not 0<expiry<=86400:
            raise FalconError('malformed_token_response')
        self._token = value
        self._expires = time.monotonic() + max(0, expiry - 5)

    def host_page(self, cursor: str | None, limit: int) -> tuple[list[dict[str, Any]], str | None]:
        query = {'limit':limit,'sort':'device_id.asc'}
        if cursor:
            query['offset'] = cursor
        result = self._request('GET', HOSTS, query=query)
        ids, cursor = self._page(result, 'offset', limit)
        if not all(isinstance(i,str) and re.fullmatch('[a-f0-9]{32}',i) for i in ids):
            raise FalconError('malformed_host_ids')
        if not ids:
            return [], None
        details = self._request('GET', HOST_DETAILS, query={'ids':ids})
        resources = details.get('resources')
        if not isinstance(resources,list) or any(not isinstance(r,dict) for r in resources) or {r.get('device_id') for r in resources} != set(ids) or len(resources)!=len(ids):
            raise FalconError('partial_host_details')
        return resources, cursor

    def alert_page(self, cursor: str | None, limit: int, since: str, until: str) -> tuple[list[dict[str, Any]], str | None]:
        # Immutable sort: updated_timestamp ordering can skip changing alerts.
        body = {'limit':limit,'sort':'created_timestamp|asc',
                'filter':f"cid:'{self.config.account_cid}'+updated_timestamp:>='{since}'+updated_timestamp:<='{until}'"}
        if cursor:
            body['after'] = cursor
        result = self._request('POST', ALERTS, payload=body)
        return self._page(result, 'after', limit)

    @staticmethod
    def _page(result, cursor_key, limit):
        resources = result.get('resources')
        meta = result.get('meta')
        pagination = meta.get('pagination') if isinstance(meta,dict) else None
        if not isinstance(resources,list) or len(resources)>limit or not isinstance(pagination,dict):
            raise FalconError('malformed_page')
        cursor = pagination.get(cursor_key)
        if cursor is not None and (not isinstance(cursor,str) or len(cursor)>8192):
            raise FalconError('malformed_cursor')
        if not resources and cursor and cursor_key == 'after':
            raise FalconError('empty_page_with_cursor')
        return resources, cursor or None
