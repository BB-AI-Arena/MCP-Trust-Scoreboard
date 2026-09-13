from dataclasses import fields
from importlib.metadata import requires

import pytest

from agent_trust.config import Settings


@pytest.fixture(autouse=True)
def clean_environment(monkeypatch):
    import os
    for name in list(os.environ):
        if name.startswith("AGENT_TRUST_") or name == "DATABASE_URL":
            monkeypatch.delenv(name)


def test_unset_environment_produces_concrete_defaults():
    settings = Settings.from_env()
    assert settings == Settings()
    for field in fields(settings):
        assert type(getattr(settings, field.name)) is type(getattr(Settings(), field.name))
    with pytest.raises(ValueError, match="API_TOKEN"):
        settings.validate()


def test_minimal_token_configuration_starts_with_typed_defaults(monkeypatch):
    monkeypatch.setenv("AGENT_TRUST_API_TOKEN", " integration-only ")
    settings = Settings.from_env()
    settings.validate()
    assert settings.api_token == "integration-only"
    assert settings.auth_mode == "token"
    assert settings.workspace_id == "local"
    assert settings.provider_timeout_seconds == 10.0


def test_explicit_environment_overrides(monkeypatch):
    values = {
        "AGENT_TRUST_VERSION": "2.0.0-alpha.1", "DATABASE_URL": "postgresql://test:test@localhost/test",
        "AGENT_TRUST_API_TOKEN": "integration-only", "AGENT_TRUST_API_SCOPES": "read, assess",
        "AGENT_TRUST_AUTH_MODE": " TOKEN ", "AGENT_TRUST_WORKSPACE_ID": " fixture ",
        "AGENT_TRUST_ALLOWED_ORIGINS": "http://localhost:5173, http://127.0.0.1:5173",
        "AGENT_TRUST_HOSTED_ANALYSIS": "true", "AGENT_TRUST_PROVIDER_TIMEOUT": "2.5",
        "AGENT_TRUST_MAX_REQUEST_BYTES": "1024", "AGENT_TRUST_RETENTION_DAYS": "7",
    }
    for name, value in values.items():
        monkeypatch.setenv(name, value)
    settings = Settings.from_env()
    settings.validate()
    assert settings.database_url == values["DATABASE_URL"]
    assert settings.api_scopes == ("read", "assess")
    assert settings.workspace_id == "fixture"
    assert settings.allowed_origins == ("http://localhost:5173", "http://127.0.0.1:5173")
    assert settings.hosted_analysis_opt_in is True
    assert settings.provider_timeout_seconds == 2.5
    assert settings.max_request_bytes == 1024
    assert settings.retention_days == 7


def test_blank_optional_lists_use_defaults(monkeypatch):
    monkeypatch.setenv("AGENT_TRUST_WORKSPACE_ID", " ")
    monkeypatch.setenv("AGENT_TRUST_ALLOWED_ORIGINS", " , ")
    assert Settings.from_env().workspace_id == Settings().workspace_id
    assert Settings.from_env().allowed_origins == Settings().allowed_origins


@pytest.mark.parametrize("name", ["AGENT_TRUST_PROVIDER_TIMEOUT", "AGENT_TRUST_MAX_REQUEST_BYTES", "AGENT_TRUST_RETENTION_DAYS"])
def test_invalid_numeric_configuration_fails(monkeypatch, name):
    monkeypatch.setenv(name, "invalid")
    with pytest.raises(ValueError):
        Settings.from_env()


def test_uvicorn_is_a_runtime_dependency():
    assert any(req.lower().startswith("uvicorn") and "extra ==" not in req for req in requires("agent-trust-platform"))
