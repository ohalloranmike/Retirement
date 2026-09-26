# Launch Streamlit using the project .venv only.
$ErrorActionPreference = "Stop"
$Root = $PSScriptRoot
$Python = Join-Path $Root ".venv\Scripts\python.exe"
if (-not (Test-Path $Python)) {
    Write-Error "Missing .venv. Run: py -3 -m venv .venv; & $Python -m pip install -e ."
}
& $Python -m streamlit run (Join-Path $Root "streamlit_app.py")
