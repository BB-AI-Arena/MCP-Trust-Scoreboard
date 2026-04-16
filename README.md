<div align="center">

<img src="https://img.shields.io/badge/version-2.4.1-00D4FF?style=for-the-badge&labelColor=0A0E1A" alt="version">
<img src="https://img.shields.io/badge/license-MIT-00FF9C?style=for-the-badge&labelColor=0A0E1A" alt="license">
<img src="https://img.shields.io/badge/python-3.10%2B-00D4FF?style=for-the-badge&logo=python&logoColor=white&labelColor=0A0E1A" alt="python">
<img src="https://img.shields.io/badge/node-18%2B-00FF9C?style=for-the-badge&logo=node.js&logoColor=white&labelColor=0A0E1A" alt="node">
<img src="https://img.shields.io/badge/react-18-00D4FF?style=for-the-badge&logo=react&logoColor=white&labelColor=0A0E1A" alt="react">
<img src="https://img.shields.io/badge/fastapi-0.111-00FF9C?style=for-the-badge&logo=fastapi&logoColor=white&labelColor=0A0E1A" alt="fastapi">

<br/><br/>

<img src="https://img.shields.io/badge/gemini-2.0%20flash-FFB800?style=for-the-badge&logo=google&logoColor=white&labelColor=0A0E1A" alt="gemini">
<img src="https://img.shields.io/badge/AbuseIPDB-threat%20intel-FF4444?style=for-the-badge&labelColor=0A0E1A" alt="abuseipdb">
<img src="https://img.shields.io/badge/Prisma%20AIRS-integrated-FF0066?style=for-the-badge&labelColor=0A0E1A" alt="prisma airs">
<img src="https://img.shields.io/badge/Cortex%20XDR-integrated-FF0066?style=for-the-badge&labelColor=0A0E1A" alt="cortex xdr">

<br/><br/>

# 🐠 Koi Security Extensions

**Enterprise AI agent security tooling for the Palo Alto Networks Koi platform.**

Four production tools that map agent blast radius, detect behavioral anomalies, audit AI-generated code, and gate MCP server trust — all wired into Prisma AIRS and Cortex XDR.

