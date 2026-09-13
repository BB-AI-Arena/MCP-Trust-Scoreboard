"""Vendor-neutral Agent Trust Platform API.

Legacy four-app endpoints remain in their original services. This API is the
namespaced migration surface and stores server-owned workspace records.
"""

from __future__ import annotations

import os
import hashlib
from typing import Any

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from starlette.responses import JSONResponse
from sqlalchemy import text

from agent_trust import __version__
from agent_trust.api.auth import AuthContext, context_dependency
from agent_trust.config import Settings
from agent_trust.providers.base import ProviderCapabilities
from agent_trust.providers.rules import RulesOnlyAnalysisProvider
from agent_trust.storage.database import create_schema, make_engine
from agent_trust.storage.job_ledger import JobLedger
from agent_trust.storage.repository import RecordRepository
from agent_trust.adapters.connectors.base import DESCRIPTORS, SourceContext
from agent_trust.adapters.connectors.json_source import EvidenceEnvelope, GenericJSONSource


class RecordRequest(BaseModel):
    payload: dict[str, Any] = Field(default_factory=dict)


class AssessmentRequest(BaseModel):
    subject_id: str = Field(min_length=1, max_length=256)
    profile: str = Field(default="default", min_length=1, max_length=80)
    content: str = Field(default="", max_length=500_000)
    idempotency_key: str | None = Field(default=None, max_length=256)


