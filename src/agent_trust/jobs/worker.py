"""Single modular worker for the PostgreSQL job ledger."""

from __future__ import annotations

import os
import time

from agent_trust.config import Settings
from agent_trust.providers.base import AnalysisRequest
from agent_trust.providers.rules import RulesOnlyAnalysisProvider
from agent_trust.storage.database import create_schema, make_engine
from agent_trust.storage.job_ledger import JobLedger


def process_one(ledger: JobLedger, worker_id: str) -> bool:
    job = ledger.claim(worker_id)
    if not job:
        return False
    try:
        if job["kind"] != "assessment":
            raise ValueError(f"unsupported job kind: {job['kind']}")
        payload = job["payload"]
        result = RulesOnlyAnalysisProvider().analyze(AnalysisRequest(subject=payload["subject_id"], content=payload.get("content", ""), schema_version="2026-01"))
        output = {"status": result.status, "findings": list(result.findings), "explanation": result.explanation, "provider": result.provider, "engine_version": result.engine_version}
        if not ledger.complete(job["id"], job["lease_token"], output):
            raise RuntimeError("job lease was lost before completion")
    except Exception as exc:
        ledger.fail(job["id"], job["lease_token"], str(exc))
    return True


def run() -> None:
    settings = Settings.from_env()
    settings.validate()
    engine = make_engine(settings.database_url)
    create_schema(engine)
    ledger = JobLedger(engine)
    worker_id = os.getenv("AGENT_TRUST_WORKER_ID", "worker")
    while True:
        if not process_one(ledger, worker_id):
            ledger.recover_abandoned()
            time.sleep(1)
