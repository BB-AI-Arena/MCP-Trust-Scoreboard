"""Test the acceptance oracle; this does not simulate Windows support."""
import importlib.util
from pathlib import Path

from sqlalchemy import create_engine, event

from agent_trust.storage.database import records
from agent_trust.storage.repository import RecordRepository

import json
import tempfile

import pytest


def load_diagnostics():
    spec=importlib.util.spec_from_file_location('windows_diagnostics',Path(__file__).resolve().parents[1]/'scripts'/'windows_diagnostics.py')
    diagnostics=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(diagnostics)
    return diagnostics


def test_replay_oracle_uses_one_snapshot_and_keeps_real_duplicates(tmp_path):
    spec=importlib.util.spec_from_file_location('windows_acceptance',
        Path(__file__).resolve().parents[1]/'scripts'/'windows_acceptance.py')
    harness=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(harness)
    engine=create_engine(f'sqlite:///{tmp_path / "oracle.db"}')
    records.create(engine)
    repository=RecordRepository(engine)
    for n in range(205):
        repository.put('evidence',{'id':str(n),'event_id':f'event-{n}'},'fixture')
    repository.put('evidence',{'id':'actual-duplicate','event_id':'event-0'},'fixture')
    repository.put('evidence',{'id':'another-workspace','event_id':'event-1'},'other')
    repository.put('findings',{'id':'not-evidence','event_id':'event-1'},'fixture')
    statements=[]
    event.listen(engine,'before_cursor_execute',lambda _c,_cursor,statement,*_:statements.append(statement))
    counts=harness.persisted_event_counts(engine,'fixture')
    assert len(statements)==1 and 'OFFSET' not in statements[0]
    assert counts['event-0']==2  # Never mask a real duplicate with set/dict dedup.
    assert counts['event-1']==counts['event-204']==1
    assert counts['missing']==0 and sum(counts.values())==206
    engine.dispose()


def test_failure_diagnostics_capture_before_actual_workspace_cleanup(tmp_path):
    diagnostics=load_diagnostics()
    evidence=tmp_path/'evidence'
    state={'phase':'before_cleanup','data_dir':None,'checkpoints':[]}
    with tempfile.TemporaryDirectory(dir=tmp_path) as temporary:
        data=Path(temporary)/'data';spool=data/'spool';spool.mkdir(parents=True)
        state['data_dir']=data
        (data/'status.json').write_text(json.dumps({'updated_at':'2026-01-01T00:00:00Z','pid':123,'identity':'fixture','online':True,'reason':'token=must-not-leak','collectors':{},'spool_depth':0,'counters':{'sent':2,'dropped':1,'nested':{'dropped':99,'fake_secret':'must-not-leak'}}}))
        (spool/'counters.json').write_text(json.dumps({'sent':2,'dropped':1,'expired':0,'nested':{'fake_secret':'must-not-leak'}}))
        for index in range(diagnostics.MAX_INVENTORY_ENTRIES+3):
            (spool/f'{index:03d}-private-name.event').write_text('payload-must-not-leak')
        with pytest.raises(RuntimeError,match='original failure'):
            with diagnostics.capture_before_cleanup(evidence,state,{'binary_sha256':'fixture'}):
                raise RuntimeError('original failure')
        report=(evidence/'failure-diagnostic.json').read_text()
        assert 'payload-must-not-leak' not in report and 'must-not-leak' not in report
        snapshot=json.loads(report)['checkpoint']
        assert snapshot['status']['value']['updated_at']=='2026-01-01T00:00:00Z'
        assert snapshot['status']['value']['counters']=={'sent':2,'dropped':1}
        assert snapshot['spool_inventory']['output_truncated'] is True
        assert len(snapshot['spool_inventory']['files'])==diagnostics.MAX_INVENTORY_ENTRIES
    assert (evidence/'failure-diagnostic.json').exists()


