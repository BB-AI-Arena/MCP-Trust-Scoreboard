"""
main.py
FastAPI entry point for MCP Trust Scorecard backend.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Optional

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from domain_checker import check_domains
from gemini_analyzer import analyze_tools
from scorer import score

load_dotenv()

app = FastAPI(title="MCP Trust Scorecard API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173","http://localhost:5174","http://localhost:5175","http://localhost:5176","http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------

class ScanRequest(BaseModel):
    url: Optional[str] = None
    manifest: Optional[dict] = None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_URL_RE = re.compile(r'https?://([^/\s"\']+)', re.IGNORECASE)


def _extract_domains(manifest: dict) -> list[str]:
    """Walk the manifest JSON and extract all unique hostnames."""
    raw = str(manifest)
    matches = _URL_RE.findall(raw)
    # Strip ports, deduplicate, ignore localhost / 127.0.0.1
    domains = set()
    for m in matches:
        host = m.split(":")[0].lower()
        if host in ("localhost", "127.0.0.1", "0.0.0.0"):
            continue
        domains.add(host)
    return list(domains)


def _extract_tools(manifest: dict) -> list:
    """Return the tools array from a manifest, handling common shapes."""
    tools = manifest.get("tools", [])
    if isinstance(tools, list):
        return tools
    return []


async def _fetch_manifest(url: str) -> dict:
    """Fetch a remote JSON manifest."""
    async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
        try:
            resp = await client.get(url)
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPStatusError as exc:
            raise HTTPException(
                status_code=502,
                detail=f"Failed to fetch manifest: HTTP {exc.response.status_code}",
            )
        except httpx.RequestError as exc:
            raise HTTPException(
                status_code=502,
                detail=f"Network error fetching manifest: {exc}",
            )
        except Exception as exc:
            raise HTTPException(
                status_code=502,
                detail=f"Could not parse manifest JSON: {exc}",
            )


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/health")
async def health():
    return {"status": "ok", "timestamp": datetime.now(timezone.utc).isoformat()}


@app.post("/scan")
async def scan(request: ScanRequest):
    # 1. Obtain manifest
    if request.manifest:
        manifest = request.manifest
    elif request.url:
        manifest = await _fetch_manifest(request.url)
    else:
        raise HTTPException(status_code=400, detail="Provide either 'url' or 'manifest'")

    # 2. Extract domains and tools
    domains = _extract_domains(manifest)
    tools = _extract_tools(manifest)

    # 3. Run domain checks (sync wrapped — check_domains uses httpx.Client)
    import asyncio
    loop = asyncio.get_event_loop()
    domain_results = await loop.run_in_executor(None, check_domains, domains)

    # 4. Run Gemini analysis (sync wrapped)
    gemini_results = await loop.run_in_executor(None, analyze_tools, tools)

    # 5. Score
    result = score(manifest, domain_results, gemini_results)

    # 6. Attach source URL if provided
    if request.url:
        result["source_url"] = request.url

    return result
