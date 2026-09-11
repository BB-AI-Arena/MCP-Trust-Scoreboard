#!/usr/bin/env python3
"""Prepare local release evidence; never creates tags or publishes artifacts."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path


def git(*args: str) -> str:
    return subprocess.check_output(["git", *args], text=True).strip()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--version", required=True)
    parser.add_argument("--sha", required=True)
    parser.add_argument("--output", default="release-manifest.json")
    args = parser.parse_args()
    root = Path(__file__).parents[1]
    actual_version = (root / "VERSION").read_text().strip()
    actual_sha = git("rev-parse", "HEAD")
    if actual_version != args.version:
        raise SystemExit(f"VERSION mismatch: expected {args.version}, found {actual_version}")
    if actual_sha != args.sha:
        raise SystemExit(f"SHA mismatch: expected {args.sha}, found {actual_sha}")
    files = []
    for name in git("ls-files").splitlines():
        path = root / name
        if path.is_file():
            files.append({"path": name, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
    manifest = {
        "version": actual_version,
        "source_sha": actual_sha,
        "published": False,
        "tag_created": False,
        "migration_notes": "docs/TECHNICAL_PLAN.md",
        "dependency_inventory": ["pyproject.toml", "app1-blast-radius/frontend/package-lock.json", "app2-behavior-baseline/frontend/package-lock.json", "app3-code-provenance/frontend/package-lock.json", "app4-mcp-scorecard/frontend/package-lock.json"],
        "sbom": "not generated until the maintainer-approved release job",
        "files": files,
    }
    (root / args.output).write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"Prepared {args.output} for {actual_version} at {actual_sha}; no tag or publication performed")


if __name__ == "__main__":
    main()
