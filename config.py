"""Configuracion global de Iphone-Cast (launcher de UxPlay)."""

# Version del producto (se inyecta en la pestana "Ajustes" y en el instalador).
APP_VERSION = "1.0.0"

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
