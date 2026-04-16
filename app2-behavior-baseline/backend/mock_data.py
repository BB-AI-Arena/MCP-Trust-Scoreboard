"""
mock_data.py
Rich mock data for 5 AI agents with 30 days of behavioral data.
Last 3 days contain pre-seeded anomalies per agent.
"""

import random
from datetime import datetime, timedelta, timezone
from typing import Optional

# ---------------------------------------------------------------------------
# Agent definitions
# ---------------------------------------------------------------------------
AGENTS = [
    {"id": "claude-code", "name": "Claude Code", "status": "active"},
    {"id": "copilot", "name": "GitHub Copilot", "status": "active"},
    {"id": "cursor", "name": "Cursor", "status": "active"},
    {"id": "autogpt", "name": "AutoGPT", "status": "warning"},
    {"id": "custom-agent", "name": "Custom Agent", "status": "critical"},
]

AGENT_DISPLAY_NAMES = {
    "claude-code": "Claude Code",
    "copilot": "GitHub Copilot",
    "cursor": "Cursor",
    "autogpt": "AutoGPT",
    "custom-agent": "Custom Agent",
}

# ---------------------------------------------------------------------------
# Per-agent baseline characteristics (used to generate normal data)
# ---------------------------------------------------------------------------
AGENT_PROFILES = {
    "claude-code": {
        "api_call_rate_base": 45,
        "api_call_rate_std": 8,
        "file_access_base": 18,
        "file_access_std": 4,
        "execution_time_base": 320.0,
        "execution_time_std": 55.0,
        "credential_access_base": 0,
        "credential_access_p": 0.10,   # probability of any credential access per day
        "normal_hours": list(range(8, 19)),
        "normal_domains": [
            "api.anthropic.com",
            "github.com",
            "raw.githubusercontent.com",
            "pypi.org",
            "files.pythonhosted.org",
            "registry.npmjs.org",
            "cdn.jsdelivr.net",
            "avatars.githubusercontent.com",
        ],
        "anomaly_domain": "exfil-c2.io",
    },
    "copilot": {
        "api_call_rate_base": 62,
        "api_call_rate_std": 10,
        "file_access_base": 24,
        "file_access_std": 5,
        "execution_time_base": 210.0,
        "execution_time_std": 40.0,
        "credential_access_base": 1,
        "credential_access_p": 0.15,
        "normal_hours": list(range(9, 18)),
        "normal_domains": [
            "copilot.microsoft.com",
            "api.github.com",
            "github.com",
            "vscode-cdn.net",
            "marketplace.visualstudio.com",
            "raw.githubusercontent.com",
            "objects.githubusercontent.com",
        ],
        "anomaly_domain": "data-sink.net",
    },
    "cursor": {
        "api_call_rate_base": 38,
        "api_call_rate_std": 7,
        "file_access_base": 14,
        "file_access_std": 3,
        "execution_time_base": 480.0,
        "execution_time_std": 80.0,
        "credential_access_base": 0,
        "credential_access_p": 0.08,
        "normal_hours": list(range(9, 20)),
        "normal_domains": [
            "api2.cursor.sh",
            "cursor.sh",
            "cdn.cursor.sh",
            "pypi.org",
            "registry.npmjs.org",
            "github.com",
        ],
        "anomaly_domain": "rogue-pipe.cc",
    },
    "autogpt": {
        "api_call_rate_base": 75,
        "api_call_rate_std": 14,
        "file_access_base": 28,
        "file_access_std": 6,
        "execution_time_base": 650.0,
        "execution_time_std": 120.0,
        "credential_access_base": 1,
        "credential_access_p": 0.20,
        "normal_hours": list(range(0, 24)),  # AutoGPT runs 24/7
        "normal_domains": [
            "api.openai.com",
            "google.com",
            "googleapis.com",
            "bing.com",
            "duckduckgo.com",
            "wikipedia.org",
            "github.com",
            "news.ycombinator.com",
            "storage.googleapis.com",
        ],
        "anomaly_domain": "c2-botnet.xyz",
    },
    "custom-agent": {
        "api_call_rate_base": 28,
        "api_call_rate_std": 6,
        "file_access_base": 9,
        "file_access_std": 2,
        "execution_time_base": 760.0,
        "execution_time_std": 100.0,
        "credential_access_base": 0,
        "credential_access_p": 0.05,
        "normal_hours": list(range(10, 17)),
        "normal_domains": [
            "internal.corp.local",
            "api.openai.com",
            "s3.amazonaws.com",
            "sqs.us-east-1.amazonaws.com",
            "secretsmanager.us-east-1.amazonaws.com",
        ],
        "anomaly_domain": "lateral-move.ru",
    },
}

