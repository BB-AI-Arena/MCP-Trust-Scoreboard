"""
domain_checker.py
Resolves domains extracted from MCP manifests and checks them against AbuseIPDB.
"""

import os
import socket
from typing import Optional

import httpx
from dotenv import load_dotenv

load_dotenv()

ABUSEIPDB_API_KEY: str = os.getenv("ABUSEIPDB_API_KEY", "")
ABUSEIPDB_ENDPOINT = "https://api.abuseipdb.com/api/v2/check"
CONFIDENCE_THRESHOLD = 25  # flag if abuse confidence % exceeds this


def _resolve_domain(domain: str) -> Optional[str]:
    """Resolve a hostname to its first IP address; return None if unresolvable."""
    try:
        return socket.gethostbyname(domain)
    except (socket.gaierror, OSError):
        return None


def _check_ip(ip: str) -> dict:
    """
    Query AbuseIPDB for an IP.
    Returns parsed JSON on success, raises on HTTP error.
    """
    headers = {
        "Key": ABUSEIPDB_API_KEY,
        "Accept": "application/json",
    }
    params = {
        "ipAddress": ip,
        "maxAgeInDays": "90",
        "verbose": "",
    }
    with httpx.Client(timeout=8) as client:
        resp = client.get(ABUSEIPDB_ENDPOINT, headers=headers, params=params)
        resp.raise_for_status()
        return resp.json()


def check_domains(domains: list) -> dict:
    """
    Check a list of domain names against AbuseIPDB.

    Returns:
        {
            "flagged": [{"domain": str, "ip": str, "confidence": int, "note": str}],
            "clean":   [{"domain": str, "ip": str, "confidence": int}],
            "unresolvable": [str],
        }
    """
    result = {"flagged": [], "clean": [], "unresolvable": []}

    if not domains:
        return result

    if not ABUSEIPDB_API_KEY:
        # Graceful degradation — no API key
        result["unresolvable"] = list(domains)
        result["flagged"].append(
            {
                "domain": "_meta",
                "ip": "",
                "confidence": 0,
                "note": "AbuseIPDB API key not configured — domain threat-intel checks skipped",
            }
        )
        return result

    for domain in domains:
        domain = domain.strip().lower()
        if not domain:
            continue

        ip = _resolve_domain(domain)
        if ip is None:
            result["unresolvable"].append(domain)
            continue

        try:
            data = _check_ip(ip)
            confidence = int(data.get("data", {}).get("abuseConfidenceScore", 0))
            if confidence > CONFIDENCE_THRESHOLD:
                result["flagged"].append(
                    {
                        "domain": domain,
                        "ip": ip,
                        "confidence": confidence,
                        "note": f"AbuseIPDB confidence {confidence}% — exceeds {CONFIDENCE_THRESHOLD}% threshold",
                    }
                )
            else:
                result["clean"].append({"domain": domain, "ip": ip, "confidence": confidence})

        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 401:
                # Invalid key — degrade gracefully for all remaining
                result["unresolvable"].append(domain)
                result["flagged"].append(
                    {
                        "domain": "_meta",
                        "ip": "",
                        "confidence": 0,
                        "note": "AbuseIPDB API key invalid — domain threat-intel checks skipped",
                    }
                )
                break
            # Other HTTP errors — mark domain as unresolvable
            result["unresolvable"].append(domain)

        except Exception as exc:  # noqa: BLE001
            result["unresolvable"].append(domain)

    return result
