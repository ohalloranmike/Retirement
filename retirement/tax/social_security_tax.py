"""Taxable portion of Social Security (provisional income simplified)."""

from __future__ import annotations


def taxable_social_security(
    ss_benefits: float,
    other_income: float,
    tax_exempt_interest: float,
    filing: str,
) -> float:
    """
    other_income: AGI components excluding SS (pension, withdrawals, wages, etc.)
    """
    if ss_benefits <= 0:
        return 0.0

    provisional = other_income + tax_exempt_interest + 0.5 * ss_benefits
    if filing == "mfj":
        base1, base2 = 32_000, 44_000
    else:
        base1, base2 = 25_000, 34_000

    if provisional <= base1:
        return 0.0
    if provisional <= base2:
        return min(0.5 * ss_benefits, 0.5 * (provisional - base1))
    excess = provisional - base2
    return min(0.85 * ss_benefits, 0.85 * excess + 0.5 * (base2 - base1))
