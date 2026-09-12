"""Strict endpoint wire/policy schemas. No arbitrary content, commands or fields."""
from datetime import datetime, timezone, timedelta
from typing import Annotated, Literal
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, model_validator

Name = Annotated[str, Field(min_length=1, max_length=128)]
Path = Annotated[str, Field(max_length=1024)]
State = Literal['supported','active','degraded','permission_missing','unsupported']


class Strict(BaseModel):
    model_config = ConfigDict(extra='forbid')


class RepositoryPolicy(Strict):
    id: UUID
    path: Path
    classification: Literal['Public','Internal','Confidential','Restricted','Regulated']


class CustomTool(Strict):
    id: Name
    path: Path


class EndpointPolicy(Strict):
    version: Literal['endpoint-policy-1'] = 'endpoint-policy-1'
    repositories: list[RepositoryPolicy] = Field(default_factory=list, max_length=20)
    approved_tools: list[Name] = Field(default_factory=list, max_length=100)
    custom_tools: list[CustomTool] = Field(default_factory=list, max_length=50)
    mcp_paths: list[Path] = Field(default_factory=list, max_length=20)
    indicator_sha256: list[Annotated[str, Field(pattern=r'^[a-f0-9]{64}$')]] = Field(default_factory=list, max_length=100)
    known_destinations: list[Annotated[str, Field(max_length=64)]] = Field(default_factory=list, max_length=100)


class Health(Strict):
    service_status: Literal['running','stopping'] = 'running'
    collectors: dict[Name, State] = Field(default_factory=dict, max_length=20)
    spool_depth: int = Field(default=0, ge=0, le=100000)
    events_sent: int = Field(default=0, ge=0)
    events_dropped: int = Field(default=0, ge=0)
    last_upload: str = Field(default='', max_length=40)
    connectivity: Literal['online','offline','unknown'] = 'unknown'
    reason: Literal['polling_gap','capacity','expiry','collector_error','startup','none'] = 'none'


class Software(Strict):
    product: Name
    version: str = Field(default='', max_length=128)
    path: Path = ''
    source: Literal['registry','os','extension','configured_path','catalog_path']


class Process(Strict):
    observation: Literal['first_seen_snapshot','no_longer_visible_snapshot'] | None = None
    process_key: Name
    pid: int = Field(ge=0, le=4294967295)
    parent_pid: int = Field(default=0, ge=0, le=4294967295)
    parent_key: str = Field(default='', max_length=128)
    executable: Path = ''
    parent_executable: Path = ''
    session_id: int = Field(default=0, ge=0)
    user_sid: str = Field(default='', max_length=184)
    sha256: str = Field(default='', pattern=r'^([a-f0-9]{64})?$')


class AITool(Strict):
    tool_id: Name
    path: Path
    version: str = Field(default='', max_length=128)
    process_key: str = Field(default='', max_length=128)
    source: Literal['catalog_path','configured_path','extension','process_snapshot']


class MCP(Strict):
    server_name: Name
    transport: Literal['stdio','http','unknown']
    executable_name: str = Field(default='', max_length=128)
    argument_count: int = Field(default=0, ge=0, le=1000)
    remote_domain: str = Field(default='', max_length=253, pattern=r'^[A-Za-z0-9.:-]*$')
    configuration_source: Path
    configuration_digest: str = Field(pattern=r'^[a-f0-9]{64}$')


class Network(Strict):
    process_key: Name
    pid: int = Field(ge=0, le=4294967295)
    destination_ip: Annotated[str, Field(max_length=45)]
    destination_port: int = Field(ge=1, le=65535)
    transport: Literal['tcp'] = 'tcp'
    direction: Literal['unknown','outbound_candidate'] = 'unknown'

    @model_validator(mode='after')
    def valid_ip(self):
        import ipaddress
        ipaddress.ip_address(self.destination_ip)
        return self


class FileActivity(Strict):
    repository_id: UUID
    relative_path: Path
    previous_relative_path: Path = ''
    process_key: str = Field(default='', max_length=128)
    relationship: Literal['repository_metadata_observation'] = 'repository_metadata_observation'
    size: int = Field(default=0, ge=0)

    @model_validator(mode='after')
    def relative_only(self):
        from pathlib import PureWindowsPath
        for value in (self.relative_path,self.previous_relative_path):
            p = PureWindowsPath(value)
            if p.is_absolute() or p.drive or '..' in p.parts:
                raise ValueError('relative_repository_path_required')
        if self.process_key:
            raise ValueError('polling_does_not_support_file_process_attribution')
        return self


DATA = {
    **dict.fromkeys(['endpoint_heartbeat','endpoint_capabilities','collector_health','visibility_gap'], Health),
    'software_inventory':Software,
    **dict.fromkeys(['ai_tool_discovered','ai_tool_running'],AITool),
    **dict.fromkeys(['mcp_configuration_discovered','mcp_configuration_changed'],MCP),
    **dict.fromkeys(['process_started','process_stopped'],Process),
    'process_network_connection':Network,
    **dict.fromkeys(['file_created','file_modified','file_renamed','file_deleted','repository_interaction'],FileActivity),
}


class EndpointEvent(Strict):
    schema_version: Literal['endpoint-1']
    event_id: UUID
    endpoint_id: UUID
    sensor_instance_id: UUID
    observed_at: datetime
    collector: Literal['runtime','software','ai','mcp','process','network','filesystem']
    sensor_version: Literal['0.1.0']
    policy_version: Literal['endpoint-policy-1']
    event_type: str
    data: dict

    @model_validator(mode='after')
    def typed_data(self):
        if self.event_type not in DATA:
            raise ValueError('unsupported_endpoint_event_type')
        # Omitting new optional None fields preserves old canonical replay hashes.
        self.data = DATA[self.event_type].model_validate(self.data).model_dump(mode='json',exclude_none=True)
        if self.observed_at.tzinfo is None or not datetime.now(timezone.utc)-timedelta(days=14) <= self.observed_at <= datetime.now(timezone.utc)+timedelta(minutes=5):
            raise ValueError('timestamp_outside_offline_window')
        self.observed_at = self.observed_at.astimezone(timezone.utc)
        return self


class EventBatch(Strict):
    events: list[EndpointEvent] = Field(min_length=1, max_length=100)


class Enrollment(Strict):
    endpoint_id: UUID
    sensor_instance_id: UUID
    bootstrap_secret: str = Field(min_length=32, max_length=128, repr=False)
