"""Explicit, safe-by-default configuration for the modular platform."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Settings:
    version: str = "2.0.0-alpha.1"
    database_url: str = "postgresql+psycopg://agent_trust:change-me@localhost:5432/agent_trust"
    api_token: str = ""
    api_scopes: tuple[str, ...] = ("read", "write", "assess")
    auth_mode: str = "token"
    workspace_id: str = "local"
    allowed_origins: tuple[str, ...] = ("http://127.0.0.1:5173", "http://localhost:5173")
    hosted_analysis_opt_in: bool = False
    provider_timeout_seconds: float = 10.0
    max_request_bytes: int = 2_000_000
    retention_days: int = 30

    @classmethod
    def from_env(cls) -> "Settings":
        # With slots=True, class attributes are descriptors, not field values.
        defaults = cls()
        origins = tuple(
            item.strip() for item in os.getenv("AGENT_TRUST_ALLOWED_ORIGINS", "http://127.0.0.1:5173,http://localhost:5173").split(",") if item.strip()
        )
        return cls(
            version=os.getenv("AGENT_TRUST_VERSION", defaults.version),
            database_url=os.getenv("DATABASE_URL", defaults.database_url),
            api_token=os.getenv("AGENT_TRUST_API_TOKEN", "").strip(),
            api_scopes=tuple(item.strip() for item in os.getenv("AGENT_TRUST_API_SCOPES", "read,write,assess").split(",") if item.strip()),
            auth_mode=os.getenv("AGENT_TRUST_AUTH_MODE", defaults.auth_mode).strip().lower(),
            workspace_id=os.getenv("AGENT_TRUST_WORKSPACE_ID", defaults.workspace_id).strip() or defaults.workspace_id,
            allowed_origins=origins or defaults.allowed_origins,
            hosted_analysis_opt_in=os.getenv("AGENT_TRUST_HOSTED_ANALYSIS", "false").lower() in {"1", "true", "yes"},
            provider_timeout_seconds=float(os.getenv("AGENT_TRUST_PROVIDER_TIMEOUT", defaults.provider_timeout_seconds)),
            max_request_bytes=int(os.getenv("AGENT_TRUST_MAX_REQUEST_BYTES", defaults.max_request_bytes)),
            retention_days=int(os.getenv("AGENT_TRUST_RETENTION_DAYS", defaults.retention_days)),
        )

    def validate(self) -> None:
        if self.auth_mode not in {"token", "disabled"}:
            raise ValueError("AGENT_TRUST_AUTH_MODE must be token or disabled")
        if self.auth_mode == "token" and not self.api_token:
            raise ValueError("AGENT_TRUST_API_TOKEN is required when token authentication is enabled")
        if self.auth_mode == "disabled" and self.hosted_analysis_opt_in:
            raise ValueError("hosted analysis cannot be enabled with disabled API authentication")
        if self.max_request_bytes <= 0 or self.provider_timeout_seconds <= 0:
            raise ValueError("request size and provider timeout must be positive")
