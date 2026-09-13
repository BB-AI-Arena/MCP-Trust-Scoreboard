"""Exercise installed wheels, image CMD, HTTP auth, real worker, and PostgreSQL."""

from concurrent.futures import ThreadPoolExecutor
import json

import httpx
import pytest

from .conftest import docker, eventually

pytestmark = pytest.mark.integration
TOKEN = "disposable-runtime-fixture-token"
HEADERS = {"Authorization": f"Bearer {TOKEN}"}


def start_api(containers, platform_image, database_url, *environment, command=()):
    name = containers.run("api", platform_image,
        "-e", f"DATABASE_URL={database_url}",
        "-e", f"AGENT_TRUST_API_TOKEN={TOKEN}", *environment, command=command)
    url = f"http://{containers.address(name)}:8080"
    with httpx.Client(base_url=url, trust_env=False, timeout=3) as client:
        def ready():
            state = json.loads(docker("inspect", "--format", "{{json .State}}", name))
            assert state["Running"], docker("logs", name)
            return client.get("/readiness").status_code == 200
        eventually(ready)
    return name, url


def test_authenticated_assessment_survives_full_restart(containers, postgres, platform_image):
    # Start worker and image CMD concurrently on an unmigrated database.
    # Only the two required env values: all optional Settings defaults are real.
    # No Redis or cloud credentials; internal test network has no external route.
    # This fixture's isolation does not certify production egress controls.
    database_url = postgres["internal"].replace("postgresql+psycopg://", "postgresql://")
    worker = containers.run("worker", platform_image,
        "-e", f"DATABASE_URL={database_url}", "-e", f"AGENT_TRUST_API_TOKEN={TOKEN}",
        command=("agent-trust-worker",))
    api, url = start_api(containers, platform_image, database_url)
    request = {"subject_id": "fixture-agent", "content": "eval(user)",
               "idempotency_key": "one-assessment", "workspace_id": "forged"}

    with httpx.Client(base_url=url, trust_env=False, timeout=3) as client:
        assert client.get("/health").json()["status"] == "ok"
        assert client.get("/version").json()["application"] == "2.0.0-alpha.1"
        assert client.post("/api/v1/assessments", json=request).status_code == 401
        assert client.post("/api/v1/assessments", json=request,
                           headers={"Authorization": "Bearer wrong"}).status_code == 401
        with ThreadPoolExecutor(max_workers=4) as pool:
            submitted = list(pool.map(lambda _: client.post("/api/v1/assessments", json=request, headers=HEADERS), range(4)))
        assert all(r.status_code == 202 for r in submitted), ([r.text for r in submitted], docker("logs", api))
        ids = {r.json()["job_id"] for r in submitted}
        assert len(ids) == 1
        job_id = ids.pop()
        job_url = f"/api/v1/jobs/{job_id}"
        assert client.get(job_url).status_code == 401

        def completed():
            response = client.get(job_url, headers=HEADERS)
            assert response.status_code == 200
            job = response.json()
            assert job["status"] != "failed", job
            return job if job["status"] == "complete" else None

        job = eventually(completed)
        assert job["workspace_id"] == "local"
        assert job["attempts"] == 1
        result = job["result"]
        assert result["provider"] == "rules-only"
        assert result["findings"][0]["rule_id"] == "execution_authority"
        projection = client.get("/api/v1/assessments", headers=HEADERS).json()["items"]
        assert len(projection) == 1
        assert projection[0]["status"] == "complete"
        assert projection[0]["result"] == result

        containers.stop(api)
        containers.stop(worker)
        containers.restart(postgres["name"])
        eventually(postgres["ready"])
        containers.restart(api)
        containers.restart(worker)
        # Docker may assign a different bridge IP after a stopped container
        # starts; re-resolve the service like a normal DNS client would.
        client.base_url = f"http://{containers.address(api)}:8080"
        eventually(lambda: client.get("/readiness").status_code == 200)
        assert client.get(job_url, headers=HEADERS).json()["result"] == result
        duplicate = client.post("/api/v1/assessments", headers=HEADERS, json=request)
        assert duplicate.status_code == 202
        assert duplicate.json()["job_id"] == job_id
        assert duplicate.json()["status"] == "complete"
        projection = client.get("/api/v1/assessments", headers=HEADERS).json()["items"]
        assert len(projection) == 1
        assert projection[0]["result"] == result
        assert projection[0]["status"] == "complete"

        # Actual readiness query fails with an established but disconnected pool.
        containers.stop(worker)
        containers.stop(postgres["name"])
        assert client.get("/readiness").status_code == 503
        containers.restart(postgres["name"])
        eventually(postgres["ready"])
        eventually(lambda: client.get("/readiness").status_code == 200)

    # A separate authenticated server-bound workspace cannot retrieve the job.
    _, other_url = start_api(containers, platform_image, database_url,
        "-e", "AGENT_TRUST_WORKSPACE_ID=other", "-e", "AGENT_TRUST_API_SCOPES=read",
        "-e", "AGENT_TRUST_HOST=0.0.0.0", command=("agent-trust-api",))
    with httpx.Client(base_url=other_url, headers=HEADERS, trust_env=False, timeout=3) as other:
        assert other.get(job_url).status_code == 404
        assert other.get("/api/v1/assessments").json()["items"] == []
        assert other.post("/api/v1/assessments", json=request).status_code == 403


@pytest.mark.parametrize("command", [(), ("agent-trust-worker",)])
def test_image_refuses_startup_without_api_token(containers, platform_image, command):
    name = containers.run("missing-token", platform_image, command=command)

    def exited():
        state = json.loads(docker("inspect", "--format", "{{json .State}}", name))
        return state if state["Status"] == "exited" else None

    state = eventually(exited)
    assert state["ExitCode"] != 0
    assert "AGENT_TRUST_API_TOKEN is required" in docker("logs", name)