def create_app(settings: Settings | None = None, engine=None) -> FastAPI:
    settings = settings or Settings.from_env()
    settings.validate()
    engine = engine or make_engine(settings.database_url)
    create_schema(engine)
    repository = RecordRepository(engine)
    ledger = JobLedger(engine)

    app = FastAPI(title="Agent Trust Platform API", version=__version__, description="Local/self-hosted assessment and monitoring for AI agents")
    app.state.settings = settings
    app.state.repository = repository
    app.state.ledger = ledger
    app.add_middleware(CORSMiddleware, allow_origins=list(settings.allowed_origins), allow_credentials=False, allow_methods=["GET", "POST"], allow_headers=["Authorization", "Content-Type", "Idempotency-Key"])

    @app.middleware("http")
    async def request_size_limit(request, call_next):
        content_length = request.headers.get("content-length")
        if content_length and content_length.isdigit() and int(content_length) > settings.max_request_bytes:
            return JSONResponse(status_code=413, content={"detail": {"code": "request_too_large", "message": "request exceeds configured size limit"}})
        return await call_next(request)

    read = context_dependency(settings, "read")
    write = context_dependency(settings, "write")
    assess = context_dependency(settings, "assess")

    @app.get("/health", tags=["system"])
    def health() -> dict[str, str]:
        return {"status": "ok", "version": __version__}

    @app.get("/readiness", tags=["system"])
    def readiness() -> dict[str, str]:
        try:
            with engine.connect() as connection:
                connection.execute(text("SELECT 1"))
        except Exception as exc:
            raise HTTPException(status_code=503, detail={"code": "database_unavailable", "message": "database is not ready"}) from exc
        return {"status": "ready", "database": "ok", "version": __version__}

    @app.get("/version", tags=["system"])
    def version() -> dict[str, str]:
        return {"application": __version__, "commit": os.getenv("AGENT_TRUST_COMMIT_SHA", "unknown"), "schema": "2026-01"}

    @app.get("/api/v1/capabilities", tags=["capabilities"])
    def capabilities(_: AuthContext = Depends(read)) -> dict[str, Any]:
        provider: ProviderCapabilities = RulesOnlyAnalysisProvider.capabilities
        return {"api_version": "v1", "workspaces": "single-tenant-local", "providers": [{"name": provider.name, "version": provider.version, "assess": provider.assess, "inventory": provider.inventory, "observe": provider.observe, "enforce": provider.enforce}], "workspaces_supported": ["tool_connector_trust", "agent_blast_radius", "behavior_monitoring", "artifact_assurance"]}

    def create_record(kind: str, request: RecordRequest, context: AuthContext) -> dict[str, Any]:
        payload = dict(request.payload)
        if kind == "events" and payload.get("idempotency_key"):
            record_id = "event-" + hashlib.sha256(f"{context.workspace_id}:{payload['idempotency_key']}".encode()).hexdigest()
        else:
            record_id = str(payload.get("id") or __import__("uuid").uuid4())
        if kind == "events":
            payload["collector_identity"] = context.subject
        payload.update({"id": record_id, "kind": kind, "workspace_id": context.workspace_id, "schema_version": "2026-01"})
        try:
            return repository.put(kind, payload, context.workspace_id)
        except PermissionError as exc:
            raise HTTPException(status_code=403, detail={"code": "record_forbidden", "message": "record belongs to another workspace"}) from exc

    def list_records(kind: str, context: AuthContext, limit: int, offset: int) -> dict[str, Any]:
        items = repository.list(kind, context.workspace_id, limit=limit, offset=offset)
        return {"items": items, "limit": min(max(limit, 1), 100), "offset": max(offset, 0), "count": len(items)}

    for kind in ("agents", "connections", "events", "findings", "graphs"):
        route = f"/api/v1/{kind}"

        def post_record(request: RecordRequest, context: AuthContext = Depends(write), record_kind=kind):
            return create_record(record_kind, request, context)

        def get_records(limit: int = Query(default=50, ge=1, le=100), offset: int = Query(default=0, ge=0), context: AuthContext = Depends(read), record_kind=kind):
            return list_records(record_kind, context, limit, offset)

        app.add_api_route(route, post_record, methods=["POST"], status_code=201, tags=[kind])
        app.add_api_route(route, get_records, methods=["GET"], tags=[kind])

    @app.post("/api/v1/assessments", status_code=202, tags=["assessments"])
    def submit_assessment(request: AssessmentRequest, context: AuthContext = Depends(assess)) -> dict[str, Any]:
        job = ledger.enqueue("assessment", context.workspace_id, {"subject_id": request.subject_id, "profile": request.profile, "content": request.content}, idempotency_key=request.idempotency_key)
        return {"job_id": job["id"], "status": job["status"], "accepted": True}

    @app.get("/api/v1/connectors", tags=["connectors"])
    def connectors(_: AuthContext = Depends(read)):
        return {"schema_version":"1", "adapters":DESCRIPTORS, "response_adapters":[],
                "delivery_semantics":"at-least-once; destination must deduplicate delivery_id"}

    @app.post("/api/v1/connectors/generic-json/events", status_code=202, tags=["connectors"])
    def ingest_evidence(request: EvidenceEnvelope, context: AuthContext = Depends(write)):
        normalized = GenericJSONSource().normalize(request, SourceContext(context.workspace_id, context.subject))
        identity = ":".join((context.subject, request.event_id))
        # Prefix keeps this connector's idempotency keys separate from legacy
        # assessment callers. Ownership always comes from authenticated context.
        key = "connector-json:" + hashlib.sha256(identity.encode()).hexdigest()
        job = ledger.enqueue("connector_ingest", context.workspace_id, normalized, idempotency_key=key)
        if job["payload"].get("input_digest") != normalized["input_digest"]:
            raise HTTPException(status_code=409, detail={"code":"event_id_conflict", "message":"event ID already used with different content"})
        return {"job_id":job["id"], "status":job["status"], "accepted":True}

    @app.get("/api/v1/evidence", tags=["connectors"])
    def list_evidence(limit: int = Query(default=50, ge=1, le=100), offset: int = Query(default=0, ge=0), context: AuthContext = Depends(read)):
        return list_records("evidence", context, limit, offset)

    @app.get("/api/v1/assessments", tags=["assessments"])
    def list_assessments(limit: int = Query(default=50, ge=1, le=100), offset: int = Query(default=0, ge=0), context: AuthContext = Depends(read)):
        return list_records("assessments", context, limit, offset)

    @app.get("/api/v1/jobs/{job_id}", tags=["jobs"])
    def get_job(job_id: str, context: AuthContext = Depends(read)):
        job = ledger.get(job_id, context.workspace_id)
        if job is None:
            raise HTTPException(status_code=404, detail={"code": "job_not_found", "message": "job not found"})
        return job

    return app


app = create_app() if os.getenv("AGENT_TRUST_IMPORT_APP", "0") == "1" else FastAPI(title="Agent Trust Platform API", version=__version__)


def run() -> None:
    import uvicorn
    uvicorn.run("agent_trust.api.app:create_app", factory=True, host=os.getenv("AGENT_TRUST_HOST", "127.0.0.1"), port=int(os.getenv("AGENT_TRUST_PORT", "8080")))
