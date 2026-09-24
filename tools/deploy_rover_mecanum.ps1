# Deploy roverMecanum lib/ + config to /root/roverMecanum on MaixCam2.
# Entry point (main.py) is synced by MaixVision from maixcam/roverMecanum/.
#
# Usage:
#   .\deploy_rover_mecanum.ps1
#   .\deploy_rover_mecanum.ps1 -MaixCamIp 192.168.1.100
#   .\deploy_rover_mecanum.ps1 -DeployOnly
#   .\deploy_rover_mecanum.ps1 -SshOnly

param(
    [string]$MaixCamIp = "10.17.43.1",
    [string]$BackupIp = "192.168.1.100",
    [string]$MaixCamUser = "root",
    [string]$RemotePath = "/root/roverMecanum",
    [string]$KeyType = "ed25519",
    [switch]$DeployOnly,
    [switch]$SshOnly,
    [switch]$SyncConfig
)

$ErrorActionPreference = "Stop"
$ToolsDir = $PSScriptRoot
$RepoRoot = Split-Path -Parent $ToolsDir
$LocalPackage = Join-Path $RepoRoot "maixcam\roverMecanum"
$SshDir = Join-Path $env:USERPROFILE ".ssh"
$PrivateKey = Join-Path $SshDir "id_$KeyType"
$PublicKey = "$PrivateKey.pub"
$script:MaixCamIp = $MaixCamIp
$script:Target = "${MaixCamUser}@${script:MaixCamIp}"
$script:SshExtraArgs = @()

function Write-Step($msg) {
    Write-Host "`n==> $msg" -ForegroundColor Cyan
}

function Invoke-Native {
    param([scriptblock]$Command)
    $prev = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    try {
        & $Command | Out-Null
        return [int]$LASTEXITCODE
    } finally {
        $ErrorActionPreference = $prev
    }
}

function Invoke-Ssh {
    param([string]$RemoteCommand)
    $sshArgs = @()
    $sshArgs += $script:SshExtraArgs
    $sshArgs += "-o", "StrictHostKeyChecking=accept-new"
    $sshArgs += $script:Target
    $sshArgs += $RemoteCommand
    return Invoke-Native { ssh @sshArgs 2>$null }
}

function Invoke-Scp {
    param(
        [string]$Source,
        [string]$Destination,
        [switch]$Recursive
    )
    $scpArgs = @()
    $scpArgs += $script:SshExtraArgs
    if ($Recursive) { $scpArgs += "-r" }
    $scpArgs += $Source
    $scpArgs += $Destination
    return Invoke-Native { scp @scpArgs 2>$null }
}

function Test-PasswordlessSsh {
    param([string[]]$ExtraArgs = @())
    $sshArgs = @()
    $sshArgs += $ExtraArgs
    $sshArgs += "-o", "BatchMode=yes"
    $sshArgs += "-o", "ConnectTimeout=5"
    $sshArgs += "-o", "StrictHostKeyChecking=accept-new"
    $sshArgs += $script:Target
    $sshArgs += "echo ok"
    $exitCode = Invoke-Native { ssh @sshArgs 2>$null }
    return $exitCode -eq 0
}

function Set-MaixCamTarget {
    param([string]$Ip)
    $script:MaixCamIp = $Ip
    $script:Target = "${MaixCamUser}@${script:MaixCamIp}"
}

function Resolve-MaixCamHost {
    if (Resolve-SshIdentity) {
        Write-Host "Using MaixCAM at $($script:MaixCamIp)"
        return
    }
    if ($BackupIp -and $BackupIp -ne $script:MaixCamIp) {
        Write-Host "Primary $($script:MaixCamIp) unreachable via SSH, trying backup $BackupIp"
        Set-MaixCamTarget $BackupIp
        if (Resolve-SshIdentity) {
            Write-Host "Using MaixCAM backup at $($script:MaixCamIp)"
            return
        }
    }
}

function Resolve-SshIdentity {
    if (Test-PasswordlessSsh) {
        $script:SshExtraArgs = @()
        Write-Host "SSH OK (default identity, same as: ssh $($script:Target))"
        return $true
    }
    if ((Test-Path $PrivateKey) -and (Test-PasswordlessSsh -ExtraArgs @("-i", $PrivateKey))) {
        $script:SshExtraArgs = @("-i", $PrivateKey)
        Write-Host "SSH OK with $PrivateKey"
        return $true
    }
    $script:SshExtraArgs = @()
    return $false
}

