# Retirement Planner (v1)

Deterministic year-by-year model for **401(k), traditional/Roth IRA, taxable accounts, pension, and Social Security**, with **RMDs** (SECURE 2.0 ages), inflation-adjusted spending, and configurable withdrawal order.

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

**PyCharm:** Settings → Project → Python Interpreter → select `.venv\Scripts\python.exe`, then use *Install requirements* on `requirements.txt` or run `pip install -e .` in the terminal with the venv active.

## Desktop GUI (recommended — standalone)

Self-contained Windows/Mac/Linux app (Tkinter, no browser). Enter all options, run the projection, then export Excel, CSV, HTML, charts, or **everything at once**:

```powershell
.\.venv\Scripts\Activate.ps1
pip install -e .
python gui.py
```

**File** menu: Export Excel, CSV, HTML, chart PNGs, export all to a folder, or open HTML in the browser for **Print / Save as PDF**. **View** menu: switch **dark** or **light** theme (Sun Valley modern ttk styling).

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

## Inputs (high level)

| Area | Fields |
|------|--------|
| Timeline | birth year, retirement age, life expectancy, planning start year |
| Balances | 401(k), traditional IRA, Roth IRA, taxable |
| Savings | salary, 401(k) deferral, employer match, IRA (traditional or Roth) |
| Returns | pre- and post-retirement annual return (fixed) |
| Pension | monthly benefit, start age, optional COLA |
| Social Security | monthly at FRA, claim age (62–70), COLA; optional spouse SS |
| Spending | annual goal in today’s dollars, inflation rate |
| Withdrawals | `taxable_traditional_roth`, `traditional_taxable_roth`, or `proportional` |

## What v1 does not include

Federal tax on withdrawals, Roth conversions, Monte Carlo, state tax, IRMAA, or full two-earner SS rules. These can be added in later layers.

## Project layout

- `retirement/projection.py` — year loop, withdrawals, RMD floor
- `retirement/rmd.py` — SECURE 2.0 start age and uniform lifetime table
- `retirement/social_security.py` — early/late claiming adjustments + COLA
- `retirement/excel_export.py` — workbook create/refresh
- `gui.py` — standalone desktop GUI (main interactive program)
- `streamlit_app.py` — optional browser UI
- `retirement/report.py` — summary metrics and HTML report
- `main.py` — CLI
