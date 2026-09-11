"""Explicit compatibility metadata for the four original app contracts."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class LegacyFlow:
    name: str
    service: str
    route: str
    response_shape: str


LEGACY_FLOWS = (
    LegacyFlow("tool_connector_trust", "api-scorecard", "POST /scan", "scorecard result"),
    LegacyFlow("agent_blast_radius", "api-blast", "POST /analyze", "nodes, edges, risk, paths"),
    LegacyFlow("behavior_monitoring", "api-baseline", "POST /ingest", "metric plus anomaly assessment"),
    LegacyFlow("artifact_assurance", "api-provenance", "POST /scan", "provenance, risks, verdict"),
)
