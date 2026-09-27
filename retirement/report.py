from __future__ import annotations

import base64
import html
from datetime import datetime, timezone
from typing import Any

import pandas as pd

from retirement.charts import balance_chart_figure, figure_to_png_bytes, income_chart_figure
from retirement.models import RetirementInputs


def summarize_projection(df: pd.DataFrame, inputs: RetirementInputs) -> dict[str, Any]:
    last = df.iloc[-1]
    ret = df[df["phase"] == "retirement"]
    broke = ret[ret["surplus_or_shortfall"] < -1]
    first_shortfall = None
    if len(broke):
        row = broke.iloc[0]
        first_shortfall = {"year": int(row["year"]), "age": int(row["age"])}

    at_retirement = df[df["age"] == inputs.retirement_age]
    balance_at_retirement = float(at_retirement["balance_total"].iloc[0]) if len(at_retirement) else None

    return {
        "plan_start_year": int(df["year"].iloc[0]),
        "plan_end_year": int(df["year"].iloc[-1]),
        "start_age": int(df["age"].iloc[0]),
        "end_age": int(last["age"]),
        "ending_balance": float(last["balance_total"]),
        "balance_at_retirement": balance_at_retirement,
        "cumulative_shortfall": float(last["cumulative_shortfall"]),
        "first_shortfall": first_shortfall,
        "retirement_years": int(len(ret)),
    }


DISPLAY_COLUMNS: list[tuple[str, str]] = [
    ("year", "Year"),
    ("age", "Age"),
    ("phase", "Phase"),
    ("balance_total", "Total balance"),
    ("income_total", "Total income"),
    ("spending_need", "Spending need"),
    ("surplus_or_shortfall", "Surplus / shortfall"),
    ("pension_income", "Pension"),
    ("ss_income", "Your SS"),
    ("spouse_ss_income", "Spouse SS"),
    ("withdrawal_total", "Portfolio withdrawals"),
    ("rmd_amount", "RMD"),
    ("balance_401k", "401(k) balance"),
    ("balance_traditional_ira", "Trad. IRA"),
    ("balance_roth_ira", "Roth IRA"),
    ("balance_taxable", "Taxable"),
]


YEARLY_FIXED_LABELS: tuple[str, ...] = ("Year", "Age")


def report_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    cols = [c for c, _ in DISPLAY_COLUMNS if c in df.columns]
    out = df[cols].copy()
    out.columns = [label for c, label in DISPLAY_COLUMNS if c in df.columns]
    return out


def yearly_scroll_column_names(table: pd.DataFrame) -> list[str]:
    return [c for c in table.columns if c not in YEARLY_FIXED_LABELS]


def format_yearly_table_parts(
    df: pd.DataFrame,
    scroll_columns: list[str] | None = None,
) -> tuple[str, str]:
    """Fixed Year/Age text plus scrollable columns (desktop year-by-year table)."""
    table = report_dataframe(df)
    money_cols = {c for c in table.columns if c not in YEARLY_FIXED_LABELS and c != "Phase"}
    fixed_lines = [f"{'Year':>6}  {'Age':>4}"]
    for _, row in table.iterrows():
        year = row["Year"] if "Year" in row else ""
        age = row["Age"] if "Age" in row else ""
        fixed_lines.append(f"{year!s:>6}  {age!s:>4}")
    available = yearly_scroll_column_names(table)
    if scroll_columns is None:
        chosen = available
    else:
        chosen = [c for c in scroll_columns if c in available]
    scroll = table[chosen].copy() if chosen else table[[]].copy()
    for col in scroll.columns:
        if col in money_cols:
            scroll[col] = scroll[col].map(lambda v: f"${float(v):,.0f}" if pd.notna(v) else "")
    scroll_text = scroll.to_string(index=False, col_space=12) if len(scroll.columns) else ""
    return "\n".join(fixed_lines), scroll_text


def _fmt_money(v: float) -> str:
    if pd.isna(v):
        return ""
    return f"${v:,.0f}"


