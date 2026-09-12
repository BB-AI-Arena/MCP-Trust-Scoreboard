"""
main.py
FastAPI entrypoint for the Blast Radius Visualizer backend.

Run locally:
    uvicorn main:app --reload --port 8000
"""

import logging
import os

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Optional

# Load .env before importing modules that read env vars
load_dotenv()

import gemini_analyzer
import graph_builder
import risk_scorer

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------
app = FastAPI(
    title="Blast Radius Visualizer API",
    description="Analyses AI agent permissions and integrations to compute blast radius.",
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

class AnalyzeRequest(BaseModel):
    agent_name: str = Field(..., min_length=1, max_length=200, description="Display name of the AI agent")
    permissions: List[str] = Field(default_factory=list, description="List of permission strings, e.g. ['s3:GetObject', 'rds:connect']")
    integrations: List[str] = Field(default_factory=list, description="List of integration names, e.g. ['openai', 'stripe']")
    endpoint_type: str = Field(default="internal", description="Exposure type: 'public', 'internal', etc.")


class NodeOut(BaseModel):
    id: str
    type: str
    label: str
    criticality: str
    x: float
    y: float
    reach_score: float


class EdgeOut(BaseModel):
    source: str
    target: str
    type: str


class AnalyzeResponse(BaseModel):
    blast_rating: str
    overall_score: int
    nodes: List[NodeOut]
    edges: List[EdgeOut]
    critical_paths: List[List[str]]
    attack_narrative: str
    mitigations: List[str]


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/health", tags=["Health"])
async def health_check():
    """Simple liveness probe."""
    return {"status": "ok"}


@app.post("/analyze", response_model=AnalyzeResponse, tags=["Analysis"])
async def analyze(request: AnalyzeRequest):
    """
    Analyse an AI agent's blast radius.

    Steps:
    1. Build a directed permission graph with graph_builder.
    2. Score the blast radius with risk_scorer.
    3. Generate Gemini-powered attack narrative and mitigations.
    4. Return the combined result.
    """
    logger.info(
        "Received /analyze request — agent=%r  permissions=%d  integrations=%d",
        request.agent_name,
        len(request.permissions),
        len(request.integrations),
    )

    # ------------------------------------------------------------------
    # Step 1 — Build graph
    # ------------------------------------------------------------------
    try:
        graph_data = graph_builder.build_graph(
            agent_name=request.agent_name,
            permissions=request.permissions,
            integrations=request.integrations,
            endpoint_type=request.endpoint_type,
        )
    except Exception as exc:
        logger.exception("graph_builder.build_graph raised an unexpected error")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to build permission graph: {exc}",
        ) from exc

    nodes = graph_data.get("nodes", [])
    edges = graph_data.get("edges", [])

    if not nodes:
        raise HTTPException(
            status_code=422,
            detail=(
                "The graph contains no nodes. "
                "Please supply at least one permission or integration."
            ),
        )

    # ------------------------------------------------------------------
    # Step 2 — Score blast radius
    # ------------------------------------------------------------------
    try:
        score_data = risk_scorer.score_blast_radius(nodes=nodes, edges=edges)
    except Exception as exc:
        logger.exception("risk_scorer.score_blast_radius raised an unexpected error")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to score blast radius: {exc}",
        ) from exc

    overall_score    = score_data.get("overall_score", 0)
    blast_rating     = score_data.get("blast_rating", "Contained")
    critical_nodes   = score_data.get("critical_nodes", [])
    critical_paths   = score_data.get("highest_risk_paths", [])

    # ------------------------------------------------------------------
    # Step 3 — Gemini analysis
    # ------------------------------------------------------------------
    try:
        ai_data = gemini_analyzer.analyze_blast_radius(
            nodes=nodes,
            edges=edges,
            blast_rating=blast_rating,
            critical_nodes=critical_nodes,
        )
    except Exception as exc:
        logger.exception("gemini_analyzer.analyze_blast_radius raised an unexpected error")
        # Non-fatal: return placeholder values rather than a 500
        ai_data = {
            "attack_narrative": (
                "If this agent were compromised, an attacker could exploit its permissions "
                "to access sensitive resources. (AI analysis unavailable.)"
            ),
            "mitigations": [
                "Review and reduce the agent's permission scope.",
                "Rotate all credentials accessible by this agent.",
                "Enable audit logging for all agent actions.",
            ],
        }

    # ------------------------------------------------------------------
    # Step 4 — Combine and return
    # ------------------------------------------------------------------
    logger.info(
        "Analysis complete — score=%d  rating=%s  critical_nodes=%d",
        overall_score,
        blast_rating,
        len(critical_nodes),
    )

    return AnalyzeResponse(
        blast_rating=blast_rating,
        overall_score=overall_score,
        nodes=[NodeOut(**n) for n in nodes],
        edges=[EdgeOut(**e) for e in edges],
        critical_paths=critical_paths,
        attack_narrative=ai_data.get("attack_narrative", ""),
        mitigations=ai_data.get("mitigations", []),
    )
