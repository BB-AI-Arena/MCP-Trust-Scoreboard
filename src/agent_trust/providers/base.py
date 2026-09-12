"""Provider contracts. Providers never decide deterministic policy outcomes."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


class ProviderError(RuntimeError):
    """A provider failed after being explicitly selected."""


class ProviderUnavailable(ProviderError):
    """A provider is not configured or does not support the requested feature."""


@dataclass(frozen=True, slots=True)
class ProviderCapabilities:
    name: str
    version: str
    assess: bool = False
    inventory: bool = False
    observe: bool = False
    enforce: bool = False
    protocol_versions: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class AnalysisRequest:
    subject: str
    content: str
    schema_version: str
    hosted_data_allowed: bool = False
    limits: dict[str, int] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class AnalysisResult:
    status: str
    findings: tuple[dict[str, Any], ...] = ()
    explanation: str = ""
    provider: str = ""
    model: str | None = None
    engine_version: str = ""


@dataclass(frozen=True, slots=True)
class ThreatIntelRequest:
    indicator: str
    indicator_type: str = "domain"


@dataclass(frozen=True, slots=True)
class ThreatIntelResult:
    status: str
    indicator: str
    confidence: int | None = None
    source: str = ""
    details: dict[str, Any] = field(default_factory=dict)


class AnalysisProvider(Protocol):
    capabilities: ProviderCapabilities

    def analyze(self, request: AnalysisRequest) -> AnalysisResult: ...


class ThreatIntelProvider(Protocol):
    capabilities: ProviderCapabilities

    def check(self, request: ThreatIntelRequest) -> ThreatIntelResult: ...
