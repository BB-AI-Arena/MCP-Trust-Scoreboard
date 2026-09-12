"""Optional adapter for the legacy Gemini analyzer.

The adapter is deliberately unavailable when no key is configured. It never
turns a missing provider into a synthetic success.
"""

from __future__ import annotations

import json
import os
from typing import Any, Callable

from .base import AnalysisRequest, AnalysisResult, ProviderCapabilities, ProviderUnavailable


class GeminiAnalysisProvider:
    capabilities = ProviderCapabilities(name="gemini", version="adapter-2026-01", assess=True)

    def __init__(self, api_key: str | None = None, model: str | None = None, caller: Callable[..., Any] | None = None):
        self.api_key = (api_key if api_key is not None else os.getenv("GEMINI_API_KEY", "")).strip()
        self.model = model or os.getenv("GEMINI_MODEL", "")
        self._caller = caller

    def analyze(self, request: AnalysisRequest) -> AnalysisResult:
        if not self.api_key and self._caller is None:
            raise ProviderUnavailable("Gemini is not configured")
        if not request.hosted_data_allowed and self._caller is None:
            raise ProviderUnavailable("hosted analysis requires explicit opt-in")
        if self._caller is None:
            try:
                import google.generativeai as genai
            except ImportError as exc:
                raise ProviderUnavailable("google-generativeai is not installed") from exc
            genai.configure(api_key=self.api_key)
            model = genai.GenerativeModel(self.model or "gemini-configured-model")
            response = model.generate_content(request.content)
            raw = getattr(response, "text", "")
        else:
            raw = self._caller(request)
        try:
            payload = json.loads(raw) if isinstance(raw, str) else raw
            if not isinstance(payload, dict):
                raise ValueError("provider response must be an object")
            if not isinstance(payload, dict):
                raise ValueError("provider response must be an object")
            findings = payload.get("findings", [])
            if not isinstance(findings, list) or not all(isinstance(item, dict) for item in findings):
                raise ValueError("findings must be a list of objects")
        except (TypeError, ValueError, json.JSONDecodeError) as exc:
            raise ProviderUnavailable(f"Gemini response failed the output contract: {exc}") from exc
        return AnalysisResult(
            status="complete", findings=tuple(findings), explanation=str(payload.get("explanation", "")),
            provider="gemini", model=self.model or None, engine_version=self.capabilities.version,
        )
