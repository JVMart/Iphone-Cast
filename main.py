"""
Iphone-Cast - launcher de UxPlay para Windows.

GUI Tkinter sencilla para arrancar/parar UxPlay (receptor AirPlay 2 Mirroring),
ver su log en vivo, entrar en modo pantalla completa y elegir idioma.

Uso:
    python main.py
"""
from __future__ import annotations

import queue
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox

import config
import i18n
import user_settings
from uxplay_runner import UxPlayRunner, find_uxplay, UxPlayNotFound
from fullscreen import FullscreenManager


# Resolver idioma una sola vez al arranque. La eleccion del usuario en la
# pestana Ajustes se persiste a settings.json pero requiere reinicio para
# aplicarse (mas simple y robusto que re-renderizar widgets vivos).
i18n.set_language(user_settings.get_language(default="en"))


class App:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title(i18n.t("app_title"))
        self.root.geometry("680x520")
        self.root.minsize(560, 420)

        self._msgs: queue.Queue[str] = queue.Queue()
        self.runner = UxPlayRunner(on_event=self._enqueue)

        self._build_ui()

        # Pantalla completa + keep-awake (creado tras _build_ui porque
        # necesita btn_fs ya construido).
        self.fs = FullscreenManager(
            self.root,
            get_pid=lambda: self.runner.pid,
            log=self._enqueue,
        )
        self.fs.on_can_fullscreen_change = self._set_fullscreen_button_state
        self.runner.on_stream_state = self.fs.on_stream_state_changed
        self.btn_fs.config(command=self.fs.toggle)

        self._tick()
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self._check_uxplay_installed()

    # ------------------------------------------------------------------ UI --
    def _build_ui(self):
        nb = ttk.Notebook(self.root)
        nb.pack(fill="both", expand=True, padx=8, pady=8)

        self._tab_receiver = ttk.Frame(nb)
        self._tab_settings = ttk.Frame(nb)
        nb.add(self._tab_receiver, text=i18n.t("tab_receiver"))
        nb.add(self._tab_settings, text=i18n.t("tab_settings"))

        self._build_receiver_tab(self._tab_receiver)
        self._build_settings_tab(self._tab_settings)

    def _build_receiver_tab(self, parent: ttk.Frame) -> None:
        pad = {"padx": 10, "pady": 6}

        # Cabecera
        header = ttk.Frame(parent)
        header.pack(fill="x", **pad)
        ttk.Label(
            header,
            text=i18n.t("header_title"),
            font=("Segoe UI", 14, "bold"),
        ).pack(anchor="w")
        ttk.Label(
            header,
            text=i18n.t("label_service_name", name=config.SERVICE_NAME),
            foreground="#555",
        ).pack(anchor="w")

        exe = find_uxplay()
        loc = exe if exe else i18n.t("label_uxplay_missing")
        self.lbl_uxplay = ttk.Label(
            header, text=i18n.t("label_uxplay", path=loc), foreground="#555"
        )
        self.lbl_uxplay.pack(anchor="w")

        # Botones
        btns = ttk.Frame(parent)
        btns.pack(fill="x", **pad)
        self.btn_start = ttk.Button(
            btns, text=i18n.t("btn_start"), command=self.start
        )
        self.btn_start.pack(side="left")
        self.btn_stop = ttk.Button(
            btns, text=i18n.t("btn_stop"), command=self.stop, state="disabled"
        )
        self.btn_stop.pack(side="left", padx=(8, 0))
        self.btn_fs = ttk.Button(
            btns, text=i18n.t("btn_fullscreen"), state="disabled"
        )
        self.btn_fs.pack(side="left", padx=(8, 0))

        self.lbl_status = ttk.Label(
            btns, text=i18n.t("status_stopped"), foreground="#a00"
        )
        self.lbl_status.pack(side="right")

        # Instrucciones
        inst = ttk.LabelFrame(parent, text=i18n.t("instructions_frame"))
        inst.pack(fill="x", **pad)
        ttk.Label(
            inst,
            text=i18n.t("instructions_text", name=config.SERVICE_NAME),
            justify="left",
        ).pack(anchor="w", padx=10, pady=8)

        # Log
        log_frame = ttk.LabelFrame(parent, text=i18n.t("log_frame"))
        log_frame.pack(fill="both", expand=True, **pad)
        self.txt = scrolledtext.ScrolledText(
            log_frame, height=12, state="disabled", wrap="word"
        )
        self.txt.pack(fill="both", expand=True, padx=6, pady=6)

    def _build_settings_tab(self, parent: ttk.Frame) -> None:
        pad = {"padx": 14, "pady": 10}

        lang_frame = ttk.Frame(parent)
        lang_frame.pack(fill="x", **pad)
        ttk.Label(
            lang_frame,
            text=i18n.t("settings_lang_label"),
            font=("Segoe UI", 10, "bold"),
        ).pack(anchor="w")

        # Dropdown de idiomas: muestra el nombre nativo, guarda el codigo.
        self._lang_var = tk.StringVar(value=i18n.LANGUAGES[i18n.current()])
        cb = ttk.Combobox(
            lang_frame,
            textvariable=self._lang_var,
            values=list(i18n.LANGUAGES.values()),
            state="readonly",
            width=20,
        )
        cb.pack(anchor="w", pady=(4, 0))
        cb.bind("<<ComboboxSelected>>", self._on_language_changed)

        self._lbl_lang_note = ttk.Label(
            lang_frame, text="", foreground="#0A84FF"
        )
        self._lbl_lang_note.pack(anchor="w", pady=(4, 0))

        # About
        about_frame = ttk.LabelFrame(
            parent, text=i18n.t("settings_about_title")
        )
        about_frame.pack(fill="x", **pad)
        ttk.Label(
            about_frame,
            text=i18n.t("settings_about_text", version=config.APP_VERSION),
            justify="left",
        ).pack(anchor="w", padx=10, pady=8)

    def _on_language_changed(self, _event=None) -> None:
        # Mapear nombre nativo -> codigo
        chosen = self._lang_var.get()
        code = next(
            (c for c, name in i18n.LANGUAGES.items() if name == chosen),
            i18n.DEFAULT_LANGUAGE,
        )
        user_settings.set_language(code)
        self._lbl_lang_note.config(text=i18n.t("settings_lang_note"))

    # ----------------------------------------------------------- acciones --
    def _check_uxplay_installed(self) -> None:
        if find_uxplay() is None:
            self._log(i18n.t("log_uxplay_missing_a"))
            self._log(i18n.t("log_uxplay_missing_b"))
            self._log(i18n.t("log_uxplay_missing_c"))
            self.btn_start.config(state="disabled")

    def start(self):
        try:
            self.runner.start()
            self.btn_start.config(state="disabled")
            self.btn_stop.config(state="normal")
            self.lbl_status.config(
                text=i18n.t("status_active"), foreground="#080"
            )
        except UxPlayNotFound as e:
            messagebox.showerror(i18n.t("dlg_uxplay_not_found"), str(e))
            self._log(f"[X] {e}")
        except Exception as e:
            messagebox.showerror(
                i18n.t("dlg_error"),
                i18n.t("dlg_start_failed", err=e),
            )
            self._log(f"[X] {e}")

    def stop(self):
        try:
            self.fs.shutdown()
            self.runner.stop()
        finally:
            self.btn_start.config(
                state="normal" if find_uxplay() else "disabled"
            )
            self.btn_stop.config(state="disabled")
            self.btn_fs.config(state="disabled")
            self.lbl_status.config(
                text=i18n.t("status_stopped"), foreground="#a00"
            )

    def _set_fullscreen_button_state(self, enabled: bool) -> None:
        self.btn_fs.config(state="normal" if enabled else "disabled")

    def _on_close(self):
        try:
            self.fs.shutdown()
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
        if not self.runner.is_running() and str(self.btn_stop["state"]) == "normal":
            self.btn_start.config(
                state="normal" if find_uxplay() else "disabled"
            )
            self.btn_stop.config(state="disabled")
            self.lbl_status.config(
                text=i18n.t("status_stopped"), foreground="#a00"
            )
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
