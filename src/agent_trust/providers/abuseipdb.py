"""Optional AbuseIPDB threat-intelligence adapter."""

from __future__ import annotations

import os

import httpx

from .base import ProviderCapabilities, ProviderError, ProviderUnavailable, ThreatIntelRequest, ThreatIntelResult


class AbuseIPDBProvider:
    capabilities = ProviderCapabilities(name="abuseipdb", version="adapter-2026-01", assess=True)
    endpoint = "https://api.abuseipdb.com/api/v2/check"

    def __init__(self, api_key: str | None = None, timeout: float = 8.0):
        self.api_key = (api_key if api_key is not None else os.getenv("ABUSEIPDB_API_KEY", "")).strip()
        self.timeout = timeout

    def check(self, request: ThreatIntelRequest) -> ThreatIntelResult:
        if not self.api_key:
            raise ProviderUnavailable("AbuseIPDB is not configured")
        if request.indicator_type not in {"ip", "domain"}:
            raise ProviderError("AbuseIPDB supports only IP and domain indicators")
        try:
            response = httpx.get(self.endpoint, headers={"Key": self.api_key, "Accept": "application/json"}, params={"ipAddress": request.indicator, "maxAgeInDays": 90}, timeout=self.timeout, follow_redirects=False)
            response.raise_for_status()
            data = response.json().get("data", {})
        except (httpx.HTTPError, ValueError) as exc:
            raise ProviderError(f"AbuseIPDB request failed: {exc}") from exc
        return ThreatIntelResult(status="complete", indicator=request.indicator, confidence=int(data.get("abuseConfidenceScore", 0)), source="abuseipdb", details={"country_code": data.get("countryCode")})
