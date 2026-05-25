"""
Persistencia de ajustes editables por el usuario.

El instalador escribe el idioma elegido en el wizard a settings.json al
final de la instalacion. Despues, la GUI lee/escribe el mismo archivo.

Ruta:  %LocalAppData%\\Iphone-Cast\\settings.json

Esquema actual:
    {
        "language": "en" | "es" | "fr"
    }

El esquema puede crecer (en versiones futuras) sin romper compatibilidad
gracias a .get() con default en los lectores.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict


APP_NAME = "Iphone-Cast"


def settings_dir() -> Path:
    base = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
    return Path(base) / APP_NAME


def settings_path() -> Path:
    return settings_dir() / "settings.json"


def load() -> Dict[str, Any]:
    """Lee settings.json. Devuelve {} si no existe o esta corrupto."""
    path = settings_path()
    if not path.is_file():
        return {}
    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            return {}
        return data
    except (OSError, json.JSONDecodeError):
        return {}


def save(data: Dict[str, Any]) -> None:
    """Guarda settings.json (atomico: escribe a .tmp y renombra)."""
    d = settings_dir()
    d.mkdir(parents=True, exist_ok=True)
    final = settings_path()
    tmp = final.with_suffix(".json.tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, final)


def get_language(default: str = "en") -> str:
    data = load()
    lang = data.get("language", default)
    if lang in ("en", "es", "fr"):
        return lang
    return default


def set_language(code: str) -> None:
    data = load()
    data["language"] = code
    save(data)
