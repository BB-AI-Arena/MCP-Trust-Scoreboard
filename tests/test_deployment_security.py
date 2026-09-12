import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from validate_deployment import validate


@pytest.fixture
def compose_config():
    env = {"PATH": os.environ["PATH"], "AGENT_TRUST_API_TOKEN": "a" * 64, "POSTGRES_PASSWORD": "b" * 48}
    return json.loads(subprocess.check_output(["docker", "compose", "--env-file", "/dev/null", "-f", str(ROOT / "docker-compose.yml"), "config", "--format", "json"], env=env, text=True, timeout=15))


def test_real_compose_is_loopback_without_database_publication(compose_config):
    validate(compose_config)
    assert not compose_config["services"]["postgres"].get("ports")
    assert not compose_config["services"]["redis"].get("ports")
    for service in compose_config["services"].values():
        assert all(p["host_ip"] == "127.0.0.1" for p in service.get("ports", []))


@pytest.mark.parametrize("host", ["0.0.0.0", "::", "192.0.2.1"])
def test_legacy_nonlocal_exposure_is_rejected(compose_config, host):
    compose_config["services"]["frontend-blast"]["ports"][0]["host_ip"] = host
    with pytest.raises(ValueError, match="local-only"):
        validate(compose_config)


def test_platform_remote_requires_explicit_configuration(compose_config):
    api = compose_config["services"]["api-platform"]
    api["ports"][0]["host_ip"] = "::"
    with pytest.raises(ValueError, match="intentional"):
        validate(compose_config)
    api["environment"]["AGENT_TRUST_ALLOW_REMOTE"] = "true"
    validate(compose_config)
    api["environment"]["AGENT_TRUST_API_TOKEN"] = "change-me-local-token"
    with pytest.raises(ValueError, match="non-placeholder"):
        validate(compose_config)


def test_config_generator_never_overwrites(tmp_path):
    target = tmp_path / ".env"
    command = [sys.executable, str(ROOT / "scripts/configure_local.py"), "--output", str(target)]
    result = subprocess.run(command, capture_output=True, text=True, timeout=5)
    assert result.returncode == 0
    contents = target.read_text()
    assert (target.stat().st_mode & 0o777) == 0o600
    assert "AGENT_TRUST_API_TOKEN=" in contents
    assert contents not in result.stdout
    assert subprocess.run(command, capture_output=True, timeout=5).returncode != 0
    assert target.read_text() == contents


def test_known_placeholder_fails_even_locally():
    from agent_trust.config import Settings
    with pytest.raises(ValueError, match="placeholder"):
        Settings(api_token="change-me-local-token").validate()


@pytest.mark.parametrize("app", ["app1-blast-radius", "app2-behavior-baseline", "app3-code-provenance", "app4-mcp-scorecard"])
def test_legacy_provider_key_alone_cannot_trigger_network(monkeypatch, app):
    import socket
    import httpx
    monkeypatch.setenv("GEMINI_API_KEY", "disposable-not-a-real-key")
    monkeypatch.setenv("ABUSEIPDB_API_KEY", "disposable-not-a-real-key")
    monkeypatch.delenv("AGENT_TRUST_HOSTED_ANALYSIS", raising=False)
    attempts = []
    def forbidden(*args, **kwargs):
        attempts.append(True)
        raise AssertionError("rules-only mode attempted external traffic")
    monkeypatch.setattr(socket, "create_connection", forbidden)
    monkeypatch.setattr(socket, "getaddrinfo", forbidden)
    monkeypatch.setattr(httpx.Client, "send", forbidden)
    monkeypatch.setattr(httpx.AsyncClient, "send", forbidden)
    spec = importlib.util.spec_from_file_location("isolated_" + app.replace("-", "_"), ROOT / app / "backend/gemini_analyzer.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    if app.startswith("app1"):
        assert module.analyze_blast_radius([], [], "Contained", [])["attack_narrative"]
    elif app.startswith("app2"):
        assert module._setup_gemini() is False
    elif app.startswith("app3"):
        assert module._get_genai() is None
    else:
        assert "not configured" in str(module.analyze_tools([{"name": "fixture"}]))
    assert not attempts, "provider swallowed an attempted network call"
