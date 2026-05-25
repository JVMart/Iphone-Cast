"""
Modo pantalla completa para la ventana de UxPlay + utilidades Windows.

Responsabilidades:
 - Localizar la ventana de video de uxplay.exe (por PID, no por titulo).
 - Quitarle el chrome (titulo, bordes) y expandirla al monitor donde esta.
 - Mostrar un overlay flotante con un boton "Salir" arriba a la derecha,
   semi-transparente, que se desvanece tras 3s sin movimiento de raton/teclado.
 - Hook global de teclado (WH_KEYBOARD_LL) para que Esc salga aunque el
   foco lo tenga UxPlay.
 - Mantener el monitor despierto mientras hay stream activo
   (SetThreadExecutionState).

Sin dependencias externas: solo ctypes + tkinter.
"""
from __future__ import annotations

import ctypes
import threading
import time
import tkinter as tk
from ctypes import wintypes
from typing import Callable, Optional


# ---------------------------------------------------------- Win32 plumbing --
user32 = ctypes.WinDLL("user32", use_last_error=True)
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

# Constantes Win32
GWL_STYLE = -16
GWL_EXSTYLE = -20
WS_OVERLAPPEDWINDOW = 0x00CF0000
WS_POPUP = 0x80000000
WS_VISIBLE = 0x10000000
WS_EX_TOPMOST = 0x00000008
WS_EX_TOOLWINDOW = 0x00000080
SWP_NOZORDER = 0x0004
SWP_SHOWWINDOW = 0x0040
SWP_FRAMECHANGED = 0x0020
HWND_TOP = 0
HWND_TOPMOST = -1
HWND_NOTOPMOST = -2
SW_SHOW = 5
SW_MAXIMIZE = 3
SM_CXSCREEN = 0
SM_CYSCREEN = 1
MONITOR_DEFAULTTONEAREST = 2

# SetThreadExecutionState flags
ES_CONTINUOUS = 0x80000000
ES_DISPLAY_REQUIRED = 0x00000002
ES_SYSTEM_REQUIRED = 0x00000001

# Hook de teclado
WH_KEYBOARD_LL = 13
WM_KEYDOWN = 0x0100
WM_SYSKEYDOWN = 0x0104
WM_QUIT = 0x0012
HC_ACTION = 0
VK_ESCAPE = 0x1B


class POINT(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]


class MONITORINFO(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.DWORD),
        ("rcMonitor", wintypes.RECT),
        ("rcWork", wintypes.RECT),
        ("dwFlags", wintypes.DWORD),
    ]


class KBDLLHOOKSTRUCT(ctypes.Structure):
    _fields_ = [
        ("vkCode", wintypes.DWORD),
        ("scanCode", wintypes.DWORD),
        ("flags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.c_void_p),
    ]


# Firmas explicitas para evitar truncamiento de punteros en x64.
user32.SetWindowLongPtrW.restype = ctypes.c_void_p
user32.SetWindowLongPtrW.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_void_p]
user32.GetWindowLongPtrW.restype = ctypes.c_void_p
user32.GetWindowLongPtrW.argtypes = [wintypes.HWND, ctypes.c_int]
user32.MonitorFromWindow.restype = wintypes.HANDLE
user32.MonitorFromWindow.argtypes = [wintypes.HWND, wintypes.DWORD]
user32.GetMonitorInfoW.restype = wintypes.BOOL
user32.GetMonitorInfoW.argtypes = [wintypes.HANDLE, ctypes.POINTER(MONITORINFO)]
user32.SetWindowsHookExW.restype = wintypes.HHOOK
user32.UnhookWindowsHookEx.restype = wintypes.BOOL
user32.CallNextHookEx.restype = ctypes.c_long
user32.GetCursorPos.argtypes = [ctypes.POINTER(POINT)]
user32.GetCursorPos.restype = wintypes.BOOL

WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
LowLevelKeyboardProc = ctypes.WINFUNCTYPE(
    ctypes.c_long, ctypes.c_int, wintypes.WPARAM, wintypes.LPARAM
)