def test_actual_workspace_teardown_captures_before_cleanup_preserves_original_and_attempts_all(tmp_path):
    diagnostics=load_diagnostics()
    spec=importlib.util.spec_from_file_location('windows_acceptance',Path(__file__).resolve().parents[1]/'scripts'/'windows_acceptance.py')
    harness=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(harness)
    evidence=tmp_path/'evidence';data=tmp_path/'data';spool=data/'spool';spool.mkdir(parents=True)
    (data/'status.json').write_text(json.dumps({'updated_at':'2026-01-01T00:00:00Z','pid':123,'online':True,'reason':None,'collectors':{},'spool_depth':0,'counters':{'sent':2,'dropped':1,'expired':0}}))
    (spool/'counters.json').write_text(json.dumps({'sent':2,'dropped':1,'expired':0}))
    state={'phase':'scenario','data_dir':data,'checkpoints':[]};order=[]
    def destructive_cleanup():
        order.append('destructive');(data/'status.json').unlink();raise OSError('cleanup failed')
    def remaining_cleanup():order.append('remaining')
    with pytest.raises(RuntimeError,match='original failure'):
        with harness.workspace(evidence,state,{'binary_sha256':'0'*64},lambda:[destructive_cleanup,remaining_cleanup]):
            raise RuntimeError('original failure')
    report=json.loads((evidence/'failure-diagnostic.json').read_text())
    assert report['checkpoint']['status']['availability']=='available'
    assert order==['destructive','remaining']
    assert json.loads((evidence/'cleanup-diagnostic.json').read_text())['cleanup_failure_types']==['OSError']


def test_capture_before_cleanup_preserves_original_exception_when_writing_fails(tmp_path,monkeypatch):
    diagnostics=load_diagnostics()
    monkeypatch.setattr(diagnostics,'record_failure',lambda *args,**kwargs: (_ for _ in ()).throw(OSError('diagnostic write failed')))
    with pytest.raises(RuntimeError,match='original failure'):
        with diagnostics.capture_before_cleanup(tmp_path/'evidence',{'phase':'fixture','data_dir':tmp_path,'checkpoints':[]},{}):
            raise RuntimeError('original failure')


def test_diagnostics_bounds_identity_and_partial_evidence(tmp_path):
    diagnostics=load_diagnostics();data=tmp_path/'data';spool=data/'spool';spool.mkdir(parents=True)
    (data/'status.json').write_text(json.dumps({'updated_at':'2026-01-01T00:00:00Z','pid':1,'online':True,'reason':'secret','collectors':{},'spool_depth':0,'counters':{}}))
    (spool/'unexpected-secret-name').write_text('secret')
    snapshot=diagnostics.checkpoint('fixture',data)
    assert diagnostics._partial(snapshot) is True
    assert 'unexpected-secret-name' not in json.dumps(snapshot)
    assert snapshot['spool_inventory']['files'][0]['name_class']=='other'
    assert diagnostics._json_evidence(tmp_path/'missing',diagnostics._counters)['availability']=='missing'
    oversized=tmp_path/'oversized.json';oversized.write_bytes(b'x'*(diagnostics.MAX_JSON_BYTES+1))
    assert diagnostics._json_evidence(oversized,diagnostics._counters)['reason']=='oversize'
    corrupt=tmp_path/'corrupt.json';corrupt.write_text('{')
    assert diagnostics._json_evidence(corrupt,diagnostics._counters)['availability']=='corrupt'
    diagnostics.record_failure(tmp_path/'evidence','fixture',data,{'source_sha':'secret-value','version':{'secret':'must-not-leak'},'binary_sha256':'0'*64},RuntimeError())
    report=(tmp_path/'evidence'/'failure-diagnostic.json').read_text()
    assert 'secret-value' not in report and 'must-not-leak' not in report


def test_failure_diagnostics_mark_missing_evidence_explicitly(tmp_path):
    diagnostics=load_diagnostics()
    diagnostics.record_failure(tmp_path/'evidence','constructor',tmp_path/'missing',{},RuntimeError())
    report=json.loads((tmp_path/'evidence'/'failure-diagnostic.json').read_text())
    assert report['diagnostics']=='partial'
    assert report['checkpoint']['status']['availability']=='missing'
    assert report['checkpoint']['counters']['availability']=='missing'
    assert report['checkpoint']['spool_inventory']['availability']=='missing'


