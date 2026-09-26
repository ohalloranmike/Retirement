"""Medicare IRMAA surcharges (Part B, simplified; based on MAGI)."""

from __future__ import annotations

# 2025 Part B total monthly premium approximations (MFJ thresholds, per person add-on over base)
# Base ~$185/mo; tiers add $0, ~74, ~185, ~296, ~407 per month per person (rounded)
_TIERS_MFJ = [
    (206_000, 0.0),
    (258_000, 74.0),
    (322_000, 185.0),
    (386_000, 296.0),
    (750_000, 407.0),
    (float("inf"), 444.0),
]
_TIERS_SINGLE = [
    (103_000, 0.0),
    (129_000, 74.0),
    (161_000, 185.0),
    (193_000, 296.0),
    (500_000, 407.0),
    (float("inf"), 444.0),
]


def irmaa_annual_surcharge(magi: float, filing: str, medicare_enrollment_age: int, age: int) -> float:
    """Extra Part B premium per year for one person (simplified)."""
    if age < medicare_enrollment_age:
        return 0.0
    tiers = _TIERS_MFJ if filing == "mfj" else _TIERS_SINGLE
    monthly_add = 0.0
    for limit, add in tiers:
        if magi <= limit:
            monthly_add = add
            break
    return monthly_add * 12.0
