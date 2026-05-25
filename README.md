# Iphone-Cast

> Read this in [Espanol](README.es.md).

Windows desktop app for **mirroring your iPhone's screen** (AirPlay 2 Mirroring) to your PC. Built for personal use.

This folder contains a simple **Python launcher** (Tkinter GUI) that drives **UxPlay**, the open-source AirPlay 2 receiver that does the real work (cryptographic handshake, H.264 stream reception, GStreamer rendering).

```
+----------+    AirPlay 2 mirror     +----------------------+
|  iPhone  | ----------------------> |  Windows PC          |
|          |                         |  +----------------+  |
| Control  |                         |  | Iphone-Cast.py |  |
| Center   |  Control Center ->      |  | (GUI/launcher) |  |
|   ->     |  Screen Mirroring ->    |  +-------+--------+  |
| Screen   |  "PC-Cast"              |          v           |
| Mirror   |                         |       uxplay.exe     |
+----------+                         |       (GStreamer)    |
                                     +----------------------+
```

## Requirements

- **Windows 10/11** (64-bit)
- **Python 3.10+** installed and on `PATH`
- iPhone and PC on the **same WiFi network** (no VPN, no guest network)

Everything else (MSYS2, GStreamer, UxPlay, Bonjour SDK, venv, `.exe`, desktop shortcut, firewall rules) is set up by `install.ps1`.

## Quick install

```powershell
git clone https://github.com/JVMart/Iphone-Cast.git
cd Iphone-Cast
.\install.ps1
```

On a clean Windows 10/11 box this takes **25-40 minutes** unattended. Every step is idempotent, so if something fails mid-run you can re-execute the script without worry: it skips what's already done.

| Flag             | Effect                                                              |
|------------------|---------------------------------------------------------------------|
| `-SkipFirewall`  | Don't touch firewall rules (you'll add them yourself).              |
| `-Force`         | Re-run every step (useful after UxPlay or GStreamer updates).       |

If PowerShell blocks the script because of execution policy:

```powershell
powershell -ExecutionPolicy Bypass -File .\install.ps1
```

