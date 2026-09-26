#!/usr/bin/env bash
# Launch Streamlit using the project .venv only (Linux / macOS).
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

if ! "${PYTHON}" -c "import streamlit" 2>/dev/null; then
  echo "Installing dependencies into .venv (first run)..." >&2
  "${PYTHON}" -m pip install -U pip
  "${PYTHON}" -m pip install -e "${ROOT}"
fi

export MPLBACKEND=Agg
# Use 127.0.0.1 explicitly (matches .streamlit/config.toml).
exec "${PYTHON}" -m streamlit run "${ROOT}/streamlit_app.py" --server.address=127.0.0.1
