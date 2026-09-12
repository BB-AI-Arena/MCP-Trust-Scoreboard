"""Strict, opt-in adapter for OpenAI-compatible hosted or local endpoints."""

from __future__ import annotations

import json
from typing import Any

import httpx

from .base import AnalysisRequest, AnalysisResult, ProviderCapabilities, ProviderError, ProviderUnavailable


class OpenAICompatibleAnalysisProvider:
    capabilities = ProviderCapabilities(name="openai-compatible", version="adapter-2026-01", assess=True)

    def __init__(self, endpoint: str, model: str, api_key: str = "", timeout: float = 10.0, hosted: bool = False):
        self.endpoint, self.model, self.api_key, self.timeout, self.hosted = endpoint.rstrip("/"), model, api_key, timeout, hosted

    def analyze(self, request: AnalysisRequest) -> AnalysisResult:
        if self.hosted and not request.hosted_data_allowed:
            raise ProviderUnavailable("hosted analysis requires explicit opt-in")
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        body = {
            "model": self.model,
            "messages": [{"role": "user", "content": request.content}],
            "temperature": 0,
            "response_format": {"type": "json_object"},
        }
        try:
            response = httpx.post(f"{self.endpoint}/chat/completions", headers=headers, json=body, timeout=self.timeout, follow_redirects=False)
            response.raise_for_status()
            data: Any = response.json()
            content = data["choices"][0]["message"]["content"]
            payload = json.loads(content)
            if not isinstance(payload, dict):
                raise ValueError("response must be an object")
            findings = payload.get("findings", [])
            if not isinstance(findings, list) or not all(isinstance(item, dict) for item in findings):
                raise ValueError("response does not match findings schema")
        except (httpx.HTTPError, KeyError, IndexError, TypeError, ValueError, json.JSONDecodeError) as exc:
            raise ProviderError(f"OpenAI-compatible provider failed: {exc}") from exc
        return AnalysisResult(status="complete", findings=tuple(findings), explanation=str(payload.get("explanation", "")), provider="openai-compatible", model=self.model, engine_version=self.capabilities.version)
