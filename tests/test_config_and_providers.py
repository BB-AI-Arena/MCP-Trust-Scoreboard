import pytest

from agent_trust.config import Settings
from agent_trust.providers.base import AnalysisRequest, ProviderUnavailable
from agent_trust.providers.gemini import GeminiAnalysisProvider
from agent_trust.providers.rules import RulesOnlyAnalysisProvider


def test_token_auth_is_required_by_default():
    with pytest.raises(ValueError, match="API_TOKEN"):
        Settings().validate()


def test_rules_provider_is_local_and_deterministic():
    result = RulesOnlyAnalysisProvider().analyze(AnalysisRequest("agent-1", 'token = "not-a-real-secret-value"', "2026-01"))
    assert result.status == "complete"
    assert result.provider == "rules-only"
    assert result.findings[0]["rule_id"] == "embedded_secret"


def test_missing_gemini_key_is_unavailable_not_success():
    with pytest.raises(ProviderUnavailable):
        GeminiAnalysisProvider(api_key="").analyze(AnalysisRequest("agent-1", "content", "2026-01"))


@pytest.mark.parametrize("failure", ["timeout", "http", "schema"])
def test_optional_endpoint_failure_is_not_synthetic_success(monkeypatch, failure):
    import httpx
    from agent_trust.providers.base import ProviderError
    from agent_trust.providers.openai_compatible import OpenAICompatibleAnalysisProvider
    calls = []
    def external_fixture(url, **kwargs):
        calls.append(url)
        assert kwargs["follow_redirects"] is False
        if failure == "timeout":
            raise httpx.ReadTimeout("fixture timeout")
        return httpx.Response(503 if failure == "http" else 200,
            json={"choices": [{"message": {"content": '{"findings": "invalid"}'}}]}, request=httpx.Request("POST", url))
    monkeypatch.setattr(httpx, "post", external_fixture)
    provider = OpenAICompatibleAnalysisProvider("https://provider.example.invalid/v1", "fixture-model", hosted=True)
    with pytest.raises(ProviderUnavailable, match="opt-in"):
        provider.analyze(AnalysisRequest("fixture", "content", "2026-01"))
    assert calls == []
    with pytest.raises(ProviderError):
        provider.analyze(AnalysisRequest("fixture", "content", "2026-01", hosted_data_allowed=True))
    assert len(calls) == 1  # Mocked optional provider only; no fallback network call.
