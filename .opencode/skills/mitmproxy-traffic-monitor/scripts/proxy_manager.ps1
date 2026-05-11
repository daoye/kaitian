<#
.SYNOPSIS
  mitmproxy process manager — start/stop/status/cleanup
.DESCRIPTION
  Manages mitmdump process via port-based PID tracking.
  start: frees port -> starts mitmdump -> waits for listening -> verifies
  stop: kills process on port + any mitmdump.exe leftovers
#>
param(
  [Parameter(Position = 0)]
  [ValidateSet("start", "stop", "status", "restart", "cleanup")]
  [string]$Command = "status",
  [int]$Port = 8080,
  [string[]]$Script,
  [hashtable]$Option = @{},
  [string[]]$Mode,
  [switch]$Insecure
)

$pidFilePath = "mitmproxy_${Port}.pid"

function Get-ListeningPid($portVal) {
  $match = netstat -ano | Select-String ":${portVal}\s" | Select-String "LISTENING" | Select-Object -First 1
  if ($match) { return [int](($match -split '\s+')[-1]) }
  return $null
}

function Kill-Tree($targetPid) {
  if (-not $targetPid) { return }
  try { Stop-Process -Id $targetPid -Force -ErrorAction Stop; Start-Sleep -Milliseconds 500 } catch {}
}

function Kill-ByPort($portVal) {
  $foundPid = Get-ListeningPid $portVal
  if ($foundPid) { Kill-Tree $foundPid; Write-Host "killed PID=$foundPid on port $portVal" }
}

function Read-FilePid { if (Test-Path $pidFilePath) { return [int](Get-Content $pidFilePath -Raw).Trim() } return $null }
function Write-FilePid($val) { Set-Content $pidFilePath -Value $val }
function Remove-FilePid { Remove-Item $pidFilePath -Force -ErrorAction SilentlyContinue }

function Is-Alive($targetPid) {
  if (-not $targetPid) { return $false }
  try { $p = Get-Process -Id $targetPid -ErrorAction Stop; return (-not $p.HasExited) } catch { return $false }
}

function Start-Proxy {
  # 如果已有运行中实例，先停再启
  $savedPid = Read-FilePid
  if ((Is-Alive $savedPid)) {
    Write-Host "mitmdump already running (PID=$savedPid, port=$Port), restarting..."
    Stop-Proxy
    Start-Sleep -Seconds 1
  }

  # validate script files exist before starting
  foreach ($s in $Script) {
    $resolved = Resolve-Path $s -ErrorAction SilentlyContinue
    if (-not $resolved) { Write-Host "ERROR: script not found: $s"; return }
  }

  Kill-ByPort $Port
  Start-Sleep -Seconds 1

  $argsList = @("run", "mitmdump", "-p", $Port, "-q")
  if ($Insecure) { $argsList += "-k" }
  foreach ($s in $Script)   { $argsList += @("-s", $s) }
  foreach ($m in $Mode)     { $argsList += @("--mode", $m) }
  foreach ($kv in $Option.GetEnumerator()) { $argsList += @("--set", "$($kv.Key)=$($kv.Value)") }

  $proc = Start-Process -WindowStyle Hidden -FilePath "uv" -ArgumentList $argsList -PassThru
  $uvPid = $proc.Id
  Write-FilePid $uvPid

  for ($i = 0; $i -lt 8; $i++) {
    Start-Sleep -Seconds 1
    $listenerPid = Get-ListeningPid $Port
    if ($listenerPid) {
      Write-Host "mitmdump started (port=$Port, listening PID=$listenerPid)"
      return
    }
    if (-not (Is-Alive $uvPid)) {
      Write-Host "mitmdump exited prematurely"
      Remove-FilePid; return
    }
  }
  Write-Host "mitmdump failed: port $Port not listening after 8s"
  Kill-ByPort $Port; Remove-FilePid
}

function Stop-Proxy {
  Kill-ByPort $Port
  Get-Process -Name "mitmdump" -ErrorAction SilentlyContinue | ForEach-Object { Kill-Tree $_.Id }
  Remove-FilePid
  Write-Host "mitmdump stopped (port $Port)"
}

function Get-Status {
  $p = Get-ListeningPid $Port
  if ($p) { Write-Host "mitmdump running (PID=$p, port=$Port)" }
  else { Write-Host "mitmdump not running on port $Port"; Remove-FilePid }
}

function Invoke-Cleanup {
  Get-ChildItem -Filter "mitmproxy_*.pid" | ForEach-Object { Remove-Item $_.FullName -Force }
  Get-Process -Name "mitmdump" -ErrorAction SilentlyContinue | ForEach-Object { Kill-Tree $_.Id; Write-Host "killed PID=$($_.Id)" }
  Write-Host "Cleanup done"
}

switch ($Command) {
  "start"   { Start-Proxy }
  "stop"    { Stop-Proxy }
  "status"  { Get-Status }
  "restart" { Stop-Proxy; Start-Proxy }
  "cleanup" { Invoke-Cleanup }
}
