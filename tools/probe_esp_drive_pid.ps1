<#
.SYNOPSIS
  Copy and run tools/probe_esp_drive_pid.py on the MaixCAM2 (encoder/PID balance).
#>
param(
  [string]$MaixCamIp = "192.168.1.100",
  [string]$BackupIp = "10.17.43.1",
  [string]$MaixCamUser = "root",
  [ValidateSet("uart2", "uart4")]
  [string]$UartPort = "uart4",
  [int]$Pwm = 40,
  [int]$Speed = 20,
  [double]$Seconds = 1.2
)

$ErrorActionPreference = "Stop"
$ToolsDir = $PSScriptRoot
$Probe = Join-Path $ToolsDir "probe_esp_drive_pid.py"

function Test-Ssh([string]$Ip) {
  ssh -o BatchMode=yes -o ConnectTimeout=4 -o StrictHostKeyChecking=accept-new `
    "${MaixCamUser}@${Ip}" "echo ok" 2>$null | Out-Null
  return $LASTEXITCODE -eq 0
}

$ip = $MaixCamIp
if (-not (Test-Ssh $ip)) {
  Write-Host "Primary $ip unreachable, trying $BackupIp"
  $ip = $BackupIp
  if (-not (Test-Ssh $ip)) {
    throw "SSH failed for $MaixCamIp and $BackupIp"
  }
}

$target = "${MaixCamUser}@${ip}"
Write-Host "==> scp probe -> ${target}:/tmp/"
scp -o StrictHostKeyChecking=accept-new $Probe "${target}:/tmp/probe_esp_drive_pid.py"
if ($LASTEXITCODE -ne 0) { throw "scp failed" }

# App must be stopped so /dev/ttyS4 is free.
Write-Host "==> ensure Maix app not holding UART (kill roverMecanum if needed)"
ssh -o StrictHostKeyChecking=accept-new $target `
  "pkill -f 'roverMecanum|main.py' 2>/dev/null; sleep 0.5; true"

Write-Host "==> ssh python3 PID probe --port $UartPort"
ssh -o StrictHostKeyChecking=accept-new $target `
  "PYTHONPATH=/root/roverMecanum python3 /tmp/probe_esp_drive_pid.py --port $UartPort --pwm $Pwm --speed $Speed --seconds $Seconds"
exit $LASTEXITCODE
