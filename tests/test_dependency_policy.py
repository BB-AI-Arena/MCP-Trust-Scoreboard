import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from dependency_audit import classify


@pytest.mark.parametrize('tool,report', [
    ('python', {'dependencies':[{'name':'fixture','version':'1','vulns':[{'id':'fixture-CVE'}]}]}),
    ('npm', {'auditReportVersion':2,'vulnerabilities':{'fixture':{'severity':'critical'}},'metadata':{}}),
])
def test_owner_accepts_findings_without_calling_scan_clean(tool, report):
    result = classify(tool, 1, report)
    assert result['scan_completed'] and result['findings_present']
    assert result['policy'] == 'Accepted for development/alpha; hardening deferred.'


@pytest.mark.parametrize('tool,code,report', [
    ('python',1,{}), ('python',2,{'dependencies':[]}),
    ('python',1,{'dependencies':[{'name':'x','vulns':[]}]}),
    ('npm',1,{'error':{'code':'registry_unavailable'}}),
    ('npm',0,{}), ('npm',2,{'auditReportVersion':2,'vulnerabilities':{},'metadata':{}}),
])
def test_scanner_failure_remains_blocking(tool, code, report):
    with pytest.raises(ValueError):
        classify(tool, code, report)


def test_skipped_dependency_is_disclosed():
    result = classify('python',0,{'dependencies':[{'name':'editable-local','skip_reason':'not on PyPI'}]})
    assert result['skipped'] and not result['findings_present']


def test_risk_register_preserves_actual_artifact_provenance(tmp_path):
    import hashlib
    import json
    import subprocess

    source = tmp_path / 'evidence'
    source.mkdir()
    report = {'Results':[{'Vulnerabilities':[{'VulnerabilityID':'fixture-CVE',
        'PkgName':'fixture', 'InstalledVersion':'1', 'Severity':'HIGH'}]}]}
    scan = {'source_sha':'a'*40, 'scanned_at':'2026-09-12T00:00:00Z',
        'scanner_image':'fixture-scanner', 'database':{},
        'images':[{'services':[{'service':'fixture-service','id':'sha256:fixture'}]}]}
    files = {'scan-summary.json':scan, 'fixture-service.vulnerabilities.json':report}
    for name, data in files.items():
        (source/name).write_text(json.dumps(data))
    (source/'checksums.json').write_text(json.dumps({name:hashlib.sha256((source/name).read_bytes()).hexdigest() for name in files}))
    script = Path(__file__).resolve().parents[1] / 'scripts/record_security_findings.py'
    output = tmp_path / 'docs'
    command = [sys.executable,str(script),'--evidence',str(source),'--output',str(output),
               '--run-id','123','--artifact-id','456','--run-attempt','2']
    subprocess.run(command,check=True,capture_output=True,timeout=10)
    generated = json.loads((output/'known_security_issues.json').read_text())
    assert generated['ci_run'] == 123 and generated['artifact_id'] == 456
    assert generated['artifact_name'] == 'container-security-123-2'
    assert generated['verified_checksums'] == 2
    assert generated['findings'][0]['status'] == 'Accepted for development/alpha; hardening deferred.'
    assert 'actions/runs/123' in (output/'KNOWN_SECURITY_ISSUES.md').read_text()
    # Corrupt evidence must fail, not regenerate a misleading accepted report.
    (source/'fixture-service.vulnerabilities.json').write_text('{}')
    assert subprocess.run(command,capture_output=True,timeout=10).returncode != 0
