import concurrent.futures
from datetime import datetime, timezone
from importlib.resources import files
import json
import select as io_select
import subprocess
import sys
import threading

import pytest
from sqlalchemy import event, select, text, update

from agent_trust.jobs.worker import process_one
from agent_trust.providers.rules import RulesOnlyAnalysisProvider
from agent_trust.storage.database import create_schema, jobs, records
from agent_trust.storage.job_ledger import JobLedger
from agent_trust.storage.repository import RecordRepository

from .conftest import eventually

pytestmark = pytest.mark.integration


def test_fresh_and_existing_schema_migrations_preserve_data(pg_engine):
    # Upgrade the exact old reference schema with an existing completed job.
    initial = files("agent_trust.storage").joinpath("migrations/001_initial.sql").read_text()
    now = datetime.now(timezone.utc).isoformat()
    with pg_engine.begin() as c:
        c.exec_driver_sql(initial)
        c.execute(jobs.insert().values(id="old-job", workspace_id="a", kind="assessment",
            payload='{"subject_id":"old-agent"}', result='{"preserved":true}',
            status="complete", attempts=1, max_attempts=3, available_at=now,
            idempotency_key="old-key", created_at=now, updated_at=now))
        c.execute(records.insert().values(id="old-agent", workspace_id="a", kind="agents",
            payload='{"id":"old-agent"}', created_at=now, updated_at=now))
        c.execute(records.insert().values(id="old-job", workspace_id="a", kind="assessments",
            payload='{"status":"queued","operator_note":"preserve me"}', created_at=now, updated_at=now))
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        list(pool.map(lambda _: create_schema(pg_engine), range(4)))
    ledger = JobLedger(pg_engine)
    assert ledger.get("old-job", "a")["result"] == {"preserved": True}
    assert RecordRepository(pg_engine).get("agents", "old-agent", "a") == {"id": "old-agent"}
    projection = RecordRepository(pg_engine).get("assessments", "old-job", "a")
    assert projection["status"] == "complete"
    assert projection["result"] == {"preserved": True}
    assert projection["operator_note"] == "preserve me"
    assert ledger.enqueue("assessment", "b", {}, idempotency_key="old-key")["id"] != "old-job"
    with pg_engine.connect() as c:
        assert c.execute(text("SELECT count(*) FROM agent_trust_migrations")).scalar() == 4
        indexes = set(c.execute(text("SELECT indexname FROM pg_indexes WHERE tablename='agent_trust_jobs'")).scalars())
        assert {"ix_agent_trust_jobs_claim", "uq_agent_trust_jobs_workspace_key"} <= indexes


def test_concurrent_idempotent_enqueue_is_workspace_scoped(pg_engine):
    create_schema(pg_engine)
    ledger = JobLedger(pg_engine)
    barrier = threading.Barrier(6)

    def submit(_):
        barrier.wait(timeout=5)
        return ledger.enqueue("assessment", "a", {"subject_id": "agent"}, idempotency_key="same")

    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
        results = list(pool.map(submit, range(6)))
    assert len({r["id"] for r in results}) == 1
    assert len(RecordRepository(pg_engine).list("assessments", "a")) == 1
    other = ledger.enqueue("assessment", "b", {"subject_id": "agent"}, idempotency_key="same")
    assert other["id"] != results[0]["id"]
    assert ledger.get(other["id"], "a") is None


def test_skip_locked_claim_and_independent_workers(pg_engine):
    create_schema(pg_engine)
    ledger = JobLedger(pg_engine)
    queued = [ledger.enqueue("assessment", "a", {"subject_id": f"agent-{i}"}) for i in range(8)]
    with pg_engine.begin() as blocker:
        blocker.execute(select(jobs).where(jobs.c.id == queued[0]["id"]).with_for_update()).one()
        # Would time out on lock_timeout without PostgreSQL SKIP LOCKED.
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
            claims = list(pool.map(lambda n: ledger.claim(f"worker-{n}"), range(7)))
        assert len({j["id"] for j in claims}) == 7
        assert queued[0]["id"] not in {j["id"] for j in claims}
    assert ledger.claim("last")["id"] == queued[0]["id"]
    assert ledger.claim("empty") is None


@pytest.mark.parametrize("operation", ["enqueue", "complete"])
def test_job_and_assessment_updates_roll_back_together(pg_engine, operation):
    create_schema(pg_engine)
    ledger = JobLedger(pg_engine)
    if operation == "complete":
        ledger.enqueue("assessment", "a", {"subject_id": "agent"})
        claim = ledger.claim("worker")

    def reject_projection(conn, cursor, statement, parameters, context, executemany):
        if statement.startswith("INSERT INTO agent_trust_records"):
            raise RuntimeError("injected projection write failure")

    event.listen(pg_engine, "before_cursor_execute", reject_projection)
    try:
        with pytest.raises(RuntimeError, match="injected"):
            if operation == "enqueue":
                ledger.enqueue("assessment", "a", {"subject_id": "agent"})
            else:
                ledger.complete(claim["id"], claim["lease_token"], {"ok": True})
    finally:
        event.remove(pg_engine, "before_cursor_execute", reject_projection)
    with pg_engine.connect() as c:
        rows = c.execute(select(jobs)).all()
    if operation == "enqueue":
        assert rows == []
        assert RecordRepository(pg_engine).list("assessments", "a") == []
    else:
        assert ledger.get(claim["id"], "a")["status"] == "running"
        assert ledger.get(claim["id"], "a")["result"] is None
        assert ledger.complete(claim["id"], claim["lease_token"], {"ok": True})
        assert RecordRepository(pg_engine).get("assessments", claim["id"], "a")["result"] == {"ok": True}


