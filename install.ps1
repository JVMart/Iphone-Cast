#Requires -Version 5.1
<#
.SYNOPSIS
    Iphone-Cast one-shot installer.

.DESCRIPTION
    From a clean Windows 10/11 box with Python 3.10+ already installed:

      1. Silent-install MSYS2 to C:\msys64 (skips if present)
      2. pacman: UCRT64 toolchain + GStreamer + libplist
      3. Clone Bonjour SDK mirror to C:\BonjourSDK
      4. Clone + build UxPlay, install into C:\msys64\ucrt64\bin\
      5. Create the project's Python venv (.venv\)
      6. Compile Iphone-Cast.exe (gcc + magick + windres)
      7. Create Desktop shortcut with the embedded icon
      8. Add three firewall rules for AirPlay (elevates if needed)

    All steps are idempotent: re-running the script picks up where it left off.

.PARAMETER SkipFirewall
    Skip step 8 entirely. Use this if you'll add the firewall rules by hand
    or if the host has another mechanism (Windows Defender Application
    Control, group policy, etc.).

.PARAMETER Force
    Re-run every step from scratch (re-downloads MSYS2, rebuilds UxPlay,
    rebuilds the launcher). Useful after UxPlay or GStreamer updates.

.EXAMPLE
    .\install.ps1
    Standard install. ~30 min on a clean box.

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File .\install.ps1
    Bypasses the default execution policy without changing it permanently.
#>
[CmdletBinding()]
param(
    [switch]$SkipFirewall,
    [switch]$Force
)

$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
$script:Root = $PSScriptRoot
$script:Msys2Root = 'C:\msys64'
$script:UxplayExe = "$Msys2Root\ucrt64\bin\uxplay.exe"

function Write-Step($msg) {
    Write-Host ""
    Write-Host "=== $msg ===" -ForegroundColor Cyan
}

function Test-IsAdmin {
    $id = [Security.Principal.WindowsIdentity]::GetCurrent()
    return ([Security.Principal.WindowsPrincipal]$id).IsInRole(
        [Security.Principal.WindowsBuiltinRole]::Administrator)
}

function Get-PythonExe {
    foreach ($c in @('python', 'py')) {
        $cmd = Get-Command $c -ErrorAction SilentlyContinue
        if (-not $cmd) { continue }
        $ver = & $cmd.Source --version 2>&1
        if ($ver -match 'Python (\d+)\.(\d+)') {
            if ([int]$matches[1] -gt 3 -or
                ([int]$matches[1] -eq 3 -and [int]$matches[2] -ge 10)) {
                return $cmd.Source
            }
        }
    }
    return $null
}

function ConvertTo-MsysPath($winPath) {
    return & "$Msys2Root\usr\bin\cygpath.exe" -u $winPath
}

function Invoke-MsysBash($command) {
    $env:MSYSTEM = 'UCRT64'
    $env:CHERE_INVOKING = 'yes'
    & "$Msys2Root\usr\bin\bash.exe" -lc $command
    if ($LASTEXITCODE -ne 0) {
        throw "bash command failed (exit $LASTEXITCODE): $command"
    }
}

# ------------------------------------------------------------------ steps --

function Install-Msys2 {
    if ((Test-Path "$Msys2Root\usr\bin\bash.exe") -and -not $Force) {
        Write-Host "MSYS2 already at $Msys2Root, skipping install."
        return
    }
    Write-Step "1/8 Installing MSYS2 to $Msys2Root"
    $url = 'https://github.com/msys2/msys2-installer/releases/download/nightly-x86_64/msys2-x86_64-latest.exe'
    $dl = Join-Path $env:TEMP 'msys2-installer.exe'
    if (-not (Test-Path $dl) -or $Force) {
        Write-Host "  downloading $url"
        Invoke-WebRequest -Uri $url -OutFile $dl -UseBasicParsing
    }
    Write-Host "  running silent installer (~2 min)..."
    $p = Start-Process -FilePath $dl `
        -ArgumentList @('in','--confirm-command','--accept-messages','--root',($Msys2Root -replace '\\','/')) `
        -PassThru -Wait
    if ($p.ExitCode -ne 0) { throw "MSYS2 installer failed (exit $($p.ExitCode))" }
    if (-not (Test-Path "$Msys2Root\usr\bin\bash.exe")) {
        throw "MSYS2 installed but bash.exe missing"
    }
}

function Build-UxPlay {
    if ((Test-Path $UxplayExe) -and -not $Force) {
        Write-Host "uxplay.exe already at $UxplayExe, skipping build."
        return
    }
    Write-Step "2-4/8 Building UxPlay (long: pacman + cmake + ninja, ~20-30 min)"
    $script = ConvertTo-MsysPath (Join-Path $Root 'scripts\build_uxplay.sh')
    Invoke-MsysBash "bash '$script'"
    if (-not (Test-Path $UxplayExe)) { throw "uxplay.exe not produced at $UxplayExe" }
}

function New-Venv {
    $venvPy = Join-Path $Root '.venv\Scripts\python.exe'
    if ((Test-Path $venvPy) -and -not $Force) {
        Write-Host ".venv already exists, skipping."
        return
    }
    Write-Step "5/8 Creating Python venv"
    $py = Get-PythonExe
    if (-not $py) { throw "Python 3.10+ not found on PATH. Install from python.org first." }
    & $py -m venv (Join-Path $Root '.venv')
    if (-not (Test-Path $venvPy)) { throw ".venv creation failed" }
}

