from dataclasses import replace
import json
import subprocess
import sys
import time

import pytest
from agent_trust.adapters.connectors.falcon_client import FalconClient, FalconError, ALERTS, HOSTS, HOST_DETAILS, TOKEN
from agent_trust.adapters.connectors.falcon_collect import check_connection
from agent_trust.adapters.connectors.falcon_source import CrowdStrikeSource
from agent_trust.adapters.connectors.base import SourceContext


def test_tls_oauth_hosts_alerts_and_expiry(falcon_server):
    state, config = falcon_server
    client = FalconClient(config)
    hosts, cursor = client.host_page(None,1)
    assert len(hosts)==1 and cursor
    assert len(client.host_page(cursor,1)[0])==1
    assert client.host_page('h:2',1)==([],None)
    client._expires = 0
    alerts, cursor = client.alert_page(None,1,'2026-09-01T00:00:00Z','2026-09-12T00:00:00Z')
    assert len(alerts)==1 and cursor
    assert len(client.alert_page(cursor,1,'2026-09-01T00:00:00Z','2026-09-12T00:00:00Z')[0])==1
    assert state['tokens']==2
    assert set(tuple(c) for c in state['calls']) <= {('POST',TOKEN),('GET',HOSTS),('GET',HOST_DETAILS),('POST',ALERTS)}


@pytest.mark.parametrize('status,code', [(401,'unauthorized'),(403,'permission_denied'),(429,'rate_limited'),(503,'temporarily_unavailable')])
def test_http_failures_are_safe_and_bounded(falcon_server,status,code):
    state, config = falcon_server
    state['plans'][HOSTS] = [{'status':status,'body':{'error':'sensitive-response-text'}}]*3
    waits = []
    with pytest.raises(FalconError,match=code) as error:
        FalconClient(config,sleep=waits.append).host_page(None,1)
    assert 'sensitive' not in str(error.value)
    assert sum(c[1]==HOSTS for c in state['calls'])<=3
    assert state['tokens']<=2


def test_401_refresh_once_and_retry_guidance(falcon_server):
    state, config = falcon_server
    state['plans'][HOSTS] = [{'status':401}]
    client = FalconClient(config)
    assert client.host_page(None,1)[0]
    assert state['tokens']==2
    state['plans'][HOSTS] = [{'status':429,'headers':{'Retry-After':'60'}}]
    with pytest.raises(FalconError,match='rate_limited') as error:
        client.host_page(None,1)
    assert error.value.retry_after>=60
    assert FalconClient.retry_delay({'x-ratelimit-retryafter':str(int(time.time())+90)},0)>85
    with pytest.raises(FalconError,match='malformed_retry'):
        FalconClient.retry_delay({'x-ratelimit-retryafter':'NaN'},0)


@pytest.mark.parametrize('response', ['not json', [], {'resources':[]},
    {'resources':[], 'errors':[{'message':'sensitive'}]},
    {'resources':[], 'meta':{'pagination':{'after':'unexpected'}}}])
def test_malformed_and_partial_pages_never_success(falcon_server,response):
    state, config = falcon_server
    state['plans'][ALERTS] = [{'body':response}]
    with pytest.raises(FalconError):
        FalconClient(config).alert_page(None,1,'2026-09-01T00:00:00Z','2026-09-12T00:00:00Z')


def test_partial_host_details_and_no_scope_escalation(falcon_server):
    state, config = falcon_server
    state['plans'][HOST_DETAILS] = [{'body':{'resources':[]}}]
    client = FalconClient(config)
    with pytest.raises(FalconError,match='partial_host_details'):
        client.host_page(None,1)
    with pytest.raises(FalconError,match='operation_not_allowed'):
        client._request('POST','/devices/entities/devices-actions/v2',payload={})
    assert all(c[1]!='/devices/entities/devices-actions/v2' for c in state['calls'])


