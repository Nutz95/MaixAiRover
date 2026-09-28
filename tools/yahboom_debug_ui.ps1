<#
.SYNOPSIS
  Launch the Yahboom Tk debug UI (gamepad + per-motor tabs).

.DESCRIPTION
  PC-only cockpit: Xbox pad via pygame, Yahboom CH340 via Rosmaster_Lib.
  No MaixCAM required. Wheels off the ground for motor tests.

.PARAMETER Port
  Default COM port shown in the UI (changeable in the window).

.EXAMPLE
  .\tools\yahboom_debug_ui.ps1
  .\tools\yahboom_debug_ui.ps1 -Port COM15
#>
param(
  [string]$Port = "COM15",
  [switch]$SkipDeps
)

$ErrorActionPreference = "Stop"
$ToolsDir = $PSScriptRoot
$Py = Join-Path $ToolsDir "yahboom_debug_ui.py"

function Test-PythonImport([string]$Statement) {
  # Native stderr from a missing module becomes a terminating error under Stop.
  $prev = $ErrorActionPreference
  $ErrorActionPreference = "Continue"
  & python -c $Statement 1>$null 2>$null
  $ok = ($LASTEXITCODE -eq 0)
  $ErrorActionPreference = $prev
  return $ok
}

function Ensure-Deps {
  if (-not (Test-PythonImport "import serial")) {
    Write-Host "Installing pyserial..."
    python -m pip install pyserial
  }
  if (-not (Test-PythonImport "from Rosmaster_Lib import Rosmaster")) {
    Write-Host "Installing Rosmaster_Lib..."
    python -m pip install "git+https://github.com/Roblibs/Rosmaster_Lib.git"
  }
  if (-not (Test-PythonImport "import pygame")) {
    Write-Host "Installing pygame..."
    python -m pip install pygame
  }
}

if (-not (Test-Path $Py)) {
  throw ("Missing {0}" -f $Py)
}

if (-not $SkipDeps) {
  Ensure-Deps
}

Write-Host "Yahboom debug UI"
Write-Host ("  default COM hint: {0}" -f $Port)
Write-Host "  tabs: Gamepad (set_car_motion) | Motors (M1..M4 open-loop)"
Write-Host "  DC 6-13 V must be ON for motors."
Write-Host ""

$env:YAHBOOM_DEBUG_PORT = $Port
python $Py
