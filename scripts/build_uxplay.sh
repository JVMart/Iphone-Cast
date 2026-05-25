#!/usr/bin/env bash
# Build UxPlay inside an MSYS2 UCRT64 environment.
#
# Invoked by install.ps1 via:
#   C:\msys64\usr\bin\bash.exe -lc 'bash <unix-path-to-this-script>'
# with MSYSTEM=UCRT64 already set.
#
# What it does:
#   1. Installs the UCRT64 toolchain + GStreamer + libplist via pacman
#   2. Clones the Bonjour SDK mirror to /c/BonjourSDK (header-only mirror,
#      no Apple installer required)
#   3. Clones UxPlay, configures with cmake + Ninja, builds, installs to
#      /ucrt64 so uxplay.exe lands next to its GStreamer DLLs
set -euo pipefail
log() { printf '\n=== %s ===\n' "$*"; }

log "Step 1/4: pacman update (idempotent)"
pacman -Syuu --noconfirm --overwrite '*' || true
pacman -Suu  --noconfirm --overwrite '*' || true

log "Step 2/4: install toolchain + GStreamer + libplist"
pacman -S --needed --noconfirm \
    git \
    mingw-w64-ucrt-x86_64-cmake \
    mingw-w64-ucrt-x86_64-ninja \
    mingw-w64-ucrt-x86_64-gcc \
    mingw-w64-ucrt-x86_64-openssl \
    mingw-w64-ucrt-x86_64-libplist \
    mingw-w64-ucrt-x86_64-gstreamer \
    mingw-w64-ucrt-x86_64-gst-plugins-base \
    mingw-w64-ucrt-x86_64-gst-plugins-good \
    mingw-w64-ucrt-x86_64-gst-plugins-bad \
    mingw-w64-ucrt-x86_64-gst-plugins-ugly \
    mingw-w64-ucrt-x86_64-gst-libav

log "Step 3/4: Bonjour SDK (header + import lib) into /c/BonjourSDK"
SDK=/c/BonjourSDK
if [ ! -d "$SDK/.git" ]; then
    git clone --depth 1 https://github.com/G-P-S/bonjour-win-sdk.git "$SDK"
else
    git -C "$SDK" pull --ff-only || true
fi
test -f "$SDK/Include/dns_sd.h"
test -f "$SDK/Lib/x64/dnssd.lib"
export BONJOUR_SDK_HOME='C:\BonjourSDK'

log "Step 4/4: clone + build UxPlay"
SRC="$HOME/UxPlay"
if [ ! -d "$SRC/.git" ]; then
    git clone --depth 1 https://github.com/FDH2/UxPlay.git "$SRC"
else
    git -C "$SRC" pull --ff-only || true
fi
cd "$SRC"
rm -rf build
mkdir build
cd build

CMAKE=/ucrt64/bin/cmake.exe
NINJA=/ucrt64/bin/ninja.exe

"$CMAKE" .. -G Ninja \
    -DCMAKE_BUILD_TYPE=Release \
    -DCMAKE_INSTALL_PREFIX=/ucrt64 \
    -DCMAKE_C_COMPILER=/ucrt64/bin/gcc.exe \
    -DCMAKE_CXX_COMPILER=/ucrt64/bin/g++.exe \
    -DCMAKE_MAKE_PROGRAM="$NINJA"

"$NINJA" -j"$(nproc)"
"$NINJA" install

test -f /ucrt64/bin/uxplay.exe
echo "uxplay.exe: $(stat -c%s /ucrt64/bin/uxplay.exe) bytes"
/ucrt64/bin/uxplay.exe -v 2>&1 | head -1

log "DONE"
