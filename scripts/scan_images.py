#!/usr/bin/env python3
"""Scan real image archives; retain full findings and CycloneDX, gate HIGH/CRITICAL.

No Docker socket or credentials are passed to the scanner. Only its database
download has network access. All image processing is offline in a bounded tool
container. No ignore files, ignore-unfixed, or blanket exceptions.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import tempfile

from acceptance_stack import AcceptanceStack, run

SCANNER = "aquasec/trivy:0.74.0@sha256:62b1e65e8869bc4b4c6aa4fa2b21595256c7c2f6018a9d9ad61caf87187c1969"


def scan(inventory, output):
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=True)
    run(["docker", "pull", SCANNER], timeout=180)
    with tempfile.TemporaryDirectory(prefix="atp-scan-") as temporary:
        work = Path(temporary)
        cache = work / "cache"
        cache.mkdir()
        base = ["docker", "run", "--rm", "--memory", "2g", "--cpus", "2",
                "--mount", f"type=bind,src={work},dst=/work",
                "--mount", f"type=bind,src={output},dst=/evidence"]
        network_base = [*base, SCANNER, "--cache-dir", "/work/cache"]
        downloaded = run([*network_base, "image", "--download-db-only"], timeout=240, check=False)
        (output / "database-download.log").write_text(downloaded.stdout + downloaded.stderr)
        if downloaded.returncode:
            raise RuntimeError("Scanner database unavailable; release gate fails")
        metadata = json.loads((cache / "db/metadata.json").read_text())
        updated = datetime.fromisoformat(metadata["UpdatedAt"].replace("Z", "+00:00"))
        age = (datetime.now(timezone.utc) - updated).total_seconds()
        assert 0 <= age <= 48 * 3600, f"Scanner database is not fresh: {age}s"
        offline = [*base, "--network", "none", SCANNER, "--cache-dir", "/work/cache"]
        version = run([*offline, "--version"]).stdout
        summary = {"source_sha": inventory["source_sha"], "dirty_source": inventory["dirty_source"],
                   "scanner_image": SCANNER, "scanner_version": version, "database": metadata,
                   "scanned_at": datetime.now(timezone.utc).isoformat(), "policy": "fail on any HIGH or CRITICAL, including unfixed", "images": []}
        # Image content deduplication does not drop service/image identities.
        by_id = {}
        for item in inventory["images"]:
            by_id.setdefault(item["id"], []).append(item)
        for image_id, services in by_id.items():
            name = services[0]["service"]
            archive = work / "image.tar"
            run(["docker", "image", "save", "--output", str(archive), image_id], timeout=120)
            common = [*offline, "image", "--input", "/work/image.tar", "--skip-db-update", "--offline-scan", "--scanners", "vuln"]
            commands = [
                [*common, "--format", "json", "--output", f"/evidence/{name}.vulnerabilities.json"],
                [*common, "--format", "cyclonedx", "--output", f"/evidence/{name}.cdx.json"],
            ]
            logs = []
            for command in commands:
                result = run(command, timeout=240)
                logs.append(result.stderr)
            (output / f"{name}.log").write_text("\n".join(logs))
            findings = json.loads((output / f"{name}.vulnerabilities.json").read_text())
            sbom = json.loads((output / f"{name}.cdx.json").read_text())
            assert sbom["bomFormat"] == "CycloneDX" and sbom["components"], "missing SBOM package inventory"
            if name.startswith("frontend-"):
                assert any(c.get("name") == "jspdf" for c in sbom["components"]), "frontend SBOM lost bundled dependency inventory"
            vulnerabilities = [v for r in findings.get("Results", []) for v in r.get("Vulnerabilities", [])]
            blockers = [{k: v.get(k) for k in ("VulnerabilityID", "PkgName", "InstalledVersion", "FixedVersion", "Severity", "PrimaryURL")} for v in vulnerabilities if v["Severity"] in {"HIGH", "CRITICAL"}]
            summary["images"].append({"services": services, "commands": [[part.replace(str(work), "<temporary>").replace(str(output), "<evidence>") for part in c] for c in commands], "total_findings": len(vulnerabilities), "blockers": blockers, "components": len(sbom["components"])})
            archive.unlink()  # exact archive created by this iteration only
        summary["passed"] = not any(item["blockers"] for item in summary["images"])
        (output / "scan-summary.json").write_text(json.dumps(summary, indent=2))
        checksums = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in output.iterdir() if p.is_file() and p.name != "checksums.json"}
        (output / "checksums.json").write_text(json.dumps(checksums, indent=2))
        return summary["passed"]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="evidence/containers")
    args = parser.parse_args()
    stack = AcceptanceStack(args.output)
    try:
        stack.build()
        for service in stack.config["services"].values():
            if "build" not in service:
                run(["docker", "pull", service["image"]], timeout=180)
        passed = scan(stack.inventory(), args.output)
    finally:
        stack.close()
        # Include final redacted teardown logs, not only pre-teardown evidence.
        output = Path(args.output)
        checksums = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in output.iterdir() if p.is_file() and p.name != "checksums.json"}
        (output / "checksums.json").write_text(json.dumps(checksums, indent=2))
    if not passed:
        raise SystemExit("Container vulnerabilities block release; see scan-summary.json (no exceptions applied)")


if __name__ == "__main__":
    main()
