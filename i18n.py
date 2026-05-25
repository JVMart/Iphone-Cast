"""
Tabla de traducciones plana para Iphone-Cast.

API minima:
    import i18n
    i18n.set_language("en")          # o "es" / "fr"
    i18n.t("btn_start")              # devuelve el string traducido
    i18n.t("log_active", name="PC")  # con placeholders {name}

Sin dependencias externas. Para anadir un idioma nuevo: copia el bloque
"en" entero, traduce los valores, registralo en LANGUAGES y en _strings.

Para anadir un string nuevo: agregalo en LOS TRES bloques (en/es/fr).
La funcion t() devuelve la clave entre [[brackets]] si falta una
traduccion para facilitar detectar omisiones durante el testing.
"""
from __future__ import annotations

from typing import Dict

# Codigo -> nombre nativo del idioma (lo que se muestra en el dropdown).
LANGUAGES: Dict[str, str] = {
    "en": "English",
    "es": "Español",
    "fr": "Français",
}

DEFAULT_LANGUAGE = "en"

_current_lang = DEFAULT_LANGUAGE


def set_language(code: str) -> None:
    global _current_lang
    if code in LANGUAGES:
        _current_lang = code
    else:
        _current_lang = DEFAULT_LANGUAGE


def current() -> str:
    return _current_lang


def t(key: str, **kwargs) -> str:
    """Devuelve el string traducido al idioma actual, con formato kwargs."""
    table = _strings.get(_current_lang) or _strings[DEFAULT_LANGUAGE]
    raw = table.get(key)
    if raw is None:
        # Fallback al ingles si el idioma actual no tiene la clave
        raw = _strings[DEFAULT_LANGUAGE].get(key)
    if raw is None:
        return f"[[{key}]]"
    try:
        return raw.format(**kwargs) if kwargs else raw
    except (KeyError, IndexError):
        return raw


