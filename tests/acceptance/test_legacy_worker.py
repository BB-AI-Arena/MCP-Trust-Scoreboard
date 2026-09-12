"""Real legacy compatibility queue, not a second durable implementation."""
import json
import time

import httpx
import pytest

pytestmark = pytest.mark.acceptance


def test_all_legacy_engines_share_one_real_worker(stack):
    cases = {
        "blast-radius": {"agent_name": "queue-fixture", "permissions": ["s3:GetObject"]},
        "behavior-baseline": {"agent_id": "claude-code"},
        "code-provenance": {"code": "eval(user)", "language": "python", "filename": "fixture.py"},
        "mcp-scorecard": {"manifest": {"name": "fixture", "tools": []}},
    }
    # Use the shipped queue helper inside the real image; no host Redis ports.
    command = "import sys; sys.path.insert(0, '/app/shared'); from job_queue import enqueue_job; import json; print(json.dumps([enqueue_job(app, payload) for app, payload in " + repr(cases) + ".items()]))"
    ids = json.loads(stack.compose("exec", "-T", "api-scorecard", "python", "-c", command).stdout)
    assert len(ids) == 4 and all(not job.startswith("sync:") for job in ids)
    results = {}
    with httpx.Client(trust_env=False, timeout=10) as client:
        url = stack.url("frontend-scorecard")
        deadline = time.monotonic() + 40
        while time.monotonic() < deadline and len(results) < 4:
            for kind, job in zip(cases, ids):
                response = client.get(url + "/jobs/" + job)
                assert response.status_code == 200
                body = response.json()
                assert body["status"] != "error", body
                if body["status"] == "complete":
                    assert body["result"]
                    results[kind] = body["result"]
            time.sleep(0.1)
    assert set(results) == set(cases)
    assert results["blast-radius"]["nodes"]
    assert results["behavior-baseline"]["summary"]["source"] == "heuristic"
    assert results["code-provenance"]["risks"]["findings"]
    assert "not configured" in str(results["mcp-scorecard"])
    (stack.evidence / "legacy-worker.json").write_text(json.dumps({"engines": list(results), "worker": "real Redis compatibility worker", "durability": "TTL cache only; not PostgreSQL ledger", "providers": "disabled"}, indent=2))
