from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).parent))


@pytest.fixture
def falcon_server(tmp_path, monkeypatch):
    import subprocess
    from threading import Thread
    from falcon_fixture import initial_state, server, CID
    from agent_trust.adapters.connectors.falcon_client import FalconConfig

    cert, key = tmp_path/'cert.pem', tmp_path/'key.pem'
    subprocess.run(['openssl','req','-x509','-newkey','rsa:2048','-nodes','-days','1',
        '-keyout',str(key),'-out',str(cert),'-subj','/CN=localhost',
        '-addext','subjectAltName=IP:127.0.0.1,DNS:localhost'],capture_output=True,check=True,timeout=20)
    state = initial_state()
    http = server(state,('127.0.0.1',0),str(cert),str(key))
    thread = Thread(target=http.serve_forever,daemon=True)
    thread.start()
    monkeypatch.setenv('SSL_CERT_FILE',str(cert))
    config = FalconConfig('fixture',CID,client_id='fixture-client',client_secret='fixture-only',
        fixture_origin=f'https://127.0.0.1:{http.server_port}',fixture_cidrs=('127.0.0.1/32',))
    try:
        yield state, config
    finally:
        http.shutdown()
        http.server_close()
        thread.join(timeout=2)


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
