import importlib.util
import json
from pathlib import Path


def test_initial_status_is_committed_before_worker_can_receive(monkeypatch):
    path = Path(__file__).parents[1] / "shared/job_queue.py"
    spec = importlib.util.spec_from_file_location("fixture_queue", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    calls = []
    class Client:
        def pipeline(self, transaction):
            assert transaction is True
            return self
        def setex(self, key, ttl, value):
            calls.append(("status", json.loads(value)["status"], ttl))
        def rpush(self, key, value):
            calls.append(("queue", key, json.loads(value)["app"]))
        def execute(self):
            calls.append(("commit",))
    monkeypatch.setattr(module, "_redis_client", Client())
    module.enqueue_job("code-provenance", {"code": "fixture"})
    assert calls == [("status", "queued", 3600), ("queue", "koi:scan:queue", "code-provenance"), ("commit",)]