@pytest.mark.parametrize("explicit_recovery", [True, False])
def test_worker_death_expiry_fencing_and_attempt_limit(pg_engine, postgres, explicit_recovery):
    create_schema(pg_engine)
    ledger = JobLedger(pg_engine)
    job = ledger.enqueue("assessment", "a", {"subject_id": "agent"}, max_attempts=2)
    # A separate process commits a claim then dies; no graceful fail() call.
    code = """
import json, os, time
from agent_trust.storage.database import make_engine
from agent_trust.storage.job_ledger import JobLedger
print(json.dumps(JobLedger(make_engine(os.environ['TEST_DATABASE_URL'])).claim('doomed', lease_seconds=1)), flush=True)
time.sleep(60)
"""
    process = subprocess.Popen([sys.executable, "-u", "-c", code], stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, text=True, env={"TEST_DATABASE_URL": postgres["external"]})
    try:
        assert io_select.select([process.stdout], [], [], 10)[0], "worker did not claim"
        first = json.loads(process.stdout.readline())
        assert first["id"] == job["id"]
    finally:
        process.kill()
        process.wait(timeout=5)
        process.stdout.close()
        process.stderr.close()
    eventually(lambda: datetime.now(timezone.utc) > datetime.fromisoformat(first["lease_until"]))
    assert not ledger.complete(first["id"], first["lease_token"], {"stale": True})
    if explicit_recovery:
        assert ledger.recover_abandoned() == 1
    second = ledger.claim("replacement", lease_seconds=1)
    assert second["attempts"] == 2
    assert not ledger.fail(first["id"], first["lease_token"], "stale failure")
    eventually(lambda: datetime.now(timezone.utc) > datetime.fromisoformat(second["lease_until"]))
    if explicit_recovery:
        ledger.recover_abandoned()
    assert ledger.claim("never-a-third-attempt") is None
    assert ledger.get(job["id"], "a")["status"] == "failed"
    assert RecordRepository(pg_engine).get("assessments", job["id"], "a")["status"] == "failed"


def test_retry_backoff_limits_and_worker_transaction_boundary(pg_engine, monkeypatch):
    create_schema(pg_engine)
    ledger = JobLedger(pg_engine)
    job = ledger.enqueue("unsupported-kind", "a", {}, max_attempts=2)
    assert process_one(ledger, "worker")
    retry = ledger.get(job["id"], "a")
    assert retry["status"] == "queued"
    assert datetime.fromisoformat(retry["available_at"]) > datetime.now(timezone.utc)
    assert not process_one(ledger, "worker")
    with pg_engine.begin() as c:
        c.execute(update(jobs).where(jobs.c.id == job["id"]).values(available_at="2000-01-01T00:00:00+00:00"))
    assert process_one(ledger, "worker")
    assert ledger.get(job["id"], "a")["status"] == "failed"
    good = ledger.enqueue("assessment", "a", {"subject_id": "agent", "content": "eval(user)"})
    original = RulesOnlyAnalysisProvider.analyze

    def analyze(provider, request):
        with pg_engine.begin() as c:
            c.execute(select(jobs).where(jobs.c.id == good["id"]).with_for_update(nowait=True)).one()
        return original(provider, request)

    monkeypatch.setattr(RulesOnlyAnalysisProvider, "analyze", analyze)
    assert process_one(ledger, "worker")
    assert ledger.get(good["id"], "a")["result"]["findings"][0]["rule_id"] == "execution_authority"


@pytest.mark.parametrize("operation", ["complete", "fail"])
def test_expiry_is_rechecked_after_waiting_for_row_lock(pg_engine, operation):
    create_schema(pg_engine)
    ledger = JobLedger(pg_engine)
    ledger.enqueue("assessment", "a", {"subject_id": "agent"})
    claim = ledger.claim("waiting-worker", lease_seconds=1)
    entered = threading.Event()

    def observe_waiter(conn, cursor, statement, parameters, context, executemany):
        if "FOR UPDATE" in statement:
            entered.set()

    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        with pg_engine.begin() as blocker:
            blocker.execute(select(jobs).where(jobs.c.id == claim["id"]).with_for_update()).one()
            event.listen(pg_engine, "before_cursor_execute", observe_waiter)
            try:
                value = {"stale": True} if operation == "complete" else "stale error"
                future = pool.submit(getattr(ledger, operation), claim["id"], claim["lease_token"], value)
                assert entered.wait(timeout=5)
                eventually(lambda: datetime.now(timezone.utc) > datetime.fromisoformat(claim["lease_until"]))
            finally:
                event.remove(pg_engine, "before_cursor_execute", observe_waiter)
        assert future.result(timeout=5) is False
    assert ledger.get(claim["id"], "a")["status"] == "running"
    assert ledger.get(claim["id"], "a")["result"] is None
