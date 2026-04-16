"""
gemini_analyzer.py
Gemini-powered deep analysis of code snippets.
Combines AI provenance signals and security findings into an actionable verdict.
Falls back to heuristic verdict when GEMINI_API_KEY is not configured.
"""

import os
import json
import logging
from typing import Dict, Any

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Gemini client setup (lazy — only initialized if API key is present)
# ---------------------------------------------------------------------------

GEMINI_API_KEY: str = os.environ.get("GEMINI_API_KEY", "")
GEMINI_MODEL: str = "gemini-2.0-flash"

_genai = None


def _get_genai():
    """
    Lazily import and configure the google.generativeai module.

    Returns:
        Configured google.generativeai module, or None if unavailable.
    """
    global _genai
    if _genai is not None:
        return _genai
    if not GEMINI_API_KEY:
        return None
    try:
        import google.generativeai as genai
        genai.configure(api_key=GEMINI_API_KEY)
        _genai = genai
        return _genai
    except ImportError:
        logger.warning("google-generativeai package not installed.")
        return None
    except Exception as exc:
        logger.warning("Failed to configure Gemini: %s", exc)
        return None


# ---------------------------------------------------------------------------
# Fallback heuristic verdict
# ---------------------------------------------------------------------------

def _heuristic_verdict(provenance: Dict[str, Any], risks: Dict[str, Any]) -> dict:
    """
    Generate a verdict without calling the Gemini API.
    Used when GEMINI_API_KEY is absent or the API call fails.

    Args:
        provenance: Output from provenance_detector.detect_provenance().
        risks: Output from code_risk_scanner.scan_code().

    Returns:
        Dict with safe_to_merge, explanation, remediations, and overall_verdict.
    """
    score: int = risks.get("score", 0)
    risk_level: str = risks.get("risk_level", "Safe")
    findings = risks.get("findings", [])
    model: str = provenance.get("likely_model", "Unknown")
    confidence: int = provenance.get("confidence", 0)

    remediations = [f["remediation"] for f in findings if f.get("remediation")]

    if score >= 81:
        verdict = "REJECT"
        safe_to_merge = False
        explanation = (
            f"Critical risk level (score {score}/100). "
            f"Code appears to originate from {model} (confidence {confidence}%). "
            f"Found {len(findings)} security issue(s) including critical/high severity findings. "
            "Merge blocked until all critical issues are resolved."
        )
    elif score >= 51:
        verdict = "REVIEW"
        safe_to_merge = False
        explanation = (
            f"High risk level (score {score}/100). "
            f"Code appears to originate from {model} (confidence {confidence}%). "
            f"Found {len(findings)} security issue(s) that require manual review before merging."
        )
    elif score >= 21:
        verdict = "REVIEW"
        safe_to_merge = False
        explanation = (
            f"Medium risk level (score {score}/100). "
            f"Code appears to originate from {model} (confidence {confidence}%). "
            f"Found {len(findings)} issue(s). Review recommended."
        )
    elif score > 0:
        verdict = "APPROVE"
        safe_to_merge = True
        explanation = (
            f"Low risk level (score {score}/100). "
            f"Code appears to originate from {model} (confidence {confidence}%). "
            f"Minor issues detected ({len(findings)}). Safe to merge with awareness of findings."
        )
    else:
        verdict = "APPROVE"
        safe_to_merge = True
        explanation = (
            f"No security issues detected (score 0/100). "
            f"Code appears to originate from {model} (confidence {confidence}%). "
            "Safe to merge."
        )

    return {
        "safe_to_merge": safe_to_merge,
        "explanation": explanation,
        "remediations": remediations[:10],  # cap at 10
        "overall_verdict": verdict,
    }


# ---------------------------------------------------------------------------
# Gemini prompt construction
# ---------------------------------------------------------------------------

