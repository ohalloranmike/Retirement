"""Ensure entry points run with the project .venv interpreter."""

from __future__ import annotations

import sys
from pathlib import Path


def project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def venv_bin_dir() -> Path:
    root = project_root()
    if sys.platform == "win32":
        return root / ".venv" / "Scripts"
    return root / ".venv" / "bin"


def venv_python() -> Path:
    name = "python.exe" if sys.platform == "win32" else "python"
    return venv_bin_dir() / name


def require_project_venv() -> None:
    """Exit with instructions if sys.executable is not this project's .venv."""
    bin_dir = venv_bin_dir()
    if not venv_python().is_file():
        sys.stderr.write(
            "Project virtual environment not found.\n"
            f"Create it:  py -3 -m venv .venv\n"
            f"Then:        .venv\\Scripts\\python.exe -m pip install -e .\n"
        )
        raise SystemExit(1)

    running = Path(sys.executable).resolve()
    if running.parent.resolve() != bin_dir.resolve():
        sys.stderr.write(
            "This project must use the local .venv interpreter, not system Python.\n\n"
            f"Current:  {running}\n"
            f"Expected: {venv_python().resolve()}\n\n"
            "In Cursor/VS Code: Python: Select Interpreter → .venv\\Scripts\\python.exe\n"
            "Terminal:          .\\.venv\\Scripts\\Activate.ps1\n"
            f"Direct run:        {venv_python()} gui.py\n"
        )
        raise SystemExit(1)
