"""Monte Carlo success rate vs fixed spending goal."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from retirement.models import RetirementInputs
from retirement.projection import run_projection


@dataclass
class MonteCarloResult:
    trials: int
    success_rate: float
    median_ending_balance: float
    p10_ending_balance: float
    p90_ending_balance: float
    ending_balances: np.ndarray


def run_monte_carlo(
    inputs: RetirementInputs,
    trials: int = 1000,
    return_mean: float | None = None,
    return_std: float | None = None,
    seed: int | None = 42,
) -> MonteCarloResult:
    """
    Randomize annual post-retirement returns (normal); pre-retirement uses mean only.
    Success = no cumulative shortfall in deterministic tax-off path (v1 engine per trial).
    """
    trials = max(100, min(trials, 20_000))
    rng = np.random.default_rng(seed)
    mean = return_mean if return_mean is not None else inputs.annual_return_post_retirement
    std = return_std if return_std is not None else inputs.monte_carlo_return_std

    endings: list[float] = []
    successes = 0

    for _ in range(trials):
        trial_inputs = RetirementInputs(**{**inputs.__dict__})
        # Override returns per year via single post-ret rate draw each year in loop — approximate:
        # run projection with random post-ret return (one draw per trial for simplicity)
        draw = float(rng.normal(mean, std))
        draw = max(-0.35, min(0.35, draw))
        trial_inputs.annual_return_post_retirement = draw
        df = run_projection(trial_inputs)
        end_bal = float(df["balance_total"].iloc[-1])
        shortfall = float(df["cumulative_shortfall"].iloc[-1])
        endings.append(end_bal)
        if shortfall <= 1.0:
            successes += 1

    arr = np.array(endings)
    return MonteCarloResult(
        trials=trials,
        success_rate=successes / trials,
        median_ending_balance=float(np.median(arr)),
        p10_ending_balance=float(np.percentile(arr, 10)),
        p90_ending_balance=float(np.percentile(arr, 90)),
        ending_balances=arr,
    )