> **What `install.ps1` does:** (1) silently downloads and installs MSYS2, (2) invokes `scripts\build_uxplay.sh`, which installs 244 pacman packages + clones the Bonjour SDK + builds UxPlay with Ninja, (3) creates `.venv\`, (4) compiles `Iphone-Cast.exe` with the embedded icon, (5) places the desktop shortcut, (6) adds 3 firewall rules (prompts for elevation). Read the script for details.

## Manual install (advanced)

If you prefer to understand or control each step, or if `install.ps1` fails and you want to debug, follow the sections below. This is exactly what the script does.

### Install UxPlay on Windows

UxPlay has no official `.msi` installer. It's installed via **MSYS2** (a Linux-style environment for Windows that ships GStreamer). It's tedious the first time but you only do it once.

#### Step 1 - Install MSYS2

Download and install MSYS2 from https://www.msys2.org/ . Accept the default path `C:\msys64`.

When done it will open an **MSYS2 UCRT64** terminal. If it doesn't, open it from the Start menu: **"MSYS2 UCRT64"** (important — not "MSYS2 MSYS").

#### Step 2 - Update MSYS2

In the UCRT64 terminal:

```bash
pacman -Syu
# Close and reopen UCRT64 when asked.
pacman -Su
```

#### Step 3 - Install dependencies and build UxPlay

**3a. pacman packages.** In the UCRT64 terminal:

```bash
pacman -S --needed \
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
```

**3b. Bonjour SDK.** UxPlay needs Apple's Bonjour headers (`dns_sd.h`, `dnssd.lib`) to advertise the mDNS service on the network. It's not in pacman. The quick way is to clone a pre-extracted mirror of the SDK:

```bash
git clone --depth 1 https://github.com/G-P-S/bonjour-win-sdk.git /c/BonjourSDK
export BONJOUR_SDK_HOME="C:\\BonjourSDK"
```

If you want this to persist, add that `export` line to your `~/.bashrc`.

> Alternative: download "Bonjour SDK for Windows v3.0" from Apple's official site (developer.apple.com, free account required) and install it. By default it lands in `C:\Program Files\Bonjour SDK`, which is where UxPlay looks without needing to touch `BONJOUR_SDK_HOME`.

**3c. Clone and build UxPlay.**

```bash
git clone https://github.com/FDH2/UxPlay.git
cd UxPlay
mkdir build && cd build
cmake .. -G Ninja -DCMAKE_INSTALL_PREFIX=/ucrt64
ninja
ninja install
```

This puts `uxplay.exe` at `C:\msys64\ucrt64\bin\uxplay.exe` (the app auto-detects this path, and it's the same folder where the GStreamer DLLs live).

> **Note:** older guides used `cmake -G "MinGW Makefiles"` + `mingw32-make`. The current `mingw-w64-ucrt-x86_64-gcc` package no longer ships `mingw32-make.exe`, so we use Ninja instead.

> **Shortcut:** some UxPlay releases include precompiled binaries in the repo's Releases tab. If you find one for Windows, download it and point `config.py -> UXPLAY_PATH` at it. You can skip everything above.

#### Step 4 - Verify from a regular Windows terminal

Open **cmd** or **PowerShell** and try:

```cmd
C:\msys64\ucrt64\bin\uxplay.exe -h
```

If it prints the help text, it's installed. If it complains about a missing GStreamer DLL, add `C:\msys64\ucrt64\bin` to your system `PATH` (Settings -> System -> About -> Advanced system settings -> Environment Variables).

### Create the Python venv

```powershell
python -m venv .venv
.\.venv\Scripts\activate
# This app uses only the Python standard library — no pip install needed.
```

## Usage

Double-click **`Iphone-Cast.exe`** (next to `main.py`). Equivalent to opening a terminal and running:

```powershell
python main.py
```

> The `.exe` is a tiny Win32 wrapper (~520 KB with the embedded icon) that launches `pythonw.exe main.py` with no console. It prefers the project's `.venv`; if missing, it falls back to `pythonw.exe` on `PATH`. To rebuild it after editing `launcher.c`, `launcher.rc`, or the icon:
>
> ```bash
> # in the MSYS2 UCRT64 terminal, from the project root
> /ucrt64/bin/magick.exe -background none -density 512 icon.svg \
>     -define icon:auto-resize="256,128,64,48,32,16" Iphone-Cast.ico
> /ucrt64/bin/windres.exe launcher.rc -O coff -o launcher_res.o
> /ucrt64/bin/gcc.exe -O2 -mwindows -static -static-libgcc \
>     -o Iphone-Cast.exe launcher.c launcher_res.o
> ```
>
> A desktop shortcut (`Iphone-Cast.lnk`) is also created with the same icon, pointing at the `.exe`.

1. Click **Iniciar receptor** (Start receiver) in the app.
2. On the iPhone: swipe down from the top-right corner to open **Control Center**.
3. Tap **Screen Mirroring** (two overlapping rectangles icon).
4. Pick **PC-Cast** from the list.
5. Your iPhone screen shows up in a window on the PC. Open your movie app and play.
6. (Optional) Click **Pantalla completa** to get a borderless fullscreen view of just the mirror. A small `[X Salir]` overlay appears in the top-right corner and fades out after 3 seconds of no mouse/keyboard activity. Press **Esc** or click the overlay button to exit.
7. To stop: on the iPhone, go back to Control Center -> Screen Mirroring -> **Stop Mirroring**. Then click **Parar** (Stop) on the PC.

While the iPhone is actively mirroring, the PC display is kept awake (`SetThreadExecutionState`) so Windows doesn't dim or sleep mid-movie. The lock releases automatically when the iPhone disconnects or you stop the receiver.

## Configuration (`config.py`)

| Variable             | What it does                                                  |
|----------------------|---------------------------------------------------------------|
| `SERVICE_NAME`       | Name shown on the iPhone (default "PC-Cast").                 |
| `UXPLAY_PATH`        | Absolute path to `uxplay.exe` if auto-detection fails.        |
| `START_FULLSCREEN`   | If `True`, UxPlay starts in fullscreen (`-fs`).               |
| `UXPLAY_EXTRA_ARGS`  | Extra flags list (see `uxplay -h` for all of them).           |

Useful flags for `UXPLAY_EXTRA_ARGS`:

- `["-vs", "d3d11videosink"]` - force the Direct3D 11 sink (faster on Windows).
- `["-fps", "60"]` - force 60fps (if your iPhone supports it).
- `["-p", "tcp"]` - use TCP instead of UDP (stabilizes on noisy WiFi).
- `["-async"]` - asynchronous audio mode (slightly higher latency, fewer dropouts).

## Firewall and network

The first time, Windows will ask if you want to allow `uxplay.exe` (and maybe Python). **Allow both on the private network.**

If "PC-Cast" doesn't show up on the iPhone:

```powershell
# PowerShell as Administrator
New-NetFirewallRule -DisplayName "UxPlay AirPlay TCP" `
    -Direction Inbound -Protocol TCP -LocalPort 7000,7001,7100 -Action Allow
New-NetFirewallRule -DisplayName "UxPlay AirPlay UDP" `
    -Direction Inbound -Protocol UDP -LocalPort 6000-7100 -Action Allow
