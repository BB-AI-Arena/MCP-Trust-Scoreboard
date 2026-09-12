"""Run the actual Compose model with disposable resources and ephemeral ports.

Never reads an operator .env, never touches another Compose project. Only the
named resources created by this instance can be removed. Evidence excludes env.
"""
from __future__ import annotations
import json
import os
from pathlib import Path
import subprocess
import tempfile
import uuid

ROOT = Path(__file__).resolve().parents[1]


def run(args, *, timeout=120, check=True, **kwargs):
    result = subprocess.run(args, text=True, capture_output=True, timeout=timeout, **kwargs)
    if check and result.returncode:
        raise RuntimeError(f"{args[:3]} failed ({result.returncode}): {result.stderr[-3000:]}")
    return result


class AcceptanceStack:
    def __init__(self, evidence):
        self.project = "atp-acceptance-" + uuid.uuid4().hex[:12]
        self.evidence = Path(evidence).resolve()
        self.evidence.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(prefix=self.project + "-")
        self.directory = Path(self.temp.name)
        self.env = {k: v for k, v in os.environ.items() if not (k.startswith("AGENT_TRUST_") or k.startswith("COMPOSE_") or k in {"DATABASE_URL", "POSTGRES_USER", "POSTGRES_PASSWORD", "POSTGRES_DB", "GEMINI_API_KEY", "ABUSEIPDB_API_KEY", "SECRET_KEY", "SCAN_MODE", "REDIS_URL", "ALLOW_PRIVATE_COLLECTOR_TARGETS"})}
        run(["python3", str(ROOT / "scripts/configure_local.py"), "--output", str(self.directory / ".env")], env=self.env)
        self.config_values = dict(line.split("=", 1) for line in (self.directory / ".env").read_text().splitlines())
        # Resolved from the release Compose file, not a hand-built replacement.
        raw = run(["docker", "compose", "--env-file", str(self.directory / ".env"), "-f", str(ROOT / "docker-compose.yml"), "config", "--format", "json"], env=self.env)
        config = json.loads(raw.stdout)
        config["name"] = self.project
        for name, service in config["services"].items():
            if "build" in service:
                service["image"] = f"{self.project}-{name}:test"
            service["restart"] = "no"
            service["mem_limit"] = "768m"
            service["cpus"] = 1.0
            for port in service.get("ports", []):
                assert port["host_ip"] == "127.0.0.1"
                port["published"] = "0"
            if "healthcheck" in service:
                service["healthcheck"].update(interval="1s", timeout="5s", retries=60)
        for name, volume in config["volumes"].items():
            assert not volume.get("external")
            volume["name"] = f"{self.project}_{name}"
        for name, network in config.get("networks", {}).items():
            assert not network.get("external")
            network["name"] = f"{self.project}_{name}"
        self.config = config
        self.path = self.directory / "compose.json"
        self.path.write_text(json.dumps(config))
        self.path.chmod(0o600)
        self.command = ["docker", "compose", "-p", self.project, "-f", str(self.path)]

    def compose(self, *args, timeout=120, check=True):
        return run([*self.command, *args], env=self.env, timeout=timeout, check=check)

    def build(self):
        result = self.compose("build", "--pull", timeout=900, check=False)
        (self.evidence / "build.log").write_text(result.stdout + result.stderr)
        if result.returncode:
            raise RuntimeError("Compose build failed; see build.log")

    def start(self):
        result = self.compose("up", "-d", "--wait", "--wait-timeout", "180", timeout=240, check=False)
        if result.returncode:
            self.logs()
            raise RuntimeError("Compose startup failed: " + result.stderr[-2000:])

    def container(self, service):
        return self.compose("ps", "-q", "--all", service).stdout.strip()

    def url(self, service):
        target = self.config["services"][service]["ports"][0]["target"]
        address = self.compose("port", service, str(target)).stdout.strip()
        assert address.startswith("127.0.0.1:")
        return "http://" + address

    def logs(self):
        result = self.compose("logs", "--no-color", "--tail", "150", check=False)
        content = result.stdout + result.stderr
        for key in ("POSTGRES_PASSWORD", "AGENT_TRUST_API_TOKEN"):
            content = content.replace(self.config_values[key], "[REDACTED]")
        (self.evidence / "services.log").write_text(content)

    def inventory(self):
        items = []
        for name, service in self.config["services"].items():
            image = json.loads(run(["docker", "image", "inspect", service["image"]]).stdout)[0]
            items.append({"service": name, "image": service["image"], "id": image["Id"], "repo_digests": image.get("RepoDigests", [])})
        manifest = {"source_sha": run(["git", "rev-parse", "HEAD"], cwd=ROOT).stdout.strip(),
                    "dirty_source": bool(run(["git", "status", "--porcelain"], cwd=ROOT).stdout.strip()),
                    "project": self.project, "images": items}
        (self.evidence / "images.json").write_text(json.dumps(manifest, indent=2))
        return manifest

    def close(self):
        self.logs()
        # `down` WITHOUT -v; validate ownership before removing exact test volumes.
        self.compose("down", "--timeout", "5", timeout=90)
        for volume in self.config["volumes"].values():
            name = volume["name"]
            result = run(["docker", "volume", "inspect", name], check=False)
            if result.returncode == 0:
                labels = json.loads(result.stdout)[0].get("Labels", {})
                assert labels.get("com.docker.compose.project") == self.project
                run(["docker", "volume", "rm", name])
        for service in self.config["services"].values():
            if "build" in service:
                run(["docker", "image", "rm", service["image"]], check=False)
        self.temp.cleanup()
