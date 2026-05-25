"""
Lanzador de UxPlay como proceso externo.

UxPlay es el receptor AirPlay 2 Mirroring que si soporta "Duplicar pantalla"
del iPhone. Esta escrito en C++ y necesita GStreamer para renderizar.

Aqui simplemente:
 - localizamos el binario `uxplay.exe`
 - lo arrancamos con las opciones que queramos
 - capturamos su stdout/stderr en tiempo real y lo enviamos a la GUI
 - vigilamos las lineas de log para saber cuando hay un stream activo
   (se usa para habilitar el boton de pantalla completa y para mantener
    el monitor despierto)
 - lo detenemos limpiamente cuando se cierra la app
"""

from __future__ import annotations

import os
import re
import shutil
import signal
import subprocess
import sys
import threading
from typing import Callable, Optional

import config


# Lineas de UxPlay que indican que un iPhone se ha conectado / desconectado.
# Las elegimos compiladas en regex para que sean case-insensitive y robustas
# frente a cambios menores entre versiones (p.ej. "Accepting Client" cambio
# a "Accepting client" en alguna release).
_STREAM_START_RE = re.compile(
    r"(accepting\s+client|client_connected|connection.*established|"
    r"video\s+stream\s+connected|started\s+receiver)",
    re.IGNORECASE,
)
_STREAM_STOP_RE = re.compile(
    r"(client\s+device\s+disconnected|client_disconnected|teardown|"
    r"connection\s+closed|stopping\s+receiver)",
    re.IGNORECASE,
)


class UxPlayNotFound(RuntimeError):
    pass


def find_uxplay() -> Optional[str]:
    """Devuelve la ruta a uxplay.exe o None si no se encuentra."""
    # 1) ruta explicita en config
    if config.UXPLAY_PATH and os.path.isfile(config.UXPLAY_PATH):
        return config.UXPLAY_PATH

    # 2) en el PATH
    found = shutil.which("uxplay") or shutil.which("uxplay.exe")
    if found:
        return found

    # 3) ubicaciones tipicas de MSYS2
    candidates = [
        r"C:\msys64\ucrt64\bin\uxplay.exe",
        r"C:\msys64\mingw64\bin\uxplay.exe",
        r"C:\Program Files\UxPlay\uxplay.exe",
    ]
    for c in candidates:
        if os.path.isfile(c):
            return c
    return None


class UxPlayRunner:
    """Envuelve un subprocess.Popen de uxplay.exe."""

    def __init__(
        self,
        on_event: Optional[Callable[[str], None]] = None,
        on_stream_state: Optional[Callable[[bool], None]] = None,
    ):
        self.on_event = on_event or (lambda _msg: None)
        # Callback que se dispara cuando el estado del stream cambia.
        # True  -> el iPhone esta efectivamente duplicando pantalla.
        # False -> aun no hay stream o ya termino.
        self.on_stream_state = on_stream_state or (lambda _active: None)
        self._proc: Optional[subprocess.Popen] = None
        self._reader: Optional[threading.Thread] = None
        self._streaming: bool = False

    # ------------------------------------------------------------------ API --
    def is_running(self) -> bool:
        return self._proc is not None and self._proc.poll() is None

    def is_streaming(self) -> bool:
        return self._streaming

    @property
    def pid(self) -> Optional[int]:
        if self._proc is None:
            return None
        return self._proc.pid

    def start(self) -> None:
        if self.is_running():
            return

        exe = find_uxplay()
        if not exe:
            raise UxPlayNotFound(
                "No se encontro uxplay.exe.\n"
                "Instalalo siguiendo el README (seccion 'Instalar UxPlay'),\n"
                "o pon la ruta exacta en config.UXPLAY_PATH."
            )

        # Construimos los argumentos
        args: list[str] = [exe]
        # -n: nombre visible en el menu Duplicar pantalla
        args += ["-n", config.SERVICE_NAME]
        # -nh: oculta el logo de UxPlay cuando no hay conexion (mas limpio)
        args += ["-nh"]
        # -fs: arrancar en fullscreen (si el usuario lo pidio)
        if config.START_FULLSCREEN:
            args += ["-fs"]
        # extras del usuario (lista de strings)
        args += list(config.UXPLAY_EXTRA_ARGS)

        self.on_event(f"[Play] Lanzando: {' '.join(args)}")

        # En Windows, CREATE_NEW_PROCESS_GROUP permite enviarle CTRL_BREAK
        # para terminarlo limpiamente.
        creationflags = 0
        if sys.platform.startswith("win"):
            creationflags = subprocess.CREATE_NEW_PROCESS_GROUP

        self._proc = subprocess.Popen(
            args,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            creationflags=creationflags,
        )

        # Hilo que lee la salida de UxPlay y la reenvia a la GUI
        self._reader = threading.Thread(target=self._pump_output, daemon=True)
        self._reader.start()

        self.on_event(f"[OK] UxPlay activo. Buscalo en el iPhone como '{config.SERVICE_NAME}'")
        self.on_event("     Centro de Control -> Duplicar pantalla -> " + config.SERVICE_NAME)

    def stop(self) -> None:
        if not self.is_running() or self._proc is None:
            return
        try:
            if sys.platform.startswith("win"):
                # Intento limpio: CTRL_BREAK al grupo
                self._proc.send_signal(signal.CTRL_BREAK_EVENT)
            else:
                self._proc.terminate()
            try:
                self._proc.wait(timeout=4)
            except subprocess.TimeoutExpired:
                self._proc.kill()
                self._proc.wait(timeout=2)
        except Exception as e:
            self.on_event(f"[!] Error al detener: {e}")
        finally:
            self._proc = None
            self._reader = None
            self._set_streaming(False)
            self.on_event("[Stop] UxPlay detenido")

    # --------------------------------------------------------------- interno --
    def _set_streaming(self, active: bool) -> None:
        if active == self._streaming:
            return
        self._streaming = active
        try:
            self.on_stream_state(active)
        except Exception as e:
            self.on_event(f"[!] on_stream_state callback fallo: {e}")

    def _pump_output(self) -> None:
        assert self._proc is not None
        stream = self._proc.stdout
        if stream is None:
            return
        for line in stream:
            line = line.rstrip()
            if not line:
                continue
            self.on_event(line)
            # Estado del stream basado en patrones de log de UxPlay.
            # Si vemos los dos (start y stop) en la misma linea (raro),
            # el ultimo gana.
            if _STREAM_START_RE.search(line):
                self._set_streaming(True)
            if _STREAM_STOP_RE.search(line):
                self._set_streaming(False)
        # Cuando el stream se cierra, normalmente es que UxPlay termino
        self._set_streaming(False)
        rc = self._proc.poll() if self._proc else None
        if rc is not None and rc != 0:
            self.on_event(f"[!] UxPlay salio con codigo {rc}")
