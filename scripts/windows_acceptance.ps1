$ErrorActionPreference = 'Stop'
$fixtureRoot = Join-Path $env:RUNNER_TEMP ("atp-postgres-" + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $fixtureRoot | Out-Null
$pgBin = (Get-ChildItem 'C:\Program Files\PostgreSQL' -Filter pg_ctl.exe -Recurse | Select-Object -First 1).DirectoryName
if (-not $pgBin) { throw 'Windows PostgreSQL tools unavailable; cannot claim acceptance' }
$dbData = Join-Path $fixtureRoot 'data'
$listener = [System.Net.Sockets.TcpListener]::new([System.Net.IPAddress]::Loopback, 0)
$listener.Start(); $pgPort = $listener.LocalEndpoint.Port; $listener.Stop()
$started = $false
try {
  & "$pgBin\initdb.exe" -D $dbData -U fixture -A trust -E UTF8
  if ($LASTEXITCODE -ne 0) { throw 'Disposable PostgreSQL initialization failed' }
  & "$pgBin\pg_ctl.exe" -D $dbData -l (Join-Path $fixtureRoot 'postgres.log') -o "-h 127.0.0.1 -p $pgPort" -w start
  if ($LASTEXITCODE -ne 0) { throw 'Disposable PostgreSQL startup failed' }
  $started = $true
  $env:DATABASE_URL = "postgresql://fixture@127.0.0.1:$pgPort/postgres"
  $env:AGENT_TRUST_DISPOSABLE_WINDOWS_TEST = '1'
  python scripts/windows_acceptance.py
  if ($LASTEXITCODE -ne 0) { throw 'Windows endpoint acceptance failed' }
} finally {
  if ($started) { & "$pgBin\pg_ctl.exe" -D $dbData -m fast -w stop }
  New-Item -ItemType Directory -Force -Path evidence/windows | Out-Null
  if (Test-Path (Join-Path $fixtureRoot 'postgres.log')) { Copy-Item (Join-Path $fixtureRoot 'postgres.log') evidence/windows/postgres.log }
  # Leave this uniquely named disposable cluster to runner destruction. No global
  # service stops, user volumes, prune, recursive cleanup or operator DB access.
}
