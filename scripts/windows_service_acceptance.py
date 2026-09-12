"""SCM operations for the real vertical scenario; disposable Windows runner only."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time
import uuid

from windows_acceptance import ROOT, wait


class ServiceAcceptance:
    def __init__(self, root, executable, config, bootstrap, evidence, env):
        self.root=root;self.install=root/'installed';self.data=self.install/'data'
        self.name='AgentTrustEndpoint-'+uuid.uuid4().hex[:12]
        self.evidence=evidence;self.env=env;self.removed=False
        self.summary={'service_name':self.name,'identity_type':'virtual service account',
            'identity':'NT SERVICE\\'+self.name,'dpapi_scope':'user',
            'actual_reboot':'unverified: hosted runner was not rebooted',
            'source_sha':os.getenv('SENSOR_SOURCE_SHA'),
            'binary_sha256':hashlib.sha256(executable.read_bytes()).hexdigest(),
            'runner_image':os.getenv('ImageVersion'),
            'windows':json.loads(subprocess.check_output([str(executable),'version'],text=True)),
            'go_version':subprocess.check_output(['go','version'],text=True).strip()}
        self.sentinel=root/'unrelated.txt';self.sentinel.write_text('preserve unrelated data')
        try:
            self.call('Install',extra=['-Source',str(executable),'-Config',str(config)],private=bootstrap)
            wait(lambda:(self.data/'status.json').exists())
            self.identity=(self.data/'identity.dpapi').read_bytes()
            assert bootstrap.encode() not in self.identity and b'"credential"' not in self.identity
            # Only this disposable fixture tree becomes readable, never a user profile.
            self.ps("param($root,$account) & icacls.exe $root /grant ($account+':(OI)(CI)(RX)') | Out-Null; if ($LASTEXITCODE) { throw 'fixture ACL failed' }",str(root),'NT SERVICE\\'+self.name)
            self.stop();self.start()
            self.summary['enrollment']='passed under SCM identity'
            # Attempt decrypt with a different logon context (runner account), even
            # though that administrator can read ciphertext. No plaintext is output.
            result=self.ps("param($path) Add-Type -AssemblyName System.Security; try { $null=[Security.Cryptography.ProtectedData]::Unprotect([IO.File]::ReadAllBytes($path),$null,[Security.Cryptography.DataProtectionScope]::CurrentUser); throw 'cross-user decrypt unexpectedly succeeded' } catch [Security.Cryptography.CryptographicException] { 'rejected' }",str(self.data/'identity.dpapi'))
            assert 'rejected' in result
            self.summary['unrelated_context_dpapi']='rejected'
            # Reinstallation must fail before touching any existing file/ACL.
            before=self.call('Inspect')
            self.call('Install',extra=['-Source',str(executable),'-Config',str(config)],private=bootstrap,expected_failure=True)
            assert json.loads(before)['acls']==json.loads(self.call('Inspect'))['acls']
        except BaseException:
            self.cleanup();raise

    def ps(self, script, *args):
        # Exact script on stdin: secrets never enter shell interpolation/argv.
        # Arguments here contain test-owned paths and service names only.
        command='& { '+script+' } '+ ' '.join("'"+a.replace("'","''")+"'" for a in args)
        r=subprocess.run(['pwsh','-NoProfile','-NonInteractive','-Command',command],env=self.env,capture_output=True,text=True,timeout=60)
        if r.returncode:raise AssertionError('SCM fixture operation failed: '+r.stderr[-2000:])
        return r.stdout

    def call(self, action, extra=(), private=None, expected_failure=False):
        args=['pwsh','-NoProfile','-NonInteractive','-File',str(ROOT/'scripts/windows_service.ps1'),
            '-Action',action,'-InstallRoot',str(self.install),'-Name',self.name,*extra]
        r=subprocess.run(args,input=(private+'\n') if private else None,env=self.env,capture_output=True,text=True,timeout=90)
        if expected_failure:
            assert r.returncode!=0,'unsafe repeat installation succeeded'
        elif r.returncode:
            # Enrollment errors can contain StartService arguments in exception
            # context, so never include private-command output in failure logs.
            if private:raise AssertionError('SCM enrollment/install failed (private output withheld)')
            raise AssertionError('SCM '+action+' failed: '+r.stderr[-2000:])
        return r.stdout

    def health(self):
        return json.loads((self.data/'status.json').read_text())

    def stop(self):
        if not self.removed:self.call('Stop')

    def start(self):
        old=self.health().get('pid') if (self.data/'status.json').exists() else None
        self.call('Start')
        wait(lambda:self.health()['pid']!=old)
        assert (self.data/'identity.dpapi').read_bytes()==self.identity
        return self

    def validate_lifecycle(self):
        inspect=json.loads(self.call('Inspect'))
        assert inspect['start_name'].lower()==self.summary['identity'].lower()
        assert inspect['start_mode']=='Auto' and inspect['state']=='Running'
        assert '86400' in inspect['recovery'] and '5000' in inspect['recovery'] and '30000' in inspect['recovery']
        assert inspect['recovery'].count('RESTART')==2 and 'NONE' in inspect['recovery']
        assert 'TRUE' in inspect['failure_flag'].upper() or '1' in inspect['failure_flag']
        assert 'SeChangeNotifyPrivilege' in inspect['privileges'] and 'SeDebugPrivilege' not in inspect['privileges']
        for path,sddl in inspect['acls'].items():
            assert ';;;BU)' not in sddl and ';;;WD)' not in sddl and ';;;AU)' not in sddl, (path,sddl)
        self.summary['scm']=inspect
        assert self.health()['identity']['sid'].startswith('S-1-5-80-') and self.health()['identity']['elevated'] is False
        self.summary['runtime_token']=self.health()['identity']
        self.stop();self.start();wait(lambda:self.health()['online'])
        old=self.health()['pid']
        # This is explicitly a disposable acceptance fault, not a sensor response.
        self.ps('param($pidToKill) Stop-Process -Id ([int]$pidToKill) -Force',str(old))
        wait(lambda:self.health()['pid']!=old and self.health()['online'],90)
        assert (self.data/'identity.dpapi').read_bytes()==self.identity
        self.summary['dpapi_restart_and_scm_recovery']='passed'
        self.summary['collector_states']=self.health()['collectors']
        assert self.health()['collectors']['process'] in ('active','permission_missing')
        for key in ('ai','mcp','software','network','filesystem','runtime'):
            assert self.health()['collectors'][key]=='active',self.health()
        # Explicitly inaccessible profile must yield degradation, not false active.
        denied=self.root/'unreadable-profile';denied.mkdir()
        self.ps("param($path) $acl=[Security.AccessControl.DirectorySecurity]::new(); $acl.SetAccessRuleProtection($true,$false); foreach($sid in @('S-1-5-18','S-1-5-32-544')) { $acl.AddAccessRule([Security.AccessControl.FileSystemAccessRule]::new([Security.Principal.SecurityIdentifier]::new($sid),'FullControl','ContainerInherit,ObjectInherit','None','Allow')) }; Set-Acl -LiteralPath $path -AclObject $acl",str(denied))
        self.stop()
        cfg=self.install/'sensor.json';original=cfg.read_bytes();c=json.loads(original);c['profile_roots'].append(str(denied));cfg.write_text(json.dumps(c))
        self.start();wait(lambda:self.health()['collectors']['ai']=='degraded' and self.health()['collectors']['mcp']=='degraded')
        self.summary['denied_profile_states']={k:self.health()['collectors'][k] for k in ('ai','mcp')}
        self.stop();cfg.write_bytes(original);self.start();wait(lambda:self.health()['online'])

    def assert_preserved(self, ids):
        wait(lambda:self.health()['reason']=='server_unavailable')
        current={json.loads(p.read_text())['event_id'] for p in (self.data/'spool').glob('*.event')}
        assert ids<=current
        assert (self.data/'identity.dpapi').read_bytes()==self.identity
        self.summary['offline_service_start']='passed'

    def validate_revocation(self):
        wait(lambda:self.health()['reason']=='authentication_rejected',60)
        self.stop();self.start()
        wait(lambda:self.health()['reason']=='authentication_rejected',60)
        assert (self.data/'identity.dpapi').read_bytes()==self.identity
        self.summary['revocation']='authentication rejected before and after service restart; identity unchanged'
        counters=self.health()['counters']
        self.summary.update(dropped_count=counters['dropped'],expired_count=counters['expired'],total_uploaded_count=counters['sent'])
        assert counters['dropped']==0 and counters['expired']==0

    def validate_uninstall(self):
        self.stop()
        retained={p.relative_to(self.install):p.read_bytes() for p in self.install.rglob('*') if p.is_file() and p.name!='agent-trust-sensor.exe'}
        self.call('Start') # Default uninstall must stop a running service itself.
        self.call('Uninstall');self.removed=True
        assert not (self.install/'agent-trust-sensor.exe').exists()
        for path,contents in retained.items():
            p=self.install/path
            assert p.exists()
            if p.name not in ('status.json','counters.json'):assert p.read_bytes()==contents
        assert self.sentinel.read_text()=='preserve unrelated data'
        assert (self.root/'repository').is_dir() and (self.root/'sensor.json').exists()
        result=self.ps('param($name) if (Get-Service -Name $name -ErrorAction SilentlyContinue) { throw "registration remains" }; "absent"',self.name)
        assert 'absent' in result
        self.summary['uninstall']='registration/binary removed; identity/spool/config/status/history/unrelated files preserved'

    def save(self):
        self.summary['result']='passed'
        (self.evidence/'scm-acceptance.json').write_text(json.dumps(self.summary,indent=2))

    def cleanup(self):
        if self.removed:return
        if (self.install/'installation.json').exists():
            self.call('Uninstall');self.removed=True


if __name__=='__main__':
    from windows_acceptance import main
    main(service_mode=True)
