from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).parents[1] / "src"))


def pytest_addoption(parser):
    parser.addoption("--run-integration", action="store_true", help="Build/run disposable platform and PostgreSQL containers")


def pytest_collection_modifyitems(config, items):
    if not config.getoption("--run-integration"):
        for item in items:
            if "integration" in item.keywords:
                item.add_marker(pytest.mark.skip(reason="requires explicit --run-integration; mandatory in CI"))
