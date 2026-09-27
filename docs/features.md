# Retirement Planner — features and user guide

Single reference for **what this tool does**, **v1 and v2 behavior**, and **how to run it**. For install commands only, see [README.md](../README.md).

**Disclaimer:** Educational cash-flow modeling only. Not investment, tax, or legal advice. Confirm Social Security estimates with [SSA.gov](https://www.ssa.gov), pension amounts with your plan, and tax rules with a qualified professional.

---

## 1. What this tool is

A **year-by-year retirement projection** that estimates:

- Account balances (401(k)/403(b), traditional IRA, Roth IRA, taxable investments)
- Contributions and growth before retirement
- Retirement income from pension, Social Security, and portfolio withdrawals
- Required minimum distributions (RMDs) from traditional balances
- Whether spending goals are met (surplus or shortfall)

**v1** focuses on deterministic math with fixed returns. **v2** (optional) adds federal/state tax, IRMAA-style Medicare surcharges, Roth conversion income, split Roth pools for employer match, after-tax spending targets, and Monte Carlo trials.

---

## 2. New user: start here

### Step 1 — Install (once per machine)

Use **only** the project virtual environment (`.venv`), not system Python.

```powershell
cd c:\Users\mohal2\PycharmProjects\Retirement
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e .
```

In Cursor/VS Code: **Python: Select Interpreter** → `Retirement\.venv\Scripts\python.exe`.

### Step 2 — Pick how you want to work

| If you want… | Use… |
|--------------|------|
| Desktop forms, charts, export menus | `run-gui.bat`, `.\run-gui.ps1`, or `python gui.py` |
| Browser UI with sliders | `streamlit run streamlit_app.py` or `.\run-streamlit.ps1` |
| Scripts, automation, CSV | `python main.py` (CLI) |
| Spreadsheet inputs you already use | Excel `retirement_planner.xlsx` + `main.py --refresh` |

### Step 3 — Run a first projection

**Simple (v1 defaults):**

```powershell
python main.py --summary
```

**Full v2 example (tax + Roth pools + Monte Carlo):**

```powershell
python main.py --config config\sample_v2.json --summary --monte-carlo
```

**GUI:** Open `gui.py` → edit **Your plan** on the left (results update automatically) → **File** or **Save & print** tab to export reports.

### Step 4 — Save your assumptions

- Copy `config/sample.json` or `config/sample_v2.json` and edit values.
- Or export from the GUI (Excel / CSV / HTML / all files in a folder).

---

## 3. Interfaces in detail

### 3.1 Desktop GUI (`gui.py`)

CustomTkinter desktop app (Windows: `run-gui.bat` / `run-gui.ps1`; requires project `.venv`).

**Layout (aligned with Streamlit):**

- **Left — Your plan:** scrollable inputs for timeline, balances, savings, returns, pension, Social Security, spending, withdrawal order (radio buttons), and **Advanced (v2)** (tax toggle, filing status, state, Roth pools, conversions, Monte Carlo trial count). Long labels **wrap** as you widen the pane (similar to Streamlit’s sidebar).
- **Right — tabs:** **Summary** (metrics and first retirement year), **Year-by-year**, **Charts**, **Save & print** (download buttons and print/PDF via browser).
- **Splitter:** drag the vertical bar to resize the left panel; width is saved in `%APPDATA%\RetirementPlanner\gui_prefs.json` (Windows) or `~/.config/RetirementPlanner/gui_prefs.json` (Linux/macOS) and restored on the next launch (including when you exit with the window **X** or **File → Exit**).

**Year-by-year (desktop):**

- **Year** and **Age** stay fixed on the left; other columns scroll horizontally.
- **Column list** above the table: multi-select listbox (**Ctrl**/**Shift** click), **All** / **None** buttons. Defaults to **all** report columns selected. Same column set as Streamlit (from `report_dataframe` / `DISPLAY_COLUMNS`).

**Input parity:** `collect_inputs()` in `gui.py` and the Streamlit sidebar both call `retirement/ui_inputs.build_retirement_inputs()` with the same fields.

**Behavior:**

- Results **recalculate automatically** after you change inputs (short debounce). **Run → Refresh now** forces an immediate update; **Run → Run projection** shows the Monte Carlo notice when trials are enabled.
- **File menu:** load sample values, Excel / CSV / HTML / chart PNGs, export all to a folder, open HTML in browser for print/PDF, exit.
- **View menu:** dark / light theme (Sun Valley + CustomTkinter styling).
- Exports need a successful projection (invalid inputs show an error above the results tabs).

### 3.2 CLI (`main.py`)

| Flag | Purpose |
|------|---------|
| `--summary` | Print plan horizon, ending balance, shortfalls |
| `--config path.json` | Load all inputs from JSON |
| `--csv path` | Write projection table |
| `--charts folder` | Write income and balance PNG charts |
| `--monte-carlo` | Run Monte Carlo after deterministic plan |
| `--init --excel file.xlsx` | Create Excel workbook with sample inputs |
| `--excel file.xlsx --refresh` | Recompute **Projection** sheet from **Inputs** |

### 3.3 Streamlit (`streamlit_app.py`)

Same **Your plan** fields as the desktop GUI (including **Advanced (v2)**), built via `retirement/ui_inputs.py`. Tabs: **Summary** (on-demand Monte Carlo when trials &gt; 0), **Year-by-year**, **Charts**, **Save & print**. Same `run_projection` and report exports as CLI/GUI.

**Year-by-year (browser):**

- **Year** and **Age** pinned on the left while you scroll horizontally (HTML table; no spurious row index).
- **Columns** multiselect lists every scrollable report column; **all are selected by default**. Year/Age are always shown and are not in the multiselect list.

**Sidebar:** expanders match the desktop sections; the sidebar width follows the browser like Streamlit’s built-in layout.

### 3.4 Excel workbook

- **Inputs** sheet: edit assumptions (labels in column B, values in column C).
- **Projection** sheet: written by Python (not Excel formulas) so RMD, SS, and v2 tax logic stay correct.
- Refresh: `python main.py --excel retirement_planner.xlsx --refresh`

Excel does **not** include every v2 field yet; for full v2 use JSON, GUI **Advanced (v2)**, or extend the workbook later.

---

## 4. Core concepts (all versions)

### Timeline

- **Planning start year** through **life expectancy age** (from birth year).
- **Retirement age** switches from accumulation (contributions) to retirement (withdrawals + fixed income).

### Accounts

| Account | Modeled as |
|---------|------------|
| 401(k) / 403(b) | `balance_401k` — traditional unless v2 routes deferrals/match to Roth pools |
| Traditional IRA | `balance_traditional_ira` |
| Roth IRA / Roth 401(k) total | `balance_roth_ira` (v2 may split into post-tax and pre-tax pools) |
| Taxable brokerage | `balance_taxable` |

### Pre-retirement

- Employee 401(k) deferral and employer match (match rate × matchable deferral, capped by % of salary).
- IRA contribution to traditional or Roth (`ira_is_roth`).
- Fixed annual return (`annual_return_pre_retirement`).

### Retirement

- **Spending goal** in today’s dollars, inflated each year (`inflation_pct`).
- **Pension** (optional): monthly at start, start age, optional COLA.
- **Social Security:** benefit at full retirement age, claim age 62–70 with simplified early/late adjustments, COLA; optional second **spouse SS** benefit.
- **Withdrawals** from portfolio to fill gap after pension + SS (order configurable).
- **RMDs** on combined traditional 401(k) + traditional IRA (SECURE 2.0 start age 73 or 75 by birth year).
- Fixed post-retirement return (`annual_return_post_retirement`).

### Withdrawal order

| Value | Behavior |
|-------|----------|
| `taxable_traditional_roth` | Taxable → 401(k) + traditional IRA → Roth |
| `traditional_taxable_roth` | Traditional → taxable → Roth |
| `proportional` | Withdraw from all accounts in proportion to balances |

RMDs are enforced as a minimum from traditional accounts when applicable.

### Outputs (deterministic table)

Common columns include year, age, phase, balances, contributions, growth, withdrawals, pension, SS, spending need, surplus/shortfall, cumulative shortfall. v2 adds tax and Roth pool columns (see §7).

### Success / shortfall

- **v1:** Compares **gross** cash inflow (including full withdrawals) to spending.
- **v2:** Spending goal is **after-tax**; compares `after_tax_income` to spending after estimated taxes and IRMAA.

---

## 5. v1 feature list

| Feature | Description |
|---------|-------------|
| Multi-account balances | 401(k), trad IRA, Roth IRA, taxable |
| Salary and savings | Deferrals, employer match, IRA |
| Fixed returns | Separate pre- and post-retirement rates |
| Pension | Inflation-adjusted optional COLA on benefit |
| Social Security | Claim age, COLA, spouse SS (simplified) |
| RMDs | Uniform lifetime table; SECURE 2.0 start age |
| Withdrawal strategies | Three ordering modes |
| Inflation | On spending goal (and pension display via plan logic) |
| Reports | Summary, CSV, Excel, HTML, charts |
| Three UIs | GUI, Streamlit, CLI + Excel refresh |

**v1 does not** model income tax, IRMAA, Roth conversions, or return uncertainty unless v2 is enabled.

---

## 6. v2 feature list (optional)

Enable with `use_tax_modeling: true` (JSON or GUI **Advanced (v2)**).

| Feature | Description |
|---------|-------------|
| Federal income tax | Ordinary brackets, standard deduction (`single` / `mfj`) |
| Taxable Social Security | Provisional income tiers (simplified) |
| Capital gains | On taxable account withdrawals using `taxable_cost_basis_ratio` |
| State tax | Flat rate by `state_code` or `custom` + `state_custom_tax_rate` |
| IRMAA | Extra Medicare Part B-style annual cost from MAGI at `medicare_start_age` |
| After-tax spending | Grosses up withdrawals iteratively to meet after-tax need |
| Roth conversions | Annual amount from `roth_conversion_start_age`–`end_age` from traditional IRA |
| Roth pools | Post-tax vs pre-tax employer money inside Roth (see §8) |
| Monte Carlo | `run_monte_carlo_trials` or CLI `--monte-carlo` |

### v2 tax inputs

| Field | Default | Notes |
|-------|---------|-------|
| `filing_status` | `single` | `single` or `mfj` |
| `state_code` | `OR` | e.g. `none`, `CA`, `custom` |
| `state_custom_tax_rate` | `0.05` | Used when `state_code` is `custom` |
| `taxable_cost_basis_ratio` | `0.60` | Share of taxable withdrawals treated as basis (not LTCG) |
| `medicare_start_age` | `65` | Age when IRMAA logic applies |

### v2 Roth conversion inputs

| Field | Notes |
|-------|-------|
| `roth_conversion_annual` | Dollars converted traditional → Roth per year |
| `roth_conversion_start_age` | `0` = off |
| `roth_conversion_end_age` | Last age conversions run |

Conversion adds **ordinary income** in that year and moves balance into the Roth post-tax pool.

### v2 Monte Carlo

| Field | Notes |
|-------|-------|
| `run_monte_carlo_trials` | e.g. `500`; `0` = skip |
| `monte_carlo_return_std` | Standard deviation of post-retirement return per trial |

Each trial draws one post-retirement return (normal, clipped); success ≈ no cumulative shortfall in that trial’s deterministic path. GUI runs Monte Carlo when trial count > 0 (use **Run → Run projection** for the notice, or wait for auto-refresh).

### v2 extra output columns

`federal_tax`, `state_tax`, `irmaa_surcharge`, `total_tax`, `after_tax_income`, `roth_conversion`, `roth_withdrawal_qualified`, `roth_withdrawal_taxable`, `roth_posttax_balance`, `roth_pretax_balance`.

---

## 7. Roth scenario: post-tax balance + pre-tax employer match

Use when Roth **already had post-tax contributions** and **employer match (or similar) later went into the same Roth bucket** as **pre-tax** dollars for distribution purposes.

### Problem

Treating the full Roth balance as tax-free on withdrawal overstates after-tax cash when part of the balance is employer pre-tax money.

### Two pools (one reported total)

| Pool | Source | v2 withdrawal tax |
|------|--------|-------------------|
| **Post-tax** | `roth_posttax_opening_balance`, employee Roth deferrals, Roth IRA contributions, conversion principal to Roth | Qualified slice (no ordinary tax in model) |
| **Pre-tax** | Remaining opening Roth + employer match when `employer_match_to_roth` | Ordinary income on that slice |

`balance_roth_ira` in output = post-tax pool + pre-tax pool.

### Controls

| Field | Purpose |
|-------|---------|
| `use_tax_modeling` | Required for pools and tax on pre-tax slice |
| `balance_roth_ira` | Total Roth at plan start |
| `roth_posttax_opening_balance` | Portion that was always post-tax |
| `employee_401k_to_roth` | Employee deferrals → post-tax pool |
| `employer_match_to_roth` | Match → pre-tax pool (not traditional 401(k)) |

**Opening:** pre-tax pool = `balance_roth_ira − roth_posttax_opening_balance` (≥ 0).

**Withdrawals:** Pro-rata from both pools; taxes computed on pre-tax slice only.

### Example

See `config/sample_v2.json`: $80k Roth, $55k post-tax opening, match and deferrals to Roth pools, Oregon tax, conversions, 500 Monte Carlo trials.

### Not modeled

Plan document / 1099-R detail; Roth five-year and 59½ rules in full; match that actually goes to **traditional** 401(k) should use `employer_match_to_roth: false`.

Code: `retirement/roth_pools.py`, integrated in `retirement/projection.py`.

---

## 8. Complete input reference

### Required / core

| Field | Type | Description |
|-------|------|-------------|
| `birth_year` | int | Year born |
| `retirement_age` | int | First year treated as retired |
| `life_expectancy_age` | int | Plan end age |
| `planning_start_year` | int | First projection year |

### Balances ($)

| Field | Description |
|-------|-------------|
| `balance_401k` | Traditional 401(k)/403(b) |
| `balance_traditional_ira` | Traditional IRA |
| `balance_roth_ira` | Roth (total; v2 may split internally) |
| `balance_taxable` | Taxable investments |

### Savings

| Field | Description |
|-------|-------------|
| `annual_salary` | For match calculation |
| `employee_401k_contribution` | Annual employee deferral |
| `employer_match_rate` | e.g. `0.5` = 50% match |
| `employer_match_up_to_pct_of_salary` | e.g. `0.06` = match on first 6% of salary |
| `annual_ira_contribution` | IRA annual contribution |
| `ira_is_roth` | `true` → Roth IRA side |

### Returns

| Field | Description |
|-------|-------------|
| `annual_return_pre_retirement` | Decimal, e.g. `0.07` |
| `annual_return_post_retirement` | Decimal, e.g. `0.05` |

### Pension

| Field | Description |
|-------|-------------|
| `pension_monthly_at_start` | Monthly benefit when pension starts |
| `pension_start_age` | Age pension begins |
| `pension_cola_pct` | Annual COLA on pension |
| `pension_survivor_pct` | Labeling only in v1 (`1.0` = full) |

### Social Security

| Field | Description |
|-------|-------------|
| `ss_monthly_at_fra` | Monthly at full retirement age |
| `ss_fra_age` | Full retirement age for baseline |
| `ss_claim_age` | 62–70 |
| `ss_cola_pct` | Annual COLA |
| `spouse_ss_monthly_at_fra` | Optional second benefit |
| `spouse_ss_claim_age` | Spouse claim age |

### Spending & withdrawals

| Field | Description |
|-------|-------------|
| `annual_spending_goal_today` | Annual spending in today’s dollars |
| `inflation_pct` | Annual inflation on spending |
| `withdrawal_order` | See §4 |

### v2-only (see §6–§7)

`use_tax_modeling`, `filing_status`, `state_code`, `state_custom_tax_rate`, `taxable_cost_basis_ratio`, `medicare_start_age`, `roth_posttax_opening_balance`, `employer_match_to_roth`, `employee_401k_to_roth`, `roth_conversion_*`, `monte_carlo_return_std`, `run_monte_carlo_trials`.

---

## 9. Exports and reports

| Export | Contents |
|--------|----------|
| **CSV** | Year-by-year table (friendly column names in HTML/CSV report path) |
| **Excel** | Inputs sheet + Projection (+ charts on sheet when generated via tool) |
| **HTML** | Summary, assumptions, embedded charts, full table — good for print/PDF |
| **PNG charts** | Income-by-source vs spending; total balance over time |
| **Export all** (GUI) | CSV + HTML + Excel + charts in one folder |

---

## 10. Sample configuration files

| File | Use |
|------|-----|
| `config/sample.json` | v1-style plan, tax off |
| `config/sample_v2.json` | v2 tax, Roth pools, conversions, Monte Carlo |

Load: `python main.py --config config\sample.json --summary`

---

## 11. Limitations (read before relying on results)

- Simplified SS, pension, and tax law; bracket tables need periodic updates (`retirement/tax/`).
- No NIIT, AMT, detailed state schedules, ACA subsidies, or variable “go-go / slow-go” spending.
- Monte Carlo is a simplified return draw, not full correlated asset-class simulation.
- Not a substitute for MoneyGuide, eMoney, or CPA-prepared tax projections.
- Excel input sheet does not expose all v2 fields.

---

## 12. Troubleshooting

| Issue | Fix |
|-------|-----|
| `ModuleNotFoundError` | Use `.venv\Scripts\python.exe`; run `pip install -e .` |
| “Must use local .venv” | Select `.venv` interpreter or use `run-gui.bat` / `run-gui.ps1` |
| GUI won’t export | Fix input errors so auto-refresh succeeds, or use **Run → Refresh now** |
| Results differ Excel vs JSON | Excel may lack v2 fields; align inputs or use JSON/GUI |

---

## 13. Code map

| Module | Role |
|--------|------|
| `retirement/projection.py` | Year-by-year engine |
| `retirement/models.py` | `RetirementInputs` |
| `retirement/rmd.py` | RMD ages and divisors |
| `retirement/social_security.py` | SS claiming adjustments |
| `retirement/roth_pools.py` | Roth post-tax / pre-tax pools |
| `retirement/tax/` | Federal, state, SS tax, IRMAA |
| `retirement/monte_carlo.py` | Trial success rate |
| `retirement/report.py` | `report_dataframe`, HTML/CSV export, `format_yearly_table_parts`, column labels |
| `retirement/excel_export.py` | Workbook create/refresh |
| `gui.py` / `streamlit_app.py` / `main.py` | Entry points |
| `retirement/gui_theme.py` | Desktop GUI fonts and ttk/Sun Valley theme |
| `retirement/gui_prefs.py` | Persist desktop GUI layout (sidebar width) |
| `retirement/ui_inputs.py` | Shared `RetirementInputs` construction for GUI and Streamlit |
| `retirement/venv_guard.py` | Enforce `.venv` only |

---

*Document version: covers v1 + v2 as implemented in this repository. Update this file when adding features.*
