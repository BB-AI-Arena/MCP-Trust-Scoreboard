"""Test the acceptance oracle; this does not simulate Windows support."""
import importlib.util
from pathlib import Path

from sqlalchemy import create_engine, event

from agent_trust.storage.database import records
from agent_trust.storage.repository import RecordRepository


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
