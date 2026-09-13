"""Regenerate the accepted-risk register from complete retained image reports."""
import argparse
import hashlib
import json
from pathlib import Path

STATUS = 'Accepted for development/alpha; hardening deferred.'


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--evidence', required=True)
    parser.add_argument('--output', default='docs')
    args = parser.parse_args()
    source, output = Path(args.evidence), Path(args.output)
    for name, digest in json.loads((source / 'checksums.json').read_text()).items():
        assert Path(name).name == name
        assert hashlib.sha256((source / name).read_bytes()).hexdigest() == digest
    scan = json.loads((source / 'scan-summary.json').read_text())
    findings = {}
    images = []
    for index, image in enumerate(scan['images'], 1):
        label = f'I{index}'
        images.append({'label':label, 'services':image['services']})
        report = json.loads((source / (image['services'][0]['service'] + '.vulnerabilities.json')).read_text())
        for result in report.get('Results', []):
            for v in result.get('Vulnerabilities', []):
                key = (v['VulnerabilityID'], v['PkgName'], v['InstalledVersion'], v['Severity'])
                item = findings.setdefault(key, {'advisory':key[0],'package':key[1],'version':key[2],
                    'severity':key[3],'fix_reported':v.get('FixedVersion') or 'not reported',
                    'source':v.get('PrimaryURL',''), 'images':[], 'scan_date':scan['scanned_at'], 'status':STATUS})
                item['images'].append(label)
    document = {'policy':STATUS, 'source_sha':scan['source_sha'], 'scanned_at':scan['scanned_at'],
        'scanner_image':scan['scanner_image'], 'database':scan['database'], 'images':images,
        'findings':list(findings.values())}
    output.mkdir(parents=True, exist_ok=True)
    (output / 'known_security_issues.json').write_text(json.dumps(document, indent=2) + '\n')
    lines = ['# Known security issues', '', STATUS, '',
        'Owner-authorized development/alpha risk acceptance supersedes earlier zero-HIGH/CRITICAL instructions. '
        'Do not restart remediation automatically. This is not production hardening, a clean scan, '
        'an exploitability determination, or maintainer approval to publish. Scanner execution, '
        'inventory, secret, build, runtime, migration and data-integrity failures still block.', '',
        f"Snapshot source: `{scan['source_sha']}`; scan: `{scan['scanned_at']}`. "
        'Historical evidence is not a newly scanned artifact. All severities are retained below. '
        'Repeated package matches and shared service images are not unique CVEs.', '',
        'Raw baseline: [CI run 34670450930](https://github.com/BB-AI-Arena/MCP-Trust-Scoreboard/actions/runs/34670450930), '
        'artifact `container-security-34670450930-1` / ID `10290422302`; 41 checksums verified. '
        'Machine-readable companion: [known_security_issues.json](known_security_issues.json).', '',
        '## Image identities', '', '| Ref | Services | Image ID |', '| --- | --- | --- |']
    for image in images:
        lines.append('| ' + image['label'] + ' | ' + ', '.join(s['service'] for s in image['services']) + ' | `' + image['services'][0]['id'] + '` |')
    lines += ['', '## Observed findings', '',
        'Every row has status **"Accepted for development/alpha; hardening deferred."** '
        'Scan date is the snapshot timestamp above. Available fixes are scanner reports, '
        'not instructions to upgrade in this slice.', '',
        '| Advisory | Package | Version | Severity | Images | Fix reported |', '| --- | --- | --- | --- | --- | --- |']
    for item in sorted(findings.values(), key=lambda i:(i['advisory'],i['package'])):
        lines.append('| ' + ' | '.join([item['advisory'],item['package'],item['version'],item['severity'],','.join(item['images']),item['fix_reported']]) + ' |')
    (output / 'KNOWN_SECURITY_ISSUES.md').write_text('\n'.join(lines) + '\n')
    print(f'Recorded {len(findings)} distinct advisory/package/version/severity rows, {len(images)} image identities')


if __name__ == '__main__':
    main()