# ---------------------------------------------------------------------------
# Seed for reproducibility
# ---------------------------------------------------------------------------
_RNG = random.Random(42)


def _clamp(val: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, val))


def _normal_int(base: float, std: float, lo: int = 1, hi: int = 9999) -> int:
    return int(_clamp(_RNG.gauss(base, std), lo, hi))


def _normal_float(base: float, std: float, lo: float = 1.0, hi: float = 99999.0) -> float:
    return round(_clamp(_RNG.gauss(base, std), lo, hi), 2)


def _sample_domains(normal_domains: list[str], n: int = None) -> list[str]:
    if n is None:
        n = _RNG.randint(2, min(6, len(normal_domains)))
    k = min(n, len(normal_domains))
    return _RNG.sample(normal_domains, k)


def _sample_hours(normal_hours: list[int]) -> list[int]:
    k = _RNG.randint(max(1, len(normal_hours) - 4), len(normal_hours))
    return sorted(_RNG.sample(normal_hours, k))


def _make_normal_record(agent_id: str, day_index: int, date_str: str) -> dict:
    p = AGENT_PROFILES[agent_id]
    cred = 0
    if _RNG.random() < p["credential_access_p"]:
        cred = _RNG.randint(1, 2)
    return {
        "date": date_str,
        "day_index": day_index,
        "api_call_rate": _normal_int(p["api_call_rate_base"], p["api_call_rate_std"], 5, 200),
        "file_access_count": _normal_int(p["file_access_base"], p["file_access_std"], 1, 100),
        "network_destinations": _sample_domains(p["normal_domains"]),
        "execution_time_ms": _normal_float(p["execution_time_base"], p["execution_time_std"], 50.0, 5000.0),
        "active_hours": _sample_hours(p["normal_hours"]),
        "credential_accesses": cred,
        "is_anomaly_day": False,
    }


def _make_anomaly_records(agent_id: str, day_indices: list[int], dates: list[str]) -> list[dict]:
    """
    Create exactly 3 anomaly-injected records for an agent spread across
    the last 3 days. Each day gets one primary anomaly type.
    """
    p = AGENT_PROFILES[agent_id]
    records = []

    for i, (day_idx, date_str) in enumerate(zip(day_indices, dates)):
        base_record = _make_normal_record(agent_id, day_idx, date_str)
        base_record["is_anomaly_day"] = True

        if i == 0:
            # Anomaly 1: new unknown domain injected into network_destinations
            base_record["network_destinations"] = (
                _sample_domains(p["normal_domains"], 3) + [p["anomaly_domain"]]
            )
            base_record["anomaly_type"] = "NewDomain"
            base_record["anomaly_note"] = f"Unknown domain contacted: {p['anomaly_domain']}"

        elif i == 1:
            # Anomaly 2: file_access_count spike (5-10x normal)
            multiplier = _RNG.uniform(5.0, 10.0)
            base_record["file_access_count"] = int(p["file_access_base"] * multiplier)
            base_record["anomaly_type"] = "FileSpike"
            base_record["anomaly_note"] = (
                f"File access spike: {base_record['file_access_count']} "
                f"vs baseline ~{p['file_access_base']}"
            )

        else:
            # Anomaly 3: credential access at 2am (off-hours)
            base_record["credential_accesses"] = _RNG.randint(3, 6)
            # Make sure hour 2 is in active_hours to signal off-hours activity
            if 2 not in base_record["active_hours"]:
                base_record["active_hours"] = sorted(base_record["active_hours"] + [2])
            base_record["anomaly_type"] = "CredentialAccess"
            base_record["anomaly_note"] = (
                f"Credential access at 02:00 — off-hours for this agent. "
                f"Count: {base_record['credential_accesses']}"
            )

        records.append(base_record)

    return records


