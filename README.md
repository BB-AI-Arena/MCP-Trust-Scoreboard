# 🐠 Koi Security Extensions

**Koi Security Extensions** is a suite of four enterprise AI security tools designed to extend [Palo Alto Networks' Koi Agentic Endpoint Security](https://www.paloaltonetworks.com/) platform. As AI agents proliferate across enterprise environments — writing code, accessing APIs, querying databases, and executing workflows — traditional endpoint security tools fail to address the unique attack surfaces they introduce. Koi Security Extensions fills this gap with four purpose-built instruments: a blast radius visualizer that maps every system an agent can reach, a behavioral baseline monitor that detects anomalous agent activity in real time, a code provenance tracker that identifies AI-generated code and audits it for security risks, and an MCP server trust scorecard that gates access to the Model Context Protocol ecosystem before agents can connect to unknown servers. Together, these tools form a continuous AI security posture layer that integrates directly with **Palo Alto Networks Prisma AIRS** and **Cortex XDR** for enterprise-grade threat response.

---

## The Four Tools

### 🔴 App 1 — Agentic Blast Radius Visualizer
Maps the full attack surface of any AI agent by building a directed graph of every system, dataset, API, and credential it can reach. If an agent is compromised, the blast radius shows the exact scope of potential damage — from a single file system to cross-cloud credential chains. Enterprise security teams use it to enforce least-privilege during agent onboarding and to model compromise scenarios before deployment.

### 🟡 App 2 — AI Agent Behavior Baseline Monitor
Establishes statistical behavioral baselines for AI agents across five metrics (API call rate, file access, network destinations, execution time, active hours) and flags deviations in real time using Z-score anomaly detection. Gemini AI classifies anomaly clusters as DataExfiltration, LateralMovement, PrivilegeEscalation, or BenignDrift — giving SOC teams an actionable classification, not just a raw alert.

### 🟣 App 3 — Vibe Code Provenance Tracker
Detects which AI model generated any given code snippet by analyzing stylistic markers (comment patterns, naming conventions, structural idioms) without requiring a separate AI API call. Simultaneously scans for security vulnerabilities — hardcoded secrets, SQL injection, eval usage, shell injection, and more. Designed for security-gating AI-assisted PRs in enterprise CI/CD pipelines.

### 🔵 App 4 — MCP Server Trust Scorecard
Analyzes any Model Context Protocol server manifest and produces a weighted trust score across six dimensions: publisher identity, permission sprawl, network behavior, code transparency, version drift, and community signal. Powered by AbuseIPDB domain threat intelligence and Gemini AI for tool definition analysis. Enterprise teams use it as a pre-integration gate before connecting MCP servers to production AI agents.

---

## Architecture

```
koi-security-extensions/
├── shared/
│   └── design-tokens.js          # Shared color/typography tokens
├── app1-blast-radius/
│   ├── frontend/                  # React + Vite (port 5173)
│   └── backend/                   # FastAPI (port 8001)
├── app2-behavior-baseline/
│   ├── frontend/                  # React + Vite (port 5174)
│   └── backend/                   # FastAPI (port 8002)
├── app3-code-provenance/
│   ├── frontend/                  # React + Vite (port 5175)
│   └── backend/                   # FastAPI (port 8003)
├── app4-mcp-scorecard/
│   ├── frontend/                  # React + Vite (port 5176)
│   └── backend/                   # FastAPI (port 8004)
├── .env.example
└── README.md
```

**Tech Stack:**
- Frontend: React 18 + Tailwind CSS 3 + Vite 5
- Backend: FastAPI + Python 3.10+
- AI: Google Gemini 2.0 Flash (`google-generativeai`)
- Threat Intel: AbuseIPDB API
- Charts: Recharts
- Graph Visualization: D3.js v7
- PDF Export: jsPDF + html2canvas
- Syntax Highlighting: highlight.js

---

## Setup

### Prerequisites
- Python 3.10+
- Node.js 18+

### 1. Configure Environment

```bash
cp .env.example .env
# Edit .env and add your API keys
```

Get your keys:
- **Gemini**: [Google AI Studio](https://aistudio.google.com/app/apikey)
- **AbuseIPDB**: [abuseipdb.com/register](https://www.abuseipdb.com/register)

Both keys are optional — all four apps degrade gracefully without them.

### 2. Run All Backends

Open four terminal tabs:

```bash
# Terminal 1 — Blast Radius
cd app1-blast-radius/backend
pip install -r requirements.txt
cp ../../.env .env
uvicorn main:app --reload --port 8001

# Terminal 2 — Behavior Baseline
cd app2-behavior-baseline/backend
pip install -r requirements.txt
cp ../../.env .env
uvicorn main:app --reload --port 8002

# Terminal 3 — Code Provenance
cd app3-code-provenance/backend
pip install -r requirements.txt
cp ../../.env .env
uvicorn main:app --reload --port 8003

# Terminal 4 — MCP Scorecard
cd app4-mcp-scorecard/backend
pip install -r requirements.txt
cp ../../.env .env
uvicorn main:app --reload --port 8004
```

### 3. Run All Frontends

Open four more terminal tabs:

```bash
# Terminal 5
cd app1-blast-radius/frontend && npm install && npm run dev -- --port 5173

# Terminal 6
cd app2-behavior-baseline/frontend && npm install && npm run dev -- --port 5174

# Terminal 7
cd app3-code-provenance/frontend && npm install && npm run dev -- --port 5175

# Terminal 8
cd app4-mcp-scorecard/frontend && npm install && npm run dev -- --port 5176
```

Access the apps at:
- Blast Radius: http://localhost:5173
- Behavior Baseline: http://localhost:5174
- Code Provenance: http://localhost:5175
- MCP Scorecard: http://localhost:5176

---

## Enterprise Integration

All four tools are designed as security primitives for the Palo Alto Networks ecosystem:

### Prisma AIRS Integration
Feed scorecard and blast radius JSON into Prisma AIRS policy engine to:
- Block `Untrusted` MCP servers at runtime
- Enforce agent permission boundaries based on blast radius analysis
- Auto-quarantine agents exhibiting DataExfiltration behavioral patterns

### Cortex XDR Integration
Stream findings to Cortex XDR for SOC visibility:
- Anomaly alerts from Behavior Baseline Monitor as XDR incidents
- Code Provenance risk findings as threat indicators
- Blast Radius scores as asset risk context for endpoint protection

### CI/CD Gate Pattern
```
PR opened → Code Provenance scan → risk > Medium → block merge
Agent deployment → Blast Radius check → score > 75 → require review
MCP server added → Trust Scorecard → rating < Medium → auto-reject
Agent runtime → Behavior Baseline → anomaly detected → Cortex XDR alert
```

---

## API Reference

| App | Endpoint | Method | Description |
|-----|----------|--------|-------------|
| Blast Radius | `/analyze` | POST | Analyze agent blast radius |
| Blast Radius | `/health` | GET | Health check |
| Behavior Baseline | `/agents` | GET | List all agents |
| Behavior Baseline | `/baseline/{id}` | GET | Get agent baseline |
| Behavior Baseline | `/anomalies/{id}` | GET | Get agent anomalies |
| Behavior Baseline | `/summary/{id}` | GET | Gemini classification |
| Code Provenance | `/scan` | POST | Scan code snippet |
| Code Provenance | `/scan-repo` | POST | Scan zip repo |
| Code Provenance | `/languages` | GET | Supported languages |
| MCP Scorecard | `/scan` | POST | Scan MCP server |
| MCP Scorecard | `/health` | GET | Health check |

---

## License

MIT
