"""Interactive retirement planner (Streamlit). Run: streamlit run streamlit_app.py"""

from __future__ import annotations

import html as html_lib

import pandas as pd

from retirement.venv_guard import require_project_venv

require_project_venv()

from retirement.charts import balance_chart_figure, income_chart_figure
from retirement.models import RetirementInputs
from retirement.projection import default_sample_inputs, run_projection
from retirement.report import (
    YEARLY_FIXED_LABELS,
    build_html_report,
    report_dataframe,
    summarize_projection,
    workbook_bytes,
    yearly_scroll_column_names,
)
from retirement.ui_inputs import WITHDRAWAL_LABELS, build_retirement_inputs

def _format_yearly_cell(column: str, value: object) -> str:
    if pd.isna(value):
        return ""
    if column in YEARLY_FIXED_LABELS:
        return html_lib.escape(str(int(float(value))))
    if column == "Phase":
        return html_lib.escape(str(value))
    try:
        return f"${float(value):,.0f}"
    except (TypeError, ValueError):
        return html_lib.escape(str(value))


def _sticky_yearly_table_html(table: pd.DataFrame, scroll_columns: list[str]) -> str:
    """HTML table with Year/Age sticky on horizontal scroll (matches desktop GUI)."""
    cols: list[str] = [c for c in YEARLY_FIXED_LABELS if c in table.columns]
    for c in scroll_columns:
        if c in table.columns and c not in cols:
            cols.append(c)
    if not cols:
        return "<p>No columns to display.</p>"

    header = "".join(
        f'<th class="{"year" if c == "Year" else "age" if c == "Age" else ""}">{html_lib.escape(c)}</th>'
        for c in cols
    )
    body_rows: list[str] = []
    for _, row in table.iterrows():
        cells = "".join(
            f'<td class="{"year" if c == "Year" else "age" if c == "Age" else ""}">'
            f"{_format_yearly_cell(c, row[c])}</td>"
            for c in cols
        )
        body_rows.append(f"<tr>{cells}</tr>")

    return f"""
<style>
.yearly-table-wrap {{
  overflow: auto;
  max-height: 480px;
  border: 1px solid #c8cdd5;
  border-radius: 8px;
  background: #e8ecf1;
}}
.yearly-table {{
  border-collapse: separate;
  border-spacing: 0;
  font-size: 14px;
  color: #1a1d21;
}}
.yearly-table th, .yearly-table td {{
  padding: 6px 12px;
  border-bottom: 1px solid #d0d5de;
  white-space: nowrap;
  background: #e8ecf1;
}}
.yearly-table thead th {{
  position: sticky;
  top: 0;
  z-index: 4;
  background: #dde2ea;
  font-weight: 600;
  text-align: left;
}}
.yearly-table td.year, .yearly-table th.year {{
  position: sticky;
  left: 0;
  z-index: 3;
}}
.yearly-table td.age, .yearly-table th.age {{
  position: sticky;
  left: 3.75rem;
  z-index: 3;
  box-shadow: 4px 0 6px -4px rgba(0,0,0,0.12);
}}
.yearly-table thead th.year {{ z-index: 5; }}
.yearly-table thead th.age {{ z-index: 5; }}
</style>
<div class="yearly-table-wrap">
  <table class="yearly-table">
    <thead><tr>{header}</tr></thead>
    <tbody>{"".join(body_rows)}</tbody>
  </table>
</div>
"""


