"""
scorer.py
Computes the six-dimension MCP Trust Scorecard from manifest + domain + AI analysis data.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


# ---------------------------------------------------------------------------
# Dimension scorers
# ---------------------------------------------------------------------------

def _score_identity(manifest: dict) -> tuple[int, str]:
    """Submitted publisher verification/URL signal → 90 | Named publisher → 60 | Anonymous → 25"""
    publisher = manifest.get("publisher") or manifest.get("author") or manifest.get("vendor") or {}

    if isinstance(publisher, str):
        publisher_name = publisher.strip()
        is_dict = False
    elif isinstance(publisher, dict):
        publisher_name = publisher.get("name", "").strip()
        is_dict = True
    else:
        publisher_name = ""
        is_dict = False

    verified = (
        (is_dict and publisher.get("verified")) or
        (is_dict and publisher.get("url", "")) or
        manifest.get("homepage") or
        manifest.get("repository")
    )

    if not publisher_name:
        return 25, "No publisher identity found — anonymous source"
    if verified:
        return 90, f'Publisher "{publisher_name}" with submitted verification/URL claim — not independently verified'
    # Has a name but no submitted verification/URL claim
    return 60, f'Named publisher "{publisher_name}" — not independently verified'


def _score_permission_sprawl(manifest: dict, gemini_results: dict) -> tuple[int, str]:
    """
    Start at 100.
    Subtract 15 per permission that exceeds 3× the tool count.
    Also factor in Gemini's suspicion score lightly.
    """
    tools = manifest.get("tools", [])
    tool_count = len(tools) if isinstance(tools, list) else 0

    permissions = manifest.get("permissions", [])
    if not isinstance(permissions, list):
        permissions = []
    perm_count = len(permissions)

    threshold = max(1, tool_count) * 3
    excess = max(0, perm_count - threshold)
    score = max(0, 100 - (excess * 15))

    # Soft penalty from Gemini suspicion
    suspicion = gemini_results.get("suspicion_score", 0)
    if suspicion >= 70:
        score = max(0, score - 15)
    elif suspicion >= 50:
        score = max(0, score - 8)

    if excess == 0:
        explanation = (
            f"{perm_count} permission(s) for {tool_count} tool(s) — within acceptable ratio"
        )
    else:
        explanation = (
            f"{excess} excess permission(s) detected "
            f"({perm_count} permissions vs {tool_count} tool(s) × 3 = {threshold} allowance)"
        )
    return score, explanation


def _score_network_behavior(domain_results: dict) -> tuple[int, str]:
    """Start 100, subtract 20 per flagged domain, subtract 10 per unresolvable."""
    flagged = domain_results.get("flagged", [])
    unresolvable = domain_results.get("unresolvable", [])
    clean = domain_results.get("clean", [])

    # Filter out _meta entries
    real_flagged = [f for f in flagged if f.get("domain") != "_meta"]
    meta_notes = [f for f in flagged if f.get("domain") == "_meta"]

    score = 100
    score -= len(real_flagged) * 20
    score -= len(unresolvable) * 10
    score = max(0, score)

    if meta_notes:
        # API not available — neutral score with note
        explanation = meta_notes[0].get("note", "Domain checks could not be completed")
        return 50, explanation

    total = len(real_flagged) + len(unresolvable) + len(clean)
    if total == 0:
        return 100, "No external network calls detected in manifest"
    if real_flagged:
        names = ", ".join(f["domain"] for f in real_flagged[:3])
        explanation = f"{len(real_flagged)} flagged domain(s): {names}"
    elif unresolvable:
        explanation = f"{len(unresolvable)} unresolvable domain(s) — unable to verify"
    else:
        explanation = f"All {len(clean)} domain(s) resolved cleanly with no abuse reports"

    return score, explanation


def _score_code_transparency(manifest: dict) -> tuple[int, str]:
    """No submitted source claim → 20 | Submitted source link → 50 | Submitted audit claim → 95"""
    repository = manifest.get("repository") or manifest.get("source") or manifest.get("repo")
    audit = manifest.get("audit") or manifest.get("security_audit") or manifest.get("audited")
    license_field = manifest.get("license")

    if audit:
        return 95, "Submitted audit claim — not independently verified; source availability not verified"
    if repository:
        repo_url = repository if isinstance(repository, str) else repository.get("url", "")
        note = f"Submitted repository link: {repo_url}" if repo_url else "Submitted source repository link"
        if license_field:
            note += f" — submitted {license_field} license"
        return 50, f"{note} — no audit record claimed"
    return 20, "No submitted source repository or code transparency information found"


def _score_version_drift(manifest: dict) -> tuple[int, str]:
    """No history → 50 | Permissions added silently → 20 | Stable → 85"""
    changelog = (
        manifest.get("changelog") or
        manifest.get("history") or
        manifest.get("release_notes")
    )
    version = manifest.get("version", "")

    # Heuristic: look for signals of silent permission changes
    silent_perm_change = (
        manifest.get("permissions_changed_silently") or
        manifest.get("undocumented_permissions")
    )

    if silent_perm_change:
        return 20, "Permissions appear to have been added without documented changelog entry"
    if changelog:
        return 85, f"Version history present (v{version}) — stable release pattern"
    if version:
        return 50, f"Version {version} declared but no changelog or history found"
    return 50, "No version or changelog information available — drift risk unknown"


def _score_community_signal(manifest: dict) -> tuple[int, str]:
    """
    Start 70.
    -20 if age < 30 days
    -20 if installs < 100
    -30 if open CVEs
    """
    score = 70
    penalties = []

    # Age
    created_at = manifest.get("created_at") or manifest.get("published_at")
    if created_at:
        try:
            published = datetime.fromisoformat(str(created_at).replace("Z", "+00:00"))
            now = datetime.now(timezone.utc)
            age_days = (now - published).days
            if age_days < 30:
                score -= 20
                penalties.append(f"published only {age_days} day(s) ago")
        except (ValueError, TypeError):
            pass

    # Install count
    installs = manifest.get("installs") or manifest.get("downloads") or manifest.get("install_count")
    if installs is not None:
        try:
            installs_int = int(installs)
            if installs_int < 100:
                score -= 20
                penalties.append(f"low install count ({installs_int})")
        except (ValueError, TypeError):
            pass
    else:
        # No install data — minor penalty
        score -= 10
        penalties.append("install count unknown")

    # CVEs
    cves = manifest.get("cves") or manifest.get("vulnerabilities") or []
    if cves:
        score -= 30
        penalties.append(f"{len(cves)} open CVE(s) referenced")

    score = max(0, min(100, score))

    if not penalties:
        explanation = "Established community presence with no known CVEs"
    else:
        explanation = "Community risk factors: " + "; ".join(penalties)

    return score, explanation


# ---------------------------------------------------------------------------
# Weighted overall score
# ---------------------------------------------------------------------------

WEIGHTS = {
    "network_behavior": 0.25,
    "permission_sprawl": 0.20,
    "identity": 0.20,
    "code_transparency": 0.15,
    "version_drift": 0.10,
    "community_signal": 0.10,
}


def _trust_rating(score: float) -> str:
    if score >= 80:
        return "High"
    if score >= 60:
        return "Medium"
    if score >= 40:
        return "Low"
    return "Untrusted"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def score(manifest: dict, domain_results: dict, gemini_results: dict) -> dict:
    """
    Compute full MCP Trust Scorecard.

    Returns a dict matching the documented response JSON shape.
    """
    identity_score, identity_exp = _score_identity(manifest)
    sprawl_score, sprawl_exp = _score_permission_sprawl(manifest, gemini_results)
    network_score, network_exp = _score_network_behavior(domain_results)
    transparency_score, transparency_exp = _score_code_transparency(manifest)
    drift_score, drift_exp = _score_version_drift(manifest)
    community_score, community_exp = _score_community_signal(manifest)

    dimensions: dict[str, Any] = {
        "identity": {"score": identity_score, "explanation": identity_exp},
        "permission_sprawl": {"score": sprawl_score, "explanation": sprawl_exp},
        "network_behavior": {"score": network_score, "explanation": network_exp},
        "code_transparency": {"score": transparency_score, "explanation": transparency_exp},
        "version_drift": {"score": drift_score, "explanation": drift_exp},
        "community_signal": {"score": community_score, "explanation": community_exp},
    }

    raw_scores = {
        "identity": identity_score,
        "permission_sprawl": sprawl_score,
        "network_behavior": network_score,
        "code_transparency": transparency_score,
        "version_drift": drift_score,
        "community_signal": community_score,
    }

    overall = sum(raw_scores[k] * w for k, w in WEIGHTS.items())
    overall_int = round(overall)

    # Build flags list
    flags: list[str] = []

    flagged_domains = [f for f in domain_results.get("flagged", []) if f.get("domain") != "_meta"]
    for fd in flagged_domains:
        flags.append(
            f"Flagged domain: {fd['domain']} ({fd.get('confidence', '?')}% abuse confidence)"
        )
    for ud in domain_results.get("unresolvable", []):
        flags.append(f"Unresolvable domain: {ud}")

    for rf in gemini_results.get("risk_flags", []):
        if rf and rf not in flags:
            flags.append(rf)

    if identity_score <= 25:
        flags.append("Anonymous publisher — identity cannot be verified")
    if transparency_score <= 20:
        flags.append("No source code or audit trail available")
    if community_score <= 30:
        flags.append("Very low community trust signal")

    return {
        "overall_score": overall_int,
        "trust_rating": _trust_rating(overall_int),
        "dimensions": dimensions,
        "flags": flags,
        "gemini_summary": gemini_results.get("intent_summary", ""),
        "permission_analysis": gemini_results.get("permission_analysis", ""),
        "suspicion_score": gemini_results.get("suspicion_score", 0),
        "scanned_at": datetime.now(timezone.utc).isoformat(),
    }
