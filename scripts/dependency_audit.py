"""Dependency findings are informational; malformed/unavailable audits still fail."""
import argparse
import json
from pathlib import Path
import subprocess
import sys


def classify(tool, returncode, report):
    if returncode not in (0, 1) or not isinstance(report, dict) or report.get('error'):
        raise ValueError('dependency scanner execution failed')
    if tool == 'python':
        dependencies = report.get('dependencies')
        if not isinstance(dependencies, list) or not dependencies:
            raise ValueError('missing Python dependency inventory')
        if not all(isinstance(d, dict) and 'name' in d and ('vulns' in d or 'skip_reason' in d) for d in dependencies):
            raise ValueError('malformed Python audit')
        count = sum(len(d.get('vulns', [])) for d in dependencies)
        skipped = [d for d in dependencies if d.get('skip_reason')]
    else:
        if not isinstance(report.get('vulnerabilities'), dict) or not report.get('auditReportVersion') or not isinstance(report.get('metadata'), dict):
            raise ValueError('missing npm dependency inventory')
        count = len(report['vulnerabilities'])
        skipped = []
    if returncode == 1 and not count:
        raise ValueError('scanner failed without a findings report')
    return {'scan_completed': True, 'findings_present': count > 0, 'finding_count': count,
            'skipped': skipped, 'policy': 'Accepted for development/alpha; hardening deferred.'}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('tool', choices=['python','npm'])
    parser.add_argument('--directory', default='.')
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    output = Path(args.output).resolve()
    output.mkdir(parents=True, exist_ok=True)
    command = ([sys.executable, '-m', 'pip_audit', '--format', 'json', '--progress-spinner', 'off']
               if args.tool == 'python' else ['npm','audit','--json'])
    result = subprocess.run(command, cwd=args.directory, text=True, capture_output=True, timeout=300)
    (output / 'raw.json').write_text(result.stdout)
    (output / 'stderr.log').write_text(result.stderr)
    summary = classify(args.tool, result.returncode, json.loads(result.stdout))
    (output / 'summary.json').write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary))


if __name__ == '__main__':
    main()