def test_diagnostic_checkpoints_are_bounded_and_retain_exact_assertion_observation(tmp_path, monkeypatch):
    diagnostics=load_diagnostics();data=tmp_path/'data';spool=data/'spool';spool.mkdir(parents=True)
    counters={'sent':12,'dropped':3,'expired':0,'last_upload':''}
    health={'updated_at':'2026-01-01T00:00:00Z','pid':123,'online':False,'reason':'private','collectors':{},'spool_depth':4,'counters':counters}
    (data/'status.json').write_text(json.dumps(health));(spool/'counters.json').write_text(json.dumps(counters))
    state={'data_dir':data};evidence=tmp_path/'evidence'
    for n in range(diagnostics.MAX_CHECKPOINTS+3):
        diagnostics.persist_checkpoint(evidence,state,str(n),data,{})
    assert len(state['checkpoints'])==diagnostics.MAX_CHECKPOINTS
    diagnostics.persist_health_observation(evidence,state,'assertion',health,{})
    # Later status changes must not replace the exact failing observation.
    (data/'status.json').write_text('{}')
    original=RuntimeError('private')
    with pytest.raises(RuntimeError) as raised:
        with diagnostics.capture_before_cleanup(evidence,state,{}):raise original
    assert raised.value is original
    report=json.loads((evidence/'failure-diagnostic.json').read_text())
    assert report['observations'][0]['status']['value']['counters']==counters
    assert report['observations'][0]['status']['value']['pid']==123
    assert report['diagnostics']=='partial'
    assert 'private' not in json.dumps(report)
    monkeypatch.setattr(diagnostics,'MAX_SCAN_ENTRIES',2)
    for n in range(4):(spool/f'.pending-{n}').write_text('not read')
    inventory=diagnostics.spool_inventory(data)
    assert inventory['scan_truncated'] and inventory['file_count_lower_bound']==2
    monkeypatch.setattr(Path,'write_text',lambda *a,**k: (_ for _ in ()).throw(OSError('private')))
    assert diagnostics.persist_checkpoint(evidence,state,'write-failure',data,{})['availability']=='unavailable'


def test_workspace_cleanup_only_failure_fails_and_temp_cleanup_cannot_mask_scenario(tmp_path):
    spec=importlib.util.spec_from_file_location('windows_acceptance',Path(__file__).resolve().parents[1]/'scripts'/'windows_acceptance.py')
    harness=importlib.util.module_from_spec(spec);spec.loader.exec_module(harness)
    class Temporary:
        def __init__(self,**kwargs):pass
        def __enter__(self):return str(tmp_path)
        def __exit__(self,*args):raise OSError('private')
    state={'phase':'fixture','data_dir':tmp_path}
    with pytest.raises(AssertionError,match='cleanup failed'):
        with harness.workspace(tmp_path/'evidence',state,{},lambda:[],Temporary):pass
    original=RuntimeError('original')
    with pytest.raises(RuntimeError) as raised:
        with harness.workspace(tmp_path/'evidence',state,{},lambda:[],Temporary):raise original
    assert raised.value is original


def test_status_missing_counter_fields_are_partial_even_when_other_evidence_available(tmp_path):
    diagnostics=load_diagnostics();data=tmp_path/'data';spool=data/'spool';spool.mkdir(parents=True)
    (data/'status.json').write_text(json.dumps({'updated_at':'2026-01-01T00:00:00Z','pid':1,'online':True,'reason':None,'collectors':{},'spool_depth':0,'counters':{'sent':1}}))
    (spool/'counters.json').write_text(json.dumps({'sent':1}))
    snapshot=diagnostics.checkpoint('fixture',data)
    assert diagnostics._partial(snapshot)
    assert 'counters.dropped' in snapshot['status']['value']['missing_fields']
    assert 'dropped' in snapshot['counters']['missing_fields']
    assert snapshot['counters']['value']=={'sent':1}
    assert diagnostics._source_binary_identity({'source_sha':'a'*40,'binary_sha256':'b'*64,'version':{'private':'secret'}})=={'source_sha':'a'*40,'binary_sha256':'b'*64}


def test_standalone_service_launcher_retains_setup_failure(tmp_path, monkeypatch):
    import runpy
    import sys
    scripts=Path(__file__).resolve().parents[1]/'scripts'
    spec=importlib.util.spec_from_file_location('windows_acceptance',scripts/'windows_acceptance.py')
    harness=importlib.util.module_from_spec(spec);spec.loader.exec_module(harness)
    monkeypatch.setattr(harness,'ROOT',tmp_path)
    original=RuntimeError('private setup details')
    def fail_setup(service_mode=False):
        assert service_mode is True
        raise original
    monkeypatch.setattr(harness,'main',fail_setup)
    monkeypatch.setitem(sys.modules,'windows_acceptance',harness)
    with pytest.raises(RuntimeError) as raised:
        runpy.run_path(str(scripts/'windows_service_acceptance.py'),run_name='__main__')
    assert raised.value is original
    report=(tmp_path/'evidence'/'windows'/'service'/'harness-failure.json').read_text()
    assert 'private setup details' not in report
    assert json.loads(report)['state']=='failed'
    assert json.loads(report)['diagnostics']=='partial'
