from __future__ import annotations

from typing import Any

import pandas as pd

from retirement.models import RetirementInputs, WithdrawalOrder
from retirement.rmd import required_minimum_distribution, rmd_start_age
from retirement.roth_pools import RothPoolState
from retirement.social_security import monthly_benefit_at_claim
from retirement.tax.engine import compute_year_taxes


def _employer_match(inputs: RetirementInputs) -> float:
    if inputs.annual_salary <= 0 or inputs.employer_match_rate <= 0:
        return 0.0
    cap = inputs.annual_salary * inputs.employer_match_up_to_pct_of_salary
    employee = min(inputs.employee_401k_contribution, cap)
    return employee * inputs.employer_match_rate


def _spending_need(inputs: RetirementInputs, years_from_start: int) -> float:
    return inputs.annual_spending_goal_today * ((1.0 + inputs.inflation_pct) ** years_from_start)


def _pension_annual(inputs: RetirementInputs, age: int, years_from_start: int) -> float:
    if age < inputs.pension_start_age or inputs.pension_monthly_at_start <= 0:
        return 0.0
    years_on_pension = age - inputs.pension_start_age
    monthly = inputs.pension_monthly_at_start * ((1.0 + inputs.pension_cola_pct) ** years_on_pension)
    cola_from_start = (1.0 + inputs.inflation_pct) ** years_from_start
    return monthly * 12.0 * cola_from_start * inputs.pension_survivor_pct


def _ss_annual(
    inputs: RetirementInputs,
    age: int,
    years_from_start: int,
    monthly_at_fra: float,
    claim_age: int,
) -> float:
    if age < claim_age or monthly_at_fra <= 0:
        return 0.0
    return monthly_benefit_at_claim(
        monthly_at_fra,
        claim_age,
        inputs.ss_fra_age,
        inputs.ss_cola_pct,
        years_from_start,
    )


def _withdrawal_key(balance_key: str) -> str:
    return {
        "balance_401k": "withdrawal_401k",
        "balance_traditional_ira": "withdrawal_traditional_ira",
        "balance_roth_ira": "withdrawal_roth",
        "balance_taxable": "withdrawal_taxable",
    }[balance_key]


def _allocate_withdrawals(
    need: float,
    balances: dict[str, float],
    order: WithdrawalOrder,
    rmd_floor_traditional: float,
) -> dict[str, float]:
    """Withdraw to cover `need`; traditional accounts must take at least RMD when applicable."""
    balances = {k: float(v) for k, v in balances.items()}
    out = {
        "withdrawal_401k": 0.0,
        "withdrawal_traditional_ira": 0.0,
        "withdrawal_roth": 0.0,
        "withdrawal_taxable": 0.0,
    }

    trad_keys = ("balance_401k", "balance_traditional_ira")
    trad_total = sum(balances[k] for k in trad_keys)
    rmd = min(rmd_floor_traditional, trad_total)
    if rmd > 0 and trad_total > 0:
        for key in trad_keys:
            take = min(balances[key], rmd * (balances[key] / trad_total))
            wkey = _withdrawal_key(key)
            out[wkey] += take
            balances[key] -= take

    rmd_taken = out["withdrawal_401k"] + out["withdrawal_traditional_ira"]
    remaining = max(0.0, need - rmd_taken)

    if order == WithdrawalOrder.PROPORTIONAL:
        total = sum(balances.values())
        if total > 0 and remaining > 0:
            for bal_key, bal in list(balances.items()):
                if bal <= 0:
                    continue
                take = min(bal, remaining * (bal / total))
                out[_withdrawal_key(bal_key)] += take
                balances[bal_key] -= take
                remaining -= take
        return {**out, **balances}

    if order == WithdrawalOrder.TRADITIONAL_TAXABLE_ROTH:
        sequence = ["balance_traditional_ira", "balance_401k", "balance_taxable", "balance_roth_ira"]
    else:
        sequence = ["balance_taxable", "balance_401k", "balance_traditional_ira", "balance_roth_ira"]

    for bal_key in sequence:
        if remaining <= 0:
            break
        take = min(balances[bal_key], remaining)
        out[_withdrawal_key(bal_key)] += take
        balances[bal_key] -= take
        remaining -= take

    return {**out, **balances}


def _init_roth_pool(inputs: RetirementInputs) -> RothPoolState | None:
    if not inputs.use_tax_modeling:
        return None
    posttax = min(inputs.roth_posttax_opening_balance, inputs.balance_roth_ira)
    pretax = max(0.0, inputs.balance_roth_ira - posttax)
    return RothPoolState(posttax_balance=posttax, pretax_balance=pretax)


