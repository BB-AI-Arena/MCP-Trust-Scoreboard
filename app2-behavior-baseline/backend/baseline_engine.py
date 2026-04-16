"""
baseline_engine.py
Builds a behavioral baseline profile for an agent using the first 27 days
of data (days 0–26), excluding the anomaly-seeded last 3 days.
"""

import math
from typing import Any

from mock_data import get_agent_data, AGENT_PROFILES


# ---------------------------------------------------------------------------
# Helper statistics
# ---------------------------------------------------------------------------

def _mean(values: list[float]) -> float:
    if not values:
        return 0.0
    return sum(values) / len(values)


def _std_dev(values: list[float], mean: float = None) -> float:
    if len(values) < 2:
        return 0.0
    m = mean if mean is not None else _mean(values)
    variance = sum((v - m) ** 2 for v in values) / (len(values) - 1)
    return math.sqrt(variance)


def _metric_stats(values: list[float]) -> dict[str, float]:
    if not values:
        return {"mean": 0.0, "std_dev": 0.0, "min": 0.0, "max": 0.0}
    m = _mean(values)
    return {
        "mean": round(m, 4),
        "std_dev": round(_std_dev(values, m), 4),
        "min": round(min(values), 4),
        "max": round(max(values), 4),
    }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def build_baseline(agent_id: str, days: int = 27) -> dict:
    """
    Build a behavioral baseline for *agent_id* using the first *days* records
    (default 27 — the clean, anomaly-free window).

    Returns
    -------
    {
        "agent_id": str,
        "metrics": {
            "api_call_rate":      {"mean", "std_dev", "min", "max"},
            "file_access_count":  {"mean", "std_dev", "min", "max"},
            "execution_time_ms":  {"mean", "std_dev", "min", "max"},
            "credential_accesses": {"mean", "std_dev", "min", "max"},
        },
        "normal_domains": list[str],
        "normal_hours":   list[int],
        "sample_days":    int,
    }
    """
    all_records = get_agent_data(agent_id, days=30)
    baseline_records = all_records[:days]  # first `days` records only

    if not baseline_records:
        return {
            "agent_id": agent_id,
            "metrics": {},
            "normal_domains": [],
            "normal_hours": [],
            "sample_days": 0,
        }

    # Numeric metrics
    api_call_rates: list[float] = []
    file_access_counts: list[float] = []
    execution_times: list[float] = []
    credential_accesses: list[float] = []

    # Domain / hour distributions
    domain_set: set[str] = set()
    hour_counts: dict[int, int] = {h: 0 for h in range(24)}

    for rec in baseline_records:
        api_call_rates.append(float(rec.get("api_call_rate", 0)))
        file_access_counts.append(float(rec.get("file_access_count", 0)))
        execution_times.append(float(rec.get("execution_time_ms", 0.0)))
        credential_accesses.append(float(rec.get("credential_accesses", 0)))

        for domain in rec.get("network_destinations", []):
            domain_set.add(domain)

        for hour in rec.get("active_hours", []):
            hour_counts[hour] = hour_counts.get(hour, 0) + 1

    # Normal hours: any hour that appeared in ≥ 20% of baseline days
    threshold = len(baseline_records) * 0.20
    normal_hours = sorted(h for h, cnt in hour_counts.items() if cnt >= threshold)

    return {
        "agent_id": agent_id,
        "metrics": {
            "api_call_rate": _metric_stats(api_call_rates),
            "file_access_count": _metric_stats(file_access_counts),
            "execution_time_ms": _metric_stats(execution_times),
            "credential_accesses": _metric_stats(credential_accesses),
        },
        "normal_domains": sorted(domain_set),
        "normal_hours": normal_hours,
        "sample_days": len(baseline_records),
    }
