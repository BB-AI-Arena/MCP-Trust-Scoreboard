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