def run_projection(inputs: RetirementInputs) -> pd.DataFrame:
    inputs.validate()
    rows: list[dict[str, Any]] = []

    b_401k = inputs.balance_401k
    b_trad = inputs.balance_traditional_ira
    b_roth = inputs.balance_roth_ira
    b_tax = inputs.balance_taxable
    roth_pool = _init_roth_pool(inputs)
    if roth_pool is not None:
        b_roth = roth_pool.total

    cumulative_shortfall = 0.0
    rmd_age = rmd_start_age(inputs.birth_year)
    match = _employer_match(inputs)

    end_year = inputs.birth_year + inputs.life_expectancy_age
    year = inputs.planning_start_year
    years_from_start = 0

    while year <= end_year:
        age = year - inputs.birth_year
        if age > inputs.life_expectancy_age:
            break

        pre_retirement = age < inputs.retirement_age
        ret_rate = inputs.annual_return_pre_retirement if pre_retirement else inputs.annual_return_post_retirement

        contrib_401k = 0.0
        contrib_ira = 0.0
        roth_conversion = 0.0
        if pre_retirement:
            if inputs.use_tax_modeling:
                if inputs.employee_401k_to_roth and roth_pool is not None:
                    roth_pool.add_contribution(inputs.employee_401k_contribution, to_pretax=False)
                else:
                    contrib_401k += inputs.employee_401k_contribution
                if inputs.employer_match_to_roth and roth_pool is not None:
                    roth_pool.add_contribution(match, to_pretax=True)
                else:
                    contrib_401k += match
            else:
                contrib_401k = inputs.employee_401k_contribution + match
            contrib_ira = inputs.annual_ira_contribution

        # Growth on beginning-of-year balances (after contributions applied at start)
        b_401k += contrib_401k
        if inputs.ira_is_roth:
            if roth_pool is not None:
                roth_pool.add_contribution(contrib_ira, to_pretax=False)
            else:
                b_roth += contrib_ira
        else:
            b_trad += contrib_ira

        g_401k = b_401k * ret_rate
        g_trad = b_trad * ret_rate
        if roth_pool is not None:
            roth_before = roth_pool.total
            roth_pool.apply_growth(ret_rate)
            g_roth = roth_pool.total - roth_before
            b_roth = roth_pool.total
        else:
            g_roth = b_roth * ret_rate
            b_roth += g_roth
        g_tax = b_tax * ret_rate

        b_401k += g_401k
        b_trad += g_trad
        b_tax += g_tax

        pension = 0.0
        ss = 0.0
        spouse_ss = 0.0
        spending = 0.0
        w_401k = w_trad = w_roth = w_tax = 0.0
        rmd_amount = 0.0
        roth_qualified = roth_taxable = 0.0
        federal_tax = state_tax = irmaa = total_tax = 0.0
        after_tax_income = 0.0

        if not pre_retirement:
            if (
                inputs.use_tax_modeling
                and inputs.roth_conversion_start_age > 0
                and inputs.roth_conversion_start_age <= age <= inputs.roth_conversion_end_age
            ):
                roth_conversion = min(inputs.roth_conversion_annual, b_trad + b_401k)
                from_trad = min(roth_conversion, b_trad)
                b_trad -= from_trad
                remainder = roth_conversion - from_trad
                b_401k -= remainder
                if roth_pool is not None:
                    roth_pool.convert_in_from_traditional(roth_conversion)

        if not pre_retirement:
            spending = _spending_need(inputs, years_from_start)
            pension = _pension_annual(inputs, age, years_from_start)
            ss = _ss_annual(inputs, age, years_from_start, inputs.ss_monthly_at_fra, inputs.ss_claim_age)
            spouse_ss = _ss_annual(
                inputs,
                age,
                years_from_start,
                inputs.spouse_ss_monthly_at_fra,
                inputs.spouse_ss_claim_age,
            )
            income_fixed = pension + ss + spouse_ss
            portfolio_need = max(0.0, spending - income_fixed) if not inputs.use_tax_modeling else spending * 0.85

            trad_for_rmd = b_401k + b_trad
            if age >= rmd_age and trad_for_rmd > 0:
                rmd_amount = required_minimum_distribution(trad_for_rmd, age)

            snap_401k, snap_trad, snap_tax = b_401k, b_trad, b_tax
            snap_roth_post = roth_pool.posttax_balance if roth_pool else 0.0
            snap_roth_pre = roth_pool.pretax_balance if roth_pool else 0.0
            snap_roth = b_roth

            for _ in range(10):
                b_401k, b_trad, b_tax = snap_401k, snap_trad, snap_tax
                b_roth = snap_roth
                if roth_pool is not None:
                    roth_pool.posttax_balance = snap_roth_post
                    roth_pool.pretax_balance = snap_roth_pre
                    b_roth = roth_pool.total

                balances = {
                    "balance_401k": b_401k,
                    "balance_traditional_ira": b_trad,
                    "balance_roth_ira": b_roth,
                    "balance_taxable": b_tax,
                }
                alloc = _allocate_withdrawals(
                    portfolio_need,
                    balances,
                    inputs.withdrawal_order,
                    rmd_amount,
                )
                w_401k = alloc["withdrawal_401k"]
                w_trad = alloc["withdrawal_traditional_ira"]
                w_roth = alloc["withdrawal_roth"]
                w_tax = alloc["withdrawal_taxable"]

                if roth_pool is not None and w_roth > 0:
                    roth_qualified, roth_taxable = roth_pool.withdraw(w_roth)
                    b_roth = roth_pool.total
                else:
                    roth_qualified, roth_taxable = w_roth, 0.0

                b_401k = alloc["balance_401k"]
                b_trad = alloc["balance_traditional_ira"]
                if roth_pool is None:
                    b_roth = alloc["balance_roth_ira"]
                b_tax = alloc["balance_taxable"]

                if not inputs.use_tax_modeling:
                    break

                tax = compute_year_taxes(
                    filing_status=inputs.filing_status,
                    state_code=inputs.state_code,
                    state_custom_rate=inputs.state_custom_tax_rate,
                    age=age,
                    medicare_age=inputs.medicare_start_age,
                    ss_benefits=ss + spouse_ss,
                    pension=pension,
                    withdrawal_traditional=w_401k + w_trad,
                    withdrawal_taxable=w_tax,
                    taxable_account_cost_basis_ratio=inputs.taxable_cost_basis_ratio,
                    roth_taxable_withdrawal=roth_taxable,
                    roth_conversion_income=roth_conversion,
                    roth_qualified_withdrawal=roth_qualified,
                )
                after_tax_income = tax.after_tax_cash
                federal_tax = tax.federal_total
                state_tax = tax.state_tax
                irmaa = tax.irmaa_surcharge
                total_tax = tax.total_tax
                if after_tax_income >= spending - 5:
                    break
                gap = spending - after_tax_income
                portfolio_need = max(portfolio_need + gap * 1.15, portfolio_need * 1.05)

        withdrawal_total = w_401k + w_trad + w_roth + w_tax
        income_total = pension + ss + spouse_ss + withdrawal_total
        if not pre_retirement:
            if inputs.use_tax_modeling:
                surplus = after_tax_income - spending
            else:
                surplus = income_total - spending
        else:
            surplus = 0.0
        if not pre_retirement and surplus < 0:
            cumulative_shortfall += -surplus

        row: dict[str, Any] = {
                "year": year,
                "age": age,
                "phase": "accumulation" if pre_retirement else "retirement",
                "return_rate": ret_rate,
                "contrib_401k": contrib_401k,
                "contrib_ira": contrib_ira,
                "contrib_total": contrib_401k + contrib_ira,
                "growth_401k": g_401k,
                "growth_traditional_ira": g_trad,
                "growth_roth_ira": g_roth,
                "growth_taxable": g_tax,
                "balance_401k": b_401k,
                "balance_traditional_ira": b_trad,
                "balance_roth_ira": b_roth,
                "balance_taxable": b_tax,
                "balance_total": b_401k + b_trad + b_roth + b_tax,
                "rmd_amount": rmd_amount,
                "withdrawal_401k": w_401k,
                "withdrawal_traditional_ira": w_trad,
                "withdrawal_roth": w_roth,
                "withdrawal_taxable": w_tax,
                "withdrawal_total": withdrawal_total,
                "pension_income": pension,
                "ss_income": ss,
                "spouse_ss_income": spouse_ss,
                "income_total": income_total,
                "spending_need": spending,
                "surplus_or_shortfall": surplus,
                "cumulative_shortfall": cumulative_shortfall,
        }
        if inputs.use_tax_modeling:
            row.update(
                {
                    "federal_tax": federal_tax,
                    "state_tax": state_tax,
                    "irmaa_surcharge": irmaa,
                    "total_tax": total_tax,
                    "after_tax_income": after_tax_income,
                    "roth_conversion": roth_conversion,
                    "roth_withdrawal_taxable": roth_taxable,
                    "roth_withdrawal_qualified": roth_qualified,
                    "roth_posttax_balance": roth_pool.posttax_balance if roth_pool else b_roth,
                    "roth_pretax_balance": roth_pool.pretax_balance if roth_pool else 0.0,
                }
            )
        rows.append(row)

        year += 1
        years_from_start += 1

    return pd.DataFrame(rows)


