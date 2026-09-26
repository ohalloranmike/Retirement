#!/usr/bin/env bash
# Launch Streamlit using the project .venv only (Linux / macOS).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON="${ROOT}/.venv/bin/python"

if [[ ! -x "${PYTHON}" ]]; then
  echo "Missing .venv. From the project folder, run:" >&2
  echo "  python3 -m venv .venv" >&2
  echo "  .venv/bin/python -m pip install -e ." >&2
  exit 1
fi

export MPLBACKEND=Agg
exec "${PYTHON}" -m streamlit run "${ROOT}/streamlit_app.py"
