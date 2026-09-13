"""Strict collector-report normalization; raw content is never persisted."""
import hashlib
import json
from typing import Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field

from agent_trust.domain.models import utc_now
from agent_trust.providers.base import AnalysisRequest
from agent_trust.providers.rules import RulesOnlyAnalysisProvider
from .base import SourceContext


class EvidenceEnvelope(BaseModel):
    model_config = ConfigDict(extra='forbid')
    schema_version: Literal['1']
    event_id: str = Field(min_length=1, max_length=128)
    subject: str = Field(min_length=1, max_length=256)
    reported_agent_id: str = Field(min_length=1, max_length=128)
    observed_at: AwareDatetime
    deployment: str | None = Field(default=None, max_length=128)
    subject_version: str | None = Field(default=None, max_length=128)
    artifact_digest: str | None = Field(default=None, pattern=r'^sha256:[a-f0-9]{64}$')
    content: str = Field(default='', max_length=100_000)


class GenericJSONSource:
    name = 'generic-json'
    schema_version = '1'

    def normalize(self, envelope: EvidenceEnvelope, context: SourceContext) -> dict:
        canonical = json.dumps(envelope.model_dump(mode='json'), sort_keys=True, separators=(',',':'))
        result = RulesOnlyAnalysisProvider().analyze(AnalysisRequest(subject=envelope.subject, content=envelope.content, schema_version='2026-01'))
        # The envelope is authenticated as a collector report, not proof of the
        # reported agent, publisher, observations or artifact's authenticity.
        return {'source':self.name, 'source_schema':'1', 'schema_version':'2026-01',
            'event_id':envelope.event_id, 'subject':envelope.subject,
            'reported_agent_id':envelope.reported_agent_id,
            'collector_identity':context.collector_identity, 'workspace_id':context.workspace_id,
            'observed_at':envelope.observed_at.isoformat(), 'collected_at':utc_now(),
            'deployment':envelope.deployment, 'version':envelope.subject_version,
            'digest':envelope.artifact_digest, 'status':'claimed', 'verification':None,
            'method':'authenticated_collector_report', 'redacted':True,
            'retention':'raw content discarded; metadata and content digest retained',
            'content_sha256':hashlib.sha256(envelope.content.encode()).hexdigest(),
            'input_digest':hashlib.sha256(canonical.encode()).hexdigest(),
            'rule_version':result.engine_version, 'rule_findings':list(result.findings)}
