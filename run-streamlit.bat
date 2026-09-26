@echo off
cd /d "%~dp0"
set "PYTHON=%~dp0.venv\Scripts\python.exe"
if not exist "%PYTHON%" (
    echo Missing .venv. Run: py -3 -m venv .venv
    echo Then: .venv\Scripts\python.exe -m pip install -e .
    pause
    exit /b 1
)
"%PYTHON%" -m streamlit run "%~dp0streamlit_app.py"
if errorlevel 1 pause
