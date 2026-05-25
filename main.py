"""
Iphone-Cast - launcher de UxPlay para Windows.

GUI Tkinter sencilla para arrancar/parar UxPlay (receptor AirPlay 2 Mirroring)
y ver su log en vivo. UxPlay es quien hace todo el trabajo real:
recibe el mirroring del iPhone y lo renderiza con GStreamer.

Uso:
    python main.py

Requiere tener UxPlay instalado (ver README).
"""

import logging
import queue
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox

import config
from uxplay_runner import UxPlayRunner, find_uxplay, UxPlayNotFound


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)


class App:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Iphone-Cast - Duplicar pantalla del iPhone")
        self.root.geometry("640x460")
        self.root.minsize(520, 380)

        self._msgs: queue.Queue[str] = queue.Queue()
        self.runner = UxPlayRunner(on_event=self._enqueue)

        self._build_ui()
        self._tick()
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self._check_uxplay_installed()

    # ------------------------------------------------------------------ UI --
    def _build_ui(self):
        pad = {"padx": 10, "pady": 6}

        # Cabecera
        header = ttk.Frame(self.root)
        header.pack(fill="x", **pad)
        ttk.Label(
            header,
            text="Receptor AirPlay 2 (Mirroring)",
            font=("Segoe UI", 14, "bold"),
        ).pack(anchor="w")
        ttk.Label(
            header,
            text=f"Nombre visible en el iPhone:  {config.SERVICE_NAME}",
            foreground="#555",
        ).pack(anchor="w")

        exe = find_uxplay()
        loc = exe if exe else "[!] uxplay.exe NO encontrado (mira el README)"
        self.lbl_uxplay = ttk.Label(header, text=f"UxPlay: {loc}", foreground="#555")
        self.lbl_uxplay.pack(anchor="w")

        # Botones
        btns = ttk.Frame(self.root)
        btns.pack(fill="x", **pad)
        self.btn_start = ttk.Button(btns, text="[Play]  Iniciar receptor", command=self.start)
        self.btn_start.pack(side="left")
        self.btn_stop = ttk.Button(btns, text="[Stop]  Parar", command=self.stop, state="disabled")
        self.btn_stop.pack(side="left", padx=(8, 0))

        self.lbl_status = ttk.Label(btns, text="Detenido", foreground="#a00")
        self.lbl_status.pack(side="right")

        # Instrucciones
        inst = ttk.LabelFrame(self.root, text="Como usarlo desde el iPhone")
        inst.pack(fill="x", **pad)
        txt = (
            "1. Pulsa 'Iniciar receptor'.\n"
            "2. iPhone y PC en la MISMA red WiFi (no VPN, no red de invitados).\n"
            f"3. En el iPhone: Centro de Control -> Duplicar pantalla -> {config.SERVICE_NAME}.\n"
            "4. La pantalla del iPhone aparecera en una ventana del PC (fullscreen por defecto)."
        )
        ttk.Label(inst, text=txt, justify="left").pack(anchor="w", padx=10, pady=8)

        # Log
        log_frame = ttk.LabelFrame(self.root, text="Log de UxPlay")
        log_frame.pack(fill="both", expand=True, **pad)
        self.txt = scrolledtext.ScrolledText(log_frame, height=12, state="disabled", wrap="word")
        self.txt.pack(fill="both", expand=True, padx=6, pady=6)

    # ----------------------------------------------------------- acciones --
    def _check_uxplay_installed(self) -> None:
        if find_uxplay() is None:
            self._log("[!] No se encontro uxplay.exe.")
            self._log("    Instalalo siguiendo el README (seccion 'Instalar UxPlay'), o")
            self._log("    pon la ruta completa en config.UXPLAY_PATH.")
            self.btn_start.config(state="disabled")

    def start(self):
        try:
            self.runner.start()
            self.btn_start.config(state="disabled")
            self.btn_stop.config(state="normal")
            self.lbl_status.config(text="Activo", foreground="#080")
        except UxPlayNotFound as e:
            messagebox.showerror("UxPlay no encontrado", str(e))
            self._log(f"[X] {e}")
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo iniciar UxPlay:\n{e}")
            self._log(f"[X] {e}")

    def stop(self):
        try:
            self.runner.stop()
        finally:
            self.btn_start.config(state="normal" if find_uxplay() else "disabled")
            self.btn_stop.config(state="disabled")
            self.lbl_status.config(text="Detenido", foreground="#a00")

    def _on_close(self):
        try:
            self.stop()
        finally:
            self.root.destroy()

    # ----------------------------------------------------------- log helpers --
    def _enqueue(self, msg: str):
        self._msgs.put(msg)

    def _tick(self):
        try:
            while True:
                self._log(self._msgs.get_nowait())
        except queue.Empty:
            pass
        # Si UxPlay muere por su cuenta, refleja el estado
        if not self.runner.is_running() and str(self.btn_stop["state"]) == "normal":
            self.btn_start.config(state="normal" if find_uxplay() else "disabled")
            self.btn_stop.config(state="disabled")
            self.lbl_status.config(text="Detenido", foreground="#a00")
        self.root.after(150, self._tick)

    def _log(self, msg: str):
        self.txt.configure(state="normal")
        self.txt.insert("end", msg + "\n")
        self.txt.see("end")
        self.txt.configure(state="disabled")


def main():
    root = tk.Tk()
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
