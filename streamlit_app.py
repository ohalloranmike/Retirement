"""Interactive retirement planner (Streamlit). Run: streamlit run streamlit_app.py"""

from __future__ import annotations

from retirement.venv_guard import require_project_venv

require_project_venv()

from retirement.charts import balance_chart_figure, income_chart_figure
from retirement.models import RetirementInputs, WithdrawalOrder
from retirement.projection import default_sample_inputs, run_projection
from retirement.report import build_html_report, report_dataframe, summarize_projection, workbook_bytes


def _inputs_from_sidebar(st) -> RetirementInputs:
    sample = default_sample_inputs()
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

        with st.expander("Account balances"):
            balance_401k = st.number_input("401(k) / 403(b) ($)", 0.0, 50_000_000.0, float(sample.balance_401k), step=1000.0)
            balance_traditional_ira = st.number_input(
                "Traditional IRA ($)", 0.0, 50_000_000.0, float(sample.balance_traditional_ira), step=1000.0
            )
            balance_roth_ira = st.number_input(
                "Roth IRA ($)", 0.0, 50_000_000.0, float(sample.balance_roth_ira), step=1000.0
            )
            balance_taxable = st.number_input(
                "Taxable investments ($)", 0.0, 50_000_000.0, float(sample.balance_taxable), step=1000.0
            )

        with st.expander("Saving (pre-retirement)"):
            annual_salary = st.number_input("Annual salary ($)", 0.0, 5_000_000.0, float(sample.annual_salary), step=1000.0)
            employee_401k_contribution = st.number_input(
                "Your 401(k) deferral ($/yr)", 0.0, 500_000.0, float(sample.employee_401k_contribution), step=500.0
            )
            employer_match_rate = st.slider(
                "Employer match rate", 0.0, 1.0, float(sample.employer_match_rate), 0.05
            )
            employer_match_up_to_pct_of_salary = st.slider(
                "Match on first % of salary", 0.0, 0.25, float(sample.employer_match_up_to_pct_of_salary), 0.01
            )
            annual_ira_contribution = st.number_input(
                "IRA contribution ($/yr)", 0.0, 50_000.0, float(sample.annual_ira_contribution), step=500.0
            )
            ira_is_roth = st.checkbox("IRA contributions go to Roth", value=sample.ira_is_roth)

        with st.expander("Investment returns"):
            annual_return_pre_retirement = st.slider(
                "Return before retirement (annual)", -0.10, 0.15, float(sample.annual_return_pre_retirement), 0.005
            )
            annual_return_post_retirement = st.slider(
                "Return in retirement (annual)", -0.10, 0.15, float(sample.annual_return_post_retirement), 0.005
            )

        with st.expander("Pension"):
            pension_monthly_at_start = st.number_input(
                "Monthly pension at start ($)", 0.0, 100_000.0, float(sample.pension_monthly_at_start), step=100.0
            )
            pension_start_age = st.number_input("Pension start age", 50, 80, sample.pension_start_age, step=1)
            pension_cola_pct = st.slider("Pension COLA (annual)", 0.0, 0.10, float(sample.pension_cola_pct), 0.005)

        with st.expander("Social Security"):
            ss_monthly_at_fra = st.number_input(
                "Your SS monthly at full retirement age ($)",
                0.0,
                20_000.0,
                float(sample.ss_monthly_at_fra),
                step=50.0,
            )
            ss_fra_age = st.number_input("Your full retirement age", 62, 70, sample.ss_fra_age, step=1)
            ss_claim_age = st.number_input("Your claim age", 62, 70, sample.ss_claim_age, step=1)
            ss_cola_pct = st.slider("SS COLA (annual)", 0.0, 0.10, float(sample.ss_cola_pct), 0.005)
            spouse_ss_monthly_at_fra = st.number_input(
                "Spouse SS monthly at FRA ($)", 0.0, 20_000.0, float(sample.spouse_ss_monthly_at_fra), step=50.0
            )
            spouse_ss_claim_age = st.number_input("Spouse claim age", 62, 70, sample.spouse_ss_claim_age, step=1)

        with st.expander("Spending & withdrawals"):
            annual_spending_goal_today = st.number_input(
                "Annual spending goal (today's $)", 0.0, 2_000_000.0, float(sample.annual_spending_goal_today), step=1000.0
            )
            inflation_pct = st.slider("Inflation (annual)", 0.0, 0.10, float(sample.inflation_pct), 0.005)
            wo_label = st.selectbox(
                "Withdrawal order",
                options=[
                    ("Taxable → traditional → Roth", WithdrawalOrder.TAXABLE_TRADITIONAL_ROTH),
                    ("Traditional → taxable → Roth", WithdrawalOrder.TRADITIONAL_TAXABLE_ROTH),
                    ("Proportional across accounts", WithdrawalOrder.PROPORTIONAL),
                ],
                format_func=lambda x: x[0],
            )
            withdrawal_order = wo_label[1]

    return RetirementInputs(
        birth_year=int(birth_year),
        retirement_age=int(retirement_age),
        life_expectancy_age=int(life_expectancy_age),
        planning_start_year=int(planning_start_year),
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
        ss_claim_age=int(ss_claim_age),
        ss_cola_pct=ss_cola_pct,
        ss_fra_age=int(ss_fra_age),
        spouse_ss_monthly_at_fra=spouse_ss_monthly_at_fra,
        spouse_ss_claim_age=int(spouse_ss_claim_age),
        annual_spending_goal_today=annual_spending_goal_today,
        inflation_pct=inflation_pct,
        withdrawal_order=withdrawal_order,
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

    inputs = _inputs_from_sidebar(st)

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

    with tab_table:
        show = st.multiselect(
            "Columns",
            options=list(report_dataframe(df).columns),
            default=["Year", "Age", "Total balance", "Total income", "Spending need", "Surplus / shortfall"],
        )
        table = report_dataframe(df)
        if show:
            table = table[show]
        st.dataframe(
            table.style.format(
                {c: "${:,.0f}" for c in table.columns if c not in ("Year", "Age", "Phase")},
                na_rep="",
            ),
            use_container_width=True,
            height=480,
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
