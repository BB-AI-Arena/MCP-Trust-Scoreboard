# Local/self-hosted quickstart

Agent Trust Platform is a single-tenant local/self-hosted alpha. The Compose
stack retains the four original visual workspaces and adds the namespaced API
on port 8080.

## Start

```bash
cp .env.example .env
# Replace AGENT_TRUST_API_TOKEN and SECRET_KEY with local random values.
docker compose up --build
```

The existing `postgres_data` and `redis_data` volumes are preserved. Do not
use them for destructive experiments. PostgreSQL stores namespaced records and
jobs; Redis supports only the legacy apps and is disposable cache/queue state.

## Service map

| Service | Port | Role |
| --- | ---: | --- |
| Agent Trust Platform API | 8080 | Authenticated `/api/v1` migration API |
| Legacy blast radius | 8001 / 5173 | Agent Access / Blast Radius workspace |
| Legacy behavior | 8002 / 5174 | Behavior Monitoring compatibility workspace |
| Legacy artifact | 8003 / 5175 | Code and Artifact Assurance compatibility workspace |
| Legacy scorecard | 8004 / 5176 | Tool and Connector Trust compatibility workspace |
| PostgreSQL | 5432 | Durable state |
| Redis | 6379 | Legacy queue/cache only |

## API smoke test

```bash
TOKEN='the-value-used-for-AGENT_TRUST_API_TOKEN'
curl http://127.0.0.1:8080/health
curl -H "Authorization: Bearer $TOKEN" http://127.0.0.1:8080/api/v1/capabilities
curl -X POST http://127.0.0.1:8080/api/v1/assessments \
  -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -H 'Idempotency-Key: local-check-1' \
  -d '{"subject_id":"agent-1","profile":"default","content":"review this artifact"}'
```

The assessment returns `202` and a durable job ID. Poll
`/api/v1/jobs/{job_id}`. The modular worker runs rules-only analysis without a
provider key. Gemini, OpenAI-compatible, and AbuseIPDB adapters require
explicit configuration and do not silently replace unavailable coverage.

## Operational safety

Do not expose port 8080 publicly. Set restrictive origins and a random token
before use beyond loopback. The API does not execute submitted source, MCP
tools, or OpenAPI operations. URL collection needs explicit scope for private
targets and must enforce TLS, allowlists, timeouts, and redirect revalidation.
ZIP uploads are bounded and reject traversal/symlink entries.

For backup and rollback, stop writers, take a logical Postgres backup, and
restore into a disposable database before upgrading. Roll back by stopping the
new services and running the prior image against preserved volumes; never
reset or delete the volumes. Expired Redis data cannot be recovered.