# --------------------------------------------------------------- tablas --
_strings: Dict[str, Dict[str, str]] = {
    "en": {
        # Window / header
        "app_title": "Iphone-Cast — Mirror your iPhone screen",
        "header_title": "AirPlay 2 Receiver (Mirroring)",
        "label_service_name": "Visible name on iPhone:  {name}",
        "label_uxplay": "UxPlay: {path}",
        "label_uxplay_missing": "[!] uxplay.exe NOT found (see README)",
        # Main buttons + status
        "btn_start": "[Play]  Start receiver",
        "btn_stop": "[Stop]  Stop",
        "btn_fullscreen": "Full screen",
        "status_stopped": "Stopped",
        "status_active": "Active",
        # Instructions
        "instructions_frame": "How to use it from the iPhone",
        "instructions_text": (
            "1. Press 'Start receiver'.\n"
            "2. iPhone and PC on the SAME Wi-Fi network (no VPN, no guest network).\n"
            "3. On the iPhone: Control Center -> Screen Mirroring -> {name}.\n"
            "4. Your iPhone screen will appear in a window on the PC."
        ),
        "log_frame": "UxPlay log",
        # Runtime log messages
        "log_launching": "[Play] Launching: {cmd}",
        "log_active": "[OK] UxPlay running. Look for it on the iPhone as '{name}'",
        "log_active_hint": "     Control Center -> Screen Mirroring -> {name}",
        "log_stopped": "[Stop] UxPlay stopped",
        "log_error_stopping": "[!] Error stopping: {err}",
        "log_callback_fail": "[!] on_stream_state callback failed: {err}",
        "log_exit_code": "[!] UxPlay exited with code {rc}",
        "log_uxplay_missing_a": "[!] uxplay.exe not found.",
        "log_uxplay_missing_b": "    Install UxPlay following the README, or",
        "log_uxplay_missing_c": "    set the full path in config.UXPLAY_PATH.",
        "err_uxplay_not_found": (
            "uxplay.exe not found.\n"
            "Install it following the README, or set the exact path in "
            "config.UXPLAY_PATH."
        ),
        # Fullscreen
        "fs_not_running": "[FS] UxPlay is not running.",
        "fs_no_window": "[FS] Could not find UxPlay's window. Try again once the iPhone is mirroring.",
        "fs_entered": "[FS] Fullscreen activated. Press Esc to exit.",
        "fs_exited": "[FS] Fullscreen deactivated.",
        "fs_overlay_btn": "X  Exit (Esc)",
        # Dialogs
        "dlg_uxplay_not_found": "UxPlay not found",
        "dlg_error": "Error",
        "dlg_start_failed": "Could not start UxPlay:\n{err}",
        # Tabs / settings
        "tab_receiver": "Receiver",
        "tab_settings": "Settings",
        "settings_lang_label": "Language:",
        "settings_lang_note": "The change will apply the next time you open the app.",
        "settings_about_title": "About",
        "settings_about_text": (
            "Iphone-Cast {version}\n"
            "AirPlay 2 receiver for Windows. Drives UxPlay under the hood.\n"
            "https://github.com/JVMart/Iphone-Cast"
        ),
    },
    "es": {
        "app_title": "Iphone-Cast — Duplicar la pantalla del iPhone",
        "header_title": "Receptor AirPlay 2 (Mirroring)",
        "label_service_name": "Nombre visible en el iPhone:  {name}",
        "label_uxplay": "UxPlay: {path}",
        "label_uxplay_missing": "[!] uxplay.exe NO encontrado (mira el README)",
        "btn_start": "[Play]  Iniciar receptor",
        "btn_stop": "[Stop]  Parar",
        "btn_fullscreen": "Pantalla completa",
        "status_stopped": "Detenido",
        "status_active": "Activo",
        "instructions_frame": "Como usarlo desde el iPhone",
        "instructions_text": (
            "1. Pulsa 'Iniciar receptor'.\n"
            "2. iPhone y PC en la MISMA red WiFi (no VPN, no red de invitados).\n"
            "3. En el iPhone: Centro de Control -> Duplicar pantalla -> {name}.\n"
            "4. La pantalla del iPhone aparecera en una ventana del PC."
        ),
        "log_frame": "Log de UxPlay",
        "log_launching": "[Play] Lanzando: {cmd}",
        "log_active": "[OK] UxPlay activo. Buscalo en el iPhone como '{name}'",
        "log_active_hint": "     Centro de Control -> Duplicar pantalla -> {name}",
        "log_stopped": "[Stop] UxPlay detenido",
        "log_error_stopping": "[!] Error al detener: {err}",
        "log_callback_fail": "[!] on_stream_state callback fallo: {err}",
        "log_exit_code": "[!] UxPlay salio con codigo {rc}",
        "log_uxplay_missing_a": "[!] No se encontro uxplay.exe.",
        "log_uxplay_missing_b": "    Instalalo siguiendo el README, o",
        "log_uxplay_missing_c": "    pon la ruta completa en config.UXPLAY_PATH.",
        "err_uxplay_not_found": (
            "No se encontro uxplay.exe.\n"
            "Instalalo siguiendo el README (seccion 'Instalar UxPlay'),\n"
            "o pon la ruta exacta en config.UXPLAY_PATH."
        ),
        "fs_not_running": "[FS] UxPlay no esta corriendo.",
        "fs_no_window": "[FS] No encontre la ventana de UxPlay. Intentalo de nuevo cuando el iPhone este duplicando.",
        "fs_entered": "[FS] Pantalla completa activada. Pulsa Esc para salir.",
        "fs_exited": "[FS] Pantalla completa desactivada.",
        "fs_overlay_btn": "X  Salir (Esc)",
        "dlg_uxplay_not_found": "UxPlay no encontrado",
        "dlg_error": "Error",
        "dlg_start_failed": "No se pudo iniciar UxPlay:\n{err}",
        "tab_receiver": "Receptor",
        "tab_settings": "Ajustes",
        "settings_lang_label": "Idioma:",
        "settings_lang_note": "El cambio se aplicara la proxima vez que abras la app.",
        "settings_about_title": "Acerca de",
        "settings_about_text": (
            "Iphone-Cast {version}\n"
            "Receptor AirPlay 2 para Windows. Por debajo controla UxPlay.\n"
            "https://github.com/JVMart/Iphone-Cast"
        ),
    },
    "fr": {
        "app_title": "Iphone-Cast — Dupliquer l'ecran de l'iPhone",
        "header_title": "Recepteur AirPlay 2 (Recopie d'ecran)",
        "label_service_name": "Nom visible sur l'iPhone :  {name}",
        "label_uxplay": "UxPlay : {path}",
        "label_uxplay_missing": "[!] uxplay.exe INTROUVABLE (voir le README)",
        "btn_start": "[Play]  Demarrer le recepteur",
        "btn_stop": "[Stop]  Arreter",
        "btn_fullscreen": "Plein ecran",
        "status_stopped": "Arrete",
        "status_active": "Actif",
        "instructions_frame": "Comment l'utiliser depuis l'iPhone",
        "instructions_text": (
            "1. Appuyez sur 'Demarrer le recepteur'.\n"
            "2. iPhone et PC sur le MEME reseau Wi-Fi (pas de VPN, pas d'invite).\n"
            "3. Sur l'iPhone : Centre de controle -> Recopie de l'ecran -> {name}.\n"
            "4. L'ecran de l'iPhone apparait dans une fenetre sur le PC."
        ),
        "log_frame": "Journal UxPlay",
        "log_launching": "[Play] Lancement : {cmd}",
        "log_active": "[OK] UxPlay actif. Cherchez-le sur l'iPhone sous '{name}'",
        "log_active_hint": "     Centre de controle -> Recopie de l'ecran -> {name}",
        "log_stopped": "[Stop] UxPlay arrete",
        "log_error_stopping": "[!] Erreur a l'arret : {err}",
        "log_callback_fail": "[!] echec du callback on_stream_state : {err}",
        "log_exit_code": "[!] UxPlay s'est arrete avec le code {rc}",
        "log_uxplay_missing_a": "[!] uxplay.exe introuvable.",
        "log_uxplay_missing_b": "    Installez UxPlay en suivant le README, ou",
        "log_uxplay_missing_c": "    indiquez le chemin complet dans config.UXPLAY_PATH.",
        "err_uxplay_not_found": (
            "uxplay.exe introuvable.\n"
            "Installez-le en suivant le README, ou indiquez le chemin "
            "exact dans config.UXPLAY_PATH."
        ),
        "fs_not_running": "[FS] UxPlay n'est pas lance.",
        "fs_no_window": "[FS] Impossible de trouver la fenetre d'UxPlay. Reessayez quand l'iPhone est en train de dupliquer.",
        "fs_entered": "[FS] Plein ecran active. Appuyez sur Esc pour quitter.",
        "fs_exited": "[FS] Plein ecran desactive.",
        "fs_overlay_btn": "X  Quitter (Esc)",
        "dlg_uxplay_not_found": "UxPlay introuvable",
        "dlg_error": "Erreur",
        "dlg_start_failed": "Impossible de demarrer UxPlay :\n{err}",
        "tab_receiver": "Recepteur",
        "tab_settings": "Parametres",
        "settings_lang_label": "Langue :",
        "settings_lang_note": "Le changement sera applique au prochain lancement de l'application.",
        "settings_about_title": "A propos",
        "settings_about_text": (
            "Iphone-Cast {version}\n"
            "Recepteur AirPlay 2 pour Windows. Pilote UxPlay en arriere-plan.\n"
            "https://github.com/JVMart/Iphone-Cast"
        ),
    },
}


# Verifica al import time que las tres tablas tienen las mismas claves.
def _self_check() -> None:
    en_keys = set(_strings["en"])
    for lang in ("es", "fr"):
        missing = en_keys - set(_strings[lang])
        extra = set(_strings[lang]) - en_keys
        if missing:
            raise RuntimeError(f"i18n[{lang}] missing keys: {sorted(missing)}")
        if extra:
            raise RuntimeError(f"i18n[{lang}] has extra keys: {sorted(extra)}")


_self_check()
