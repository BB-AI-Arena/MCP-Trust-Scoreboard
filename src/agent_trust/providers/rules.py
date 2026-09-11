"""Deterministic analysis that works without network access or API keys."""

from __future__ import annotations

import re

from .base import AnalysisRequest, AnalysisResult, ProviderCapabilities


class RulesOnlyAnalysisProvider:
    capabilities = ProviderCapabilities(
        name="rules-only", version="rules-2026-01", assess=True, observe=False, enforce=False
    )

    _RULES = (
        ("embedded_secret", re.compile(r"(?i)(api[_-]?key|password|secret|token)\s*[:=]\s*['\"][^'\"]{8,}['\"]"), "Potential embedded credential"),
        ("execution_authority", re.compile(r"(?i)\b(eval|exec|shell=True|subprocess)\b"), "Dynamic or shell execution requires review"),
        ("broad_network", re.compile(r"(?i)https?://0\.0\.0\.0|0\.0\.0\.0/0|\*\.\*\.\*"), "Broad network target requires review"),
    )

    def analyze(self, request: AnalysisRequest) -> AnalysisResult:
        findings = tuple(
            {"rule_id": rule_id, "title": title, "severity": "high" if rule_id == "embedded_secret" else "medium"}
            for rule_id, pattern, title in self._RULES
            if pattern.search(request.content)
        )
        return AnalysisResult(
            status="complete",
            findings=findings,
            explanation="Deterministic rules ran locally; no model or hosted provider was used.",
            provider=self.capabilities.name,
            engine_version=self.capabilities.version,
        )
