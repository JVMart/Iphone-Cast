#Requires -Version 5.1
<#
.SYNOPSIS
    Stage the Iphone-Cast bundle and produce Iphone-Cast-Setup-<version>.exe.

.DESCRIPTION
    Single-shot build pipeline. Run from any cwd. Steps:

      1. Clean installer\staging\ and installer\output\.
      2. Create a fresh build venv at installer\.build-venv\ and pip-install
         pyinstaller into it (isolated from the project's runtime venv).
      3. Run PyInstaller (--windowed --onedir) over main.py with our icon
         and version metadata. Output lands in installer\staging\.
      4. Copy uxplay.exe + the audited DLL closure (122 files) from
         C:\msys64\ucrt64\bin\ into installer\staging\bin\.
      5. Copy the 14 needed GStreamer plugins into
         installer\staging\bin\lib\gstreamer-1.0\.
      6. Copy LICENSE, THIRD_PARTY_LICENSES.md, PRIVACY.md, README.md into
         installer\staging\.
      7. Invoke ISCC.exe on installer\installer.iss to produce the .exe.

    Idempotent: any step can be re-run after fixing inputs.

.PARAMETER Sign
    If provided, signs the output .exe via signtool.exe after build.
    Requires the signing cert to be available; skipped for v1.0.0.
#>
[CmdletBinding()]
param(
    [switch]$Sign
)

$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'

# --------------------------------------------------------------- paths --
$RepoRoot   = Split-Path -Parent $PSScriptRoot
$Staging    = Join-Path $PSScriptRoot 'staging'
$Output     = Join-Path $PSScriptRoot 'output'
$BuildVenv  = Join-Path $PSScriptRoot '.build-venv'
$UcrtBin    = 'C:\msys64\ucrt64\bin'
$GstPlugins = 'C:\msys64\ucrt64\lib\gstreamer-1.0'
$Iscc       = 'C:\Program Files (x86)\Inno Setup 6\ISCC.exe'

function Write-Step($msg) {
    Write-Host ""
    Write-Host "=== $msg ===" -ForegroundColor Cyan
}

function Test-PythonAvailable {
    foreach ($c in @('python', 'py')) {
        try {
            $v = & $c --version 2>&1
            if ($v -match 'Python (\d+)\.(\d+)') {
                if ([int]$matches[1] -gt 3 -or
                    ([int]$matches[1] -eq 3 -and [int]$matches[2] -ge 10)) {
                    return (Get-Command $c).Source
                }
            }
        } catch {}
    }
    throw "Python 3.10+ not found on PATH"
}

# DLL closure produced by the audit (uxplay.exe transitive + plugin deps).
# Listed explicitly so the build is deterministic and a stray new DLL in
# ucrt64\bin doesn't silently bloat the installer.
$BundledBinDlls = @(
    'avcodec-62.dll','avfilter-11.dll','avformat-62.dll','avutil-60.dll',
    'libaom.dll','libass-9.dll','libbluray-3.dll','libbrotlicommon.dll',
    'libbrotlidec.dll','libbrotlienc.dll','libbz2-1.dll','libcairo-2.dll',
    'libcairo-gobject-2.dll','libcrypto-3-x64.dll','libdatrie-1.dll',
    'libdav1d-7.dll','libdeflate.dll','libdovi.dll','libexpat-1.dll',
    'libffi-8.dll','libfontconfig-1.dll','libfreetype-6.dll','libfribidi-0.dll',
    'libgcc_s_seh-1.dll','libgdk_pixbuf-2.0-0.dll','libgio-2.0-0.dll',
    'libglib-2.0-0.dll','libgme.dll','libgmodule-2.0-0.dll','libgmp-10.dll',
    'libgnutls-30.dll','libgobject-2.0-0.dll','libgomp-1.dll','libgraphite2.dll',
    'libgsm.dll','libgstapp-1.0-0.dll','libgstaudio-1.0-0.dll',
    'libgstbase-1.0-0.dll','libgstcodecparsers-1.0-0.dll','libgstcodecs-1.0-0.dll',
    'libgstd3d11-1.0-0.dll','libgstd3dshader-1.0-0.dll','libgstdxva-1.0-0.dll',
    'libgstpbutils-1.0-0.dll','libgstreamer-1.0-0.dll','libgsttag-1.0-0.dll',
    'libgstvideo-1.0-0.dll','libharfbuzz-0.dll','libhogweed-6.dll','libhwy.dll',
    'libiconv-2.dll','libidn2-0.dll','libintl-8.dll','libjbig-0.dll',
    'libjpeg-8.dll','libjxl.dll','libjxl_cms.dll','libjxl_threads.dll',
    'liblc3-1.dll','liblcms2-2.dll','liblerc.dll','liblzma-5.dll',
    'libmodplug-1.dll','libmp3lame-0.dll','libnettle-8.dll','libogg-0.dll',
    'libopencore-amrnb-0.dll','libopencore-amrwb-0.dll','libopenjp2-7.dll',
    'libopus-0.dll','liborc-0.4-0.dll','libp11-kit-0.dll','libpango-1.0-0.dll',
    'libpangocairo-1.0-0.dll','libpangoft2-1.0-0.dll','libpangowin32-1.0-0.dll',
    'libpcre2-8-0.dll','libpixman-1-0.dll','libplacebo-360.dll','libplist-2.0.dll',
    'libpng16-16.dll','librav1e.dll','librsvg-2-2.dll','librtmp-1.dll',
    'libshaderc_shared.dll','libsharpyuv-0.dll','libsoxr.dll','libspeex-1.dll',
    'libspirv-cross-c-shared.dll','libsrt.dll','libssh.dll','libstdc++-6.dll',
    'libsvtav1enc-4.dll','libtasn1-6.dll','libthai-0.dll','libtheoradec-2.dll',
    'libtheoraenc-2.dll','libtiff-6.dll','libunibreak-7.dll','libunistring-5.dll',
    'libva.dll','libva_win32.dll','libvidstab.dll','libvorbis-0.dll',
    'libvorbisenc-2.dll','libvpl-2.dll','libvpx-1.dll','libwebp-7.dll',
    'libwebpmux-3.dll','libwinpthread-1.dll','libx264-165.dll','libx265-216.dll',
    'libxml2-16.dll','libzimg-2.dll','libzstd.dll','libzvbi-0.dll',
    'swresample-6.dll','swscale-9.dll','vulkan-1.dll','xvidcore.dll','zlib1.dll'
)

$BundledPlugins = @(
    'libgstcoreelements.dll','libgstvideoconvertscale.dll',
    'libgstvideoparsersbad.dll','libgstlibav.dll','libgstd3d11.dll',
    'libgstwasapi2.dll','libgstwasapi.dll','libgstaudioconvert.dll',
    'libgstaudioresample.dll','libgstautodetect.dll','libgstapp.dll',
    'libgstaudioparsers.dll','libgstalaw.dll','libgstplayback.dll'
)

# ------------------------------------------------------------- main flow --
Write-Step "Inputs"
$python = Test-PythonAvailable
Write-Host "  python:  $python"
Write-Host "  iscc:    $Iscc"
Write-Host "  ucrt:    $UcrtBin"
if (-not (Test-Path $Iscc))    { throw "ISCC.exe not found at $Iscc - install Inno Setup 6" }
if (-not (Test-Path $UcrtBin)) { throw "MSYS2 UCRT64 bin not found at $UcrtBin" }

Write-Step "1/7 Clean staging + output"
if (Test-Path $Staging) { Remove-Item $Staging -Recurse -Force }
New-Item -ItemType Directory -Path $Staging | Out-Null
New-Item -ItemType Directory -Path $Output -Force | Out-Null

Write-Step "2/7 Build venv + pyinstaller"
if (-not (Test-Path "$BuildVenv\Scripts\python.exe")) {
    & $python -m venv $BuildVenv
}
$venvPy = "$BuildVenv\Scripts\python.exe"
& $venvPy -m pip install --quiet --upgrade pip
& $venvPy -m pip install --quiet pyinstaller

Write-Step "3/7 PyInstaller (Python app onedir)"
$pyiWork = Join-Path $PSScriptRoot '.pyi-work'
$pyiDist = Join-Path $PSScriptRoot '.pyi-dist'
if (Test-Path $pyiWork) { Remove-Item $pyiWork -Recurse -Force }
if (Test-Path $pyiDist) { Remove-Item $pyiDist -Recurse -Force }
# --collect-submodules tkinter is paranoid in case PyInstaller's hook misses
# a piece of Tcl; --noconfirm avoids interactive overwrite prompts.
& $venvPy -m PyInstaller `
    --noconfirm `
    --windowed `
    --onedir `
    --name "Iphone-Cast" `
    --icon "$RepoRoot\Iphone-Cast.ico" `
    --collect-submodules tkinter `
    --add-data "$RepoRoot\Iphone-Cast.ico;." `
    --distpath $pyiDist `
    --workpath $pyiWork `
    --specpath $pyiWork `
    "$RepoRoot\main.py"
if ($LASTEXITCODE -ne 0) { throw "PyInstaller failed (exit $LASTEXITCODE)" }
# Robocopy the PyInstaller output into staging. Robocopy handles brand-new
# directories more reliably than Move-Item on Windows (AV-scan races on
# freshly-created child folders).
$pyiOut = Join-Path $pyiDist 'Iphone-Cast'
robocopy $pyiOut $Staging /E /NFL /NDL /NJH /NJS /NP | Out-Null
if ($LASTEXITCODE -ge 8) { throw "robocopy failed (exit $LASTEXITCODE)" }
Remove-Item $pyiDist -Recurse -Force

Write-Step "4/7 Copy uxplay.exe + DLL closure -> staging\bin"
$bin = Join-Path $Staging 'bin'
New-Item -ItemType Directory -Path $bin | Out-Null
Copy-Item (Join-Path $UcrtBin 'uxplay.exe') $bin
$dllCount = 0
foreach ($dll in $BundledBinDlls) {
    $src = Join-Path $UcrtBin $dll
    if (-not (Test-Path $src)) {
        Write-Warning "  missing in ucrt64\bin: $dll"
        continue
    }
    Copy-Item $src $bin
    $dllCount++
}
Write-Host "  copied: 1 exe + $dllCount DLLs"

Write-Step "5/7 Copy GStreamer plugins -> staging\bin\lib\gstreamer-1.0"
$plug = Join-Path $bin 'lib\gstreamer-1.0'
New-Item -ItemType Directory -Path $plug -Force | Out-Null
$plugCount = 0
foreach ($p in $BundledPlugins) {
    $src = Join-Path $GstPlugins $p
    if (-not (Test-Path $src)) {
        Write-Warning "  missing plugin: $p"
        continue
    }
    Copy-Item $src $plug
    $plugCount++
}
Write-Host "  copied: $plugCount plugins"

Write-Step "6/7 Copy LICENSE / PRIVACY / docs"
foreach ($f in @('LICENSE','THIRD_PARTY_LICENSES.md','PRIVACY.md','README.md','README.es.md')) {
    Copy-Item (Join-Path $RepoRoot $f) $Staging
}

Write-Step "7/7 Inno Setup compile"
& $Iscc /Q "/O$Output" (Join-Path $PSScriptRoot 'installer.iss')
if ($LASTEXITCODE -ne 0) { throw "ISCC failed (exit $LASTEXITCODE)" }

$built = Get-ChildItem $Output -Filter 'Iphone-Cast-Setup-*.exe' |
         Sort-Object LastWriteTime -Descending | Select-Object -First 1
Write-Host ""
Write-Host "DONE" -ForegroundColor Green
Write-Host "  output: $($built.FullName)"
Write-Host "  size:   $('{0:N1} MB' -f ($built.Length / 1MB))"

if ($Sign) {
    Write-Step "Sign (signtool)"
    # Placeholder: hook up signtool with the Trusted Signing endpoint once
    # the cert is in place.
    Write-Warning "Sign step is a placeholder; wire signtool here when the cert is ready."
}
