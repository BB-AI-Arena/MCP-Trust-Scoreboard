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
