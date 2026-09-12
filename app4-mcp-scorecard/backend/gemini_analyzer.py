"""
gemini_analyzer.py
Analyzes MCP tool definitions using Gemini 2.0 Flash for security insights.
"""

import json
import os
from dotenv import load_dotenv

load_dotenv()

_api_key = os.getenv("GEMINI_API_KEY", "")

SYSTEM_PROMPT = (
    "You are a security analyst. Analyze these MCP tool definitions for suspicious behavior, "
    "permission overreach, and malicious intent. Return ONLY valid JSON, no markdown, no backticks."
)

_FALLBACK = {
    "risk_flags": ["Gemini analysis unavailable — API key not configured or quota exceeded"],
    "permission_analysis": "Unable to complete AI-assisted permission analysis.",
    "intent_summary": "Gemini API call failed. Manual review recommended.",
    "suspicion_score": 50,
}


def analyze_tools(tool_definitions: list) -> dict:
    """
    Send tool definitions to Gemini 2.0 Flash and return structured risk analysis.

    Returns a dict with keys:
        risk_flags: list[str]
        permission_analysis: str
        intent_summary: str
        suspicion_score: int (0–100)
    """
    if not _api_key:
        result = dict(_FALLBACK)
        result["risk_flags"] = ["Gemini API key not configured — set GEMINI_API_KEY in .env"]
        return result

    # Keep the optional provider out of the import path for rules-only scans.
    # A missing SDK is an unavailable provider, never a startup failure.
    try:
        import google.generativeai as genai
        genai.configure(api_key=_api_key)
    except Exception as exc:  # noqa: BLE001
        result = dict(_FALLBACK)
        result["risk_flags"] = [f"Gemini provider unavailable: {exc}"]
        return result

    prompt = (
        f"{SYSTEM_PROMPT}\n\n"
        f"Tool definitions:\n{json.dumps(tool_definitions, indent=2)}\n\n"
        "Return JSON with this exact shape:\n"
        '{"risk_flags": [], "permission_analysis": "", "intent_summary": "", "suspicion_score": 0}'
    )

    try:
        model = genai.GenerativeModel("gemini-2.0-flash")
        response = model.generate_content(prompt)
        raw = response.text.strip()

        # Strip any accidental markdown fences
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        raw = raw.strip()

        parsed = json.loads(raw)

        # Validate and normalise fields
        return {
            "risk_flags": list(parsed.get("risk_flags", [])),
            "permission_analysis": str(parsed.get("permission_analysis", "")),
            "intent_summary": str(parsed.get("intent_summary", "")),
            "suspicion_score": max(0, min(100, int(parsed.get("suspicion_score", 50)))),
        }

    except json.JSONDecodeError as exc:
        result = dict(_FALLBACK)
        result["risk_flags"] = [f"Gemini returned non-JSON response: {exc}"]
        return result
    except Exception as exc:  # noqa: BLE001
        result = dict(_FALLBACK)
        result["risk_flags"] = [f"Gemini API error: {exc}"]
        return result
