"""Persist desktop GUI layout preferences."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

_PREF_KEY_SIDEBAR_FRACTION = "sidebar_sash_fraction"


def _prefs_path() -> Path:
    if sys.platform == "win32":
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
    else:
        base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    return base / "RetirementPlanner" / "gui_prefs.json"


def load_gui_prefs() -> dict[str, Any]:
    path = _prefs_path()
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def save_gui_prefs(prefs: dict[str, Any]) -> None:
    path = _prefs_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(prefs, indent=2) + "\n", encoding="utf-8")
    except OSError:
        pass


def get_sidebar_sash_fraction() -> float | None:
    raw = load_gui_prefs().get(_PREF_KEY_SIDEBAR_FRACTION)
    if raw is None:
        return None
    try:
        frac = float(raw)
    except (TypeError, ValueError):
        return None
    if not 0.15 <= frac <= 0.85:
        return None
    return frac


def set_sidebar_sash_fraction(fraction: float) -> None:
    frac = max(0.15, min(0.85, fraction))
    prefs = load_gui_prefs()
    prefs[_PREF_KEY_SIDEBAR_FRACTION] = round(frac, 4)
    save_gui_prefs(prefs)
