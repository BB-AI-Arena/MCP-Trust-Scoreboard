# Local POC Model

This document covers everything you need to run Koi Security Extensions on a developer machine using Docker Compose. The local POC is designed to be a fully functional evaluation environment — not a toy demo.

---

## Purpose

The local POC gives security engineers, architects, and evaluators a way to:

- Run all four tools against real data without any cloud infrastructure
- Validate scan output and scoring logic end-to-end
- Explore the codebase in a working environment before committing to an enterprise deployment
- Demo the product to stakeholders without requiring a live cloud environment

The local model maps directly to the enterprise architecture — same code, same APIs, same behavior. The difference is the runtime envelope: Docker Compose on a laptop vs. ECS/EKS on AWS.

---

## Stack

| Service | Local Component | Enterprise Equivalent |
|---|---|---|
| `frontend` | Nginx-served Vite build (×4 apps) | S3 + CloudFront |
| `api-blast` | FastAPI, port 8001 | ECS Fargate service |
| `api-baseline` | FastAPI, port 8002 | ECS Fargate service |
| `api-provenance` | FastAPI, port 8003 | ECS Fargate service |
| `api-scorecard` | FastAPI, port 8004 | ECS Fargate service |
| `worker` | Python job processor | ECS worker service (SQS consumer) |
| `postgres` | PostgreSQL 15 | Amazon RDS (PostgreSQL) |
| `redis` | Redis 7 | Amazon ElastiCache (Redis) |

The worker service processes async scan jobs. In the local model it polls a Redis queue directly. In enterprise it consumes from SQS — the job schema is identical.

---

## Prerequisites

- Docker Desktop 4.x or Docker Engine 24+ with Compose v2
- 8 GB RAM recommended (all services running simultaneously)
- Ports 5173–5176 and 8001–8004 free on localhost

Optional (both degrade gracefully if missing):
- Gemini API key — [aistudio.google.com](https://aistudio.google.com/app/apikey)
- AbuseIPDB API key — [abuseipdb.com/register](https://www.abuseipdb.com/register)

---

## Environment Setup

```bash
git clone https://github.com/BB-AI-Arena/MCP-Trust-Scoreboard.git
cd MCP-Trust-Scoreboard

cp .env.example .env
```

Edit `.env` and fill in:

```env
# Required — set to anything locally, used for JWT signing
SECRET_KEY=dev-secret-change-in-production

# Optional — AI analysis features degrade gracefully without these
GEMINI_API_KEY=
ABUSEIPDB_API_KEY=

# These are set automatically by Docker Compose — override only if needed
POSTGRES_USER=koi
POSTGRES_PASSWORD=koi_dev_password
POSTGRES_DB=koi_security
DATABASE_URL=postgresql://koi:koi_dev_password@postgres:5432/koi_security
REDIS_URL=redis://redis:6379/0
```

---

## Starting the Stack

```bash
# Build and start everything
docker compose up --build

# Or run detached
docker compose up --build -d

# Follow logs for a specific service
docker compose logs -f api-scorecard
```

First startup takes 2–3 minutes while images build and dependencies install.

---

## Port Map

| Service | URL |
|---|---|
| Blast Radius Visualizer | http://localhost:5173 |
| Behavior Baseline Monitor | http://localhost:5174 |
| Code Provenance Tracker | http://localhost:5175 |
| MCP Trust Scorecard | http://localhost:5176 |
| Blast Radius API | http://localhost:8001 |
| Behavior Baseline API | http://localhost:8002 |
| Code Provenance API | http://localhost:8003 |
| MCP Scorecard API | http://localhost:8004 |
| PostgreSQL | localhost:5432 |
| Redis | localhost:6379 |

---

## How a Scan Flows Through the System

```
Browser (localhost:517x)
  └── POST /scan  →  API service (FastAPI)
        ├── Validate request
        ├── Enqueue job  →  Redis (list: koi:scan:queue)
        │     └── Worker polls queue
        │           ├── Run scoring logic
        │           ├── Call Gemini API (if key present)
        │           ├── Call AbuseIPDB (if key present)
        │           └── Write result  →  PostgreSQL + Redis cache
        └── Return job_id to browser
              └── Browser polls GET /scan/{job_id}
                    └── Returns cached result from Redis / DB
```

For the POC, the API also supports a synchronous mode (`?sync=true`) that runs the scan inline without enqueueing — useful for development and debugging.

---

## Synchronous vs. Async Mode

Both modes are supported locally:

| Mode | How | When to use |
|---|---|---|
| Sync | `POST /scan?sync=true` | Development, single scans, debugging |
| Async | `POST /scan` (default) | Normal usage, mirrors enterprise behavior |

The frontend defaults to async. Set `SCAN_MODE=sync` in `.env` to flip the frontend default during local development.

---

## Optional API Keys — Graceful Degradation

When keys are missing, each check degrades gracefully and surfaces a note in the scan result:

| Missing Key | Behavior |
|---|---|
| `GEMINI_API_KEY` | AI narrative, tool analysis, and verdict fields return a `"Gemini unavailable"` placeholder. All rule-based scoring still runs. |
| `ABUSEIPDB_API_KEY` | Domain threat intelligence is skipped. Domains are still extracted and listed but not checked against abuse databases. Network behavior score defaults to 50. |

All other scoring dimensions function fully without either key.

---

## Stopping and Resetting

```bash
# Stop all services
docker compose down

# Stop and delete all data volumes (full reset)
docker compose down -v

# Rebuild a single service after code change
docker compose up --build api-scorecard
```

---

## Troubleshooting

**Port already in use**
```bash
lsof -i :8001   # find what's using the port
kill -9 <PID>
```

**Worker not picking up jobs**
```bash
docker compose logs -f worker
# Check REDIS_URL is set correctly in .env
```

**Postgres connection refused**
```bash
docker compose ps postgres
# If not running: docker compose up postgres
# Check DATABASE_URL matches POSTGRES_USER/PASSWORD/DB in .env
```

**Frontend shows blank page**
The frontends are React SPAs — they require JavaScript to render. If the page is blank, open browser DevTools → Console and check for API connection errors. Confirm the API service is running on the expected port.

**Gemini returns empty results**
Check `GEMINI_API_KEY` is set in `.env` and that the `.env` file was present when the container started (`docker compose up --build` to force a rebuild).

---

## Mapping Local to AWS

When you're ready to move beyond the POC, every local component has a direct AWS analog:

| Local | AWS |
|---|---|
| `postgres` container | Amazon RDS for PostgreSQL (Multi-AZ) |
| `redis` container | Amazon ElastiCache for Redis (cluster mode) |
| `worker` container | ECS Fargate task (SQS consumer) |
| `api-*` containers | ECS Fargate services behind ALB |
| `frontend-*` containers | Static assets on S3, served via CloudFront |
| Docker Compose network | VPC with private subnets |
| `.env` file | AWS Secrets Manager + Parameter Store |

See [ENTERPRISE_ARCHITECTURE.md](./ENTERPRISE_ARCHITECTURE.md) for the full AWS reference architecture.
