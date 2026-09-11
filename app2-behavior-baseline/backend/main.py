"""
main.py
FastAPI backend for the AI Agent Behavior Baseline Monitor (App2).

Endpoints:
  GET  /health                → liveness check
  GET  /agents                → all agents with status
  GET  /baseline/{agent_id}   → 27-day behavioral baseline
  GET  /anomalies/{agent_id}  → detected anomaly list
  GET  /summary/{agent_id}    → Gemini classification summary
  GET  /agent-data/{agent_id} → full 30-day data for charts
  POST /ingest                → ingest a live metric, run anomaly detection
"""

import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from mock_data import get_all_agents, get_agent_data, get_recent_events, AGENT_PROFILES
from baseline_engine import build_baseline
from anomaly_detector import detect_anomalies
from gemini_analyzer import classify_anomaly_cluster


# ---------------------------------------------------------------------------
# App init
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Koi Security — Agent Behavior Baseline API",
    description="Monitors AI agent behavioral baselines and detects anomalies.",
    version="2.0.0-alpha.1",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173","http://localhost:5174","http://localhost:5175","http://localhost:5176","http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------

class IngestPayload(BaseModel):
    agent_id: str = Field(..., description="Agent identifier")
    metric: str = Field(..., description="Metric name (e.g. 'api_call_rate')")
    value: float = Field(..., description="Observed metric value")
    timestamp: Optional[str] = Field(
        default=None,
        description="ISO-8601 timestamp; defaults to now if omitted",
    )


class IngestResult(BaseModel):
    agent_id: str
    metric: str
    value: float
    timestamp: str
    baseline_mean: Optional[float]
    baseline_std_dev: Optional[float]
    z_score: Optional[float]
    is_anomalous: bool
    anomaly_type: Optional[str]
    severity: Optional[str]
    message: str


# ---------------------------------------------------------------------------
# Helper: validate agent_id exists
# ---------------------------------------------------------------------------

def _require_agent(agent_id: str) -> None:
    known = {a["id"] for a in get_all_agents()}
    if agent_id not in known:
        raise HTTPException(
            status_code=404,
            detail=f"Agent '{agent_id}' not found. Known agents: {sorted(known)}",
        )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/health", tags=["System"])
def health_check():
    """Liveness probe."""
    return {"status": "ok", "timestamp": datetime.now(tz=timezone.utc).isoformat()}


@app.get("/agents", tags=["Agents"])
def list_agents():
    """
    Return all registered agents with their current status and anomaly counts.
    """
    agents = get_all_agents()
    enriched = []
    for agent in agents:
        anomaly_list = detect_anomalies(agent["id"])
        critical_count = sum(1 for a in anomaly_list if a.get("severity") == "critical")
        high_count = sum(1 for a in anomaly_list if a.get("severity") == "high")
        enriched.append(
            {
                **agent,
                "anomaly_count": len(anomaly_list),
                "critical_anomalies": critical_count,
                "high_anomalies": high_count,
            }
        )
    return {"agents": enriched, "total": len(enriched)}


@app.get("/baseline/{agent_id}", tags=["Baseline"])
def get_baseline(agent_id: str, days: int = 27):
    """
    Return the behavioral baseline profile for *agent_id* built from the
    first *days* days of data (default 27 — the clean window).
    """
    _require_agent(agent_id)
    baseline = build_baseline(agent_id, days=days)
    return baseline


@app.get("/anomalies/{agent_id}", tags=["Anomalies"])
def get_anomalies(agent_id: str):
    """
    Return all detected anomalies for *agent_id* (seeded + dynamically
    detected), sorted newest-first.
    """
    _require_agent(agent_id)
    anomalies = detect_anomalies(agent_id)
    return {
        "agent_id": agent_id,
        "anomaly_count": len(anomalies),
        "anomalies": anomalies,
    }


