"""
worker.py
Koi Security Extensions — Async Scan Worker

Polls a Redis queue for scan jobs and processes them asynchronously.
In the enterprise model this is replaced by an SQS consumer — the job
schema and processing logic are identical.

Queue key: koi:scan:queue  (Redis RPUSH / BLPOP)
Job schema: { "job_id": str, "app": str, "payload": dict, "enqueued_at": str }
Result key: koi:scan:result:{job_id}  (Redis SET with TTL)
"""

from __future__ import annotations

import importlib
import json
import logging
import os
import sys
import time
from datetime import datetime, timezone
from typing import Any

import redis
from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] worker %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%SZ",
)
log = logging.getLogger("koi-worker")

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
QUEUE_KEY = "koi:scan:queue"
RESULT_TTL = 3600  # seconds — results cached for 1 hour
POLL_TIMEOUT = 5   # BLPOP block timeout seconds

# ---------------------------------------------------------------------------
# Redis connection
# ---------------------------------------------------------------------------
def connect_redis(url: str, max_retries: int = 10) -> redis.Redis:
    for attempt in range(1, max_retries + 1):
        try:
            r = redis.from_url(url, decode_responses=True)
            r.ping()
            log.info(f"Connected to Redis at {url}")
            return r
        except redis.ConnectionError:
            wait = min(2 ** attempt, 30)
            log.warning(f"Redis not ready (attempt {attempt}/{max_retries}), retrying in {wait}s")
            time.sleep(wait)
    log.error("Could not connect to Redis after maximum retries — exiting")
    sys.exit(1)

# ---------------------------------------------------------------------------
# Job processors — delegate to each app's backend modules
# ---------------------------------------------------------------------------

def _add_to_sys_path(app_backend: str) -> None:
    """Add an app backend directory to sys.path so its modules are importable."""
    backend_dir = os.path.join(
        os.path.dirname(__file__), "..", app_backend, "backend"
    )
    backend_dir = os.path.realpath(backend_dir)
    if backend_dir not in sys.path:
        sys.path.insert(0, backend_dir)


def process_blast_radius(payload: dict) -> dict:
    _add_to_sys_path("app1-blast-radius")
    graph_builder = importlib.import_module("graph_builder")
    risk_scorer = importlib.import_module("risk_scorer")
    gemini_analyzer = importlib.import_module("gemini_analyzer")

    graph = graph_builder.build_graph(
        agent_name=payload.get("agent_name", "Unknown Agent"),
        permissions=payload.get("permissions", []),
        integrations=payload.get("integrations", []),
        endpoint_type=payload.get("endpoint_type", "custom"),
    )
    risk = risk_scorer.score_blast_radius(graph["nodes"], graph["edges"])
    narrative = gemini_analyzer.analyze_blast_radius(
        graph["nodes"], graph["edges"],
        risk["blast_rating"], risk["critical_nodes"]
    )
    return {**graph, **risk, **narrative}


def process_behavior_scan(payload: dict) -> dict:
    _add_to_sys_path("app2-behavior-baseline")
    anomaly_detector = importlib.import_module("anomaly_detector")
    gemini_analyzer = importlib.import_module("gemini_analyzer")

    agent_id = payload.get("agent_id", "claude-code")
    anomalies = anomaly_detector.detect_anomalies(agent_id)
    summary = gemini_analyzer.classify_anomaly_cluster(agent_id, anomalies)
    return {"agent_id": agent_id, "anomalies": anomalies, "summary": summary}


def process_code_provenance(payload: dict) -> dict:
    _add_to_sys_path("app3-code-provenance")
    provenance_detector = importlib.import_module("provenance_detector")
    code_risk_scanner = importlib.import_module("code_risk_scanner")
    gemini_analyzer = importlib.import_module("gemini_analyzer")

    code = payload.get("code", "")
    language = payload.get("language", "python")
    filename = payload.get("filename", "")

    provenance = provenance_detector.detect_provenance(code, language)
    risks = code_risk_scanner.scan_code(code, language)
    verdict = gemini_analyzer.analyze_snippet(code, provenance, risks)
    return {"filename": filename, "language": language, "provenance": provenance, "risks": risks, "gemini": verdict}


def process_mcp_scorecard(payload: dict) -> dict:
    _add_to_sys_path("app4-mcp-scorecard")
    domain_checker = importlib.import_module("domain_checker")
    scorer = importlib.import_module("scorer")
    gemini_analyzer = importlib.import_module("gemini_analyzer")

    import re
    manifest = payload.get("manifest", {})
    _URL_RE = re.compile(r'https?://([^/\s"\']+)', re.IGNORECASE)
    raw = str(manifest)
    domains = list({m.split(":")[0].lower() for m in _URL_RE.findall(raw) if m.split(":")[0].lower() not in ("localhost", "127.0.0.1")})
    tools = manifest.get("tools", []) if isinstance(manifest.get("tools"), list) else []

    domain_results = domain_checker.check_domains(domains)
    gemini_results = gemini_analyzer.analyze_tools(tools)
    result = scorer.score(manifest, domain_results, gemini_results)
    if payload.get("source_url"):
        result["source_url"] = payload["source_url"]
    return result


PROCESSORS = {
    "blast-radius": process_blast_radius,
    "behavior-baseline": process_behavior_scan,
    "code-provenance": process_code_provenance,
    "mcp-scorecard": process_mcp_scorecard,
}

# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------

def process_job(r: redis.Redis, raw: str) -> None:
    try:
        job = json.loads(raw)
    except json.JSONDecodeError as e:
        log.error(f"Invalid job JSON: {e} — raw: {raw[:200]}")
        return

    job_id = job.get("job_id", "unknown")
    app = job.get("app", "")
    payload = job.get("payload", {})

    log.info(f"Processing job {job_id} (app={app})")
    started = time.time()

    processor = PROCESSORS.get(app)
    if not processor:
        log.error(f"No processor for app '{app}' — dropping job {job_id}")
        return

    try:
        result = processor(payload)
        status = "complete"
        error = None
    except Exception as exc:
        log.exception(f"Job {job_id} failed: {exc}")
        result = {}
        status = "error"
        error = str(exc)

    elapsed = round(time.time() - started, 3)
    output = {
        "job_id": job_id,
        "app": app,
        "status": status,
        "error": error,
        "result": result,
        "processed_at": datetime.now(timezone.utc).isoformat(),
        "elapsed_s": elapsed,
    }
    result_key = f"koi:scan:result:{job_id}"
    r.setex(result_key, RESULT_TTL, json.dumps(output))
    log.info(f"Job {job_id} {status} in {elapsed}s — cached at {result_key}")


def main() -> None:
    log.info("Koi Security Worker starting up")
    r = connect_redis(REDIS_URL)
    log.info(f"Listening on queue: {QUEUE_KEY}")

    while True:
        try:
            item = r.blpop(QUEUE_KEY, timeout=POLL_TIMEOUT)
            if item is None:
                continue
            _, raw = item
            process_job(r, raw)
        except redis.RedisError as e:
            log.error(f"Redis error: {e} — reconnecting in 5s")
            time.sleep(5)
            r = connect_redis(REDIS_URL)
        except KeyboardInterrupt:
            log.info("Worker shutting down")
            break


if __name__ == "__main__":
    main()
