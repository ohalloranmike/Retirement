@echo off
REM Launch the desktop GUI using the project .venv only.
cd /d "%~dp0"

set "PYTHON=%~dp0.venv\Scripts\python.exe"
if not exist "%PYTHON%" (
    echo Missing .venv in this folder.
    echo.
    echo One-time setup:
    echo   py -3 -m venv .venv
    echo   .venv\Scripts\python.exe -m pip install -e .
    echo.
    pause
    exit /b 1
)

"%PYTHON%" "%~dp0gui.py"
if errorlevel 1 pause
