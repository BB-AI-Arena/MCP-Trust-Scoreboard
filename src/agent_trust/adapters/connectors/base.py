"""Separate connector roles; transport delivery is not a response action."""
from dataclasses import dataclass
from typing import Any, Protocol


@dataclass(frozen=True)
class SourceContext:
    workspace_id: str
    collector_identity: str


class EvidenceSource(Protocol):
    name: str
    schema_version: str

    def normalize(self, envelope: Any, context: SourceContext) -> dict: ...


class FindingDestination(Protocol):
    name: str

    def deliver(self, finding: dict, delivery_id: str) -> dict: ...


class ResponseAdapter(Protocol):
    """Future response implementations require separate authority and tests.

    No implementation is registered in alpha. Evidence sources/destinations
    must never be promoted to this interface merely because delivery succeeded.
    """
    name: str

    def request_response(self, authorized_request: dict) -> dict: ...


DESCRIPTORS = [
    {'id':'windows-endpoint','role':'evidence_source','schema_versions':['endpoint-1'],
     'capabilities':['typed_endpoint_ingest','observe_only'], 'enforce':False,
     'validation':'Windows CI required; per-collector coverage reported independently'},
    {'id':'generic-json','role':'evidence_source','schema_versions':['1'],
     'capabilities':['ingest'], 'enforce':False},
    {'id':'webhook','role':'finding_destination','schema_versions':['1'],
     'capabilities':['deliver_findings'], 'enforce':False},
    {'id':'crowdstrike-falcon','role':'evidence_source','schema_versions':['falcon-1'],
     'capabilities':['read_host_inventory','read_alerts'], 'enforce':False,
     'validation':'local TLS protocol fixtures; live pending',
     'operations':['oauth2AccessToken','QueryDevicesByFilterScroll','GetDeviceDetailsV2','PostCombinedAlertsV1']},
]
