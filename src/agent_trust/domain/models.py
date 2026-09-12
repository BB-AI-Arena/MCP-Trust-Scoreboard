"""Stable, JSON-serializable domain models.

The models intentionally preserve unknown values. An assessment is allowed to
say that evidence is unavailable; callers must not infer a clean result from
missing data.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4

SCHEMA_VERSION = "2026-01"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class EvidenceStatus(str, Enum):
    CLAIMED = "claimed"
    VERIFIED = "verified"
    OBSERVED = "observed"
    UNAVAILABLE = "unavailable"
    NOT_APPLICABLE = "not_applicable"


@dataclass(slots=True)
class Evidence:
    source: str
    subject: str
    status: EvidenceStatus
    collected_at: str = field(default_factory=utc_now)
    method: str = "unspecified"
    retention: str = "minimal"
    redacted: bool = True
    deployment: str | None = None
    version: str | None = None
    digest: str | None = None
    verification: dict[str, Any] | None = None
    id: str = field(default_factory=lambda: str(uuid4()))
    schema_version: str = SCHEMA_VERSION


@dataclass(slots=True)
class Agent:
    name: str
    workspace_id: str
    id: str = field(default_factory=lambda: str(uuid4()))
    deployment: str | None = None
    reported_identity: str | None = None
    authenticated_collector: str | None = None
    version: str | None = None
    status: str = "active"
    created_at: str = field(default_factory=utc_now)
    schema_version: str = SCHEMA_VERSION


@dataclass(slots=True)
class Run:
    agent_id: str
    run_type: str
    workspace_id: str
    status: str = "started"
    id: str = field(default_factory=lambda: str(uuid4()))
    started_at: str = field(default_factory=utc_now)
    finished_at: str | None = None
    schema_version: str = SCHEMA_VERSION


@dataclass(slots=True)
class Principal:
    name: str
    kind: str
    workspace_id: str
    id: str = field(default_factory=lambda: str(uuid4()))
    schema_version: str = SCHEMA_VERSION


@dataclass(slots=True)
class Connection:
    agent_id: str
    target: str
    connection_type: str
    workspace_id: str
    id: str = field(default_factory=lambda: str(uuid4()))
    capabilities: list[str] = field(default_factory=list)
    evidence_ids: list[str] = field(default_factory=list)
    schema_version: str = SCHEMA_VERSION


@dataclass(slots=True)
class Tool:
    name: str
    workspace_id: str
    id: str = field(default_factory=lambda: str(uuid4()))
    description: str | None = None
    version: str | None = None
    digest: str | None = None
    schema: dict[str, Any] = field(default_factory=dict)
    schema_version: str = SCHEMA_VERSION


@dataclass(slots=True)
class Resource:
    name: str
    resource_type: str
    workspace_id: str
    id: str = field(default_factory=lambda: str(uuid4()))
    identifier: str | None = None
    schema_version: str = SCHEMA_VERSION


@dataclass(slots=True)
class Permission:
    actor_id: str
    target_id: str
    action: str
    access_state: str = "declared"
    conditions: dict[str, Any] = field(default_factory=dict)
    provenance: list[str] = field(default_factory=list)
    valid_from: str | None = None
    valid_until: str | None = None
    id: str = field(default_factory=lambda: str(uuid4()))
    schema_version: str = SCHEMA_VERSION


@dataclass(slots=True)
class Event:
    agent_id: str
    event_type: str
    occurred_at: str
    payload: dict[str, Any]
    collector_identity: str
    id: str = field(default_factory=lambda: str(uuid4()))
    idempotency_key: str | None = None
    schema_version: str = SCHEMA_VERSION


@dataclass(slots=True)
class Finding:
    title: str
    severity: str
    subject_id: str
    description: str
    workspace_id: str
    id: str = field(default_factory=lambda: str(uuid4()))
    evidence_ids: list[str] = field(default_factory=list)
    status: str = "open"
    schema_version: str = SCHEMA_VERSION


@dataclass(slots=True)
class Assessment:
    subject_id: str
    profile: str
    workspace_id: str
    risk: int | None = None
    coverage: int | None = None
    confidence: int | None = None
    skipped_checks: list[str] = field(default_factory=list)
    failed_checks: list[str] = field(default_factory=list)
    policy_decisions: list[dict[str, Any]] = field(default_factory=list)
    engine_version: str = "rules-2026-01"
    rule_version: str = "rules-2026-01"
    id: str = field(default_factory=lambda: str(uuid4()))
    created_at: str = field(default_factory=utc_now)
    schema_version: str = SCHEMA_VERSION


@dataclass(slots=True)
class GraphSnapshot:
    workspace_id: str
    nodes: list[dict[str, Any]]
    edges: list[dict[str, Any]]
    access_semantics: str = "declared"
    captured_at: str = field(default_factory=utc_now)
    id: str = field(default_factory=lambda: str(uuid4()))
    schema_version: str = SCHEMA_VERSION


@dataclass(slots=True)
class Artifact:
    name: str
    digest: str
    workspace_id: str
    source_revision: str | None = None
    build_metadata: dict[str, Any] = field(default_factory=dict)
    attestations: list[dict[str, Any]] = field(default_factory=list)
    provenance_status: EvidenceStatus = EvidenceStatus.UNAVAILABLE
    id: str = field(default_factory=lambda: str(uuid4()))
    schema_version: str = SCHEMA_VERSION


@dataclass(slots=True)
class PolicyDecision:
    subject_id: str
    decision: str
    reason: str
    policy_version: str
    id: str = field(default_factory=lambda: str(uuid4()))
    created_at: str = field(default_factory=utc_now)
    schema_version: str = SCHEMA_VERSION


@dataclass(slots=True)
class Job:
    kind: str
    workspace_id: str
    payload: dict[str, Any]
    status: str = "queued"
    id: str = field(default_factory=lambda: str(uuid4()))
    attempts: int = 0
    max_attempts: int = 3
    schema_version: str = SCHEMA_VERSION


def model_dict(model: Any) -> dict[str, Any]:
    """Serialize a domain model without leaking implementation details."""
    result = asdict(model)
    for key, value in list(result.items()):
        if isinstance(value, Enum):
            result[key] = value.value
    return result