New-NetFirewallRule -DisplayName "mDNS" `
    -Direction Inbound -Protocol UDP -LocalPort 5353 -Action Allow
```

## What works and what doesn't

**Works fine** (no DRM or permissive DRM): Photos, Camera, Safari (web), YouTube, Twitch, games, iPhone home screen, Messages, "alternative" streaming apps, general browsing.

**Does NOT work** (DRM-blocked): **Netflix, Disney+, HBO Max, Apple TV+, Prime Video, Movistar+, DAZN, Filmin**. These apps detect that the receiver isn't MFi-certified and **render a black screen or show an error**. There's no legal way to get around this from the receiver side — it's end-to-end DRM.

If your "movie app" is one of the above, **you can't mirror it**. This is independent of UxPlay: no solution (paid or otherwise) outside Apple's MFi list will let you.

## Project structure

```
Iphone-cast/
|-- install.ps1         # All-in-one installer (main entry point)
|-- scripts/
|   +-- build_uxplay.sh # UxPlay build (invoked by install.ps1)
|-- main.py             # Tkinter GUI (launcher)
|-- uxplay_runner.py    # subprocess wrapper for uxplay.exe
|-- fullscreen.py       # Win32 fullscreen, overlay, Esc hook, keep-awake
|-- config.py           # Service name, path to UxPlay, extra flags
|-- launcher.c          # Wrapper .exe source (Win32, gcc-compilable)
|-- launcher.rc         # Resource embedding the icon into the .exe
|-- icon.svg            # Vector design of the icon (AirPlay-style)
|-- requirements.txt    # (empty - standard library only)
|-- README.md           # This file (English)
+-- README.es.md        # Spanish version
```

`Iphone-Cast.exe`, `Iphone-Cast.ico`, `.venv/`, and `launcher_res.o` are artifacts generated by `install.ps1`; they're in `.gitignore` to keep the public repo clean.

## Troubleshooting

- **"uxplay.exe not found"** -> install UxPlay (section above) or set `UXPLAY_PATH` in `config.py`.
- **"PC-Cast" shows up but tapping it doesn't connect** -> port 7000 is taken by another app (close AirServer/5KPlayer/iTunes). Or firewall is blocking UDP 6000-7100.
- **Connects but the picture is black** -> the iPhone app has DRM. Nothing you can do.
- **Stuttering picture / audio drift** -> try `UXPLAY_EXTRA_ARGS = ["-p", "tcp"]` or move the iPhone closer to the router.
- **UxPlay window doesn't appear** -> the GStreamer sink might have failed. Try `UXPLAY_EXTRA_ARGS = ["-vs", "d3d11videosink"]` or `["-vs", "glimagesink"]`.
