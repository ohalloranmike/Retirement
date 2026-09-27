"""Shared retirement plan inputs for desktop GUI and Streamlit."""

from __future__ import annotations

from retirement.models import RetirementInputs, WithdrawalOrder

WITHDRAWAL_LABELS: dict[str, WithdrawalOrder] = {
    "Taxable, then traditional, then Roth": WithdrawalOrder.TAXABLE_TRADITIONAL_ROTH,
    "Traditional, then taxable, then Roth": WithdrawalOrder.TRADITIONAL_TAXABLE_ROTH,
    "Proportional across accounts": WithdrawalOrder.PROPORTIONAL,
}


def parse_float(text: str, field: str) -> float:
    raw = text.strip().replace(",", "").replace("$", "")
    if not raw:
        return 0.0
    try:
        return float(raw)
    except ValueError:
        raise ValueError(f"{field} must be a number.") from None


def parse_int(text: str, field: str) -> int:
    raw = text.strip().replace(",", "")
    if not raw:
        raise ValueError(f"{field} is required.")
    try:
        return int(float(raw))
    except ValueError:
        raise ValueError(f"{field} must be a whole number.") from None


def withdrawal_order_from_label(label: str) -> WithdrawalOrder:
    return WITHDRAWAL_LABELS.get(label, WithdrawalOrder.TAXABLE_TRADITIONAL_ROTH)


def build_retirement_inputs(
    *,
    birth_year: int,
    planning_start_year: int,
    retirement_age: int,
    life_expectancy_age: int,
    balance_401k: float,
    balance_traditional_ira: float,
    balance_roth_ira: float,
    balance_taxable: float,
    annual_salary: float,
    employee_401k_contribution: float,
    employer_match_rate: float,
    employer_match_up_to_pct_of_salary: float,
    annual_ira_contribution: float,
    ira_is_roth: bool,
    annual_return_pre_retirement: float,
    annual_return_post_retirement: float,
    pension_monthly_at_start: float,
    pension_start_age: int,
    pension_cola_pct: float,
    ss_monthly_at_fra: float,
    ss_fra_age: int,
    ss_claim_age: int,
    ss_cola_pct: float,
    spouse_ss_monthly_at_fra: float,
    spouse_ss_claim_age: int,
    annual_spending_goal_today: float,
    inflation_pct: float,
    withdrawal_order: WithdrawalOrder,
    use_tax_modeling: bool = False,
    filing_status: str = "single",
    state_code: str = "none",
    state_custom_tax_rate: float = 0.05,
    taxable_cost_basis_ratio: float = 0.60,
    roth_posttax_opening_balance: float = 0.0,
    employee_401k_to_roth: bool = False,
    employer_match_to_roth: bool = False,
    roth_conversion_annual: float = 0.0,
    roth_conversion_start_age: int = 0,
    roth_conversion_end_age: int = 0,
    run_monte_carlo_trials: int = 0,
) -> RetirementInputs:
    return RetirementInputs(
        birth_year=birth_year,
        planning_start_year=planning_start_year,
        retirement_age=retirement_age,
        life_expectancy_age=life_expectancy_age,
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
        pension_start_age=pension_start_age,
        pension_cola_pct=pension_cola_pct,
        ss_monthly_at_fra=ss_monthly_at_fra,
        ss_fra_age=ss_fra_age,
        ss_claim_age=ss_claim_age,
        ss_cola_pct=ss_cola_pct,
        spouse_ss_monthly_at_fra=spouse_ss_monthly_at_fra,
        spouse_ss_claim_age=spouse_ss_claim_age,
        annual_spending_goal_today=annual_spending_goal_today,
        inflation_pct=inflation_pct,
        withdrawal_order=withdrawal_order,
        use_tax_modeling=use_tax_modeling,
        filing_status=filing_status,
        state_code=state_code.strip() or "none",
        state_custom_tax_rate=state_custom_tax_rate,
        taxable_cost_basis_ratio=taxable_cost_basis_ratio,
        roth_posttax_opening_balance=roth_posttax_opening_balance,
        employee_401k_to_roth=employee_401k_to_roth,
        employer_match_to_roth=employer_match_to_roth,
        roth_conversion_annual=roth_conversion_annual,
        roth_conversion_start_age=roth_conversion_start_age,
        roth_conversion_end_age=roth_conversion_end_age,
        run_monte_carlo_trials=run_monte_carlo_trials,
    )
