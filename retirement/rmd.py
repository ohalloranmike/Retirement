"""Required minimum distributions (SECURE 2.0 simplified)."""

from __future__ import annotations

# IRS Uniform Lifetime Table (2023+), ages 72–120 (excerpt used in projection)
_UNIFORM_LIFETIME: dict[int, float] = {
    72: 27.4,
    73: 26.5,
    74: 25.5,
    75: 24.6,
    76: 23.7,
    77: 22.9,
    78: 22.0,
    79: 21.1,
    80: 20.2,
    81: 19.4,
    82: 18.5,
    83: 17.7,
    84: 16.8,
    85: 16.0,
    86: 15.2,
    87: 14.4,
    88: 13.7,
    89: 12.9,
    90: 12.2,
    91: 11.5,
    92: 10.8,
    93: 10.1,
    94: 9.5,
    95: 8.9,
    96: 8.4,
    97: 7.8,
    98: 7.3,
    99: 6.8,
    100: 6.4,
    101: 6.0,
    102: 5.6,
    103: 5.2,
    104: 4.9,
    105: 4.6,
    106: 4.3,
    107: 4.1,
    108: 3.9,
    109: 3.7,
    110: 3.5,
    111: 3.4,
    112: 3.3,
    113: 3.1,
    114: 3.0,
    115: 2.9,
    116: 2.8,
    117: 2.7,
    118: 2.5,
    119: 2.3,
    120: 2.0,
}


def rmd_start_age(birth_year: int) -> int:
    """SECURE 2.0: RMD age 73 if born 1951–1959, else 75 if born 1960+."""
    if birth_year <= 1950:
        return 72
    if birth_year <= 1959:
        return 73
    return 75


def uniform_lifetime_divisor(age: int) -> float:
    if age in _UNIFORM_LIFETIME:
        return _UNIFORM_LIFETIME[age]
    if age < 72:
        return _UNIFORM_LIFETIME[72]
    return _UNIFORM_LIFETIME[120]


def required_minimum_distribution(prior_year_traditional_balance: float, age: int) -> float:
    if prior_year_traditional_balance <= 0:
        return 0.0
    divisor = uniform_lifetime_divisor(age)
    return prior_year_traditional_balance / divisor
