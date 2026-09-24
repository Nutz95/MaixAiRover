<#
.SYNOPSIS
  Interactive bench menu for the Yahboom ROS driver board (USB CH340).

.DESCRIPTION
  Opens the Micro-USB Connect-USB COM port and talks Rosmaster binary
  protocol via tools/yahboom_bench.py (vendor Rosmaster_Lib).

.PARAMETER Port
  CH340 COM port. Default COM15.

.PARAMETER Pwm
  Open-loop PWM duty for motor tests (1..100). Default 30.

.PARAMETER Seconds
  How long each motor spin lasts. Default 1.5.

.EXAMPLE
  .\tools\yahboom_bench.ps1
  .\tools\yahboom_bench.ps1 -Port COM15 -Pwm 25
#>
param(
  [string]$Port = "COM15",
  [ValidateRange(1, 100)]
  [int]$Pwm = 30,
  [ValidateRange(1, 30)]
  [double]$Seconds = 1.5,
  [switch]$SkipDeps
)

$ErrorActionPreference = "Stop"
$ToolsDir = $PSScriptRoot
$Py = Join-Path $ToolsDir "yahboom_bench.py"

function Get-SerialPorts {
  try {
    return [System.IO.Ports.SerialPort]::GetPortNames() | Sort-Object
  } catch {
    return @()
  }
}

function Ensure-PythonDeps {
  python -c "import serial" 2>$null
  if ($LASTEXITCODE -ne 0) {
    Write-Host "Installing pyserial..."
    python -m pip install pyserial
  }
  python -c "from Rosmaster_Lib import Rosmaster" 2>$null
  if ($LASTEXITCODE -ne 0) {
    Write-Host "Installing Rosmaster_Lib (Yahboom driver)..."
    python -m pip install "git+https://github.com/Roblibs/Rosmaster_Lib.git"
  }
}

function Show-Ports {
  $ports = Get-SerialPorts
  Write-Host ""
  Write-Host "Available COM ports:"
  if (-not $ports -or $ports.Count -eq 0) {
    Write-Host "  (none detected)"
  } else {
    foreach ($p in $ports) {
      if ($p -eq $Port) {
        Write-Host ("  {0} <== selected" -f $p)
      } else {
        Write-Host ("  {0}" -f $p)
      }
    }
  }
  Write-Host ""
}

function Show-Banner {
  Write-Host ""
  Write-Host "Yahboom ROS board bench"
  Write-Host ("  Port     : {0} @ 115200" -f $Port)
  Write-Host ("  PWM      : {0}  (open-loop set_motor - wheels OFF the ground)" -f $Pwm)
  Write-Host ("  Duration : {0} s per motor spin" -f $Seconds)
  Write-Host "  Map      : M1=FR  M2=FL  M3=RR  M4=RL"
  Write-Host ""
  Write-Host "DC power (6-13 V) must be ON for motors / battery reading."
  Write-Host "Micro-USB Connect USB = data. Type-C is 5 V OUT only."
  Write-Host ""
}

function Show-Menu {
  Write-Host "--- menu ---"
  Write-Host "  1  ping (beep + version + battery)"
  Write-Host "  2  full status snapshot"
  Write-Host "  3  watch IMU 9-axis (5s)"
  Write-Host "  4  watch encoders (8s) - spin shaft by hand"
  Write-Host "  5  watch battery (5s)"
  Write-Host "  6  motor submenu (one wheel at a time)"
  Write-Host "  7  STOP all motors"
  Write-Host "  8  beep"
  Write-Host ("  9  change COM port (now {0})" -f $Port)
  Write-Host (" 10  change PWM (now {0})" -f $Pwm)
  Write-Host " 11  interactive Python menu (keeps serial open)"
  Write-Host "  q  quit"
}

function Invoke-MotorSubmenu {
  Write-Host "  Motor map: 1=FR  2=FL  3=RR  4=RL"
  Write-Host "  a  M1 fwd    b  M1 rev"
  Write-Host "  c  M2 fwd    d  M2 rev"
  Write-Host "  e  M3 fwd    f  M3 rev"
  Write-Host "  g  M4 fwd    h  M4 rev"
  Write-Host "  s  STOP"
  $m = (Read-Host "motor").Trim().ToLowerInvariant()
  $map = @{
    "a" = @(1, "fwd"); "b" = @(1, "rev")
    "c" = @(2, "fwd"); "d" = @(2, "rev")
    "e" = @(3, "fwd"); "f" = @(3, "rev")
    "g" = @(4, "fwd"); "h" = @(4, "rev")
  }
  if ($m -eq "s") {
    python $Py --port $Port stop
    return
  }
  if (-not $map.ContainsKey($m)) {
    Write-Host "unknown motor choice"
    return
  }
  $idx = $map[$m][0]
  $dir = $map[$m][1]
  Write-Host ("Spinning M{0} {1} at PWM={2} for {3}s - confirm wheels are clear." -f $idx, $dir, $Pwm, $Seconds)
  $ok = Read-Host "type YES to run"
  if ($ok -eq "YES") {
    python $Py --port $Port --pwm $Pwm --seconds $Seconds motor $idx $dir
  } else {
    Write-Host "cancelled"
  }
}

if (-not (Test-Path $Py)) {
  throw ("Missing {0}" -f $Py)
}

if (-not $SkipDeps) {
  Ensure-PythonDeps
}

Show-Ports
$ports = Get-SerialPorts
if ($ports -and ($Port -notin $ports)) {
  Write-Host ("WARN: {0} not in detected list. Pick another or continue anyway." -f $Port)
  $answer = Read-Host ("Enter COM port [{0}]" -f $Port)
  if ($answer.Trim()) { $Port = $answer.Trim() }
}

Show-Banner

$choice = ""
while ($choice -ne "q") {
  Show-Menu
  $choice = (Read-Host "choice").Trim().ToLowerInvariant()

  switch ($choice) {
    "1" { python $Py --port $Port ping }
    "2" { python $Py --port $Port status }
    "3" { python $Py --port $Port --seconds 5 imu }
    "4" { python $Py --port $Port --seconds 8 encoders }
    "5" { python $Py --port $Port --seconds 5 battery }
    "6" { Invoke-MotorSubmenu }
    "7" { python $Py --port $Port stop }
    "8" { python $Py --port $Port beep }
    "9" {
      Show-Ports
      $answer = Read-Host ("COM port [{0}]" -f $Port)
      if ($answer.Trim()) { $Port = $answer.Trim() }
    }
    "10" {
      $answer = Read-Host ("PWM 1..100 [{0}]" -f $Pwm)
      if ($answer.Trim()) {
        $Pwm = [Math]::Max(1, [Math]::Min(100, [int]$answer))
      }
    }
    "11" {
      Write-Host "Launching interactive session (q to leave)..."
      python $Py --port $Port --pwm $Pwm --seconds $Seconds menu
    }
    "q" { }
    default {
      if ($choice) { Write-Host ("unknown choice: {0}" -f $choice) }
    }
  }
}

Write-Host "bye"
