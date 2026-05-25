# Third-Party Licenses

The Iphone-Cast installer (`Iphone-Cast-Setup-x.y.z.exe`) bundles
third-party software. Each component is governed by its own license. The
Iphone-Cast project code itself is licensed under the MIT License (see
[`LICENSE`](LICENSE)).

Source code for every component is available at the upstream URL listed
below; the Iphone-Cast project does not modify these components and does
not host their source. Where required by GPL or LGPL, the corresponding
source can be obtained from each upstream project.

## GPL v3

- **UxPlay** — open-source AirPlay 2 mirroring receiver. Distributed
  inside the installer as `uxplay.exe`.
  Source: <https://github.com/FDH2/UxPlay>
  License: GNU General Public License, version 3 (or later).
  Full text: <https://www.gnu.org/licenses/gpl-3.0.html>

## GPL v2 (transitive via the FFmpeg / gst-libav decoder pipeline)

Some codec libraries linked by `libgstlibav.dll` (via `avcodec-*.dll`) are
GPL-licensed. They are loaded at runtime as part of the GStreamer plugin
chain. Loading does not imply use — the Iphone-Cast pipeline only invokes
the H.264 and AAC decoders, which are LGPL — but their presence as link
dependencies makes the combined bundle GPL.

- **x264** — H.264 encoder. Source: <https://www.videolan.org/developers/x264.html>. License: GPL v2 (or later).
- **x265** — H.265/HEVC encoder. Source: <https://www.videolan.org/developers/x265.html>. License: GPL v2 (or later).
- **libpostproc** (FFmpeg) — only present if FFmpeg was built with `--enable-gpl`. License: GPL v2 (or later).

## LGPL v2.1 (or later)

- **GStreamer** (core + base + plugins kept by the audit). Source: <https://gstreamer.freedesktop.org/>. License: LGPL v2.1 (or later).
- **glib** / **gobject** / **gio**. Source: <https://gitlab.gnome.org/GNOME/glib>. License: LGPL v2.1 (or later).
- **FFmpeg** libraries: `libavcodec`, `libavformat`, `libavfilter`, `libavutil`, `libswresample`, `libswscale`. Source: <https://ffmpeg.org/>. License: LGPL v2.1 (or later); see GPL v2 note above for transitive deps.
- **libplist** — Apple property list parser used by UxPlay. Source: <https://github.com/libimobiledevice/libplist>. License: LGPL v2.1 (or later).
- **libiconv** — character set conversion. Source: <https://www.gnu.org/software/libiconv/>. License: LGPL v2.1.

## Permissive (MIT, BSD, Zlib, ISC, etc.)

- **Python 3.10 embeddable distribution** — interpreter + standard library + Tcl/Tk. Source: <https://www.python.org/>. License: Python Software Foundation License.
- **OpenSSL** (`libcrypto-3-x64.dll`). Source: <https://www.openssl.org/>. License: Apache License 2.0.
- **libwinpthread** (MinGW-w64 pthreads). Source: <https://www.mingw-w64.org/>. License: MIT.
- **libffi** — foreign function interface. Source: <https://github.com/libffi/libffi>. License: MIT.
- **libpcre2** — Perl-compatible regex. Source: <https://www.pcre.org/>. License: BSD 3-clause.
- **zlib** / **libdeflate** / **libzstd** / **liblzma** / **libbz2** — compression. Licenses: zlib license / MIT / BSD.
- **libpng** / **libjpeg-turbo** / **libwebp** / **libtiff** / **libjxl** / **libgif** — image codecs (loaded transitively, not used at runtime). Licenses: zlib-like / IJG / BSD / various permissive.
- **libopus** / **libvorbis** / **libogg** / **libspeex** / **libtheora** — Xiph media codecs (loaded transitively, not used at runtime). License: BSD 3-clause.
- **libaom** / **libdav1d** / **librav1e** / **libsvtav1** — AV1 codecs (loaded transitively, not used at runtime). License: BSD 2-clause / ISC.
- **harfbuzz**, **freetype**, **fribidi**, **libthai**, **libdatrie**, **graphite2**, **pango**, **cairo**, **pixman**, **expat**, **libxml2** — text/layout/parsing libraries (loaded transitively for GStreamer plugin init). Licenses: MIT / FTL / BSD / various permissive.
- **MinGW-w64 runtime** (`libgcc_s_seh-1.dll`, `libstdc++-6.dll`, `libgomp-1.dll`). License: GCC Runtime Library Exception 3.1 (LGPL-style).

## Apple components (linked but not redistributed)

Iphone-Cast links against the Apple **Bonjour SDK** at build time
(`dns_sd.h` header + `dnssd.lib` import library). The runtime
`dnssd.dll` is provided by the user's existing Bonjour installation
(commonly via iTunes or Apple's free Bonjour Print Services for
Windows). The Iphone-Cast installer **does not** redistribute Apple's
SDK, runtime, or installer.

If Bonjour is absent on the target machine, the Iphone-Cast installer
prompts the user to obtain it from
<https://support.apple.com/kb/dl999>.

## License texts in the installer

The installer payload (`Iphone-Cast-Setup-x.y.z.exe`) includes:

- `LICENSE` — MIT, our code (shown on the wizard's "License Agreement" page).
- `licenses/GPL-3.0.txt` — GPL v3 text.
- `licenses/GPL-2.0.txt` — GPL v2 text.
- `licenses/LGPL-2.1.txt` — LGPL v2.1 text.
- `THIRD_PARTY_LICENSES.md` — this file.

## Distribution obligations (summary)

Because the combined installer contains GPL-licensed code (UxPlay,
plus x264/x265 link-time deps), redistributing it requires offering
recipients the same GPL rights:

1. Pass along the GPL license text (we ship `GPL-3.0.txt` and `GPL-2.0.txt`).
2. Make the corresponding source code available. Iphone-Cast satisfies this by linking to upstream repositories above and to the GitHub mirror of this project at <https://github.com/JVMart/Iphone-Cast>.
3. Preserve attribution notices.

These obligations apply to anyone redistributing the installer; using
the application yourself does not impose obligations.