def _build_prompt(code: str, provenance: Dict[str, Any], risks: Dict[str, Any]) -> str:
    """
    Build the Gemini analysis prompt.

    Args:
        code: Source code being analyzed.
        provenance: Provenance detection results.
        risks: Security scan results.

    Returns:
        Formatted prompt string.
    """
    findings_summary = ""
    for f in risks.get("findings", [])[:10]:
        findings_summary += (
            f"  - [{f['severity'].upper()}] {f['type']} at line {f['line']}: {f['description']}\n"
        )

    if not findings_summary:
        findings_summary = "  No findings.\n"

    prompt = f"""You are a senior security engineer reviewing a code snippet for safe merging into a production codebase.

## Code Provenance Analysis
- Likely AI model origin: {provenance.get('likely_model', 'Unknown')}
- Confidence: {provenance.get('confidence', 0)}%
- Top markers: {', '.join(m['marker'] for m in provenance.get('markers', [])[:3])}

## Security Scan Results
- Risk level: {risks.get('risk_level', 'Safe')} (score: {risks.get('score', 0)}/100)
- Summary: {risks.get('summary', 'No summary.')}
- Findings:
{findings_summary}

## Code Snippet (first 3000 chars)
```
{code[:3000]}
```

## Your Task
Analyze the code considering its likely AI origin and the security findings above.
Return a JSON object with EXACTLY these fields:
{{
  "safe_to_merge": <boolean>,
  "explanation": "<string: 2-4 sentence analysis>",
  "remediations": ["<string>", ...],
  "overall_verdict": "<one of: APPROVE, REVIEW, REJECT>"
}}

Rules:
- APPROVE: no significant issues, safe to merge as-is
- REVIEW: issues present but not blocking; requires human review
- REJECT: critical issues that must be fixed before merging
- Return ONLY valid JSON. No markdown, no extra text."""

    return prompt


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def analyze_snippet(code: str, provenance: dict, risks: dict) -> dict:
    """
    Analyze a code snippet using Gemini AI, combining provenance and risk signals.

    Args:
        code: The source code string to analyze.
        provenance: Dict from provenance_detector.detect_provenance().
        risks: Dict from code_risk_scanner.scan_code().

    Returns:
        Dict with keys:
          - safe_to_merge (bool): Whether the code is safe to merge.
          - explanation (str): Analysis explanation.
          - remediations (list[str]): Suggested fixes.
          - overall_verdict (str): "APPROVE", "REVIEW", or "REJECT".
    """
    genai = _get_genai()

    if genai is None:
        logger.info("Gemini API key not configured — using heuristic fallback.")
        return _heuristic_verdict(provenance, risks)

    try:
        model = genai.GenerativeModel(GEMINI_MODEL)
        prompt = _build_prompt(code, provenance, risks)

        response = model.generate_content(
            prompt,
            generation_config={
                "temperature": 0.2,
                "max_output_tokens": 1024,
            },
        )

        raw_text: str = response.text.strip()

        # Strip markdown code fences if present
        if raw_text.startswith("```"):
            lines = raw_text.split("\n")
            # Remove first and last fence lines
            inner_lines = []
            in_block = False
            for line in lines:
                if line.startswith("```") and not in_block:
                    in_block = True
                    continue
                if line.startswith("```") and in_block:
                    break
                inner_lines.append(line)
            raw_text = "\n".join(inner_lines)

        parsed = json.loads(raw_text)

        # Validate required keys and types
        result = {
            "safe_to_merge": bool(parsed.get("safe_to_merge", False)),
            "explanation": str(parsed.get("explanation", "")),
            "remediations": [str(r) for r in parsed.get("remediations", [])],
            "overall_verdict": str(parsed.get("overall_verdict", "REVIEW")).upper(),
        }

        # Ensure verdict is one of the allowed values
        if result["overall_verdict"] not in ("APPROVE", "REVIEW", "REJECT"):
            result["overall_verdict"] = "REVIEW"

        return result

    except json.JSONDecodeError as exc:
        logger.warning("Gemini returned non-JSON response: %s", exc)
        return _heuristic_verdict(provenance, risks)
    except Exception as exc:
        logger.warning("Gemini API call failed: %s", exc)
        return _heuristic_verdict(provenance, risks)
