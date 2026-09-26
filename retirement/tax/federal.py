"""Simplified U.S. federal income tax (ordinary brackets + standard deduction)."""

from __future__ import annotations

from dataclasses import dataclass

# 2024 inflation-adjusted brackets (approximate; update annually)
_BRACKETS_SINGLE = [
    (11_600, 0.10),
    (47_150, 0.12),
    (100_525, 0.22),
    (191_950, 0.24),
    (243_725, 0.32),
    (609_350, 0.35),
    (float("inf"), 0.37),
]
_BRACKETS_MFJ = [
    (23_200, 0.10),
    (94_300, 0.12),
    (201_050, 0.22),
    (383_900, 0.24),
    (487_450, 0.32),
    (731_200, 0.35),
    (float("inf"), 0.37),
]

_STANDARD_DEDUCTION = {"single": 14_600, "mfj": 29_200}


@dataclass(frozen=True)
class FilingStatus:
    code: str  # single | mfj


def federal_ordinary_tax(taxable_ordinary: float, filing: str) -> float:
    if taxable_ordinary <= 0:
        return 0.0
    brackets = _BRACKETS_MFJ if filing == "mfj" else _BRACKETS_SINGLE
    tax = 0.0
    lower = 0.0
    for upper, rate in brackets:
        band = min(taxable_ordinary, upper) - lower
        if band > 0:
            tax += band * rate
        if taxable_ordinary <= upper:
            break
        lower = upper
    return tax


def federal_ltcg_tax(
    ltcg: float,
    ordinary_taxable_after_deduction: float,
    filing: str,
) -> float:
    """Stack LTCG on top of ordinary taxable income using 2024 LTCG thresholds."""
    if ltcg <= 0:
        return 0.0
    if filing == "mfj":
        t0, t15, t20 = 94_050, 583_750, float("inf")
    else:
        t0, t15, t20 = 47_025, 518_900, float("inf")

    remaining = ltcg
    tax = 0.0
    stack = ordinary_taxable_after_deduction

    def take(limit: float, rate: float) -> None:
        nonlocal remaining, tax, stack
        if remaining <= 0:
            return
        room = max(0.0, limit - stack)
        chunk = min(remaining, room)
        tax += chunk * rate
        remaining -= chunk
        stack += chunk

    take(t0, 0.0)
    take(t15, 0.15)
    take(t20, 0.20)
    return tax


def taxable_ordinary_after_standard(ordinary_income: float, filing: str) -> float:
    ded = _STANDARD_DEDUCTION.get(filing, _STANDARD_DEDUCTION["single"])
    return max(0.0, ordinary_income - ded)