def _inputs_from_sidebar(st) -> RetirementInputs:
    sample = default_sample_inputs()
    withdrawal_options = list(WITHDRAWAL_LABELS.keys())
    default_wo_label = withdrawal_options[0]
    for label, order in WITHDRAWAL_LABELS.items():
        if order == sample.withdrawal_order:
            default_wo_label = label
            break

    with st.sidebar:
        st.header("Your plan")
        with st.expander("Timeline", expanded=True):
            birth_year = st.number_input("Birth year", 1940, 2010, sample.birth_year, step=1)
            planning_start_year = st.number_input(
                "Planning start year", 2020, 2100, sample.planning_start_year, step=1
            )
            retirement_age = st.number_input("Retirement age", 50, 80, sample.retirement_age, step=1)
            life_expectancy_age = st.number_input(
                "Life expectancy (age)", retirement_age + 1, 110, sample.life_expectancy_age, step=1
            )

        with st.expander("Account balances ($)"):
            balance_401k = st.number_input(
                "401(k) / 403(b)", 0.0, 50_000_000.0, float(sample.balance_401k), step=1000.0
            )
            balance_traditional_ira = st.number_input(
                "Traditional IRA", 0.0, 50_000_000.0, float(sample.balance_traditional_ira), step=1000.0
            )
            balance_roth_ira = st.number_input(
                "Roth IRA", 0.0, 50_000_000.0, float(sample.balance_roth_ira), step=1000.0
            )
            balance_taxable = st.number_input(
                "Taxable investments", 0.0, 50_000_000.0, float(sample.balance_taxable), step=1000.0
            )

        with st.expander("Saving (pre-retirement)"):
            annual_salary = st.number_input("Annual salary", 0.0, 5_000_000.0, float(sample.annual_salary), step=1000.0)
            employee_401k_contribution = st.number_input(
                "Your 401(k) deferral / year", 0.0, 500_000.0, float(sample.employee_401k_contribution), step=500.0
            )
            employer_match_rate = st.number_input(
                "Employer match rate (0–1)",
                0.0,
                1.0,
                float(sample.employer_match_rate),
                step=0.05,
            )
            employer_match_up_to_pct_of_salary = st.number_input(
                "Match on first fraction of salary",
                0.0,
                0.25,
                float(sample.employer_match_up_to_pct_of_salary),
                step=0.01,
            )
            annual_ira_contribution = st.number_input(
                "IRA contribution / year", 0.0, 50_000.0, float(sample.annual_ira_contribution), step=500.0
            )
            ira_is_roth = st.checkbox("IRA contributions go to Roth", value=sample.ira_is_roth)

        with st.expander("Returns (annual, as decimal)"):
            annual_return_pre_retirement = st.number_input(
                "Before retirement", -0.50, 0.50, float(sample.annual_return_pre_retirement), step=0.005
            )
            annual_return_post_retirement = st.number_input(
                "In retirement", -0.50, 0.50, float(sample.annual_return_post_retirement), step=0.005
            )

        with st.expander("Pension"):
            pension_monthly_at_start = st.number_input(
                "Monthly benefit at start", 0.0, 100_000.0, float(sample.pension_monthly_at_start), step=100.0
            )
            pension_start_age = st.number_input("Start age", 50, 80, sample.pension_start_age, step=1)
            pension_cola_pct = st.number_input(
                "COLA (0–1)", 0.0, 0.10, float(sample.pension_cola_pct), step=0.005
            )

        with st.expander("Social Security"):
            ss_monthly_at_fra = st.number_input(
                "Your monthly at full retirement age",
                0.0,
                20_000.0,
                float(sample.ss_monthly_at_fra),
                step=50.0,
            )
            ss_fra_age = st.number_input("Your full retirement age", 62, 70, sample.ss_fra_age, step=1)
            ss_claim_age = st.number_input("Your claim age (62–70)", 62, 70, sample.ss_claim_age, step=1)
            ss_cola_pct = st.number_input("Your SS COLA (0–1)", 0.0, 0.10, float(sample.ss_cola_pct), step=0.005)
            spouse_ss_monthly_at_fra = st.number_input(
                "Spouse monthly at FRA", 0.0, 20_000.0, float(sample.spouse_ss_monthly_at_fra), step=50.0
            )
            spouse_ss_claim_age = st.number_input("Spouse claim age", 62, 70, sample.spouse_ss_claim_age, step=1)

        with st.expander("Spending"):
            annual_spending_goal_today = st.number_input(
                "Annual spending (today's dollars)",
                0.0,
                2_000_000.0,
                float(sample.annual_spending_goal_today),
                step=1000.0,
            )
            inflation_pct = st.number_input(
                "Inflation (0–1)", 0.0, 0.10, float(sample.inflation_pct), step=0.005
            )

        wo_label = st.radio(
            "Withdrawal order",
            options=withdrawal_options,
            index=withdrawal_options.index(default_wo_label),
        )
        withdrawal_order = WITHDRAWAL_LABELS[wo_label]

        with st.expander("Advanced (v2): tax, Roth pools, conversions"):
            use_tax_modeling = st.checkbox(
                "Model federal / state tax, IRMAA (after-tax spending)",
                value=sample.use_tax_modeling,
            )
            employee_401k_to_roth = st.checkbox(
                "Employee 401(k) deferrals → Roth (post-tax pool)",
                value=sample.employee_401k_to_roth,
            )
            employer_match_to_roth = st.checkbox(
                "Employer match → Roth (pre-tax pool)",
                value=sample.employer_match_to_roth,
            )
            filing_status = st.radio(
                "Filing status",
                options=["single", "mfj"],
                index=0 if sample.filing_status == "single" else 1,
                horizontal=True,
            )
            state_code = st.text_input(
                "State code (e.g. OR, none, custom)",
                value=sample.state_code,
            )
            state_custom_tax_rate = st.number_input(
                "Custom state rate (if state=custom)",
                0.0,
                0.20,
                float(sample.state_custom_tax_rate),
                step=0.005,
            )
            taxable_cost_basis_ratio = st.number_input(
                "Taxable acct cost basis ratio (0–1)",
                0.0,
                1.0,
                float(sample.taxable_cost_basis_ratio),
                step=0.05,
            )
            roth_posttax_opening_balance = st.number_input(
                "Roth post-tax $ before employer match",
                0.0,
                50_000_000.0,
                float(sample.roth_posttax_opening_balance),
                step=1000.0,
            )
            roth_conversion_annual = st.number_input(
                "Roth conversion $ / year",
                0.0,
                5_000_000.0,
                float(sample.roth_conversion_annual),
                step=1000.0,
            )
            roth_conversion_start_age = st.number_input(
                "Conversion start age (0=off)",
                0,
                100,
                sample.roth_conversion_start_age,
                step=1,
            )
            roth_conversion_end_age = st.number_input(
                "Conversion end age",
                0,
                100,
                sample.roth_conversion_end_age,
                step=1,
            )
            run_monte_carlo_trials = st.number_input(
                "Monte Carlo trials (0=skip)",
                0,
                10_000,
                sample.run_monte_carlo_trials,
                step=50,
            )

    return build_retirement_inputs(
        birth_year=int(birth_year),
        planning_start_year=int(planning_start_year),
        retirement_age=int(retirement_age),
        life_expectancy_age=int(life_expectancy_age),
        balance_401k=balance_401k,
        balance_traditional_ira=balance_traditional_ira,
        balance_roth_ira=balance_roth_ira,
        balance_taxable=balance_taxable,
        annual_salary=annual_salary,
        employee_401k_contribution=employee_401k_contribution,
        employer_match_rate=employer_match_rate,
        employer_match_up_to_pct_of_salary=employer_match_up_to_pct_of_salary,
        annual_ira_contribution=annual_ira_contribution,
        ira_is_roth=ira_is_roth,
        annual_return_pre_retirement=annual_return_pre_retirement,
        annual_return_post_retirement=annual_return_post_retirement,
        pension_monthly_at_start=pension_monthly_at_start,
        pension_start_age=int(pension_start_age),
        pension_cola_pct=pension_cola_pct,
        ss_monthly_at_fra=ss_monthly_at_fra,
        ss_fra_age=int(ss_fra_age),
        ss_claim_age=int(ss_claim_age),
        ss_cola_pct=ss_cola_pct,
        spouse_ss_monthly_at_fra=spouse_ss_monthly_at_fra,
        spouse_ss_claim_age=int(spouse_ss_claim_age),
        annual_spending_goal_today=annual_spending_goal_today,
        inflation_pct=inflation_pct,
        withdrawal_order=withdrawal_order,
        use_tax_modeling=use_tax_modeling,
        filing_status=filing_status,
        state_code=state_code,
        state_custom_tax_rate=state_custom_tax_rate,
        taxable_cost_basis_ratio=taxable_cost_basis_ratio,
        roth_posttax_opening_balance=roth_posttax_opening_balance,
        employee_401k_to_roth=employee_401k_to_roth,
        employer_match_to_roth=employer_match_to_roth,
        roth_conversion_annual=roth_conversion_annual,
        roth_conversion_start_age=int(roth_conversion_start_age),
        roth_conversion_end_age=int(roth_conversion_end_age),
        run_monte_carlo_trials=int(run_monte_carlo_trials),
    )


