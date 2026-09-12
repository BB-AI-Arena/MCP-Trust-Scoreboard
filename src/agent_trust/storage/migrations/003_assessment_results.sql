-- Repair only namespaced assessment projections from their durable job ledger.
-- Older workers completed jobs without updating (or creating) the projection.
-- Preserve original jobs and unrelated record metadata; do not import Redis.
INSERT INTO agent_trust_records (id, workspace_id, kind, payload, created_at, updated_at)
SELECT j.id, j.workspace_id, 'assessments',
  jsonb_build_object(
    'id', j.id, 'job_id', j.id, 'workspace_id', j.workspace_id,
    'subject_id', j.payload::jsonb ->> 'subject_id',
    'profile', COALESCE(j.payload::jsonb ->> 'profile', 'default'),
    'schema_version', '2026-01', 'status', j.status,
    'result', j.result::jsonb, 'error', j.error
  )::text, j.created_at, j.updated_at
FROM agent_trust_jobs j WHERE j.kind = 'assessment'
ON CONFLICT (id) DO UPDATE SET
  payload = (agent_trust_records.payload::jsonb || EXCLUDED.payload::jsonb)::text,
  updated_at = EXCLUDED.updated_at
WHERE agent_trust_records.kind = 'assessments'
  AND agent_trust_records.workspace_id = EXCLUDED.workspace_id;