[Live Demo — Blast Radius](https://www.perplexity.ai/computer/a/koi-blast-radius-visualizer-r2Pz6fQdT0yzaXS2Ne7Lsg) · [Behavior Baseline](https://www.perplexity.ai/computer/a/koi-behavior-baseline-monitor-S8UY.9XZQ9aq52ZOwYZE3A) · [Code Provenance](https://www.perplexity.ai/computer/a/koi-code-provenance-tracker-n49zbDo3R0uEZ.B_LzebaQ) · [MCP Scorecard](https://www.perplexity.ai/computer/a/koi-mcp-trust-scorecard-3hfsJodeRKSzLa9PeUpZ2g)

</div>

---

## Why This Exists

AI agents are eating enterprise infrastructure. They write code, query databases, call APIs, hold credentials, and operate autonomously across blast radii that would have required full red-team engagements to map two years ago.

Koi Security Extensions is a set of four lightweight, self-hostable tools built to answer the questions that existing EDR and SIEM platforms aren't asking yet:

- **What can this agent reach if it's compromised right now?**
- **Is this agent behaving the way it did last week?**
- **Who wrote this code — a human, or a hallucinating model with a SQL injection problem?**
- **Should we trust this MCP server enough to let our agents connect to it?**

Each tool runs independently. Together they form a continuous AI security posture layer on top of the Koi platform.

---

## The Suite

| | Tool | What It Does |
|---|---|---|
| 🔴 | **Blast Radius Visualizer** | D3 force graph mapping every system, credential, and API an agent can reach. Scores 0–100 (Contained → Catastrophic). |
| 🟡 | **Behavior Baseline Monitor** | Z-score anomaly detection across 5 behavioral metrics. Gemini classifies clusters as DataExfiltration / LateralMovement / PrivilegeEscalation / BenignDrift. |
| 🟣 | **Vibe Code Provenance Tracker** | 40-rule heuristic detector for AI model attribution (Claude / GPT-4 / Gemini / Copilot / Human). 21-rule security scanner runs in parallel. No external API needed for detection. |
| 🔵 | **MCP Server Trust Scorecard** | 6-dimension weighted trust score for any MCP server manifest. AbuseIPDB domain checks + Gemini tool intent analysis. |

---

## Architecture

```
koi-security-extensions/
├── shared/
│   └── design-tokens.js              # Single source of truth for colors/typography
├── app1-blast-radius/
│   ├── frontend/                      # React + Vite  →  :5173
│   └── backend/                       # FastAPI        →  :8001
│       ├── main.py
│       ├── graph_builder.py           # NetworkX directed graph + BFS reach scoring
│       ├── risk_scorer.py             # Blast radius 0-100 + path analysis
│       └── gemini_analyzer.py         # Attack narrative + mitigations
├── app2-behavior-baseline/
│   ├── frontend/                      # React + Vite  →  :5174
│   └── backend/                       # FastAPI        →  :8002
│       ├── main.py
│       ├── mock_data.py               # 30-day seeded behavioral data, 5 agents
│       ├── baseline_engine.py         # Mean/stddev baseline builder
│       ├── anomaly_detector.py        # Z-score detection, 6 anomaly types
│       └── gemini_analyzer.py         # Cluster classification
├── app3-code-provenance/
│   ├── frontend/                      # React + Vite  →  :5175
│   └── backend/                       # FastAPI        →  :8003
│       ├── main.py
│       ├── provenance_detector.py     # 40-pattern heuristic AI model attribution
│       ├── code_risk_scanner.py       # 21-rule security vulnerability scanner
│       └── gemini_analyzer.py         # APPROVE / REVIEW / REJECT verdict
├── app4-mcp-scorecard/
│   ├── frontend/                      # React + Vite  →  :5176
│   └── backend/                       # FastAPI        →  :8004
│       ├── main.py
│       ├── domain_checker.py          # AbuseIPDB domain threat intel
│       ├── scorer.py                  # 6-dimension weighted scoring engine
│       └── gemini_analyzer.py         # Tool definition intent analysis
├── .env.example
└── README.md
```

---

## Stack

| Layer | Technology |
|---|---|
| Frontend | React 18, Tailwind CSS 3, Vite 5 |
| Backend | FastAPI, Python 3.10+, uvicorn |
| Async HTTP | httpx |
| AI Analysis | Google Gemini 2.0 Flash (`google-generativeai`) |
| Threat Intel | AbuseIPDB `/v2/check` |
| Graph Visualization | D3.js v7 (force-directed, treemap) |
| Charts | Recharts |
| Code Highlighting | highlight.js (Atom One Dark) |
| PDF Export | jsPDF + html2canvas |
| Graph Computation | NetworkX |
| Numerical Analysis | NumPy |

---

## Getting Started

### Prerequisites

- Python 3.10+
- Node.js 18+
- (Optional) Gemini API key — [Google AI Studio](https://aistudio.google.com/app/apikey)
- (Optional) AbuseIPDB key — [abuseipdb.com/register](https://www.abuseipdb.com/register)

> Both keys are optional. All four apps degrade gracefully — skipped checks are surfaced in the UI as informational flags, not silent failures.

### 1. Environment

```bash
git clone https://github.com/BB-AI-Arena/MCP-Trust-Scoreboard.git
cd MCP-Trust-Scoreboard

cp .env.example .env
# Add your keys — or leave blank for graceful degradation
```

### 2. Backends

```bash
# Blast Radius  — :8001
cd app1-blast-radius/backend
pip install -r requirements.txt && cp ../../.env .env
uvicorn main:app --reload --port 8001

# Behavior Baseline  — :8002
cd app2-behavior-baseline/backend
pip install -r requirements.txt && cp ../../.env .env
uvicorn main:app --reload --port 8002

# Code Provenance  — :8003
cd app3-code-provenance/backend
pip install -r requirements.txt && cp ../../.env .env
uvicorn main:app --reload --port 8003

# MCP Scorecard  — :8004
cd app4-mcp-scorecard/backend
pip install -r requirements.txt && cp ../../.env .env
uvicorn main:app --reload --port 8004
```

### 3. Frontends

```bash
cd app1-blast-radius/frontend   && npm install && npm run dev -- --port 5173
cd app2-behavior-baseline/frontend && npm install && npm run dev -- --port 5174
cd app3-code-provenance/frontend   && npm install && npm run dev -- --port 5175
cd app4-mcp-scorecard/frontend     && npm install && npm run dev -- --port 5176
```

| App | URL |
|---|---|
| Blast Radius Visualizer | http://localhost:5173 |
| Behavior Baseline Monitor | http://localhost:5174 |
| Code Provenance Tracker | http://localhost:5175 |
| MCP Trust Scorecard | http://localhost:5176 |

---

## API Reference

### App 1 — Blast Radius (`:8001`)

```http
POST /analyze
Content-Type: application/json

{
  "agent_name": "GPT-4 Code Assistant",
  "permissions": ["read_files", "write_files", "execute_code", "access_env_vars"],
  "integrations": ["github", "s3", "openai_api", "postgres_db"],
  "endpoint_type": "code"
}
```

```json
{
  "blast_rating": "Severe",
  "overall_score": 78,
  "nodes": [{ "id": "agent-0", "type": "Agent", "label": "GPT-4 Code Assistant", "criticality": "low", "x": 0, "y": 0 }],
  "edges": [{ "source": "agent-0", "target": "cred-1", "type": "Authenticate" }],
  "critical_paths": [["agent-0", "cred-1", "db-2"]],
  "attack_narrative": "If this agent were compromised, an attacker could...",
  "mitigations": ["Revoke write access to S3", "Rotate env var credentials", "Scope DB user to read-only"]
}
```

### App 2 — Behavior Baseline (`:8002`)

```http
GET  /agents
GET  /baseline/{agent_id}
GET  /anomalies/{agent_id}
GET  /summary/{agent_id}
GET  /agent-data/{agent_id}
POST /ingest
```

### App 3 — Code Provenance (`:8003`)

```http
POST /scan
Content-Type: application/json

{ "code": "...", "language": "python", "filename": "utils.py" }
```

```http
POST /scan-repo
Content-Type: multipart/form-data

file=@repo.zip
```

### App 4 — MCP Scorecard (`:8004`)

```http
POST /scan
Content-Type: application/json

{ "url": "https://mcp-server.example.com/manifest.json" }
```

```json
{
  "overall_score": 72,
  "trust_rating": "Medium",
  "dimensions": {
    "identity":           { "score": 80, "explanation": "Publisher identity verified" },
    "permission_sprawl":  { "score": 60, "explanation": "3 excess permissions detected" },
    "network_behavior":   { "score": 75, "explanation": "All domains resolved cleanly" },
    "code_transparency":  { "score": 50, "explanation": "Source available, no audit" },
    "version_drift":      { "score": 85, "explanation": "Stable version history" },
    "community_signal":   { "score": 65, "explanation": "Low install count" }
  },
  "flags": [],
  "gemini_summary": "...",
  "scanned_at": "2026-04-16T17:00:00Z"
}
```

---

## Enterprise Integration

### Prisma AIRS

- Block `Untrusted` MCP servers from agent runtime connections
- Enforce agent permission caps derived from blast radius scores
- Auto-quarantine agents exhibiting `DataExfiltration` behavioral classification

### Cortex XDR

- Anomaly alerts → XDR incidents with MITRE ATT&CK tactic mapping
- Code Provenance `REJECT` verdicts → threat indicators for the file hash
- Blast Radius `Catastrophic` scores → asset risk context on the endpoint record

### CI/CD Gate Pattern

```
PR opened
  └── Code Provenance /scan
        ├── risk > Medium     → block merge, require security review
        └── REJECT verdict    → auto-close PR

Agent deployment
  └── Blast Radius /analyze
        └── score > 75        → require manual approval before deploy

MCP server added to registry
  └── MCP Scorecard /scan
        └── trust_rating < Medium  → reject integration, log to SIEM

Agent runtime (continuous)
  └── Behavior Baseline /ingest
        └── anomaly detected   → POST to Cortex XDR /incidents/create
```

---

## Scoring Reference

### Blast Radius (App 1)

| Score | Rating | Meaning |
|---|---|---|
| 0–25 | Contained | Agent has minimal reach; compromise is bounded |
| 26–50 | Moderate | Meaningful lateral movement possible |
| 51–75 | Severe | Multi-system compromise likely; credentials reachable |
| 76–100 | Catastrophic | Full environment compromise possible |

### MCP Trust Score (App 4)

| Dimension | Weight | Scoring Logic |
|---|---|---|
| Network Behavior | 25% | −20 per flagged domain, −10 per unresolvable |
| Permission Sprawl | 20% | −15 per permission exceeding 3× tool count |
| Identity | 20% | Verified org=90, named=60, anonymous=25 |
| Code Transparency | 15% | Audited=95, source only=50, none=20 |
| Version Drift | 10% | Stable=85, silent perm add=20, no history=50 |
| Community Signal | 10% | −20 if age<30d, −20 if installs<100, −30 if CVEs |

---

## Contributing

Pull requests are welcome. For major changes, open an issue first.

**Code style:**
- Python: type hints on all public functions, graceful degradation required for any external API call
- JSX: Tailwind classes only, no inline styles
- New Gemini prompts must request `ONLY valid JSON` and include fallback parsing

---

## Roadmap

- [ ] Docker Compose for single-command suite startup
- [ ] Unified dashboard aggregating findings across all four tools
- [ ] Webhook support for Cortex XDR incident auto-creation
- [ ] GitHub Action for Code Provenance CI/CD gating
- [ ] SARIF output for Code Provenance scanner
- [ ] MCP registry bulk scan (CSV input)
- [ ] Agent behavior policy-as-code (YAML rules)

---

## License

MIT © 2026

---

<div align="center">
<sub>Built as an extension layer for <strong>Palo Alto Networks Koi Agentic Endpoint Security</strong> · Integrates with Prisma AIRS and Cortex XDR</sub>
</div>
