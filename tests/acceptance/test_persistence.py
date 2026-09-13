import json
import subprocess
import time

import httpx
import pytest

pytestmark = pytest.mark.acceptance


def wait_for(check, seconds=45):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        try:
            result = check()
            if result:
                return result
        except httpx.HTTPError:
            pass
        time.sleep(0.2)
    raise AssertionError("runtime did not become ready")


def test_installed_result_survives_recreation_and_backup_restore(stack):
    with httpx.Client(trust_env=False, timeout=5) as client:
        headers = {"Authorization": "Bearer " + stack.config_values["AGENT_TRUST_API_TOKEN"]}
        url = stack.url("api-platform")
        assert client.post(url + "/api/v1/assessments", json={"subject_id": "fixture"}).status_code == 401
        submitted = client.post(url + "/api/v1/assessments", headers=headers,
            json={"subject_id": "volume-fixture", "content": "eval(user)", "idempotency_key": "survives-recreation"})
        assert submitted.status_code == 202
        job_id = submitted.json()["job_id"]
        def completed():
            job = client.get(url + "/api/v1/jobs/" + job_id, headers=headers).json()
            return job if job.get("status") == "complete" else None
        before = wait_for(completed)
        assert before["result"]["provider"] == "rules-only"
        original_containers = {s: stack.container(s) for s in ("api-platform", "worker-platform", "postgres")}
        stack.compose("up", "-d", "--force-recreate", "--wait", "--wait-timeout", "120",
                      "postgres", "api-platform", "worker-platform", timeout=180)
        assert all(stack.container(s) != c for s, c in original_containers.items())
        url = stack.url("api-platform")
        after = wait_for(completed)
        assert before["result"] == after["result"]
        assert before["attempts"] == after["attempts"] == 1
        assert client.get(url + "/api/v1/assessments", headers=headers).json()["items"][0]["result"] == before["result"]

    # Check installed release image, not a source mount or test installation.
    stack.compose("exec", "-T", "api-platform", "python", "-c",
        "import importlib.util, agent_trust; assert importlib.util.find_spec('pytest') is None; assert importlib.util.find_spec('playwright') is None; assert '/site-packages/' in agent_trust.__file__")
    stack.compose("exec", "-T", "api-platform", "python", "-m", "pip", "check")
    pg = stack.container("postgres")
    dump = stack.directory / "backup.dump"
    with dump.open("wb") as handle:
        subprocess.run(["docker", "exec", pg, "pg_dump", "-U", "koi", "-d", "koi_security", "-Fc"], stdout=handle, stderr=subprocess.PIPE, check=True, timeout=30)
    stack.compose("exec", "-T", "postgres", "createdb", "-U", "koi", "restore_fixture")
    with dump.open("rb") as handle:
        subprocess.run(["docker", "exec", "-i", pg, "pg_restore", "-U", "koi", "--exit-on-error", "-d", "restore_fixture"], stdin=handle, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True, timeout=30)
    restored = stack.compose("exec", "-T", "postgres", "psql", "-U", "koi", "-d", "restore_fixture", "-Atc",
        f"SELECT result FROM agent_trust_jobs WHERE id='{job_id}'").stdout
    assert json.loads(restored) == before["result"]
    (stack.evidence / "persistence.json").write_text(json.dumps({"container_recreation": "passed", "backup_restore": "separate disposable database", "installed_without_test_extras": True, "provider": "rules-only"}, indent=2))


def test_previous_schema_upgrade_and_repeated_migration(stack):
    from acceptance_stack import ROOT
    stack.compose("exec", "-T", "postgres", "createdb", "-U", "koi", "upgrade_fixture")
    original = (ROOT / "src/agent_trust/storage/migrations/001_initial.sql").read_bytes()
    seed = b"""
INSERT INTO agent_trust_jobs(id,workspace_id,kind,payload,status,attempts,max_attempts,
available_at,result,idempotency_key,created_at,updated_at) VALUES
('old-complete','local','assessment','{"subject_id":"old-subject"}','complete',1,3,
'2026-01-01T00:00:00+00:00','{"preserved":true}','old-key','2026-01-01T00:00:00+00:00','2026-01-01T00:00:00+00:00');
CREATE TABLE legacy_fixture (id integer primary key, note text);
INSERT INTO legacy_fixture VALUES (1,'preserve unrelated records');
"""
    subprocess.run(["docker", "exec", "-i", stack.container("postgres"), "psql", "-U", "koi", "-d", "upgrade_fixture", "-v", "ON_ERROR_STOP=1"], input=original + seed, capture_output=True, check=True, timeout=30)
    url = "postgresql+psycopg://koi:" + stack.config_values["POSTGRES_PASSWORD"] + "@postgres:5432/upgrade_fixture"
    for _ in range(2):
        stack.compose("run", "--rm", "--no-deps", "-e", "DATABASE_URL=" + url, "api-platform", "python", "-c",
            "from agent_trust.config import Settings; from agent_trust.storage.database import make_engine,create_schema; create_schema(make_engine(Settings.from_env().database_url))")
    def sql(query):
        return stack.compose("exec", "-T", "postgres", "psql", "-U", "koi", "-d", "upgrade_fixture", "-Atc", query).stdout.strip()
    assert sql("SELECT count(*) FROM agent_trust_migrations") == "5"
    assert json.loads(sql("SELECT result FROM agent_trust_jobs WHERE id='old-complete'")) == {"preserved": True}
    projection = json.loads(sql("SELECT payload FROM agent_trust_records WHERE id='old-complete'"))
    assert projection["status"] == "complete" and projection["result"] == {"preserved": True}
    assert sql("SELECT note FROM legacy_fixture") == "preserve unrelated records"
