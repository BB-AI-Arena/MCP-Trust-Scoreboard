"""
gemini_analyzer.py
Uses Gemini 2.0 Flash to generate a human-readable attack narrative and
concrete mitigations for the current blast-radius graph.
"""

import json
import os
import logging
from typing import Any, Dict, List

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Fallback content used when the API is unavailable or the key is missing
# ---------------------------------------------------------------------------

_FALLBACK_NARRATIVE = (
    "If this agent were compromised, an attacker could leverage its permissions "
    "to access sensitive resources and pivot to connected systems. "
    "The agent's integrations with external services create multiple lateral movement "
    "opportunities. Credential and identity resources are especially at risk given "
    "the current permission scope. "
    "An attacker could exfiltrate data, escalate privileges, or cause service disruption "
    "depending on the resources reachable from this agent."
)

_FALLBACK_MITIGATIONS = [
    "Apply the principle of least privilege: audit and remove any permissions the agent "
    "does not actively require for its core function.",
    "Rotate and scope API keys and credentials so that each integration uses a unique, "
    "short-lived secret with the minimum necessary scope.",
    "Enable network-level segmentation to restrict the agent's outbound connections "
    "to only the endpoints it legitimately needs to reach.",
]


def analyze_blast_radius(
    nodes: List[Dict[str, Any]],
    edges: List[Dict[str, Any]],
    blast_rating: str,
    critical_nodes: List[str],
) -> Dict[str, Any]:
    """
    Call Gemini 2.0 Flash with a structured prompt about the agent's blast radius.

    Parameters
    ----------
    nodes          : list of node dicts from graph_builder
    edges          : list of edge dicts from graph_builder
    blast_rating   : e.g. "Severe"
    critical_nodes : list of node IDs flagged as critical or high

    Returns
    -------
    {
        "attack_narrative": str,
        "mitigations": list[str]
    }
    """
    api_key = (os.getenv("GEMINI_API_KEY", "").strip() if os.getenv("AGENT_TRUST_HOSTED_ANALYSIS", "false").lower() == "true" else "")
    if not api_key:
        logger.warning("GEMINI_API_KEY not set — returning fallback analysis.")
        return {
            "attack_narrative": _FALLBACK_NARRATIVE,
            "mitigations": _FALLBACK_MITIGATIONS,
        }

    # Build a condensed representation of the graph for the prompt
    node_summary = [
        {"id": n["id"], "type": n["type"], "label": n["label"], "criticality": n["criticality"]}
        for n in nodes
    ]
    edge_summary = [
        {"source": e["source"], "target": e["target"], "type": e["type"]}
        for e in edges
    ]

    prompt = (
        f"You are a cybersecurity expert analyzing an AI agent's blast radius. "
        f"The agent has a blast rating of '{blast_rating}'. "
        f"The following critical/high-risk nodes have been identified: {critical_nodes}.\n\n"
        f"Graph nodes: {json.dumps(node_summary)}\n"
        f"Graph edges: {json.dumps(edge_summary)}\n\n"
        "Write an attack narrative (3-5 sentences starting with "
        "'If this agent were compromised, an attacker could...') "
        "and provide exactly 3 concrete mitigations. "
        "Return ONLY valid JSON, no markdown, no backticks: "
        '{"attack_narrative": "", "mitigations": []}'
    )

    try:
        import google.generativeai as genai  # lazy import to avoid hard failure at module load

        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-2.0-flash")

        response = model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=0.4,
                max_output_tokens=1024,
            ),
        )

        raw_text = response.text.strip()

        # Strip accidental markdown fences the model may include despite instructions
        if raw_text.startswith("```"):
            lines = raw_text.splitlines()
            # Remove first and last fence lines
            lines = [l for l in lines if not l.strip().startswith("```")]
            raw_text = "\n".join(lines).strip()

        parsed = json.loads(raw_text)

        attack_narrative = str(parsed.get("attack_narrative", "")).strip()
        mitigations_raw  = parsed.get("mitigations", [])

        # Ensure mitigations is a list of strings
        if isinstance(mitigations_raw, list):
            mitigations = [str(m) for m in mitigations_raw[:3]]
        else:
            mitigations = [str(mitigations_raw)]

        # Safety: fall back to defaults if the model returned empty values
        if not attack_narrative:
            attack_narrative = _FALLBACK_NARRATIVE
        if not mitigations:
            mitigations = _FALLBACK_MITIGATIONS

        return {
            "attack_narrative": attack_narrative,
            "mitigations": mitigations,
        }

    except json.JSONDecodeError as exc:
        logger.error("Failed to parse Gemini JSON response: %s", exc)
        return {
            "attack_narrative": _FALLBACK_NARRATIVE,
            "mitigations": _FALLBACK_MITIGATIONS,
        }
    except Exception as exc:  # noqa: BLE001
        logger.error("Gemini API call failed: %s", exc)
        return {
            "attack_narrative": _FALLBACK_NARRATIVE,
            "mitigations": _FALLBACK_MITIGATIONS,
        }
