"""Contract tests for the four preserved legacy FastAPI workspaces.

Each legacy app has same-named helper modules (for example, ``gemini_analyzer``).
The loader therefore removes those modules from ``sys.modules`` before loading one
app, so a test cannot accidentally exercise another workspace's implementation.
These tests intentionally run with provider credentials absent: the deterministic
flows must remain useful and must label optional-provider degradation in responses.
"""

from __future__ import annotations

import io
import importlib.util
import os
import sys
import zipfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


ROOT = Path(__file__).parents[1]
LEGACY_MODULES = {
    "gemini_analyzer",
    "graph_builder",
    "risk_scorer",
    "mock_data",
    "baseline_engine",
    "anomaly_detector",
    "provenance_detector",
    "code_risk_scanner",
    "domain_checker",
    "scorer",
    "egress_guard",
    "job_queue",
}


def _load_legacy_app(name: str, relative_backend: str):
    """Load a legacy ``main.py`` with its backend directory first on sys.path."""

    for module_name in (*LEGACY_MODULES, "main"):
        sys.modules.pop(module_name, None)

    backend = ROOT / relative_backend
    sys.path.insert(0, str(backend))
    module_name = f"legacy_{name}_contract_main"
    spec = importlib.util.spec_from_file_location(module_name, backend / "main.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    try:
        spec.loader.exec_module(module)
    except Exception:
        sys.path.remove(str(backend))
        sys.modules.pop(module_name, None)
        raise
    return module


@pytest.fixture(autouse=True)
def no_optional_provider_credentials(monkeypatch):
    for key in ("GEMINI_API_KEY", "ABUSEIPDB_API_KEY", "OPENAI_API_KEY"):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("SCAN_MODE", "sync")
    monkeypatch.setenv("ALLOW_PRIVATE_COLLECTOR_TARGETS", "false")


def test_blast_radius_contract_and_rules_fallback():
    module = _load_legacy_app("blast_radius", "app1-blast-radius/backend")
    response = TestClient(module.app).post(
        "/analyze",
        json={
            "agent_name": "contract-test-agent",
            "permissions": ["s3:GetObject"],
            "integrations": ["artifact-store"],
            "endpoint_type": "internal",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert set(body) == {
        "blast_rating",
        "overall_score",
        "nodes",
        "edges",
        "critical_paths",
        "attack_narrative",
        "mitigations",
    }
    assert isinstance(body["overall_score"], int)
    assert body["nodes"]
    assert body["edges"]
    assert body["mitigations"]
    assert "AI analysis unavailable" not in body["attack_narrative"]


def test_behavior_contract_labels_seeded_demo_data_and_ingests_metric():
    module = _load_legacy_app("behavior", "app2-behavior-baseline/backend")
    client = TestClient(module.app)

    agents_response = client.get("/agents")
    assert agents_response.status_code == 200
    agents_body = agents_response.json()
    assert agents_body["total"] == 5
    assert {agent["id"] for agent in agents_body["agents"]} >= {
        "claude-code",
        "custom-agent",
    }
    assert agents_body["data_mode"] == "demo"

    response = client.post(
        "/ingest",
        json={
            "agent_id": "claude-code",
            "metric": "api_call_rate",
            "value": 45,
            "timestamp": "2026-09-11T12:00:00Z",
        },
    )
    assert response.status_code == 200
    assert response.json()["agent_id"] == "claude-code"
    assert response.json()["is_anomalous"] is False


def test_artifact_assurance_contract_and_rejects_traversal_zip():
    module = _load_legacy_app("artifact", "app3-code-provenance/backend")
    client = TestClient(module.app)

    response = client.post(
        "/scan",
        json={
            "code": "def safe(value):\n    return value\n",
            "language": "Python",
            "filename": "safe.py",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert set(body) == {"filename", "language", "provenance", "risks", "gemini"}
    assert body["filename"] == "safe.py"
    assert body["language"] == "Python"
    assert "experimental" in body["provenance"]["limitations"].lower()

    archive = io.BytesIO()
    with zipfile.ZipFile(archive, "w") as zf:
        zf.writestr("../../outside.py", "print('unsafe')")
    archive.seek(0)
    rejected = client.post(
        "/scan-repo",
        files={"file": ("unsafe.zip", archive.getvalue(), "application/zip")},
    )
    assert rejected.status_code == 422
    assert "escapes extraction root" in rejected.json()["detail"]


def test_tool_connector_contract_uses_manifest_and_rejects_private_url():
    module = _load_legacy_app("tool_connector", "app4-mcp-scorecard/backend")
    client = TestClient(module.app)

    response = client.post(
        "/scan",
        json={
            "manifest": {
                "name": "local-fixture-server",
                "version": "1.0.0",
                "tools": [
                    {
                        "name": "read_record",
                        "description": "Read a record by identifier",
                    }
                ],
            }
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert "dimensions" in body
    assert "overall_score" in body
    assert body["flags"]
    assert any("API key" in flag for flag in body["flags"])

    rejected = client.post(
        "/scan",
        json={"url": "http://127.0.0.1:8000/manifest.json"},
    )
    assert rejected.status_code == 422
    assert "Unsafe manifest URL" in rejected.json()["detail"]


@pytest.mark.parametrize(
    ("manifest", "expected_scores", "expected_overall", "expected_rating", "expected_flags", "expected_identity", "expected_transparency"),
    [
        (
            {"publisher": {"name": "Claimed Audit", "verified": True}, "audit": "vendor attestation", "version": "1.0.0", "installs": 1000},
            {"identity": 90, "permission_sprawl": 100, "network_behavior": 100, "code_transparency": 95, "version_drift": 50, "community_signal": 70},
            89,
            "High",
            [],
            'Publisher "Claimed Audit" with submitted verification/URL claim — not independently verified',
            "Submitted audit claim — not independently verified; source availability not verified",
        ),
        (
            {"publisher": {"name": "Verified Flag", "verified": True}, "version": "1.0.0", "installs": 1000},
            {"identity": 90, "permission_sprawl": 100, "network_behavior": 100, "code_transparency": 20, "version_drift": 50, "community_signal": 70},
            78,
            "Medium",
            ["No source code or audit trail available"],
            'Publisher "Verified Flag" with submitted verification/URL claim — not independently verified',
            "No submitted source repository or code transparency information found",
        ),
        (
            {"publisher": {"name": "Publisher URL", "url": "https://publisher.example"}, "version": "1.0.0", "installs": 1000},
            {"identity": 90, "permission_sprawl": 100, "network_behavior": 100, "code_transparency": 20, "version_drift": 50, "community_signal": 70},
            78,
            "Medium",
            ["No source code or audit trail available"],
            'Publisher "Publisher URL" with submitted verification/URL claim — not independently verified',
            "No submitted source repository or code transparency information found",
        ),
        (
            {"publisher": {"name": "Homepage Signal"}, "homepage": "https://homepage.example", "version": "1.0.0", "installs": 1000},
            {"identity": 90, "permission_sprawl": 100, "network_behavior": 100, "code_transparency": 20, "version_drift": 50, "community_signal": 70},
            78,
            "Medium",
            ["No source code or audit trail available"],
            'Publisher "Homepage Signal" with submitted verification/URL claim — not independently verified',
            "No submitted source repository or code transparency information found",
        ),
        (
            {"publisher": {"name": "Repository Signal"}, "repository": "https://repo.example/project", "version": "1.0.0", "installs": 1000},
            {"identity": 90, "permission_sprawl": 100, "network_behavior": 100, "code_transparency": 50, "version_drift": 50, "community_signal": 70},
            82,
            "High",
            [],
            'Publisher "Repository Signal" with submitted verification/URL claim — not independently verified',
            "Submitted repository link: https://repo.example/project — no audit record claimed",
        ),
        (
            {"source": "https://source.example/project", "version": "1.0.0", "installs": 1000},
            {"identity": 25, "permission_sprawl": 100, "network_behavior": 100, "code_transparency": 50, "version_drift": 50, "community_signal": 70},
            70,
            "Medium",
            ["Anonymous publisher — identity cannot be verified"],
            "No publisher identity found — anonymous source",
            "Submitted repository link: https://source.example/project — no audit record claimed",
        ),
        (
            {"version": "1.0.0", "installs": 1000},
            {"identity": 25, "permission_sprawl": 100, "network_behavior": 100, "code_transparency": 20, "version_drift": 50, "community_signal": 70},
            65,
            "Medium",
            ["Anonymous publisher — identity cannot be verified", "No source code or audit trail available"],
            "No publisher identity found — anonymous source",
            "No submitted source repository or code transparency information found",
        ),
    ],
)
def test_tool_connector_claimed_identity_and_transparency_are_not_verified(
    monkeypatch,
    manifest,
    expected_scores,
    expected_overall,
    expected_rating,
    expected_flags,
    expected_identity,
    expected_transparency,
):
    module = _load_legacy_app("tool_connector_claims", "app4-mcp-scorecard/backend")
    monkeypatch.setattr(module, "check_domains", lambda domains: {"flagged": [], "unresolvable": [], "clean": []})
    monkeypatch.setattr(
        module,
        "analyze_tools",
        lambda tools: {
            "risk_flags": [],
            "intent_summary": "deterministic fixture",
            "permission_analysis": "deterministic fixture",
            "suspicion_score": 0,
        },
    )

    response = TestClient(module.app).post("/scan", json={"manifest": manifest})

    assert response.status_code == 200
    body = response.json()
    assert set(body["dimensions"]) == set(expected_scores)
    assert {name: dimension["score"] for name, dimension in body["dimensions"].items()} == expected_scores
    assert body["overall_score"] == expected_overall
    assert body["trust_rating"] == expected_rating
    assert body["flags"] == expected_flags
    assert body["dimensions"]["identity"]["explanation"] == expected_identity
    assert body["dimensions"]["code_transparency"]["explanation"] == expected_transparency
    assert "independently audited" not in body["dimensions"]["code_transparency"]["explanation"]
    assert "with verified identity/URL" not in body["dimensions"]["identity"]["explanation"]
