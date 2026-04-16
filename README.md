<div align="center">

<img src="https://img.shields.io/badge/status-active%20dev-FFB800?style=flat-square&labelColor=0A0E1A" alt="status">
<img src="https://img.shields.io/badge/version-0.4.0--alpha-FF4444?style=flat-square&labelColor=0A0E1A" alt="version">
<img src="https://img.shields.io/badge/license-MIT-6B7A99?style=flat-square&labelColor=0A0E1A" alt="license">
<img src="https://img.shields.io/badge/python-3.10%2B-3572A5?style=flat-square&logo=python&logoColor=white&labelColor=0A0E1A" alt="python">
<img src="https://img.shields.io/badge/node-18%2B-339933?style=flat-square&logo=node.js&logoColor=white&labelColor=0A0E1A" alt="node">
<img src="https://img.shields.io/badge/PRs-welcome-00FF9C?style=flat-square&labelColor=0A0E1A" alt="prs welcome">

# 🐠 Koi Security Extensions

**Experimental security tooling for AI agents — built on top of Palo Alto Networks Koi.**

Four dev-stage tools: blast radius mapping, behavioral anomaly detection, AI code provenance, and MCP server trust scoring.

> ⚠️ This is a work in progress. APIs will change. Mock data is hardcoded in several places. Use in dev/lab environments only.

[Blast Radius →](https://www.perplexity.ai/computer/a/koi-blast-radius-visualizer-r2Pz6fQdT0yzaXS2Ne7Lsg) · [Behavior Baseline →](https://www.perplexity.ai/computer/a/koi-behavior-baseline-monitor-S8UY.9XZQ9aq52ZOwYZE3A) · [Code Provenance →](https://www.perplexity.ai/computer/a/koi-code-provenance-tracker-n49zbDo3R0uEZ.B_LzebaQ) · [MCP Scorecard →](https://www.perplexity.ai/computer/a/koi-mcp-trust-scorecard-3hfsJodeRKSzLa9PeUpZ2g)

</div>

---

## What's in here

Four standalone React + FastAPI apps that each tackle a different slice of AI agent security. They share a design system and nav but run on separate ports — no monorepo magic, just folders.

### App 1 — Blast Radius Visualizer
Input an agent's permissions and integrations, get a D3 force graph showing everything it can reach and a blast radius score (0–100). Gemini generates an attack narrative if you have an API key.

### App 2 — Behavior Baseline Monitor
30 days of mock behavioral data for 5 agents (Claude Code, Copilot, Cursor, AutoGPT, Custom). Z-score anomaly detection flags deviations. Gemini classifies anomaly clusters. Live feed simulates new events every 5s.

### App 3 — Code Provenance Tracker
Paste code, upload a file, or drop a zip. Heuristic pattern matching (no API needed) tries to attribute code to Claude / GPT-4 / Gemini / Copilot / Human. Security scanner checks for secrets, SQLi, eval, shell injection, etc. Gemini gives an APPROVE / REVIEW / REJECT verdict.

### App 4 — MCP Server Trust Scorecard
Scan an MCP server by URL or paste a manifest. Scores 6 dimensions weighted into an overall trust rating. AbuseIPDB checks domains. Gemini analyzes tool definitions for suspicious intent.

---

## Project layout

```
koi-security-extensions/
├── shared/
│   └── design-tokens.js
├── app1-blast-radius/
│   ├── frontend/          # Vite dev server → :5173
│   └── backend/           # FastAPI         → :8001
├── app2-behavior-baseline/
│   ├── frontend/          # Vite dev server → :5174
│   └── backend/           # FastAPI         → :8002
├── app3-code-provenance/
│   ├── frontend/          # Vite dev server → :5175
│   └── backend/           # FastAPI         → :8003
├── app4-mcp-scorecard/
│   ├── frontend/          # Vite dev server → :5176
│   └── backend/           # FastAPI         → :8004
├── .env.example
└── README.md
```

---

## Stack

- **Frontend:** React 18 + Tailwind CSS 3 + Vite 5
- **Backend:** FastAPI + Python 3.10+, async via httpx
- **AI:** Gemini 2.0 Flash (`google-generativeai`) — optional, degrades gracefully
- **Threat intel:** AbuseIPDB — optional, degrades gracefully
- **Graphs:** D3.js v7
- **Charts:** Recharts
- **Syntax highlighting:** highlight.js
- **PDF export:** jsPDF + html2canvas

---

## Running locally

### 1. Env setup

```bash
cp .env.example .env
# Fill in GEMINI_API_KEY and/or ABUSEIPDB_API_KEY if you have them
# Both are optional — apps note skipped checks in the UI
```

### 2. Backends (4 terminals)

```bash
cd app1-blast-radius/backend   && pip install -r requirements.txt && cp ../../.env .env && uvicorn main:app --reload --port 8001
cd app2-behavior-baseline/backend && pip install -r requirements.txt && cp ../../.env .env && uvicorn main:app --reload --port 8002
cd app3-code-provenance/backend   && pip install -r requirements.txt && cp ../../.env .env && uvicorn main:app --reload --port 8003
cd app4-mcp-scorecard/backend     && pip install -r requirements.txt && cp ../../.env .env && uvicorn main:app --reload --port 8004
```

### 3. Frontends (4 more terminals)

```bash
cd app1-blast-radius/frontend   && npm install && npm run dev -- --port 5173
cd app2-behavior-baseline/frontend && npm install && npm run dev -- --port 5174
cd app3-code-provenance/frontend   && npm install && npm run dev -- --port 5175
cd app4-mcp-scorecard/frontend     && npm install && npm run dev -- --port 5176
```

---

## API keys

| Key | Used by | Get it |
|---|---|---|
| `GEMINI_API_KEY` | All 4 apps (AI analysis) | [aistudio.google.com](https://aistudio.google.com/app/apikey) |
| `ABUSEIPDB_API_KEY` | App 2, App 4 (domain checks) | [abuseipdb.com/register](https://www.abuseipdb.com/register) |

---

## Known issues / TODO

- [ ] App 2 mock data is seeded — `/ingest` endpoint doesn't persist state between restarts
- [ ] App 3 zip scan has no file size limit yet
- [ ] App 1 graph layout can get crowded with >15 nodes
- [ ] No Docker Compose yet — running 8 processes manually is annoying
- [ ] Nav links between apps are `href="#"` placeholders — needs a proper launcher or shared shell
- [ ] Tests: basically none

---

## Integration targets

Designed to eventually wire into **Palo Alto Networks Prisma AIRS** and **Cortex XDR** — but that plumbing doesn't exist yet. The JSON response shapes are modeled after what those APIs expect.

---

## Contributing

Open an issue or just send a PR. No formal process right now.

```bash
# Backend — type hints on all public functions, graceful degradation required for any external API call
# Frontend — Tailwind only, no inline styles, no new dependencies without a good reason
```

---

<sub>MIT · Part of the Koi platform exploration · Not affiliated with or endorsed by Palo Alto Networks</sub>
