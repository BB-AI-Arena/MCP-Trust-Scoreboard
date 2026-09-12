import json
import re

import pytest

pytestmark = pytest.mark.acceptance

MANIFEST = {"name": "Fixture Connector", "version": "1.0.0", "description": "Read-only fixture",
            "tools": [{"name": "read_notes", "description": "Read supplied notes", "inputSchema": {"type": "object"}}]}


def report(page, folder, button, target, expected):
    from pypdf import PdfReader
    from PIL import ImageStat
    # Validate rendered source content before exercising the real download.
    content = page.locator(target)
    for word in expected:
        assert word.lower() in content.inner_text().lower()
    with page.expect_download(timeout=45000) as download:
        page.get_by_role("button", name=button, exact=True).click()
    path = folder / download.value.suggested_filename
    download.value.save_as(path)
    pdf = PdfReader(path)
    assert 1 <= len(pdf.pages) <= 12
    images = []
    for index, sheet in enumerate(pdf.pages):
        assert float(sheet.mediabox.width) > 200
        assert float(sheet.mediabox.height) > 200
        for embedded in sheet.images:
            picture = embedded.image.convert("RGB")
            assert min(picture.size) > 100
            assert max(ImageStat.Stat(picture).stddev) > 15, "blank report panel"
            picture.save(folder / f"report-page-{index}-{len(images)}.png")
            images.append(picture)
    assert images, "report lost its rendered findings/graph"
    # Guard against a clipped/empty lower portion of the report.
    largest = max(images, key=lambda image: image.width * image.height)
    for fraction in (0.2, 0.5, 0.8):
        y = int(largest.height * fraction)
        band = largest.crop((0, y, largest.width, min(largest.height, y + max(30, largest.height // 10))))
        assert max(ImageStat.Stat(band).stddev) > 5, "empty/clipped report band"
    (folder / "report-review.json").write_text(json.dumps({"file": path.name, "pages": len(pdf.pages),
        "expected_rendered_content": expected, "embedded_images": len(images),
        "review": "Automated content/layout checks; PNGs retained for human visual review."}, indent=2))


def test_blast_submission_graph_report(browser_page, stack):
    page, folder = browser_page
    page.goto(stack.url("frontend-blast"))
    assert page.get_by_role("button", name="Analyze Blast Radius").is_enabled()
    with page.expect_response(lambda r: r.url.endswith("/analyze") and r.request.method == "POST") as response:
        page.get_by_role("button", name="Analyze Blast Radius").click()
    assert response.value.status == 200
    result = response.value.json()
    assert result["nodes"] and result["edges"]
    page.locator("#blast-results").wait_for()
    assert page.locator("#blast-results svg circle").count() >= len(result["nodes"])
    report(page, folder, "Export PDF Report", "#blast-results", ["Blast", "Mitigation"])


def test_behavior_real_seeded_routes_and_graphs(browser_page, stack):
    page, folder = browser_page
    page.goto(stack.url("frontend-baseline"))
    page.get_by_text("Demo mode · seeded examples").wait_for()
    page.get_by_text("Analysis source: heuristic", exact=False).wait_for()
    assert page.locator(".recharts-surface path.recharts-line-curve").count() > 0
    assert page.locator("main svg rect").count() >= 100
    assert page.get_by_role("alert").count() == 0
    # This workspace has never implemented a report download or submit form.
    # Do not fabricate one to satisfy acceptance or silently add a feature.
    agents = page.request.get(stack.url("frontend-baseline") + "/agents").json()["agents"]
    assert len(agents) >= 2
    page.get_by_role("button", name=re.compile(re.escape(agents[1]["name"]))).click()
    page.get_by_text("Analysis source: heuristic", exact=False).wait_for()
    (folder / "coverage.json").write_text(json.dumps({"data": "real backend seeded demo", "report_download": "not implemented in this workspace"}))


def test_artifact_submission_experimental_report(browser_page, stack):
    page, folder = browser_page
    page.goto(stack.url("frontend-provenance"))
    page.get_by_placeholder("Paste code here...").fill("import subprocess\nsubprocess.run(user_input, shell=True)\n")
    page.get_by_placeholder("e.g. config.py").fill("fixture.py")
    with page.expect_response(lambda r: r.url.endswith("/scan") and r.request.method == "POST") as response:
        page.get_by_role("button", name="Scan for Provenance").click()
    assert response.value.status == 200
    page.locator("#provenance-results").wait_for()
    page.get_by_text("Experimental stylistic signals", exact=False).wait_for()
    assert "subprocess.run" in page.locator("#provenance-results").inner_text()
    assert "shell" in page.locator("#provenance-results").inner_text().lower()
    report(page, folder, "Export PDF Report", "#provenance-results", ["fixture.py", "Experimental", "Risk"])


def test_connector_manifest_results_report(browser_page, stack):
    page, folder = browser_page
    page.goto(stack.url("frontend-scorecard"))
    page.locator('input[type="file"]').set_input_files({"name": "manifest.json", "mimeType": "application/json", "buffer": json.dumps(MANIFEST).encode()})
    with page.expect_response(lambda r: r.url.endswith("/scan") and r.request.method == "POST") as response:
        page.get_by_role("button", name="Analyze MCP Server").click()
    assert response.value.status == 200
    assert "not configured" in json.dumps(response.value.json())
    page.locator("#results-view").wait_for()
    result = response.value.json()
    ring = page.locator("circle[data-report-offset]")
    circumference = float(ring.get_attribute("stroke-dasharray"))
    assert float(ring.get_attribute("data-report-offset")) == pytest.approx(circumference * (1 - result["overall_score"] / 100))
    assert page.locator("[data-report-width]").count() == len(result["dimensions"])
    report(page, folder, "Export PDF", "#results-view", ["Trust Rating", "Overall Score", "not configured"])


@pytest.mark.parametrize("workspace,api,submit", [
    ("blast", "analyze", "Analyze Blast Radius"),
    ("provenance", "scan", "Scan for Provenance"),
    ("scorecard", "scan", "Analyze MCP Server"),
])
def test_real_backend_outage_is_visible(browser_page, stack, workspace, api, submit):
    page, _ = browser_page
    page.goto(stack.url(f"frontend-{workspace}"))
    if workspace == "provenance":
        page.get_by_placeholder("Paste code here...").fill("print('fixture')")
    if workspace == "scorecard":
        page.locator('input[type="file"]').set_input_files({"name": "manifest.json", "mimeType": "application/json", "buffer": json.dumps(MANIFEST).encode()})
    stack.compose("stop", "--timeout", "2", f"api-{workspace}")
    try:
        with page.expect_response(lambda r: r.url.endswith('/' + api) and r.request.method == "POST") as response:
            page.get_by_role("button", name=re.compile(submit)).click()
        assert response.value.status in {502, 504}  # refused vs timed-out upstream
        page.get_by_text(re.compile("error|failed|Unexpected", re.I)).first.wait_for()
    finally:
        stack.compose("up", "-d", "--wait", f"api-{workspace}")


def test_behavior_outage_never_invents_agents(browser_page, stack):
    page, _ = browser_page
    stack.compose("stop", "--timeout", "2", "api-baseline")
    try:
        page.goto(stack.url("frontend-baseline"))
        page.get_by_role("alert").wait_for()
        assert page.locator("aside li").count() == 0
        assert page.locator(".recharts-line-curve").count() == 0
    finally:
        stack.compose("up", "-d", "--wait", "api-baseline")


def test_real_validation_errors_and_ingestion(stack):
    import httpx
    with httpx.Client(trust_env=False, timeout=10) as client:
        for service, route, payload, code in [
            ("blast", "/analyze", {"agent_name": ""}, 422),
            ("provenance", "/scan", {"code": "", "language": "Python"}, 422),
            ("scorecard", "/scan", {}, 400),
            ("baseline", "/ingest", {"agent_id": "unknown", "metric": "api_call_rate", "value": 1}, 404),
        ]:
            response = client.post(stack.url("frontend-" + service) + route, json=payload)
            assert response.status_code == code, (service, response.text)
        url = stack.url("frontend-baseline")
        agent = client.get(url + "/agents").json()["agents"][0]["id"]
        response = client.post(url + "/ingest", json={"agent_id": agent, "metric": "api_call_rate", "value": 1000})
        assert response.status_code == 200
        assert "is_anomalous" in response.json()


def test_artifact_repository_treemap_and_report(browser_page, stack):
    import io
    import zipfile
    page, folder = browser_page
    archive = io.BytesIO()
    with zipfile.ZipFile(archive, "w") as handle:
        handle.writestr("fixture.py", "eval(user)\n")
        handle.writestr("safe.py", "answer = 42\n")
    page.goto(stack.url("frontend-provenance"))
    page.get_by_role("button", name="Upload Repo (.zip)", exact=False).click()
    page.locator('input[type="file"]').set_input_files({"name": "fixture.zip", "mimeType": "application/zip", "buffer": archive.getvalue()})
    with page.expect_response(lambda r: r.url.endswith("/scan-repo") and r.request.method == "POST") as response:
        page.get_by_role("button", name="Scan for Provenance").click()
    assert response.value.status == 200
    page.locator(".treemap-cell").first.wait_for()
    assert page.locator(".treemap-cell").count() == 2
    report(page, folder, "Export PDF Report", "#provenance-results", ["fixture.py", "safe.py", "Experimental", "Scanned Files"])


def test_browser_input_validation(browser_page, stack):
    page, _ = browser_page
    page.goto(stack.url("frontend-blast"))
    name = page.get_by_placeholder("e.g. GPT-4 Code Assistant")
    name.fill("")
    assert page.get_by_role("button", name="Analyze Blast Radius").is_disabled()
    assert name.evaluate("element => element.validity.valueMissing")
    assert page.locator("#blast-results").count() == 0
    page.goto(stack.url("frontend-provenance"))
    page.get_by_placeholder("Paste code here...").fill("   ")
    assert page.get_by_role("button", name="Scan for Provenance").is_disabled()
    page.goto(stack.url("frontend-scorecard"))
    with page.expect_event("dialog") as dialog:
        page.locator('input[type="file"]').set_input_files({"name": "bad.json", "mimeType": "application/json", "buffer": b"not json"})
    assert "Invalid JSON" in dialog.value.message
    dialog.value.accept()
    assert page.get_by_role("button", name="Analyze MCP Server").is_disabled()
