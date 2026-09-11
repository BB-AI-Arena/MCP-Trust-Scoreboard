-- PostgreSQL reference migration. SQLAlchemy create_all is retained for the
-- disposable local bootstrap; production upgrades should run migrations.
CREATE TABLE IF NOT EXISTS agent_trust_records (
  id varchar(128) PRIMARY KEY,
  workspace_id varchar(128) NOT NULL,
  kind varchar(64) NOT NULL,
  payload text NOT NULL,
  created_at varchar(40) NOT NULL,
  updated_at varchar(40) NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_agent_trust_records_workspace ON agent_trust_records (workspace_id, kind, created_at);
CREATE TABLE IF NOT EXISTS agent_trust_jobs (
  id varchar(128) PRIMARY KEY,
  workspace_id varchar(128) NOT NULL,
  kind varchar(64) NOT NULL,
  payload text NOT NULL,
  status varchar(24) NOT NULL,
  attempts integer NOT NULL DEFAULT 0,
  max_attempts integer NOT NULL DEFAULT 3,
  available_at varchar(40) NOT NULL,
  lease_until varchar(40),
  lease_token varchar(128),
  result text,
  error text,
  idempotency_key varchar(256) UNIQUE,
  created_at varchar(40) NOT NULL,
  updated_at varchar(40) NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_agent_trust_jobs_claim ON agent_trust_jobs (status, available_at, created_at);