# --------------------------------------------------------- window discovery --
def find_window_by_pid(pid: int) -> Optional[int]:
    """Devuelve el HWND de la ventana visible mas grande propiedad de `pid`."""
    best_hwnd = None
    best_area = 0

    @WNDENUMPROC
    def cb(hwnd, _lparam):
        nonlocal best_hwnd, best_area
        if not user32.IsWindowVisible(hwnd):
            return True
        wpid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(wpid))
        if wpid.value != pid:
            return True
        rect = wintypes.RECT()
        user32.GetWindowRect(hwnd, ctypes.byref(rect))
        area = (rect.right - rect.left) * (rect.bottom - rect.top)
        if area > best_area and area > 100 * 100:  # filtra ventanas residuales
            best_area = area
            best_hwnd = hwnd
        return True

    user32.EnumWindows(cb, 0)
    return best_hwnd


def _monitor_rect_for_window(hwnd: int) -> tuple[int, int, int, int]:
    """Devuelve (left, top, width, height) del monitor donde esta hwnd."""
    mon = user32.MonitorFromWindow(hwnd, MONITOR_DEFAULTTONEAREST)
    mi = MONITORINFO()
    mi.cbSize = ctypes.sizeof(MONITORINFO)
    user32.GetMonitorInfoW(mon, ctypes.byref(mi))
    r = mi.rcMonitor
    return r.left, r.top, r.right - r.left, r.bottom - r.top


# ----------------------------------------------------- keep-display-awake --
class KeepAwake:
    """Wrapper de SetThreadExecutionState (idempotente)."""

    def __init__(self) -> None:
        self._active = False

    def acquire(self) -> None:
        if self._active:
            return
        kernel32.SetThreadExecutionState(
            ES_CONTINUOUS | ES_DISPLAY_REQUIRED | ES_SYSTEM_REQUIRED
        )
        self._active = True

    def release(self) -> None:
        if not self._active:
            return
        kernel32.SetThreadExecutionState(ES_CONTINUOUS)
        self._active = False


# ---------------------------------------------------------- Esc hook (LL) --
class EscapeHook:
    """Hook de teclado de bajo nivel; llama on_escape cuando se pulsa Esc.

    Corre en su propio hilo con bombeo de mensajes Win32. on_escape se
    invoca en ese hilo, asi que debe ser thread-safe (en nuestro caso
    delega a Tk via root.after_idle).
    """

    def __init__(self, on_escape: Callable[[], None]):
        self._on_escape = on_escape
        self._thread: Optional[threading.Thread] = None
        self._thread_id: Optional[int] = None
        self._hook: Optional[int] = None
        self._proc = None  # mantener viva la WINFUNCTYPE

    def install(self) -> None:
        if self._thread:
            return
        ready = threading.Event()
        self._thread = threading.Thread(
            target=self._run, args=(ready,), daemon=True, name="EscHook"
        )
        self._thread.start()
        ready.wait(timeout=2)

    def uninstall(self) -> None:
        if not self._thread:
            return
        if self._thread_id is not None:
            user32.PostThreadMessageW(self._thread_id, WM_QUIT, 0, 0)
        self._thread.join(timeout=1)
        self._thread = None
        self._thread_id = None
        self._hook = None
        self._proc = None

    def _run(self, ready: threading.Event) -> None:
        self._thread_id = kernel32.GetCurrentThreadId()

        @LowLevelKeyboardProc
        def proc(nCode, wParam, lParam):
            if nCode == HC_ACTION and wParam in (WM_KEYDOWN, WM_SYSKEYDOWN):
                kb = ctypes.cast(lParam, ctypes.POINTER(KBDLLHOOKSTRUCT))[0]
                if kb.vkCode == VK_ESCAPE:
                    try:
                        self._on_escape()
                    except Exception:
                        pass
            return user32.CallNextHookEx(None, nCode, wParam, lParam)

        self._proc = proc
        self._hook = user32.SetWindowsHookExW(
            WH_KEYBOARD_LL, proc, kernel32.GetModuleHandleW(None), 0
        )
        ready.set()
        if not self._hook:
            return

        msg = wintypes.MSG()
        while True:
            ret = user32.GetMessageW(ctypes.byref(msg), None, 0, 0)
            if ret in (0, -1):
                break
            user32.TranslateMessage(ctypes.byref(msg))
            user32.DispatchMessageW(ctypes.byref(msg))

        if self._hook:
            user32.UnhookWindowsHookEx(self._hook)
            self._hook = None


