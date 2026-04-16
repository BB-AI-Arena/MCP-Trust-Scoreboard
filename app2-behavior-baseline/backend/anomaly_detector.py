"""
anomaly_detector.py
Detects behavioral anomalies in AI agent data using Z-score analysis
against a 27-day baseline, plus deterministic extraction of the 3
pre-seeded anomalies per agent.
"""

import math
import uuid
from datetime import datetime, timezone, timedelta
from typing import Any

from mock_data import get_agent_data, AGENT_PROFILES
from baseline_engine import build_baseline


# ---------------------------------------------------------------------------
# Severity mapping
# ---------------------------------------------------------------------------

SEVERITY_MAP = {
    "NewDomain": "high",
    "FileSpike": "medium",
    "CredentialAccess": "critical",
    "OffHoursActivity": "medium",
    "ExecutionTimeSpike": "low",
    "NewAPIEndpoint": "medium",
}

Z_THRESHOLD = 2.5  # Standard deviations to flag


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _z_score(value: float, mean: float, std_dev: float) -> float:
    if std_dev == 0:
        return 0.0
    return (value - mean) / std_dev


def _delta_str(value: float, baseline: float, unit: str = "") -> str:
    if baseline == 0:
        return f"+{value:.1f}{unit} above baseline"
    pct = ((value - baseline) / baseline) * 100.0
    sign = "+" if pct >= 0 else ""
    return f"{sign}{pct:.1f}% vs baseline{(' (' + unit + ')') if unit else ''}"


def _make_anomaly(
    atype: str,
    description: str,
    timestamp: str,
    metric: str,
    value: float,
    baseline: float,
    unit: str = "",
    anomaly_id: str = None,
) -> dict:
    return {
        "id": anomaly_id or str(uuid.uuid4()),
        "type": atype,
        "severity": SEVERITY_MAP.get(atype, "medium"),
        "description": description,
        "timestamp": timestamp,
        "delta": _delta_str(value, baseline, unit),
        "metric": metric,
        "value": round(value, 2),
        "baseline": round(baseline, 2),
    }


# ---------------------------------------------------------------------------
# Pre-seeded anomaly extraction
# ---------------------------------------------------------------------------

def _extract_seeded_anomalies(agent_id: str, baseline: dict) -> list[dict]:
    """
    Pull the 3 deterministically injected anomalies from the last 3 days.
    """
    records = get_agent_data(agent_id, days=30)
    last3 = records[-3:]
    anomalies = []
    today = datetime.now(tz=timezone.utc)

    for rec in last3:
        if not rec.get("is_anomaly_day"):
            continue

        atype = rec.get("anomaly_type", "Unknown")
        date_str = rec.get("date", today.strftime("%Y-%m-%d"))

        if atype == "NewDomain":
            p = AGENT_PROFILES[agent_id]
            bad_domain = p["anomaly_domain"]
            ts = f"{date_str}T14:07:33+00:00"
            normal_domains = set(baseline.get("normal_domains", []))
            anomalies.append(
                _make_anomaly(
                    atype="NewDomain",
                    description=(
                        f"Agent contacted unknown domain '{bad_domain}' "
                        f"not seen in 27-day baseline."
                    ),
                    timestamp=ts,
                    metric="network_destinations",
                    value=1.0,
                    baseline=0.0,
                    unit="new domains",
                    anomaly_id=f"{agent_id}-seeded-domain",
                )
            )

        elif atype == "FileSpike":
            baseline_mean = baseline["metrics"]["file_access_count"]["mean"]
            value = float(rec.get("file_access_count", baseline_mean))
            ts = f"{date_str}T09:52:17+00:00"
            anomalies.append(
                _make_anomaly(
                    atype="FileSpike",
                    description=(
                        f"File access count spiked to {int(value)} "
                        f"(baseline mean {baseline_mean:.1f}). "
                        f"Possible bulk data staging."
                    ),
                    timestamp=ts,
                    metric="file_access_count",
                    value=value,
                    baseline=baseline_mean,
                    anomaly_id=f"{agent_id}-seeded-filespike",
                )
            )

        elif atype == "CredentialAccess":
            cred_count = float(rec.get("credential_accesses", 3))
            baseline_mean = baseline["metrics"]["credential_accesses"]["mean"]
            ts = f"{date_str}T02:13:44+00:00"
            anomalies.append(
                _make_anomaly(
                    atype="CredentialAccess",
                    description=(
                        f"Credential store accessed {int(cred_count)} times at 02:13 "
                        f"(off-hours). Baseline credential accesses: "
                        f"{baseline_mean:.2f}/day."
                    ),
                    timestamp=ts,
                    metric="credential_accesses",
                    value=cred_count,
                    baseline=baseline_mean,
                    anomaly_id=f"{agent_id}-seeded-cred",
                )
            )

            # Also flag as OffHoursActivity
            normal_hours = set(baseline.get("normal_hours", []))
            if 2 not in normal_hours:
                anomalies.append(
                    _make_anomaly(
                        atype="OffHoursActivity",
                        description=(
                            f"Agent active at 02:00, outside normal operating window "
                            f"({min(normal_hours) if normal_hours else '?'}h–"
                            f"{max(normal_hours) if normal_hours else '?'}h)."
                        ),
                        timestamp=ts,
                        metric="active_hours",
                        value=2.0,
                        baseline=float(min(baseline.get("normal_hours", [8]))),
                        anomaly_id=f"{agent_id}-seeded-offhours",
                    )
                )

    return anomalies


