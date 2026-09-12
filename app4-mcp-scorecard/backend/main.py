"""
main.py
FastAPI entry point for MCP Trust Scorecard backend.

Supports two scan modes:
  - Sync  (default for local dev): POST /scan          — runs inline, returns result directly
  - Async (default in production): POST /scan/enqueue  — enqueues job, returns job_id
                                   GET  /jobs/{job_id} — poll for result

Set SCAN_MODE=sync in .env to make the frontend default to sync mode.
"""

from __future__ import annotations

import os
import re
import sys
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
from egress_guard import validate_collector_url, UnsafeCollectorURL

load_dotenv()

# ---------------------------------------------------------------------------
# Shared job queue (gracefully skipped if Redis is not available)
# ---------------------------------------------------------------------------
_shared_path = os.path.join(os.path.dirname(__file__), "..", "..", "shared")
if _shared_path not in sys.path:
    sys.path.insert(0, os.path.realpath(_shared_path))

try:
    from job_queue import enqueue_job, get_job_result, write_sync_result
    _queue_available = True
except ImportError:
    _queue_available = False

SCAN_MODE = os.getenv("SCAN_MODE", "async")

# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------
app = FastAPI(
    title="MCP Trust Scorecard API",
    version="2.0.0-alpha.1",
    description="Analyzes MCP server manifests for security trust across six dimensions.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:5174",
        "http://localhost:5175",
        "http://localhost:5176",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class ScanRequest(BaseModel):
    url: Optional[str] = None
    manifest: Optional[dict] = None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_URL_RE = re.compile(r'https?://([^/\s"\']+)', re.IGNORECASE)


def _extract_domains(manifest: dict) -> list[str]:
    raw = str(manifest)
    matches = _URL_RE.findall(raw)
    domains = set()
    for m in matches:
        host = m.split(":")[0].lower()
        if host in ("localhost", "127.0.0.1", "0.0.0.0"):
            continue
        domains.add(host)
    return list(domains)


def _extract_tools(manifest: dict) -> list:
    tools = manifest.get("tools", [])
    return tools if isinstance(tools, list) else []


async def _fetch_manifest(url: str) -> dict:
    try:
        validate_collector_url(url, allow_private=os.getenv("ALLOW_PRIVATE_COLLECTOR_TARGETS", "false").lower() == "true")
    except UnsafeCollectorURL as exc:
        raise HTTPException(status_code=422, detail=f"Unsafe manifest URL: {exc}") from exc
    async with httpx.AsyncClient(timeout=15, follow_redirects=False) as client:
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
            raise HTTPException(status_code=502, detail=f"Network error: {exc}")
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"Could not parse manifest: {exc}")


async def _run_scan(manifest: dict, source_url: Optional[str] = None) -> dict:
    """Core scan logic — shared between sync and async paths."""
    import asyncio
    loop = asyncio.get_event_loop()

    domains = _extract_domains(manifest)
    tools = _extract_tools(manifest)

    domain_results = await loop.run_in_executor(None, check_domains, domains)
    gemini_results = await loop.run_in_executor(None, analyze_tools, tools)
    result = score(manifest, domain_results, gemini_results)

    if source_url:
        result["source_url"] = source_url

    return result


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/health")
async def health():
    return {
        "status": "ok",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "scan_mode": SCAN_MODE,
        "queue_available": _queue_available,
    }


@app.post("/scan")
async def scan(request: ScanRequest):
    """
    Synchronous scan — runs inline and returns result directly.
    Used by default in local dev, or when ?sync=true is passed.
    Preserves full backward compatibility with existing frontend.
    """
    if request.manifest:
        manifest = request.manifest
    elif request.url:
        manifest = await _fetch_manifest(request.url)
    else:
        raise HTTPException(status_code=400, detail="Provide either 'url' or 'manifest'")

    return await _run_scan(manifest, source_url=request.url)


@app.post("/scan/enqueue")
async def scan_enqueue(request: ScanRequest):
    """
    Async scan — enqueues a job and returns job_id immediately.
    The worker processes the job and caches the result in Redis.
    Poll GET /jobs/{job_id} for status and result.
    """
    if not _queue_available:
        # Graceful degradation: fall back to sync if Redis isn't up
        return await scan(request)

    if request.manifest:
        manifest = request.manifest
        source_url = None
    elif request.url:
        manifest = await _fetch_manifest(request.url)
        source_url = request.url
    else:
        raise HTTPException(status_code=400, detail="Provide either 'url' or 'manifest'")

    payload = {"manifest": manifest}
    if source_url:
        payload["source_url"] = source_url

    job_id = enqueue_job("mcp-scorecard", payload)
    return {
        "job_id": job_id,
        "status": "queued",
        "poll_url": f"/jobs/{job_id}",
        "enqueued_at": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/jobs/{job_id}")
async def get_job(job_id: str):
    """Poll for async scan result."""
    if not _queue_available:
        raise HTTPException(status_code=503, detail="Job queue unavailable — use POST /scan for synchronous mode")

    result = get_job_result(job_id)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found or expired")
    return result
