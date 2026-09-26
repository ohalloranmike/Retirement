"""Track post-tax vs pre-tax (employer) portions inside a Roth account."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class RothPoolState:
    """Roth balance split: post-tax contributions vs pre-tax employer deposits."""

    posttax_balance: float
    pretax_balance: float

    @property
    def total(self) -> float:
        return self.posttax_balance + self.pretax_balance

    def apply_growth(self, rate: float) -> None:
        g_post = self.posttax_balance * rate
        g_pre = self.pretax_balance * rate
        self.posttax_balance += g_post
        self.pretax_balance += g_pre

    def add_contribution(self, amount: float, to_pretax: bool) -> None:
        if amount <= 0:
            return
        if to_pretax:
            self.pretax_balance += amount
        else:
            self.posttax_balance += amount

    def withdraw(self, amount: float) -> tuple[float, float]:
        """
        Pro-rata withdrawal from pools.
        Returns (qualified_amount, taxable_ordinary_amount from Roth).
        """
        if amount <= 0 or self.total <= 0:
            return 0.0, 0.0
        amount = min(amount, self.total)
        pretax_share = self.pretax_balance / self.total
        from_pretax = amount * pretax_share
        from_posttax = amount - from_pretax
        self.pretax_balance -= from_pretax
        self.posttax_balance -= from_posttax
        return from_posttax, from_pretax

    def convert_in_from_traditional(self, amount: float) -> None:
        """Roth conversion increases post-tax pool (basis) — earnings taxed separately via conversion income."""
        self.posttax_balance += amount
