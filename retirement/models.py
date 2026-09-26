from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Literal


class WithdrawalOrder(str, Enum):
    TAXABLE_TRADITIONAL_ROTH = "taxable_traditional_roth"
    TRADITIONAL_TAXABLE_ROTH = "traditional_taxable_roth"
    PROPORTIONAL = "proportional"


@dataclass
class RetirementInputs:
    """Assumptions for a deterministic year-by-year retirement projection."""

    birth_year: int
    retirement_age: int
    life_expectancy_age: int
    planning_start_year: int = 2025

    balance_401k: float = 0.0
    balance_traditional_ira: float = 0.0
    balance_roth_ira: float = 0.0
    balance_taxable: float = 0.0

    annual_salary: float = 0.0
    employee_401k_contribution: float = 0.0
    employer_match_rate: float = 0.0  # e.g. 0.50 for 50% match
    employer_match_up_to_pct_of_salary: float = 0.06  # match on first 6% of salary
    annual_ira_contribution: float = 0.0
    ira_is_roth: bool = False

    annual_return_pre_retirement: float = 0.07
    annual_return_post_retirement: float = 0.05

    pension_monthly_at_start: float = 0.0
    pension_start_age: int = 65
    pension_cola_pct: float = 0.0
    pension_survivor_pct: float = 1.0  # 1.0 = full; used for labeling only in v1

    ss_monthly_at_fra: float = 0.0
    ss_claim_age: int = 67
    ss_cola_pct: float = 0.02
    ss_fra_age: int = 67  # full retirement age for benefit baseline

    annual_spending_goal_today: float = 80_000.0
    inflation_pct: float = 0.03

    withdrawal_order: WithdrawalOrder = WithdrawalOrder.TAXABLE_TRADITIONAL_ROTH

    # Optional second person (simplified: add SS only)
    spouse_ss_monthly_at_fra: float = 0.0
    spouse_ss_claim_age: int = 67

    def validate(self) -> None:
        if self.life_expectancy_age <= self.retirement_age:
            raise ValueError("life_expectancy_age must be greater than retirement_age")
        if self.retirement_age < 50 or self.retirement_age > 80:
            raise ValueError("retirement_age looks out of range (50–80)")
        if not 62 <= self.ss_claim_age <= 70:
            raise ValueError("ss_claim_age must be between 62 and 70")
        if self.annual_return_pre_retirement < -0.5 or self.annual_return_pre_retirement > 0.5:
            raise ValueError("annual_return_pre_retirement must be between -50% and 50%")
        if self.annual_return_post_retirement < -0.5 or self.annual_return_post_retirement > 0.5:
            raise ValueError("annual_return_post_retirement must be between -50% and 50%")


ProjectionRowKey = Literal[
    "year",
    "age",
    "phase",
    "return_rate",
    "contrib_401k",
    "contrib_ira",
    "contrib_total",
    "growth_401k",
    "growth_traditional_ira",
    "growth_roth_ira",
    "growth_taxable",
    "balance_401k",
    "balance_traditional_ira",
    "balance_roth_ira",
    "balance_taxable",
    "balance_total",
    "rmd_amount",
    "withdrawal_401k",
    "withdrawal_traditional_ira",
    "withdrawal_roth",
    "withdrawal_taxable",
    "withdrawal_total",
    "pension_income",
    "ss_income",
    "spouse_ss_income",
    "income_total",
    "spending_need",
    "surplus_or_shortfall",
    "cumulative_shortfall",
]
