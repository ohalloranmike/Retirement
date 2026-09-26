"""Re-exec entry scripts with .venv/bin/python when launched via system Python."""

from __future__ import annotations

import os
import sys
from pathlib import Path

_ENV_FLAG = "RETIREMENT_VENV_BOOTSTRAP"


def _project_root(entry: str | Path) -> Path:
    return Path(entry).resolve().parent


def _venv_python(bin_dir: Path) -> Path | None:
    for name in ("python", "python3"):
        candidate = bin_dir / name
        if candidate.is_file():
            return candidate.resolve()
    return None


def _in_project_venv(executable: Path, bin_dir: Path) -> bool:
    try:
        if executable.resolve().parent != bin_dir.resolve():
            return False
    except OSError:
        return False
    name = executable.name.lower()
    if sys.platform == "win32":
        return name == "python.exe" or name.startswith("python3")
    return name == "python" or name.startswith("python3")


def relaunch_with_project_venv(entry: str | Path, *, streamlit: bool = False) -> None:
    """
    If sys.executable is not the project .venv, replace this process with the venv interpreter.

    Must run before other project imports. No-op when already on .venv or .venv is missing.
    """
    if os.environ.get(_ENV_FLAG) == "1":
        return

    root = _project_root(entry)
    bin_dir = root / ".venv" / ("Scripts" if sys.platform == "win32" else "bin")
    venv_py = _venv_python(bin_dir)
    if venv_py is None:
        return

    running = Path(sys.executable)
    try:
        if _in_project_venv(running, bin_dir):
            return
    except OSError:
        pass

    os.environ[_ENV_FLAG] = "1"
    script = Path(entry).resolve()

    if streamlit:
        argv = [str(venv_py), "-m", "streamlit", "run", str(script)]
    else:
        argv = [str(venv_py), str(script)] + sys.argv[1:]

    os.execv(str(venv_py), argv)