def test_vendor_revision_mapping_and_minimal_retention(falcon_server):
    state, config = falcon_server
    raw = state['alerts'][0]
    source = CrowdStrikeSource()
    envelope = {'resource':raw,'resource_type':'alert','config':config,'collected_at':'now','agent_mapping':{}}
    context = SourceContext('workspace','operator')
    original = source.normalize(envelope,context)
    assert original['agent_id'] is None and original['status']=='claimed'
    assert 'sensitive-fixture-command' not in json.dumps(original)
    raw['status'] = 'closed'
    changed = source.normalize(envelope,context)
    assert changed['logical_id']==original['logical_id'] and changed['revision']!=original['revision']
    raw['description'] = 'revised description'
    assert source.normalize(envelope,context)['revision']!=changed['revision']
    envelope['agent_mapping'] = {raw['agent_id']:'registered-agent'}
    mapped = source.normalize(envelope,context)
    assert mapped['agent_id']=='registered-agent' and mapped['agent_link']=='explicit_operator_mapping'
    _, findings, _ = source.records(mapped,'job')
    assert findings[0]['origin']=='vendor_alert' and 'rule_id' not in findings[0]
    host = source.normalize({**envelope,'resource':state['hosts'][0],'resource_type':'host'},context)
    assert source.records(host,'host-job')[1]==[]
    other = source.normalize(envelope,SourceContext('other-workspace','operator'))
    assert other['logical_id']!=mapped['logical_id']
    raw['cid'] = 'b'*32
    with pytest.raises(FalconError,match='account_mismatch'):
        source.normalize(envelope,context)


def test_check_empty_missing_credentials_and_no_implicit_live(falcon_server):
    state, config = falcon_server
    state['hosts'] = state['alerts'] = []
    assert check_connection(config)['coverage']=={'hosts':'read_ok_empty','alerts':'read_ok_empty'}
    with pytest.raises(FalconError,match='credentials_unavailable'):
        FalconClient(replace(config,client_secret=''))
    assert 'fixture-only' not in repr(config)
    result = subprocess.run([sys.executable,'-m','agent_trust.adapters.connectors.falcon_cli','live-smoke',
        '--connection','fixture','--account-cid',config.account_cid],capture_output=True,text=True,timeout=10)
    assert result.returncode==2 and 'explicit_live_read_authorization_required' in result.stdout


def test_untrusted_tls_and_redirect_never_followed(falcon_server,monkeypatch):
    state, config = falcon_server
    monkeypatch.delenv('SSL_CERT_FILE')
    with pytest.raises(FalconError,match='transport_unavailable'):
        FalconClient(config,sleep=lambda _:None).host_page(None,1)
    assert not state['calls']


def test_redirect_and_resource_budgets_fail_closed(falcon_server):
    state, config = falcon_server
    state['plans'][TOKEN] = [{'status':302,'headers':{'Location':'https://untrusted.invalid/'}}]
    with pytest.raises(FalconError,match='unexpected_http_status'):
        FalconClient(config).host_page(None,1)
    assert state['calls']==[['POST',TOKEN]]
    with pytest.raises(FalconError,match='collection_budget_exhausted'):
        FalconClient(config,max_requests=0).host_page(None,1)
    state['plans'][ALERTS] = [{'body':'x'*2_000_001}]*3
    with pytest.raises(FalconError,match='transport_unavailable'):
        FalconClient(config,sleep=lambda _:None).alert_page(None,1,'2026-09-01T00:00:00Z','2026-09-12T00:00:00Z')


def test_temporary_failure_recovers_and_bad_token_is_not_success(falcon_server):
    state, config = falcon_server
    state['plans'][HOSTS] = [{'status':503}]
    waits = []
    assert FalconClient(config,sleep=waits.append).host_page(None,1)[0]
    assert waits==[1.0]
    state['plans'][TOKEN] = [{'body':{'access_token':'fixture','expires_in':'invalid'}}]
    with pytest.raises(FalconError,match='malformed_token_response'):
        FalconClient(config).host_page(None,1)


def test_rate_guidance_also_defers_other_vendor_operations(falcon_server):
    state, config = falcon_server
    state['plans'][HOSTS] = [{'status':429,'headers':{'Retry-After':'60'}}]
    result = check_connection(config)
    assert result['coverage']=={'hosts':'rate_limited','alerts':'retry_not_before'}
    assert [c[1] for c in state['calls']]==[TOKEN,HOSTS]