# ----------------------------------------------------- the manager class --
class FullscreenManager:
    """Coordina el modo pantalla completa.

    Uso desde main.py:
        fs = FullscreenManager(root, runner, log)
        # crea boton ttk.Button(parent, command=fs.toggle)
        runner.on_stream_state = fs.on_stream_state_changed

    El boton de Tk lo gestiona el caller (asi mantenemos la responsabilidad
    de layout en main.py); aqui solo exponemos hooks para habilitarlo/desactivarlo.
    """

    OVERLAY_FADE_AFTER_SEC = 3.0
    OVERLAY_POLL_MS = 100

    def __init__(self, root: tk.Tk, get_pid: Callable[[], Optional[int]],
                 log: Callable[[str], None]):
        self.root = root
        self.get_pid = get_pid
        self.log = log

        self._active = False
        self._target_hwnd: Optional[int] = None
        self._saved_style: Optional[int] = None
        self._saved_exstyle: Optional[int] = None
        self._saved_rect: Optional[wintypes.RECT] = None

        self._overlay: Optional[tk.Toplevel] = None
        self._overlay_btn: Optional[tk.Button] = None
        self._last_cursor = (0, 0)
        self._last_activity = 0.0
        self._overlay_visible = False

        self.keep_awake = KeepAwake()
        self._esc_hook = EscapeHook(on_escape=self._on_esc_pressed)

        # callbacks externos (ej. main.py habilita su boton)
        self.on_can_fullscreen_change: Callable[[bool], None] = lambda _b: None

    # ------------------------------------------------ stream state plumbing --
    def on_stream_state_changed(self, streaming: bool) -> None:
        """Lo conecta el caller a UxPlayRunner.on_stream_state.

        Se llama desde el hilo de _pump_output, asi que NO tocamos Tk
        directamente: re-enviamos al hilo principal via after_idle.
        """
        self.root.after_idle(self._apply_stream_state, streaming)

    def _apply_stream_state(self, streaming: bool) -> None:
        if streaming:
            self.keep_awake.acquire()
            self.on_can_fullscreen_change(True)
        else:
            self.keep_awake.release()
            self.on_can_fullscreen_change(False)
            if self._active:
                # iPhone se desconecto durante fullscreen: salimos.
                self.exit_fullscreen()

    # -------------------------------------------------------------- toggle --
    def toggle(self) -> None:
        if self._active:
            self.exit_fullscreen()
        else:
            self.enter_fullscreen()

    def enter_fullscreen(self) -> None:
        if self._active:
            return
        pid = self.get_pid()
        if not pid:
            self.log("[FS] UxPlay no esta corriendo.")
            return

        # La ventana de video puede tardar un pelin en aparecer; reintentamos.
        hwnd = None
        for _ in range(20):  # ~2 segundos
            hwnd = find_window_by_pid(pid)
            if hwnd:
                break
            time.sleep(0.1)
        if not hwnd:
            self.log("[FS] No encontre la ventana de UxPlay. Intentalo de nuevo cuando el iPhone este duplicando.")
            return

        # Guardar estado original
        self._target_hwnd = hwnd
        self._saved_style = user32.GetWindowLongPtrW(hwnd, GWL_STYLE)
        self._saved_exstyle = user32.GetWindowLongPtrW(hwnd, GWL_EXSTYLE)
        rect = wintypes.RECT()
        user32.GetWindowRect(hwnd, ctypes.byref(rect))
        self._saved_rect = rect

        # Aplicar estilo "popup borderless"
        new_style = (self._saved_style & ~WS_OVERLAPPEDWINDOW) | WS_POPUP | WS_VISIBLE
        user32.SetWindowLongPtrW(hwnd, GWL_STYLE, new_style)

        left, top, w, h = _monitor_rect_for_window(hwnd)
        user32.SetWindowPos(
            hwnd, HWND_TOPMOST, left, top, w, h,
            SWP_FRAMECHANGED | SWP_SHOWWINDOW,
        )

        # Overlay flotante
        self._build_overlay(left, top, w)

        # Hook Esc + polling de raton/teclado para auto-hide del overlay
        self._esc_hook.install()
        self._last_activity = time.monotonic()
        self._poll_inactivity()

        self._active = True
        self.log("[FS] Pantalla completa activada. Esc para salir.")

    def exit_fullscreen(self) -> None:
        if not self._active:
            return
        self._active = False
        self._esc_hook.uninstall()

        if self._overlay is not None:
            try:
                self._overlay.destroy()
            except Exception:
                pass
            self._overlay = None
            self._overlay_btn = None

        if self._target_hwnd and self._saved_style is not None:
            user32.SetWindowLongPtrW(self._target_hwnd, GWL_STYLE, self._saved_style)
            if self._saved_exstyle is not None:
                user32.SetWindowLongPtrW(
                    self._target_hwnd, GWL_EXSTYLE, self._saved_exstyle
                )
            r = self._saved_rect
            if r is not None:
                user32.SetWindowPos(
                    self._target_hwnd, HWND_NOTOPMOST,
                    r.left, r.top, r.right - r.left, r.bottom - r.top,
                    SWP_FRAMECHANGED | SWP_SHOWWINDOW,
                )
        self._target_hwnd = None
        self._saved_style = None
        self._saved_exstyle = None
        self._saved_rect = None
        self.log("[FS] Pantalla completa desactivada.")

    # ------------------------------------------------------------ overlay --
    def _build_overlay(self, mon_left: int, mon_top: int, mon_w: int) -> None:
        ov = tk.Toplevel(self.root)
        ov.overrideredirect(True)
        ov.attributes("-topmost", True)
        ov.attributes("-alpha", 0.85)
        ov.configure(bg="#000000")
        ov.title("Iphone-Cast overlay")

        btn = tk.Button(
            ov,
            text="✕  Salir (Esc)",
            font=("Segoe UI", 11, "bold"),
            bg="#0A84FF",
            fg="white",
            activebackground="#0060d0",
            activeforeground="white",
            bd=0,
            padx=14, pady=8,
            cursor="hand2",
            command=self.exit_fullscreen,
        )
        btn.pack()

        ov.update_idletasks()
        ow = ov.winfo_reqwidth()
        oh = ov.winfo_reqheight()
        x = mon_left + mon_w - ow - 24
        y = mon_top + 24
        ov.geometry(f"{ow}x{oh}+{x}+{y}")

        self._overlay = ov
        self._overlay_btn = btn
        self._overlay_visible = True

    def _poll_inactivity(self) -> None:
        if not self._active:
            return
        pt = POINT()
        user32.GetCursorPos(ctypes.byref(pt))
        cur = (pt.x, pt.y)
        if cur != self._last_cursor:
            self._last_cursor = cur
            self._last_activity = time.monotonic()
            self._show_overlay()
        else:
            idle = time.monotonic() - self._last_activity
            if idle >= self.OVERLAY_FADE_AFTER_SEC and self._overlay_visible:
                self._hide_overlay()
        self.root.after(self.OVERLAY_POLL_MS, self._poll_inactivity)

    def _show_overlay(self) -> None:
        if not self._overlay or self._overlay_visible:
            return
        try:
            self._overlay.deiconify()
            self._overlay.attributes("-alpha", 0.85)
        except Exception:
            pass
        self._overlay_visible = True

    def _hide_overlay(self) -> None:
        if not self._overlay or not self._overlay_visible:
            return
        try:
            self._overlay.withdraw()
        except Exception:
            pass
        self._overlay_visible = False

    # ------------------------------------------------------------- esc cb --
    def _on_esc_pressed(self) -> None:
        # Llamado desde el hilo del hook; rebotamos al hilo de Tk.
        try:
            self.root.after_idle(self.exit_fullscreen)
        except Exception:
            pass

    # ------------------------------------------------------- limpieza app --
    def shutdown(self) -> None:
        """Cleanup completo: salir de fullscreen, soltar keep-awake, hook."""
        try:
            self.exit_fullscreen()
        finally:
            self.keep_awake.release()
            self._esc_hook.uninstall()