@app.get("/summary/{agent_id}", tags=["Analysis"])
def get_summary(agent_id: str):
    """
    Run Gemini (or heuristic fallback) classification on all current anomalies
    for *agent_id* and return a threat summary.
    """
    _require_agent(agent_id)
    anomalies = detect_anomalies(agent_id)
    summary = classify_anomaly_cluster(agent_id, anomalies)
    return {
        "agent_id": agent_id,
        "anomaly_count": len(anomalies),
        **summary,
    }


@app.get("/agent-data/{agent_id}", tags=["Data"])
def get_full_agent_data(agent_id: str, days: int = 30):
    """
    Return up to *days* daily records for *agent_id* for time-series charts.
    """
    _require_agent(agent_id)
    records = get_agent_data(agent_id, days=days)
    return {
        "agent_id": agent_id,
        "days": len(records),
        "records": records,
    }


@app.get("/events/{agent_id}", tags=["Data"])
def get_agent_events(agent_id: str):
    """
    Return a live-feed of recent events for *agent_id* (normal + anomaly events).
    """
    _require_agent(agent_id)
    events = get_recent_events(agent_id)
    return {
        "agent_id": agent_id,
        "event_count": len(events),
        "events": events,
    }


@app.post("/ingest", response_model=IngestResult, tags=["Ingest"])
def ingest_metric(payload: IngestPayload):
    """
    Accept a single live metric reading, compare against the baseline,
    and return an anomaly assessment.

    Body: {"agent_id": str, "metric": str, "value": float, "timestamp": str}
    """
    _require_agent(payload.agent_id)

    ts = payload.timestamp or datetime.now(tz=timezone.utc).isoformat()

    # Build baseline (cached in a production system; rebuilt here for simplicity)
    baseline = build_baseline(payload.agent_id, days=27)
    metric_stats = baseline["metrics"].get(payload.metric)

    baseline_mean = None
    baseline_std_dev = None
    z_score = None
    is_anomalous = False
    anomaly_type = None
    severity = None

    if metric_stats:
        baseline_mean = metric_stats["mean"]
        baseline_std_dev = metric_stats["std_dev"]
        if baseline_std_dev and baseline_std_dev > 0:
            z_score = round((payload.value - baseline_mean) / baseline_std_dev, 3)
            if abs(z_score) > 2.5:
                is_anomalous = True
                # Pick anomaly type based on metric
                metric_type_map = {
                    "api_call_rate": "NewAPIEndpoint",
                    "file_access_count": "FileSpike",
                    "execution_time_ms": "ExecutionTimeSpike",
                    "credential_accesses": "CredentialAccess",
                }
                anomaly_type = metric_type_map.get(payload.metric, "ExecutionTimeSpike")
                severity_map = {
                    "NewAPIEndpoint": "medium",
                    "FileSpike": "medium",
                    "ExecutionTimeSpike": "low",
                    "CredentialAccess": "critical",
                }
                severity = severity_map.get(anomaly_type, "medium")

    if is_anomalous:
        message = (
            f"ANOMALY: {payload.metric} value {payload.value} is {abs(z_score):.1f}σ "
            f"{'above' if z_score > 0 else 'below'} baseline mean {baseline_mean:.2f}."
        )
    elif metric_stats:
        message = (
            f"Normal: {payload.metric} value {payload.value} within expected range "
            f"(mean={baseline_mean:.2f}, σ={baseline_std_dev:.2f})."
        )
    else:
        message = f"Metric '{payload.metric}' not found in baseline. Cannot evaluate."

    return IngestResult(
        agent_id=payload.agent_id,
        metric=payload.metric,
        value=payload.value,
        timestamp=ts,
        baseline_mean=baseline_mean,
        baseline_std_dev=baseline_std_dev,
        z_score=z_score,
        is_anomalous=is_anomalous,
        anomaly_type=anomaly_type,
        severity=severity,
        message=message,
    )


# ---------------------------------------------------------------------------
# Entry point (uvicorn)
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8002, reload=True)