def build_html_report(df: pd.DataFrame, inputs: RetirementInputs) -> str:
    summary = summarize_projection(df, inputs)
    report_df = report_dataframe(df)
    generated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    images: list[tuple[str, str]] = []
    for title, maker in (
        ("Income by source", income_chart_figure),
        ("Portfolio balance", balance_chart_figure),
    ):
        fig = maker(df)
        if fig:
            b64 = base64.b64encode(figure_to_png_bytes(fig)).decode("ascii")
            images.append((title, b64))

    shortfall_line = "No spending shortfalls in retirement years."
    if summary["first_shortfall"]:
        fs = summary["first_shortfall"]
        shortfall_line = f"First shortfall: {fs['year']} (age {fs['age']})."

    bal_ret = summary["balance_at_retirement"]
    bal_ret_s = _fmt_money(bal_ret) if bal_ret is not None else "n/a"

    table_rows = []
    for _, row in report_df.iterrows():
        cells = []
        for col in report_df.columns:
            val = row[col]
            if col in ("Year", "Age", "Phase"):
                cells.append(html.escape(str(val)))
            else:
                cells.append(html.escape(_fmt_money(float(val)) if val != "" else ""))
        table_rows.append("<tr>" + "".join(f"<td>{c}</td>" for c in cells) + "</tr>")

    header = "".join(f"<th>{html.escape(c)}</th>" for c in report_df.columns)
    img_blocks = "".join(
        f'<h2>{html.escape(title)}</h2><img alt="{html.escape(title)}" src="data:image/png;base64,{b64}" />'
        for title, b64 in images
    )

    assumptions = f"""
    <ul>
      <li>Birth year {inputs.birth_year}; retire at {inputs.retirement_age}; plan through age {inputs.life_expectancy_age}</li>
      <li>Spending goal (today): {_fmt_money(inputs.annual_spending_goal_today)}/yr; inflation {inputs.inflation_pct:.1%}</li>
      <li>Returns: {inputs.annual_return_pre_retirement:.1%} pre-retirement, {inputs.annual_return_post_retirement:.1%} in retirement</li>
      <li>Withdrawal order: {html.escape(inputs.withdrawal_order.value)}</li>
    </ul>
    """

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <title>Retirement projection report</title>
  <style>
    body {{ font-family: Georgia, "Times New Roman", serif; margin: 1.5rem 2rem; color: #111; }}
    h1 {{ font-size: 1.5rem; border-bottom: 2px solid #1f4e79; padding-bottom: 0.25rem; }}
    h2 {{ font-size: 1.15rem; margin-top: 1.5rem; color: #1f4e79; }}
    .meta {{ color: #444; font-size: 0.9rem; }}
    .summary dl {{ display: grid; grid-template-columns: 14rem 1fr; gap: 0.35rem 1rem; }}
    .summary dt {{ font-weight: bold; }}
    table {{ border-collapse: collapse; width: 100%; font-size: 0.75rem; margin-top: 0.5rem; }}
    th, td {{ border: 1px solid #ccc; padding: 0.35rem 0.5rem; text-align: right; }}
    th {{ background: #1f4e79; color: #fff; }}
    td:first-child, th:first-child {{ text-align: left; }}
    img {{ max-width: 100%; height: auto; page-break-inside: avoid; }}
    .disclaimer {{ margin-top: 2rem; font-size: 0.85rem; color: #555; }}
    @media print {{
      body {{ margin: 0.5in; }}
      a {{ display: none; }}
    }}
  </style>
</head>
<body>
  <h1>Retirement cash-flow projection</h1>
  <p class="meta">Generated {html.escape(generated)}. Educational model only — not investment or tax advice.</p>

  <h2>Summary</h2>
  <div class="summary">
    <dl>
      <dt>Plan horizon</dt><dd>{summary['plan_start_year']} – {summary['plan_end_year']} (ages {summary['start_age']} – {summary['end_age']})</dd>
      <dt>Balance at retirement</dt><dd>{bal_ret_s}</dd>
      <dt>Ending total balance</dt><dd>{_fmt_money(summary['ending_balance'])}</dd>
      <dt>Cumulative shortfall</dt><dd>{_fmt_money(summary['cumulative_shortfall'])}</dd>
      <dt>Shortfall timing</dt><dd>{html.escape(shortfall_line)}</dd>
    </dl>
  </div>

  <h2>Assumptions</h2>
  {assumptions}

  {img_blocks}

  <h2>Year-by-year detail</h2>
  <table>
    <thead><tr>{header}</tr></thead>
    <tbody>
      {"".join(table_rows)}
    </tbody>
  </table>

  <p class="disclaimer">Social Security, pension, RMDs, and taxes are simplified. Verify amounts with SSA.gov, your plan administrator, and a qualified professional before making decisions.</p>
</body>
</html>
"""


def workbook_bytes(inputs: RetirementInputs) -> bytes:
    import tempfile
    from pathlib import Path

    from retirement.excel_export import create_workbook

    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "report.xlsx"
        create_workbook(path, inputs)
        return path.read_bytes()


def save_excel(path: Path, inputs: RetirementInputs) -> Path:
    from retirement.excel_export import create_workbook

    path = Path(path)
    create_workbook(path, inputs)
    return path


def export_report_bundle(directory: Path, df: pd.DataFrame, inputs: RetirementInputs) -> list[Path]:
    """Write CSV, HTML, Excel, and chart PNGs into a folder."""
    from retirement.charts import save_charts

    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []

    csv_path = directory / "retirement_projection.csv"
    report_dataframe(df).to_csv(csv_path, index=False)
    written.append(csv_path)

    html_path = directory / "retirement_report.html"
    html_path.write_text(build_html_report(df, inputs), encoding="utf-8")
    written.append(html_path)

    xlsx_path = directory / "retirement_planner.xlsx"
    save_excel(xlsx_path, inputs)
    written.append(xlsx_path)

    chart_dir = directory / "charts"
    written.extend(save_charts(df, chart_dir))
    return written
