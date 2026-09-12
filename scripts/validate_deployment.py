#!/usr/bin/env python3
"""Validate a resolved Compose document without echoing its credential values."""
import ipaddress
import json
import sys


def validate(config):
    for name, service in config["services"].items():
        ports = service.get("ports", [])
        if name in {"postgres", "redis"} and ports:
            raise ValueError("database/cache ports must not be published")
        environment = service.get("environment", {})
        token = environment.get("AGENT_TRUST_API_TOKEN", "")
        if name in {"api-platform", "worker-platform"}:
            if environment.get("AGENT_TRUST_AUTH_MODE", "token") != "token":
                raise ValueError("supported Compose deployments require token authentication")
            if len(token) < 32 or "change-me" in token.lower() or token.lower() in {"password", "local-only-secret"}:
                raise ValueError("configure a strong non-placeholder platform token")
        for port in ports:
            host = port.get("host_ip", "0.0.0.0")
            if not ipaddress.ip_address(host).is_loopback:
                if name != "api-platform":
                    raise ValueError("legacy interfaces are unauthenticated and local-only")
                if environment.get("AGENT_TRUST_ALLOW_REMOTE") != "true":
                    raise ValueError("nonlocal platform API requires intentional AGENT_TRUST_ALLOW_REMOTE=true plus TLS at a trusted proxy")
        for volume in service.get("volumes", []):
            if "docker.sock" in str(volume):
                raise ValueError("Docker sockets must not be mounted in application services")


if __name__ == "__main__":
    try:
        validate(json.load(sys.stdin))
    except (ValueError, KeyError) as exc:
        raise SystemExit(str(exc))
    print("Deployment boundaries validated; legacy workspaces remain local-only.")