def main() -> None:
    import streamlit as st

    st.set_page_config(
        page_title="Retirement Planner",
        page_icon="📊",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    st.markdown(
        """
        <style>
        @media print {
            [data-testid="stSidebar"], [data-testid="stToolbar"], footer, header { display: none !important; }
            .main .block-container { max-width: 100%; padding-top: 0; }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.title("Retirement cash-flow planner")
    st.caption("Enter assumptions in the sidebar. Reports update automatically. Not investment or tax advice.")

    inputs: RetirementInputs = _inputs_from_sidebar(st)

    try:
        df = run_projection(inputs)
    except ValueError as exc:
        st.error(str(exc))
        return

    summary = summarize_projection(df, inputs)
    tab_summary, tab_table, tab_charts, tab_export = st.tabs(["Summary", "Year-by-year", "Charts", "Save & print"])

    with tab_summary:
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Ending balance", f"${summary['ending_balance']:,.0f}")
        if summary["balance_at_retirement"] is not None:
            c2.metric("Balance at retirement", f"${summary['balance_at_retirement']:,.0f}")
        c3.metric("Cumulative shortfall", f"${summary['cumulative_shortfall']:,.0f}")
        c4.metric("Plan years", f"{summary['plan_start_year']}–{summary['plan_end_year']}")

        if summary["first_shortfall"]:
            fs = summary["first_shortfall"]
            st.warning(f"Spending shortfall begins in **{fs['year']}** (age **{fs['age']}**).")
        else:
            st.success("No spending shortfalls in the retirement years of this projection.")

        ret = df[df["phase"] == "retirement"]
        if not ret.empty:
            st.subheader("First year of retirement")
            row = ret.iloc[0]
            st.write(
                f"In **{int(row['year'])}** (age **{int(row['age'])}**): "
                f"spending need **${row['spending_need']:,.0f}**, "
                f"income **${row['income_total']:,.0f}** "
                f"(pension ${row['pension_income']:,.0f}, SS ${row['ss_income'] + row['spouse_ss_income']:,.0f}, "
                f"withdrawals ${row['withdrawal_total']:,.0f})."
            )

        if inputs.run_monte_carlo_trials > 0:
            st.subheader("Monte Carlo")
            st.caption(
                "Same as desktop **Run → Run projection**: deterministic plan above; "
                "run trials on demand (can take a minute)."
            )
            if st.button("Run Monte Carlo analysis", type="primary"):
                from retirement.monte_carlo import run_monte_carlo

                with st.spinner(f"Running {inputs.run_monte_carlo_trials} trials…"):
                    mc = run_monte_carlo(inputs, trials=inputs.run_monte_carlo_trials)
                st.info(
                    f"**{mc.trials}** trials: **{mc.success_rate:.1%}** success rate, "
                    f"median ending balance **${mc.median_ending_balance:,.0f}**."
                )

    with tab_table:
        table = report_dataframe(df)
        scroll_options = yearly_scroll_column_names(table)
        show_scroll = st.multiselect(
            "Columns (Year and Age stay fixed on the left)",
            options=scroll_options,
            default=scroll_options,
        )
        st.caption("Scroll horizontally for more columns; Year and Age remain visible.")
        st.components.v1.html(
            _sticky_yearly_table_html(table, show_scroll),
            height=500,
            scrolling=False,
        )

    with tab_charts:
        fig_income = income_chart_figure(df)
        if fig_income:
            st.pyplot(fig_income, use_container_width=True)
        fig_bal = balance_chart_figure(df)
        if fig_bal:
            st.pyplot(fig_bal, use_container_width=True)

    with tab_export:
        st.subheader("Download")
        col_a, col_b, col_c = st.columns(3)
        csv_bytes = report_dataframe(df).to_csv(index=False).encode("utf-8")
        html_bytes = build_html_report(df, inputs).encode("utf-8")
        xlsx_bytes = workbook_bytes(inputs)

        col_a.download_button(
            "Download CSV",
            data=csv_bytes,
            file_name="retirement_projection.csv",
            mime="text/csv",
            use_container_width=True,
        )
        col_b.download_button(
            "Download Excel",
            data=xlsx_bytes,
            file_name="retirement_planner.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )
        col_c.download_button(
            "Download HTML report",
            data=html_bytes,
            file_name="retirement_report.html",
            mime="text/html",
            use_container_width=True,
        )

        st.subheader("Print")
        st.markdown(
            "1. **From this page:** use your browser **Print** (Ctrl+P). Side panels are hidden in print view.\n"
            "2. **Full report:** download **HTML report**, open it in Chrome or Edge, then **Print** or **Save as PDF**."
        )
        with st.expander("Preview HTML report (scrollable)"):
            st.components.v1.html(build_html_report(df, inputs), height=600, scrolling=True)


def _launch() -> None:
    """Run under Streamlit server; re-launch if started as `python streamlit_app.py`."""
    import subprocess
    import sys
    from pathlib import Path

    from streamlit.runtime.scriptrunner import get_script_run_ctx

    if get_script_run_ctx() is not None:
        main()
        return

    script = Path(__file__).resolve()
    print("Launching Streamlit (use run-streamlit.bat or: python -m streamlit run streamlit_app.py)")
    raise SystemExit(subprocess.call([sys.executable, "-m", "streamlit", "run", str(script)]))


if __name__ == "__main__":
    _launch()
else:
    from streamlit.runtime.scriptrunner import get_script_run_ctx

    if get_script_run_ctx() is not None:
        main()
