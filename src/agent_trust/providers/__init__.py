"""Provider interfaces and explicit optional integrations."""

from .base import (
    AnalysisProvider,
    AnalysisRequest,
    AnalysisResult,
    ProviderCapabilities,
    ProviderError,
    ProviderUnavailable,
    ThreatIntelProvider,
    ThreatIntelRequest,
    ThreatIntelResult,
)

__all__ = [
    "AnalysisProvider", "AnalysisRequest", "AnalysisResult", "ProviderCapabilities",
    "ProviderError", "ProviderUnavailable", "ThreatIntelProvider", "ThreatIntelRequest",
    "ThreatIntelResult",
]
