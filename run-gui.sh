#!/usr/bin/env bash
# Launch the desktop GUI using the project .venv only (Linux / macOS).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON="${ROOT}/.venv/bin/python"
if [[ ! -x "${PYTHON}" ]]; then
  PYTHON="${ROOT}/.venv/bin/python3"
fi

if [[ ! -x "${PYTHON}" ]]; then
  echo "Missing .venv. From the project folder, run:" >&2
  echo "  python3 -m venv .venv" >&2
  echo "  .venv/bin/python -m pip install -e ." >&2
  exit 1
fi

if [[ "$(uname -s)" == "Linux" ]] && command -v dpkg >/dev/null; then
  if ! dpkg -s python3-tk &>/dev/null; then
    echo "Note: python3-tk is not installed. The GUI needs it:" >&2
    echo "  sudo apt install python3-tk" >&2
  fi
fi

export MPLBACKEND=TkAgg
exec "${PYTHON}" "${ROOT}/gui.py"
