"""Configuracion global de Iphone-Cast (launcher de UxPlay)."""

# Nombre visible en el menu "Duplicar pantalla" del iPhone.
SERVICE_NAME = "PC-Cast"

# Si esta vacio, se busca uxplay.exe en el PATH y en rutas tipicas
# (C:\msys64\ucrt64\bin\, C:\msys64\mingw64\bin\, C:\Program Files\UxPlay\).
# Si tu binario esta en otro sitio, pon aqui la ruta absoluta.
UXPLAY_PATH = ""

# Arrancar UxPlay en pantalla completa (-fs).
START_FULLSCREEN = True

# Argumentos extra para uxplay.exe. Utiles:
#   "-vs", "d3d11videosink"  -> forzar sink Direct3D11 (Windows)
#   "-async"                 -> modo audio asincrono
#   "-fps", "60"             -> forzar 60fps
#   "-p", "tcp"              -> usar TCP (ayuda con WiFi inestable)
#   "-bt709"                 -> forzar colorimetria BT.709
UXPLAY_EXTRA_ARGS: list[str] = []
