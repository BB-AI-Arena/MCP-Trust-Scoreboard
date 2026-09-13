-- Preserve jobs/results and keys while allowing the same key in two workspaces.
-- The previous global unique constraint also affected SQLAlchemy bootstraps.
DO $$
DECLARE constraint_name text;
BEGIN
  FOR constraint_name IN
    SELECT c.conname FROM pg_constraint c
    WHERE c.conrelid = 'agent_trust_jobs'::regclass AND c.contype = 'u'
      AND c.conkey = ARRAY[(SELECT attnum FROM pg_attribute
        WHERE attrelid = 'agent_trust_jobs'::regclass AND attname = 'idempotency_key')]
  LOOP
    EXECUTE format('ALTER TABLE agent_trust_jobs DROP CONSTRAINT %I', constraint_name);
  END LOOP;
END $$;

CREATE UNIQUE INDEX IF NOT EXISTS uq_agent_trust_jobs_workspace_key
  ON agent_trust_jobs (workspace_id, idempotency_key);
