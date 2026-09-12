-- Additive operator-owned state; no API record namespace or existing data changes.
CREATE TABLE IF NOT EXISTS agent_trust_connector_checkpoints (
    id varchar(128) PRIMARY KEY,
    workspace_id varchar(128) NOT NULL,
    payload text NOT NULL,
    updated_at varchar(40) NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_agent_trust_connector_checkpoints_workspace_id
    ON agent_trust_connector_checkpoints(workspace_id);
