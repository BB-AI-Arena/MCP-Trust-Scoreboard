"""Real, bounded Docker fixtures. Never connect to an operator's database."""

import ipaddress
import json
from pathlib import Path
import subprocess
import time
import uuid

import httpx
import pytest
from sqlalchemy import create_engine


ROOT = Path(__file__).resolve().parents[2]


def docker(*args, timeout=60):
    result = subprocess.run(["docker", *args], capture_output=True, text=True, timeout=timeout)
    if result.returncode:
        raise RuntimeError(f"docker {args[0]} failed: {result.stderr[-4000:]}")
    return (result.stdout + (result.stderr if args[0] == "logs" else "")).strip()


def eventually(check, timeout=40):
    deadline = time.monotonic() + timeout
    last_error = None
    while time.monotonic() < deadline:
        try:
            value = check()
            if value:
                return value
        except (httpx.HTTPError, RuntimeError, OSError) as exc:
            last_error = exc
        time.sleep(0.2)
    raise AssertionError(f"condition did not become true in {timeout}s: {last_error}")


class Containers:
    def __init__(self):
        self.prefix = f"agent-trust-test-{uuid.uuid4().hex[:12]}"
        self.network = self.prefix
        self.names = []

    def run(self, role, image, *args, command=()):
        name = f"{self.prefix}-{role}-{len(self.names)}"
        self.names.append(name)
        docker("run", "-d", "--name", name, "--label", f"agent-trust-test={self.prefix}",
               "--network", self.network, "--memory", "384m", "--cpus", "1", *args, image, *command)
        return name

    def address(self, name):
        # Linux host reaches the private bridge; no published ports or egress.
        networks = json.loads(docker("inspect", "--format", "{{json .NetworkSettings.Networks}}", name))
        address = networks[self.network]["IPAddress"]
        assert ipaddress.ip_address(address).is_private
        return address

    def stop(self, name):
        docker("stop", "--time", "5", name)

    def restart(self, name):
        docker("restart", "--time", "5", name)


@pytest.fixture(scope="session")
def postgres_image():
    docker("version", "--format", "{{.Server.Version}}")
    docker("pull", "postgres:15-alpine", timeout=180)
    # Freeze the image ID for this entire run, even if a tag later moves.
    return docker("image", "inspect", "postgres:15-alpine", "--format", "{{.Id}}")


@pytest.fixture(scope="session")
def platform_image():
    tag = f"agent-trust-platform:test-{uuid.uuid4().hex[:12]}"
    docker("build", "-f", str(ROOT / "Dockerfile.platform"), "-t", tag, str(ROOT), timeout=300)
    try:
        yield tag
    finally:
        docker("image", "rm", tag)


@pytest.fixture
def containers():
    group = Containers()
    docker("network", "create", "--internal", "--label", f"agent-trust-test={group.prefix}", group.network)
    try:
        yield group
    finally:
        # Only IDs created by this fixture; no globs, prune, or volume removal.
        for name in reversed(group.names):
            docker("rm", "--force", name)
        docker("network", "rm", group.network)


@pytest.fixture
def postgres(containers, postgres_image):
    # Real data uses the container's writable layer, which survives restart.
    # Cover the image's unused VOLUME with tmpfs to avoid anonymous volumes.
    name = containers.run("postgres", postgres_image,
        "--tmpfs", "/var/lib/postgresql/data",
        "-e", "PGDATA=/var/lib/postgresql/test-data",
        "-e", "POSTGRES_USER=fixture", "-e", "POSTGRES_PASSWORD=fixture-only",
        "-e", "POSTGRES_DB=fixture")

    def ready():
        result = subprocess.run(["docker", "exec", name, "pg_isready", "-h", "127.0.0.1", "-U", "fixture", "-d", "fixture"], capture_output=True, timeout=5)
        return result.returncode == 0

    eventually(ready)
    external = f"postgresql+psycopg://fixture:fixture-only@{containers.address(name)}:5432/fixture"
    internal = f"postgresql+psycopg://fixture:fixture-only@{name}:5432/fixture"
    return {"name": name, "external": external, "internal": internal, "ready": ready}


@pytest.fixture
def pg_engine(postgres):
    engine = create_engine(postgres["external"], pool_pre_ping=True,
                           connect_args={"options": "-c statement_timeout=5000 -c lock_timeout=3000"})
    try:
        yield engine
    finally:
        engine.dispose()
