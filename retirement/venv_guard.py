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


def venv_problem_message() -> str | None:
    """Return a user-facing error if the active interpreter is not this project's .venv."""
    bin_dir = venv_bin_dir()
    py = venv_python()
    if not py.is_file() and sys.platform != "win32":
        py3 = bin_dir / "python3"
        if py3.is_file():
            py = py3
    if not py.is_file():
        if sys.platform == "win32":
            return (
                "Project virtual environment not found.\n"
                "Create it:  py -3 -m venv .venv\n"
                "Then:        .venv\\Scripts\\python.exe -m pip install -e ."
            )
        return (
            "Project virtual environment not found.\n"
            "Create it:  python3 -m venv .venv\n"
            "Then:        .venv/bin/python -m pip install -e ."
        )

    running = Path(sys.executable)
    if not _in_project_venv(running, bin_dir.resolve()):
        lines = [
            "This project must use the local .venv interpreter, not system Python.",
            "",
            f"Current:  {running.resolve()}",
            f"Expected: a python under {bin_dir.resolve()}",
            "",
        ]
        if sys.platform == "win32":
            lines.append("Use:  .\\run-gui.ps1   or   .\\run-streamlit.ps1")
        else:
            lines.extend(
                [
                    "Use:  ./run-gui.sh   or   ./run-streamlit.sh",
                    "Or:   .venv/bin/python -m streamlit run streamlit_app.py",
                    "",
                    "If you used system `streamlit` or PyCharm with /usr/bin/python,",
                    "pull the latest code (auto-relaunch) or switch the IDE interpreter to .venv/bin/python3.",
                ]
            )
        return "\n".join(lines)
    return None


def require_project_venv() -> None:
    """Exit with instructions if sys.executable is not this project's .venv."""
    msg = venv_problem_message()
    if msg:
        sys.stderr.write(msg + "\n")
        raise SystemExit(1)
