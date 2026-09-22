<#
.SYNOPSIS
  Copy and run tools/probe_esp_uart_on_maix.py on the MaixCAM2 over SSH.
#>
param(
  [string]$MaixCamIp = "192.168.1.100",
  [string]$BackupIp = "10.17.43.1",
  [string]$MaixCamUser = "root",
  [ValidateSet("uart2", "uart4")]
  [string]$UartPort = "uart2"
)

$ErrorActionPreference = "Stop"
$ToolsDir = $PSScriptRoot
$Probe = Join-Path $ToolsDir "probe_esp_uart_on_maix.py"

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
scp -o StrictHostKeyChecking=accept-new $Probe "${target}:/tmp/probe_esp_uart_on_maix.py"
if ($LASTEXITCODE -ne 0) { throw "scp failed" }

Write-Host "==> ssh python3 probe --port $UartPort"
$wifiHost = if ($env:ESP_WIFI_HOST) { $env:ESP_WIFI_HOST } else { "192.168.20.148" }
ssh -o StrictHostKeyChecking=accept-new $target `
  "python3 /tmp/probe_esp_uart_on_maix.py --port $UartPort --wifi-host $wifiHost"
exit $LASTEXITCODE