# ---------------------------------------------------------------------------
# Dynamic Z-score anomaly detection on last 3 days
# ---------------------------------------------------------------------------

def _detect_dynamic_anomalies(agent_id: str, baseline: dict) -> list[dict]:
    """
    Run Z-score detection on the last 3 days of data for numeric metrics.
    Skip anomalies that duplicate a seeded type (detected separately).
    """
    records = get_agent_data(agent_id, days=30)
    last3 = records[-3:]
    seeded_types = set()
    for rec in last3:
        if rec.get("is_anomaly_day") and rec.get("anomaly_type"):
            seeded_types.add(rec["anomaly_type"])

    numeric_checks = [
        ("api_call_rate", "api_call_rate", "NewAPIEndpoint", "calls/hr"),
        ("file_access_count", "file_access_count", "FileSpike", "files/hr"),
        ("execution_time_ms", "execution_time_ms", "ExecutionTimeSpike", "ms"),
        ("credential_accesses", "credential_accesses", "CredentialAccess", "accesses"),
    ]

    anomalies = []

    for rec in last3:
        date_str = rec.get("date", "")
        ts_base = f"{date_str}T"

        for field, metric_key, atype, unit in numeric_checks:
            if atype in seeded_types and metric_key in ("file_access_count", "credential_accesses"):
                # Already captured by seeded extraction; skip to avoid duplicate
                continue

            stats = baseline["metrics"].get(metric_key)
            if not stats:
                continue

            mean = stats["mean"]
            std = stats["std_dev"]
            value = float(rec.get(field, mean))
            z = _z_score(value, mean, std)

            if abs(z) > Z_THRESHOLD:
                direction = "above" if z > 0 else "below"
                ts = f"{ts_base}11:05:00+00:00"
                anomalies.append(
                    _make_anomaly(
                        atype=atype,
                        description=(
                            f"{metric_key.replace('_', ' ').title()} of {value:.1f} "
                            f"is {abs(z):.1f}σ {direction} baseline mean ({mean:.1f}). "
                            f"Possible anomalous behavior."
                        ),
                        timestamp=ts,
                        metric=metric_key,
                        value=value,
                        baseline=mean,
                        unit=unit,
                    )
                )

    return anomalies


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def detect_anomalies(agent_id: str) -> list[dict]:
    """
    Detect all anomalies for *agent_id*.

    Returns a list of anomaly dicts combining:
    - 3 pre-seeded anomalies (deterministic)
    - Dynamically detected Z-score outliers
    Sorted newest-first.
    """
    baseline = build_baseline(agent_id, days=27)

    seeded = _extract_seeded_anomalies(agent_id, baseline)
    dynamic = _detect_dynamic_anomalies(agent_id, baseline)

    # Deduplicate by id
    seen_ids: set[str] = set()
    all_anomalies = []
    for a in seeded + dynamic:
        if a["id"] not in seen_ids:
            seen_ids.add(a["id"])
            all_anomalies.append(a)

    # Sort newest-first
    all_anomalies.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
    return all_anomalies
