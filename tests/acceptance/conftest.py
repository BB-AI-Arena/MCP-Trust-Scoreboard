import json
import os
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
from acceptance_stack import AcceptanceStack


@pytest.fixture(scope="session")
def stack():
    instance = AcceptanceStack(os.getenv("ACCEPTANCE_EVIDENCE", "evidence/acceptance"))
    try:
        instance.build()
        instance.start()
        instance.inventory()
        yield instance
    finally:
        instance.close()


@pytest.fixture
def browser_page(stack, request):
    from playwright.sync_api import sync_playwright
    folder = stack.evidence / request.node.name
    folder.mkdir(exist_ok=True)
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        context = browser.new_context(viewport={"width": 1440, "height": 1100}, accept_downloads=True)
        context.tracing.start(screenshots=True, snapshots=True, sources=True)
        page = context.new_page()
        page.set_default_timeout(20000)
        errors = []
        external_requests = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.on("request", lambda request: external_requests.append(request.url) if request.url.startswith(("https://", "http://")) and not request.url.startswith("http://127.0.0.1:") else None)
        try:
            yield page, folder
            assert not errors, errors
            assert not external_requests, external_requests
        finally:
            page.screenshot(path=str(folder / "page.png"), full_page=True)
            context.tracing.stop(path=str(folder / "trace.zip"))
            (folder / "browser-errors.txt").write_text("\n".join(errors))
            (folder / "external-requests.json").write_text(json.dumps(external_requests))
            browser.close()
