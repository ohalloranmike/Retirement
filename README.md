# Retirement Planner

Deterministic year-by-year model for **401(k), traditional/Roth IRA, taxable accounts, pension, and Social Security**, with **RMDs** (SECURE 2.0 ages), inflation-adjusted spending, and configurable withdrawal order. Optional **v2** adds tax, IRMAA, Roth conversions, mixed Roth pools, and Monte Carlo.

**Full feature list and new-user guide:** [docs/features.md](docs/features.md)

**Not investment or tax advice.** SS and pension are simplified; use SSA.gov estimates and your plan documents for real decisions.

## Setup

Use the project virtual environment (`.venv` is not committed to git).

**Windows (PowerShell):**

```powershell
cd c:\Users\mohal2\PycharmProjects\Retirement
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e .
```

`pip install -e .` reads dependencies from `pyproject.toml` and registers the `retirement` package so imports work in PyCharm and the terminal.

Alternative (requirements file only):

```powershell
python -m pip install -r requirements.txt
```

**IDE (Cursor / VS Code):** Open this folder as the workspace root so `.vscode/settings.json` applies. Choose interpreter **`.venv\Scripts\python.exe`**. Entry scripts (`gui.py`, `main.py`, `streamlit_app.py`) **exit** if you run them with system Python.

**Quick launch (always uses .venv):**

```powershell
.\run-gui.ps1
.\run-streamlit.ps1
```

Double-click **`run-gui.bat`** (Cmd) if PowerShell script policy blocks `.ps1` files.

**Linux Mint (and other Unix shells):**

```bash
chmod +x run-streamlit.sh   # once
./run-streamlit.sh
```

## Desktop GUI (recommended — standalone)

Self-contained Windows/Mac/Linux app (Tkinter, no browser). Enter all options, run the projection, then export Excel, CSV, HTML, charts, or **everything at once**:

```powershell
.\.venv\Scripts\Activate.ps1
pip install -e .
python gui.py
```

**File** menu: Export Excel, CSV, HTML, chart PNGs, export all to a folder, or open HTML in the browser for **Print / Save as PDF**. **View** menu: switch **dark** or **light** theme (CustomTkinter rounded controls; Sun Valley styling for the year-by-year table).

## Streamlit app (optional)

Browser-based UI with the same exports:

```powershell
streamlit run streamlit_app.py
```

## Quick start (CLI)

```bash
python main.py --summary
python main.py --config config\sample.json --csv output\projection.csv --charts output\charts
```

## Excel workbook

Create a workbook with an **Inputs** sheet and a **Projection** sheet (projection is computed in Python because RMD/SS/withdrawal logic is easier to maintain in code):

```bash
python main.py --init --excel retirement_planner.xlsx
```

Edit values on the **Inputs** sheet, then refresh:

```bash
python main.py --excel retirement_planner.xlsx --refresh --summary
```

Opening `retirement_planner.xlsx` after `--init` includes charts on the Projection sheet.

## Documentation

- **[docs/features.md](docs/features.md)** — complete v1/v2 features, inputs, Roth pools, exports, limitations, troubleshooting
- `config/sample.json` — basic plan
- `config/sample_v2.json` — tax, Roth pools, conversions, Monte Carlo

Quick v2 run:

```powershell
python main.py --config config\sample_v2.json --summary --monte-carlo
```

## Project layout

- `retirement/projection.py` — year loop, withdrawals, RMD floor
- `retirement/rmd.py` — SECURE 2.0 start age and uniform lifetime table
- `retirement/social_security.py` — early/late claiming adjustments + COLA
- `retirement/excel_export.py` — workbook create/refresh
- `gui.py` — standalone desktop GUI (main interactive program)
- `streamlit_app.py` — optional browser UI
- `retirement/report.py` — summary metrics and HTML report
- `main.py` — CLI
