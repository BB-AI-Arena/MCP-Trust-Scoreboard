from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).parents[1] / "src"))


def pytest_addoption(parser):
    parser.addoption("--run-integration", action="store_true", help="Build/run disposable platform and PostgreSQL containers")
    parser.addoption("--run-acceptance", action="store_true", help="Build/run real Compose stack and Chromium")


def pytest_collection_modifyitems(config, items):
    for item in items:
        if "acceptance" in item.keywords and not config.getoption("--run-acceptance"):
            item.add_marker(pytest.mark.skip(reason="requires --run-acceptance; separate mandatory CI job"))
    if not config.getoption("--run-integration"):
        for item in items:
            if "integration" in item.keywords:
                item.add_marker(pytest.mark.skip(reason="requires explicit --run-integration; mandatory in CI"))