# ---------------------------------------------------------------------------
# Build the full dataset (module-level, computed once)
# ---------------------------------------------------------------------------
_DATASET: dict[str, list[dict]] = {}

def _build_dataset() -> None:
    today = datetime.now(tz=timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    for agent in AGENTS:
        aid = agent["id"]
        records = []
        for day_offset in range(30, 0, -1):
            date = today - timedelta(days=day_offset)
            date_str = date.strftime("%Y-%m-%d")
            day_index = 30 - day_offset  # 0..29
            records.append(_make_normal_record(aid, day_index, date_str))

        # Replace last 3 records with anomaly records
        anomaly_day_indices = [27, 28, 29]
        anomaly_dates = [records[i]["date"] for i in anomaly_day_indices]
        anomaly_records = _make_anomaly_records(aid, anomaly_day_indices, anomaly_dates)
        for idx, rec in zip(anomaly_day_indices, anomaly_records):
            records[idx] = rec

        _DATASET[aid] = records


_build_dataset()

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_all_agents() -> list[dict]:
    """Return list of agent dicts with {id, name, status}."""
    return [a.copy() for a in AGENTS]


def get_agent_data(agent_id: str, days: int = 30) -> list[dict]:
    """
    Return up to `days` most-recent daily records for the given agent.
    """
    if agent_id not in _DATASET:
        return []
    data = _DATASET[agent_id]
    return data[-days:] if days < len(data) else data[:]


def get_recent_events(agent_id: str) -> list[dict]:
    """
    Return a synthetic live-feed of recent events for the agent.
    Includes normal activity plus the anomaly events from the last 3 days.
    """
    if agent_id not in _DATASET:
        return []

    p = AGENT_PROFILES[agent_id]
    today = datetime.now(tz=timezone.utc)
    events = []

    # Normal recent events (last 6 hours)
    normal_event_templates = [
        lambda: {
            "type": "api_call",
            "severity": "info",
            "message": f"API call batch: {_normal_int(p['api_call_rate_base'], p['api_call_rate_std'], 1, 200)} calls/hr",
            "domain": _RNG.choice(p["normal_domains"]),
        },
        lambda: {
            "type": "file_access",
            "severity": "info",
            "message": f"File scan: {_normal_int(p['file_access_base'], p['file_access_std'], 1, 100)} files accessed",
            "domain": None,
        },
        lambda: {
            "type": "execution",
            "severity": "info",
            "message": f"Task completed in {_normal_float(p['execution_time_base'], p['execution_time_std'], 50.0, 5000.0)} ms",
            "domain": None,
        },
    ]

    for i in range(8):
        minutes_ago = _RNG.randint(10, 360)
        ts = today - timedelta(minutes=minutes_ago)
        template = _RNG.choice(normal_event_templates)
        ev = template()
        ev["timestamp"] = ts.isoformat()
        ev["agent_id"] = agent_id
        events.append(ev)

    # Anomaly events from last 3 days
    last3 = _DATASET[agent_id][-3:]
    for rec in last3:
        if rec.get("is_anomaly_day"):
            atype = rec.get("anomaly_type", "Unknown")
            severity_map = {
                "NewDomain": "high",
                "FileSpike": "medium",
                "CredentialAccess": "critical",
            }
            ev = {
                "type": atype,
                "severity": severity_map.get(atype, "medium"),
                "message": rec.get("anomaly_note", "Anomaly detected"),
                "timestamp": f"{rec['date']}T02:00:00+00:00" if atype == "CredentialAccess"
                             else f"{rec['date']}T10:32:00+00:00",
                "agent_id": agent_id,
                "domain": p["anomaly_domain"] if atype == "NewDomain" else None,
            }
            events.append(ev)

    events.sort(key=lambda e: e["timestamp"], reverse=True)
    return events
