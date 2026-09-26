"""Simplified Social Security benefit adjustment vs full retirement age."""

from __future__ import annotations


def monthly_benefit_at_claim(
    monthly_at_fra: float,
    claim_age: int,
    fra_age: int,
    cola_pct: float,
    years_since_base: int,
) -> float:
    """
    Approximate SS monthly benefit at claim age with COLA from planning start.

    Early retirement: ~5/9% per month for first 36 months before FRA, then 5/12% per month.
    Delayed: 8% per year after FRA up to age 70 (2/3% per month).
    """
    if monthly_at_fra <= 0:
        return 0.0

    months_from_fra = (claim_age - fra_age) * 12
    adjusted = monthly_at_fra

    if months_from_fra < 0:
        months_early = -months_from_fra
        first_36 = min(36, months_early)
        rest = months_early - first_36
        reduction = (first_36 * (5 / 9) / 100) + (rest * (5 / 12) / 100)
        adjusted *= max(0.0, 1.0 - reduction)
    elif months_from_fra > 0:
        months_delay = min(months_from_fra, (70 - fra_age) * 12)
        adjusted *= 1.0 + (months_delay * (2 / 3) / 100)

    cola_factor = (1.0 + cola_pct) ** years_since_base
    return adjusted * 12.0 * cola_factor  # annual dollars
