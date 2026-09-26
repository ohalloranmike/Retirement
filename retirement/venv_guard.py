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


def _in_project_venv(executable: Path, bin_dir: Path) -> bool:
    running = executable.resolve()
    if running.parent.resolve() != bin_dir.resolve():
        return False
    name = running.name.lower()
    if sys.platform == "win32":
        return name == "python.exe" or name.startswith("python3")
    return name == "python" or name.startswith("python3")


def require_project_venv() -> None:
    """Exit with instructions if sys.executable is not this project's .venv."""
    bin_dir = venv_bin_dir()
    py = venv_python()
    if not py.is_file() and sys.platform != "win32":
        py3 = bin_dir / "python3"
        if py3.is_file():
            py = py3
    if not py.is_file():
        if sys.platform == "win32":
            sys.stderr.write(
                "Project virtual environment not found.\n"
                "Create it:  py -3 -m venv .venv\n"
                "Then:        .venv\\Scripts\\python.exe -m pip install -e .\n"
            )
        else:
            sys.stderr.write(
                "Project virtual environment not found.\n"
                "Create it:  python3 -m venv .venv\n"
                "Then:        .venv/bin/python -m pip install -e .\n"
            )
        raise SystemExit(1)

    running = Path(sys.executable)
    if not _in_project_venv(running, bin_dir.resolve()):
        sys.stderr.write(
            "This project must use the local .venv interpreter, not system Python.\n\n"
            f"Current:  {running.resolve()}\n"
            f"Expected: a python under {bin_dir.resolve()}\n\n"
        )
        if sys.platform == "win32":
            sys.stderr.write(
                "In Cursor/VS Code: Python: Select Interpreter → .venv\\Scripts\\python.exe\n"
                "Terminal:          .\\.venv\\Scripts\\Activate.ps1\n"
            )
        else:
            sys.stderr.write("Terminal:  ./run-streamlit.sh   or   .venv/bin/python -m streamlit run streamlit_app.py\n")
        raise SystemExit(1)
