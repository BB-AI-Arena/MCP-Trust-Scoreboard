# Development installer. Run elevated; runtime uses a virtual service account.
# Bootstrap is read from stdin, never a command-line or persisted service value.
param(
  [Parameter(Mandatory)][ValidateSet('Install','Enroll','Start','Stop','Inspect','Uninstall')][string]$Action,
  [Parameter(Mandatory)][string]$InstallRoot,
  [Parameter(Mandatory)][ValidatePattern('^AgentTrustEndpoint[-A-Za-z0-9]*$')][string]$Name,
  [string]$Source,
  [string]$Config
)
$ErrorActionPreference = 'Stop'
$InstallRoot = [IO.Path]::GetFullPath($InstallRoot)
if ($InstallRoot.StartsWith('\\') -or $InstallRoot -eq [IO.Path]::GetPathRoot($InstallRoot)) { throw 'Explicit local installation directory required' }
# Never traverse a junction/symlink into unrelated paths.
$ancestor = $InstallRoot
while ($ancestor) {
  if ((Test-Path -LiteralPath $ancestor) -and ((Get-Item -LiteralPath $ancestor -Force).Attributes -band [IO.FileAttributes]::ReparsePoint)) { throw 'Reparse path refused' }
  $ancestor = [IO.Path]::GetDirectoryName($ancestor)
}
$exe = Join-Path $InstallRoot 'agent-trust-sensor.exe'
$settings = Join-Path $InstallRoot 'sensor.json'
$data = Join-Path $InstallRoot 'data'
$marker = Join-Path $InstallRoot 'installation.json'
$account = "NT SERVICE\$Name"
function Set-PrivateAcl([string]$Path, [string]$ServiceRights) {
  $acl = [Security.AccessControl.DirectorySecurity]::new()
  $acl.SetAccessRuleProtection($true, $false)
  foreach ($sid in @('S-1-5-18','S-1-5-32-544')) {
    $acl.AddAccessRule([Security.AccessControl.FileSystemAccessRule]::new([Security.Principal.SecurityIdentifier]::new($sid), 'FullControl', 'ContainerInherit,ObjectInherit', 'None', 'Allow'))
  }
  if ($ServiceRights) {
    $acl.AddAccessRule([Security.AccessControl.FileSystemAccessRule]::new($account, $ServiceRights, 'ContainerInherit,ObjectInherit', 'None', 'Allow'))
  }
  Set-Acl -LiteralPath $Path -AclObject $acl
}
if ($Action -eq 'Install') {
  if (Get-Service -Name $Name -ErrorAction SilentlyContinue) { throw 'Service already exists; no changes made' }
  if (Test-Path -LiteralPath $InstallRoot) { throw 'Installation path already exists; no changes made' }
  if (-not (Test-Path -LiteralPath $Source -PathType Leaf)) { throw 'Sensor binary required' }
  $c = Get-Content -LiteralPath $Config -Raw | ConvertFrom-Json
  $c.data_dir = $data
  # Create only the leaf; never create/rewrite an operator parent tree.
  if (-not (Test-Path -LiteralPath ([IO.Path]::GetDirectoryName($InstallRoot)) -PathType Container)) { throw 'Parent must exist' }
  New-Item -ItemType Directory -Path $InstallRoot | Out-Null
  Set-PrivateAcl $InstallRoot ''
  Copy-Item -LiteralPath $Source -Destination $exe
  $c | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath $settings -Encoding utf8NoBOM
  & $exe install-service --config $settings --name $Name
  if ($LASTEXITCODE -ne 0) { throw 'SCM registration failed; preserve installation for inspection' }
  @{ name=$Name; binary_sha256=(Get-FileHash $exe -Algorithm SHA256).Hash; format=1 } | ConvertTo-Json | Set-Content $marker
  Set-PrivateAcl $InstallRoot 'ReadAndExecute'
  # Existing files were created before the directory ACL was finalized; grant
  # the virtual account read/execute explicitly without touching the parent.
  & icacls.exe $exe /grant ($account+':(RX)') | Out-Null
  & icacls.exe $settings /grant ($account+':(R)') | Out-Null
  if ($LASTEXITCODE -ne 0) { throw 'Owned executable/config ACL failed' }
  New-Item -ItemType Directory -Path $data | Out-Null
  Set-PrivateAcl $data 'Modify'
  # Service has only traversal privilege; no debug/backup/restore/impersonation.
  & sc.exe privs $Name SeChangeNotifyPrivilege | Out-Null
  if ($LASTEXITCODE -ne 0) { throw 'Service privilege restriction failed' }
  $Action = 'Enroll'
} else {
  $owned = Get-Content -LiteralPath $marker -Raw | ConvertFrom-Json
  if ($owned.name -ne $Name -or $owned.format -ne 1) { throw 'Installation ownership mismatch' }
  if ((Get-FileHash $exe -Algorithm SHA256).Hash -ne $owned.binary_sha256) { throw 'Installed binary changed; explicit reconciliation required' }
}
$svc = [ServiceProcess.ServiceController]::new($Name)
function Wait-Running {
  try { $svc.WaitForStatus('Running', [TimeSpan]::FromSeconds(40)) }
  catch {
    $state = (& sc.exe queryex $Name | Out-String)
    $config = (& sc.exe qc $Name | Out-String)
    throw ("service did not reach Running: " + $_.Exception.Message + "`n" + $state + $config)
  }
}
try {
  switch ($Action) {
    'Enroll' {
      $secret = [Console]::ReadLine()
      if (-not $secret -or $secret.Length -lt 32) { throw 'Private bootstrap input required' }
      # ServiceController.Start(string[]) is not consistently bound by PowerShell
      # 7 on hosted runners. Call StartService directly with an in-memory argv;
      # the bootstrap is never an ImagePath/process command-line value.
      Add-Type @'
using System;
using System.ComponentModel;
using System.Runtime.InteropServices;
public static class AtpScmStart {
  [DllImport("advapi32.dll", CharSet=CharSet.Unicode, SetLastError=true)] static extern IntPtr OpenSCManager(string m,string d,uint a);
  [DllImport("advapi32.dll", CharSet=CharSet.Unicode, SetLastError=true)] static extern IntPtr OpenService(IntPtr h,string n,uint a);
  [DllImport("advapi32.dll", SetLastError=true)] static extern bool StartService(IntPtr h,uint c,IntPtr a);
  [DllImport("advapi32.dll", SetLastError=true)] static extern bool CloseServiceHandle(IntPtr h);
  public static void Start(string name,string arg) {
    var m=OpenSCManager(null,null,0xF003F); if(m==IntPtr.Zero) throw new Win32Exception();
    try {
      var s=OpenService(m,name,0x0010); if(s==IntPtr.Zero) throw new Win32Exception();
      IntPtr serviceText=IntPtr.Zero, text=IntPtr.Zero, argv=IntPtr.Zero;
      try {
        serviceText=Marshal.StringToHGlobalUni(name);
        text=Marshal.StringToHGlobalUni(arg);
        argv=Marshal.AllocHGlobal(IntPtr.Size*2);
        Marshal.WriteIntPtr(argv,0,serviceText);
        Marshal.WriteIntPtr(argv,IntPtr.Size,text);
        if(!StartService(s,2,argv)) throw new Win32Exception();
      } finally { if(argv!=IntPtr.Zero) Marshal.FreeHGlobal(argv); if(text!=IntPtr.Zero) Marshal.FreeHGlobal(text); if(serviceText!=IntPtr.Zero) Marshal.FreeHGlobal(serviceText); CloseServiceHandle(s); }
    } finally { CloseServiceHandle(m); }
  }
}
'@
      try { [AtpScmStart]::Start($Name,$secret) } finally { $secret = $null }
      Wait-Running
    }
    'Start' { $svc.Start(); Wait-Running }
    'Stop' { if ($svc.Status -ne 'Stopped') { $svc.Stop(); $svc.WaitForStatus('Stopped', [TimeSpan]::FromSeconds(40)) } }
    'Inspect' {
      $w = Get-CimInstance Win32_Service -Filter "Name='$Name'"
      $acls = @{}
      foreach ($p in @($InstallRoot,$exe,$settings,$data,(Join-Path $data 'identity.dpapi'),(Join-Path $data 'spool'),(Join-Path $data 'status.json'))) {
        if (Test-Path -LiteralPath $p) { $acls[$p] = (Get-Acl -LiteralPath $p).Sddl }
      }
      @{ name=$Name; start_name=$w.StartName; start_mode=$w.StartMode; state=$w.State; pid=$w.ProcessId;
         recovery=(& sc.exe qfailure $Name | Out-String); failure_flag=(& sc.exe qfailureflag $Name | Out-String);
         privileges=(& sc.exe qprivs $Name | Out-String); service_acl=(& sc.exe sdshow $Name | Out-String); acls=$acls } | ConvertTo-Json -Depth 10
    }
    'Uninstall' {
      & $exe uninstall-service --name $Name
      if ($LASTEXITCODE -ne 0) { throw 'Safe SCM removal failed' }
      $svc.Dispose()
      # No recursive deletion. Identity, spool, local status, config and marker
      # stay private for explicit operator reconciliation. No purge option.
      Remove-Item -LiteralPath $exe
    }
  }
} finally { $svc.Dispose() }
