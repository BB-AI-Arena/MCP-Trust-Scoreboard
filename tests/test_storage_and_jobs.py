import time

from sqlalchemy import create_engine

from agent_trust.storage.database import create_schema
from agent_trust.storage.job_ledger import JobLedger
from agent_trust.storage.repository import RecordRepository


def make_db(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'state.db'}", future=True)
    create_schema(engine)
    return engine


def test_records_survive_new_repository_instance(tmp_path):
    engine = make_db(tmp_path)
    RecordRepository(engine).put("agents", {"id": "agent-1", "name": "local"}, "workspace-a")
    reopened = RecordRepository(create_engine(f"sqlite:///{tmp_path / 'state.db'}", future=True))
    assert reopened.get("agents", "agent-1", "workspace-a")["name"] == "local"
    assert reopened.get("agents", "agent-1", "workspace-b") is None


def test_idempotency_returns_same_job(tmp_path):
    ledger = JobLedger(make_db(tmp_path))
    first = ledger.enqueue("assessment", "workspace-a", {"subject": "a"}, idempotency_key="same")
    second = ledger.enqueue("assessment", "workspace-a", {"subject": "different"}, idempotency_key="same")
    assert second["id"] == first["id"]
    assert second["payload"] == {"subject": "a"}


def test_stale_worker_cannot_complete_new_lease(tmp_path):
    ledger = JobLedger(make_db(tmp_path))
    ledger.enqueue("assessment", "workspace-a", {"content": "x"})
    first = ledger.claim("worker-a", lease_seconds=1)
    assert first
    # Let the short lease expire, then recover it for another worker.
    time.sleep(1.1)
    ledger.recover_abandoned()
    second = ledger.claim("worker-b", lease_seconds=60)
    assert second and second["id"] == first["id"]
    assert not ledger.complete(first["id"], first["lease_token"], {"stale": True})
    assert ledger.complete(second["id"], second["lease_token"], {"ok": True})
