"""
gemini_analyzer.py
Uses Google Gemini 2.0 Flash to classify a cluster of anomalies for an AI agent.
Falls back gracefully when GEMINI_API_KEY is absent.
"""

import os
import json
import re
from typing import Any

from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# Gemini client setup
# ---------------------------------------------------------------------------

_GEMINI_CONFIGURED = False
_genai = None

def _setup_gemini() -> bool:
    global _GEMINI_CONFIGURED, _genai
    if _GEMINI_CONFIGURED:
        return _genai is not None

    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        _GEMINI_CONFIGURED = True
        return False

    try:
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        _genai = genai
        _GEMINI_CONFIGURED = True
        return True
    except Exception:
        _GEMINI_CONFIGURED = True
        return False


# ---------------------------------------------------------------------------
# Classification labels
# ---------------------------------------------------------------------------

CLASSIFICATIONS = [
    "DataExfiltration",
    "LateralMovement",
    "PrivilegeEscalation",
    "BenignDrift",
]

# ---------------------------------------------------------------------------
# Fallback heuristic classifier
# ---------------------------------------------------------------------------

def _heuristic_classify(agent_id: str, anomalies: list[dict]) -> dict:
    """
    Simple rule-based fallback when Gemini is unavailable.
    """
    types = {a.get("type") for a in anomalies}
    severities = [a.get("severity") for a in anomalies]
    critical_count = severities.count("critical")
    high_count = severities.count("high")

    if "NewDomain" in types and "CredentialAccess" in types:
        classification = "DataExfiltration"
        confidence = 72
        action = (
            "Immediately quarantine agent, revoke credentials, and inspect "
            "all outbound network traffic to the flagged domain."
        )
        explanation = (
            "The combination of credential access anomalies and contact with an unknown "
            "external domain strongly suggests an active data exfiltration attempt. "
            "The agent may have been compromised or is operating outside its intended scope."
        )
    elif "CredentialAccess" in types and "OffHoursActivity" in types:
        classification = "PrivilegeEscalation"
        confidence = 65
        action = (
            "Rotate all credentials the agent has access to. Review IAM policies "
            "and audit logs for unauthorized permission changes."
        )
        explanation = (
            "Off-hours credential access without a corresponding legitimate workload "
            "is a classic indicator of privilege escalation — the agent (or a process "
            "controlling it) is attempting to acquire elevated permissions."
        )
    elif "FileSpike" in types and "NewDomain" in types:
        classification = "LateralMovement",
        confidence = 60
        action = (
            "Suspend agent operations and conduct a forensic review of all files "
            "accessed during the spike window."
        )
        explanation = (
            "Bulk file access followed by contact with an unknown external domain "
            "may indicate the agent is staging data for transfer or scanning the "
            "filesystem for lateral movement vectors."
        )
    elif critical_count == 0 and high_count == 0:
        classification = "BenignDrift"
        confidence = 80
        action = (
            "Monitor for 48 hours. If metrics stabilize, update the baseline. "
            "No immediate action required."
        )
        explanation = (
            "The detected deviations are minor and within expected variance ranges "
            "for this agent's evolving workload. This appears to be natural behavioral "
            "drift rather than a security event."
        )
    else:
        classification = "DataExfiltration"
        confidence = 55
        action = (
            "Escalate to the security team for manual review within 1 hour."
        )
        explanation = (
            "Multiple high-severity anomalies detected without a clear single "
            "classification. Manual investigation is required to determine root cause."
        )

    # Unwrap tuple if classification is accidentally a tuple (safety guard)
    if isinstance(classification, tuple):
        classification = classification[0]

    return {
        "classification": classification,
        "confidence": confidence,
        "recommended_action": action,
        "explanation": explanation,
        "source": "heuristic",
    }


# ---------------------------------------------------------------------------
# Gemini-powered classifier
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """You are a cybersecurity AI analyst specializing in AI agent behavioral security.
You analyze clusters of behavioral anomalies detected in AI coding/automation agents and classify them into one of exactly four categories:

- DataExfiltration: Agent appears to be sending data to unauthorized external destinations
- LateralMovement: Agent is accessing resources or systems outside its normal scope
- PrivilegeEscalation: Agent is attempting to gain elevated credentials or permissions
- BenignDrift: Anomalies are explainable by legitimate workload changes, not a security threat

Respond ONLY with valid JSON in this exact schema:
{
  "classification": "<one of the four categories>",
  "confidence": <integer 0-100>,
  "recommended_action": "<concrete 1-2 sentence action>",
  "explanation": "<2-3 sentence technical explanation>"
}"""


def _build_prompt(agent_id: str, anomalies: list[dict]) -> str:
    anomaly_summary = []
    for a in anomalies:
        anomaly_summary.append(
            f"- Type: {a.get('type')} | Severity: {a.get('severity')} | "
            f"Metric: {a.get('metric')} | Value: {a.get('value')} | "
            f"Baseline: {a.get('baseline')} | "
            f"Description: {a.get('description')}"
        )

    return (
        f"Agent ID: {agent_id}\n"
        f"Total anomalies detected: {len(anomalies)}\n\n"
        f"Anomaly details:\n"
        + "\n".join(anomaly_summary)
        + "\n\nClassify this anomaly cluster."
    )


def _call_gemini(agent_id: str, anomalies: list[dict]) -> dict | None:
    if not _setup_gemini() or _genai is None:
        return None

    try:
        model = _genai.GenerativeModel(
            model_name="gemini-2.0-flash",
            system_instruction=SYSTEM_PROMPT,
        )
        prompt = _build_prompt(agent_id, anomalies)
        response = model.generate_content(prompt)
        raw_text = response.text.strip()

        # Strip markdown fences if present
        raw_text = re.sub(r"^```(?:json)?\s*", "", raw_text, flags=re.MULTILINE)
        raw_text = re.sub(r"\s*```$", "", raw_text, flags=re.MULTILINE)
        raw_text = raw_text.strip()

        parsed = json.loads(raw_text)

        # Validate fields
        classification = parsed.get("classification", "BenignDrift")
        if classification not in CLASSIFICATIONS:
            classification = "BenignDrift"

        return {
            "classification": classification,
            "confidence": int(parsed.get("confidence", 50)),
            "recommended_action": str(parsed.get("recommended_action", "")),
            "explanation": str(parsed.get("explanation", "")),
            "source": "gemini-2.0-flash",
        }
    except Exception as exc:
        # Log but don't raise — caller will use heuristic fallback
        print(f"[gemini_analyzer] Gemini call failed for {agent_id}: {exc}")
        return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def classify_anomaly_cluster(agent_id: str, anomalies: list[dict]) -> dict:
    """
    Classify a cluster of anomalies for *agent_id*.

    Tries Gemini 2.0 Flash first; falls back to a heuristic classifier if
    the API key is absent or the call fails.

    Returns
    -------
    {
        "classification": str,   # DataExfiltration | LateralMovement | PrivilegeEscalation | BenignDrift
        "confidence": int,        # 0-100
        "recommended_action": str,
        "explanation": str,
        "source": str,            # "gemini-2.0-flash" | "heuristic"
    }
    """
    if not anomalies:
        return {
            "classification": "BenignDrift",
            "confidence": 90,
            "recommended_action": "No anomalies detected. Continue routine monitoring.",
            "explanation": "All behavioral metrics are within expected baseline ranges. No action required.",
            "source": "heuristic",
        }

    result = _call_gemini(agent_id, anomalies)
    if result is not None:
        return result

    return _heuristic_classify(agent_id, anomalies)
