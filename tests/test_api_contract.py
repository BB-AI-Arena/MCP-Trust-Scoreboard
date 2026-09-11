from fastapi.testclient import TestClient
from sqlalchemy import create_engine

from agent_trust.api.app import create_app
from agent_trust.config import Settings
from agent_trust.storage.database import create_schema


def test_versioned_api_binds_workspace_server_side(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'api.db'}", future=True)
    create_schema(engine)
    settings = Settings(database_url="sqlite://", auth_mode="token", api_token="test-token", workspace_id="server-workspace")
    app = create_app(settings, engine)
    client = TestClient(app)
    headers = {"Authorization": "Bearer test-token"}
    response = client.post("/api/v1/agents", json={"payload": {"name": "agent", "workspace_id": "attacker-workspace"}}, headers=headers)
    assert response.status_code == 201
    assert response.json()["workspace_id"] == "server-workspace"
    assert client.get("/api/v1/agents", headers=headers).json()["count"] == 1
    assert client.get("/api/v1/agents", headers={"Authorization": "Bearer bad"}).status_code == 401


def test_assessment_is_async_and_idempotent(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'api.db'}", future=True)
    create_schema(engine)
    settings = Settings(database_url="sqlite://", auth_mode="disabled", workspace_id="test")
    client = TestClient(create_app(settings, engine))
    body = {"subject_id": "agent-1", "content": "eval(user)", "idempotency_key": "assessment-1"}
    first = client.post("/api/v1/assessments", json=body)
    second = client.post("/api/v1/assessments", json=body)
    assert first.status_code == second.status_code == 202
    assert first.json()["job_id"] == second.json()["job_id"]


def test_event_idempotency_and_collector_identity_are_server_bound(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'api.db'}", future=True)
    create_schema(engine)
    settings = Settings(database_url="sqlite://", auth_mode="disabled", workspace_id="test")
    client = TestClient(create_app(settings, engine))
    body = {"payload": {"agent_id": "reported-agent", "idempotency_key": "event-1", "collector_identity": "forged"}}
    assert client.post("/api/v1/events", json=body).status_code == 201
    assert client.post("/api/v1/events", json=body).status_code == 201
    events = client.get("/api/v1/events").json()
    assert events["count"] == 1
    assert events["items"][0]["collector_identity"] == "local-disabled-auth"