def inputs_from_dict(data: dict[str, Any]) -> RetirementInputs:
    wo = data.get("withdrawal_order", WithdrawalOrder.TAXABLE_TRADITIONAL_ROTH)
    if isinstance(wo, str):
        wo = WithdrawalOrder(wo)
    data = {**data, "withdrawal_order": wo}
    return RetirementInputs(**{k: v for k, v in data.items() if k in RetirementInputs.__dataclass_fields__})


def default_sample_inputs() -> RetirementInputs:
    return RetirementInputs(
        birth_year=1965,
        retirement_age=65,
        life_expectancy_age=90,
        planning_start_year=2025,
        balance_401k=450_000,
        balance_traditional_ira=120_000,
        balance_roth_ira=80_000,
        balance_taxable=150_000,
        annual_salary=120_000,
        employee_401k_contribution=15_000,
        employer_match_rate=0.5,
        annual_ira_contribution=7_000,
        ira_is_roth=True,
        annual_return_pre_retirement=0.07,
        annual_return_post_retirement=0.05,
        pension_monthly_at_start=2_500,
        pension_start_age=65,
        pension_cola_pct=0.0,
        ss_monthly_at_fra=3_200,
        ss_claim_age=67,
        ss_cola_pct=0.02,
        annual_spending_goal_today=85_000,
        inflation_pct=0.03,
    )
