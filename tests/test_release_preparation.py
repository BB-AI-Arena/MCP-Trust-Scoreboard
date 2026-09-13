"""Release evidence must identify clean, exact source and never imply approval."""

import json
from pathlib import Path
import shutil
import subprocess
import sys

import pytest


@pytest.fixture
def release_checkout(tmp_path):
    root = tmp_path / "repo"
    (root / "scripts").mkdir(parents=True)
    shutil.copyfile(Path(__file__).parents[1] / "scripts/prepare_release.py", root / "scripts/prepare_release.py")
    (root / "VERSION").write_text("2.0.0-alpha.1\n")

    def git(*args):
        return subprocess.check_output(["git", "-C", str(root), *args], text=True, stderr=subprocess.PIPE, timeout=10).strip()

    git("init", "--quiet")
    git("add", "scripts/prepare_release.py", "VERSION")
    git("-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid",
        "-c", "commit.gpgsign=false", "commit", "--quiet", "-m", "test: release fixture")
    return root, git("rev-parse", "HEAD"), git


def prepare(root, sha, output, version="2.0.0-alpha.1"):
    return subprocess.run([sys.executable, "scripts/prepare_release.py", "--sha", sha,
        "--version", version, "--output", str(output)], cwd=root, text=True,
        capture_output=True, timeout=10)


def test_clean_exact_source_produces_only_unapproved_manifest(release_checkout, tmp_path):
    root, sha, git = release_checkout
    output = tmp_path / "manifest.json"
    assert prepare(root, sha, output).returncode == 0
    manifest = json.loads(output.read_text())
    assert manifest["source_sha"] == sha
    assert manifest["release_ready"] is False
    assert manifest["published"] is False
    assert manifest["tag_created"] is False
    assert len(manifest["files"]) == 2
    assert git("tag", "--list") == ""
    assert git("status", "--porcelain") == ""


@pytest.mark.parametrize("change", ["tracked", "untracked", "version", "sha"])
def test_dirty_or_mismatched_source_cannot_prepare(release_checkout, tmp_path, change):
    root, sha, _ = release_checkout
    version = "2.0.0-alpha.1"
    if change == "tracked":
        (root / "scripts/prepare_release.py").write_text((root / "scripts/prepare_release.py").read_text() + "\n# dirty\n")
    elif change == "untracked":
        (root / "untracked.txt").write_text("fixture")
    elif change == "version":
        version = "2.0.0"
    else:
        sha = "0" * 40
    output = tmp_path / "manifest.json"
    result = prepare(root, sha, output, version)
    assert result.returncode != 0
    assert not output.exists()
    assert "clean checkout" in result.stderr or "mismatch" in result.stderr
