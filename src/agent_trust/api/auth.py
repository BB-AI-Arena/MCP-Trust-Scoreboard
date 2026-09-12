"""Request authentication and scope binding.

The workspace comes from server-side configuration, never from submitted
payloads. Reported agent identity and authenticated collector identity remain
separate fields.
"""

from __future__ import annotations

import secrets
from dataclasses import dataclass

from fastapi import Header, HTTPException

from agent_trust.config import Settings


@dataclass(frozen=True, slots=True)
class AuthContext:
    workspace_id: str
    subject: str
    scopes: frozenset[str]


def authenticate(settings: Settings, authorization: str | None, required_scope: str) -> AuthContext:
    if settings.auth_mode == "disabled":
        return AuthContext(settings.workspace_id, "local-disabled-auth", frozenset(settings.api_scopes))
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail={"code": "missing_bearer_token", "message": "Bearer authentication is required"}, headers={"WWW-Authenticate": "Bearer"})
    supplied = authorization[7:].strip()
    if not settings.api_token or not secrets.compare_digest(supplied, settings.api_token):
        raise HTTPException(status_code=401, detail={"code": "invalid_token", "message": "The supplied bearer token is invalid"}, headers={"WWW-Authenticate": "Bearer"})
    if required_scope not in settings.api_scopes:
        raise HTTPException(status_code=403, detail={"code": "scope_not_granted", "message": f"Required scope: {required_scope}"})
    return AuthContext(settings.workspace_id, "api-token", frozenset(settings.api_scopes))


def context_dependency(settings: Settings, required_scope: str):
    def dependency(authorization: str | None = Header(default=None)) -> AuthContext:
        return authenticate(settings, authorization, required_scope)
    return dependency