function Build-Launcher {
    $exe = Join-Path $Root 'Iphone-Cast.exe'
    $srcC = Join-Path $Root 'launcher.c'
    if ((Test-Path $exe) -and -not $Force `
            -and (Get-Item $exe).LastWriteTime -ge (Get-Item $srcC).LastWriteTime) {
        Write-Host "Iphone-Cast.exe up to date, skipping."
        return
    }
    Write-Step "6/8 Compiling Iphone-Cast.exe (icon + windres + gcc)"
    $bashRoot = ConvertTo-MsysPath $Root
    $cmd = @(
        "cd '$bashRoot'",
        '/ucrt64/bin/magick.exe -background none -density 512 icon.svg -define icon:auto-resize="256,128,64,48,32,16" Iphone-Cast.ico',
        '/ucrt64/bin/windres.exe launcher.rc -O coff -o launcher_res.o',
        '/ucrt64/bin/gcc.exe -O2 -mwindows -static -static-libgcc -o Iphone-Cast.exe launcher.c launcher_res.o',
        'rm -f launcher_res.o'
    ) -join ' && '
    Invoke-MsysBash $cmd
    if (-not (Test-Path $exe)) { throw "Iphone-Cast.exe not produced" }
}

function New-Shortcut {
    Write-Step "7/8 Creating Desktop shortcut"
    $exe = Join-Path $Root 'Iphone-Cast.exe'
    $desktop = [Environment]::GetFolderPath('Desktop')
    $lnk = Join-Path $desktop 'Iphone-Cast.lnk'
    $shell = New-Object -ComObject WScript.Shell
    $s = $shell.CreateShortcut($lnk)
    $s.TargetPath = $exe
    $s.WorkingDirectory = $Root
    $s.IconLocation = "$exe,0"
    $s.Description = 'Iphone-Cast - receptor AirPlay para duplicar pantalla del iPhone'
    $s.WindowStyle = 1
    $s.Save()
    Write-Host "  shortcut: $lnk"
}

function Add-FirewallRules {
    Write-Step "8/8 Firewall rules for AirPlay"
    $rules = @(
        [pscustomobject]@{ Name='Iphone-Cast: AirPlay TCP'; Protocol='TCP'; LocalPort='7000,7001,7100' },
        [pscustomobject]@{ Name='Iphone-Cast: AirPlay UDP'; Protocol='UDP'; LocalPort='6000-7100' },
        [pscustomobject]@{ Name='Iphone-Cast: mDNS';        Protocol='UDP'; LocalPort='5353' }
    )
    $needed = $rules | Where-Object {
        -not (Get-NetFirewallRule -DisplayName $_.Name -ErrorAction SilentlyContinue)
    }
    if (-not $needed) {
        Write-Host "  all rules already present, skipping."
        return
    }
    if (Test-IsAdmin) {
        foreach ($r in $needed) {
            New-NetFirewallRule -DisplayName $r.Name -Direction Inbound `
                -Protocol $r.Protocol -LocalPort $r.LocalPort -Action Allow `
                -Profile Private,Domain | Out-Null
            Write-Host "  added: $($r.Name)"
        }
        return
    }
    Write-Host "  $($needed.Count) rule(s) missing. Elevating for firewall step..."
    $oneLine = ($needed | ForEach-Object {
        "New-NetFirewallRule -DisplayName '$($_.Name)' -Direction Inbound -Protocol $($_.Protocol) -LocalPort $($_.LocalPort) -Action Allow -Profile Private,Domain | Out-Null"
    }) -join '; '
    try {
        Start-Process powershell -ArgumentList '-NoProfile','-Command',$oneLine -Verb RunAs -Wait
        Write-Host "  firewall rules added."
    } catch {
        Write-Warning "  could not elevate. You can add the rules later by running:"
        Write-Warning "    .\install.ps1   (in an Administrator PowerShell)"
    }
}

function Test-SmokeTest {
    Write-Step "Smoke test"
    & $UxplayExe -v 2>&1 | Select-Object -First 1
    if ($LASTEXITCODE -ne 0) { throw "uxplay.exe -v failed (exit $LASTEXITCODE)" }
    $venvPy = Join-Path $Root '.venv\Scripts\python.exe'
    & $venvPy -c "import sys; sys.path.insert(0, '$($Root -replace '\\','/')'); import main; print('launcher imports OK')"
}

# --------------------------------------------------------------- main flow --

Write-Host ""
Write-Host "Iphone-Cast installer" -ForegroundColor Green
Write-Host "  repo:  $Root"
Write-Host "  force: $Force"
Write-Host "  fw:    $(-not $SkipFirewall)"

if (-not (Get-PythonExe)) {
    throw "Python 3.10+ not found on PATH. Install from https://www.python.org/downloads/ and re-run."
}

Install-Msys2
Build-UxPlay
New-Venv
Build-Launcher
New-Shortcut
if (-not $SkipFirewall) { Add-FirewallRules } else { Write-Host "(firewall step skipped)" }
Test-SmokeTest

Write-Host ""
Write-Host "DONE. Double-click 'Iphone-Cast' on your Desktop, or run Iphone-Cast.exe." -ForegroundColor Green