function Ensure-SshDirectory {
    if (-not (Test-Path $SshDir)) {
        New-Item -ItemType Directory -Path $SshDir -Force | Out-Null
    }
}

function Ensure-SshKey {
    Ensure-SshDirectory
    if ((Test-Path $PrivateKey) -and (Test-Path $PublicKey)) {
        Write-Host "Existing SSH key: $PrivateKey"
        return
    }
    Write-Step "Generating SSH key ($KeyType)"
    $exitCode = Invoke-Native { ssh-keygen -t $KeyType -f $PrivateKey -N '""' -q }
    if ($exitCode -ne 0) {
        throw "ssh-keygen failed"
    }
}

function Install-PublicKeyOnMaixCam {
    if (Resolve-SshIdentity) {
        return
    }
    Write-Step "SSH key exchange (root password required once)"
    Write-Host "Installing $PublicKey on $($script:Target) ..."
    $exitCode = Invoke-Native {
        Get-Content $PublicKey -Raw | ssh -o StrictHostKeyChecking=accept-new $script:Target `
            "mkdir -p ~/.ssh && chmod 700 ~/.ssh && touch ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys && cat >> ~/.ssh/authorized_keys"
    }
    if ($exitCode -ne 0) {
        throw "Failed to install public key on $($script:Target) (exit code $exitCode)"
    }
    if (-not (Resolve-SshIdentity)) {
        throw "Key installed but passwordless SSH still fails. Try: ssh $($script:Target)"
    }
}

function Deploy-Package {
    if (-not (Test-Path $LocalPackage)) {
        throw "Local package not found: $LocalPackage"
    }
    if (-not (Resolve-SshIdentity)) {
        throw "Passwordless SSH required. Re-run without -DeployOnly."
    }
    Write-Step "Creating $RemotePath on $($script:Target)"
    $exitCode = Invoke-Ssh "mkdir -p '$RemotePath'"
    if ($exitCode -ne 0) { throw "Remote mkdir failed" }
    if (-not (Test-Path "$LocalPackage\lib")) {
        throw "Local lib/ not found: $LocalPackage\lib"
    }
    # Replace remote lib wholly — scp -r merges and leaves stale flat modules.
    Write-Step "Replacing $RemotePath/lib on remote"
    $exitCode = Invoke-Ssh "rm -rf '$RemotePath/lib'"
    if ($exitCode -ne 0) { throw "Remote rm lib failed" }
    Write-Step "Uploading lib/ to $RemotePath (scp)"
    $exitCode = Invoke-Scp "$LocalPackage\lib" "$($script:Target):${RemotePath}/" -Recursive
    if ($exitCode -ne 0) { throw "scp lib failed" }
    $configExitCode = Invoke-Ssh "test -f '$RemotePath/config.json'"
    if ($configExitCode -ne 0 -or $SyncConfig) {
        if ($SyncConfig) {
            Write-Host "SyncConfig -> uploading config.json (overwrites remote)"
        } else {
            Write-Host "config.json missing on target -> uploading"
        }
        $exitCode = Invoke-Scp "$LocalPackage\config.json" "$($script:Target):${RemotePath}/"
        if ($exitCode -ne 0) { throw "scp config failed" }
    } else {
        Write-Host "Remote config.json kept (use -SyncConfig to overwrite from repo)"
    }
    Write-Step "Remote verification"
    $exitCode = Invoke-Ssh "ls -la '$RemotePath' && ls -la '$RemotePath/lib' | head"
    if ($exitCode -ne 0) { throw "Remote verification failed" }
    Write-Host "`nDeploy complete: $RemotePath/lib + config.json" -ForegroundColor Green
    Write-Host "Run via MaixVision: open maixcam/roverMecanum (main.py)"
    Write-Host "main.py loads dependencies from $RemotePath"
}

Resolve-MaixCamHost

if (-not $DeployOnly) {
    if (-not (Resolve-SshIdentity)) {
        Ensure-SshKey
        Install-PublicKeyOnMaixCam
    }
}

if (-not $SshOnly) {
    Deploy-Package
}
