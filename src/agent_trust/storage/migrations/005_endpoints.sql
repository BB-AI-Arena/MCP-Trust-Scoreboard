CREATE TABLE IF NOT EXISTS agent_trust_endpoints (
 id varchar(128) PRIMARY KEY,
 workspace_id varchar(128) NOT NULL,
 sensor_instance_id varchar(128),
 state varchar(24) NOT NULL,
 bootstrap_hash varchar(64),
 bootstrap_until varchar(40),
 token_hash varchar(64),
 policy text NOT NULL,
 health text NOT NULL,
 correlation text NOT NULL,
 last_seen varchar(40),
 created_at varchar(40) NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_agent_trust_endpoints_workspace ON agent_trust_endpoints(workspace_id);
