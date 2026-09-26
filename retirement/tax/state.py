"""State income tax (flat effective rate by code or override)."""

from __future__ import annotations

# Approximate top marginal / effective planning rates (simplified flat for modeling)
_STATE_FLAT_RATE: dict[str, float] = {
    "none": 0.0,
    "AK": 0.0,
    "FL": 0.0,
    "NV": 0.0,
    "SD": 0.0,
    "TX": 0.0,
    "WA": 0.0,
    "WY": 0.0,
    "TN": 0.0,
    "NH": 0.0,
    "AZ": 0.025,
    "CO": 0.044,
    "GA": 0.055,
    "IL": 0.0495,
    "IN": 0.0315,
    "MA": 0.05,
    "MI": 0.0425,
    "NC": 0.045,
    "OR": 0.087,
    "CA": 0.093,
    "NY": 0.065,
    "NJ": 0.0637,
    "PA": 0.0307,
    "custom": 0.0,
}


def state_income_tax(taxable_income: float, state_code: str, custom_rate: float) -> float:
    if taxable_income <= 0:
        return 0.0
    code = state_code.upper()
    rate = custom_rate if code == "CUSTOM" else _STATE_FLAT_RATE.get(code, custom_rate)
    return taxable_income * rate
