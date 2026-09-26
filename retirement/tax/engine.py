from __future__ import annotations

from dataclasses import dataclass

from retirement.tax.federal import federal_ltcg_tax, federal_ordinary_tax, taxable_ordinary_after_standard
from retirement.tax.irmaa import irmaa_annual_surcharge
from retirement.tax.social_security_tax import taxable_social_security
from retirement.tax.state import state_income_tax


@dataclass
class TaxBreakdown:
    taxable_ss: float
    ordinary_income: float
    ltcg_income: float
    roth_taxable_withdrawal: float
    federal_ordinary: float
    federal_ltcg: float
    state_tax: float
    irmaa_surcharge: float
    total_tax: float
    magi: float
    after_tax_cash: float

    @property
    def federal_total(self) -> float:
        return self.federal_ordinary + self.federal_ltcg


def compute_year_taxes(
    *,
    filing_status: str,
    state_code: str,
    state_custom_rate: float,
    age: int,
    medicare_age: int,
    ss_benefits: float,
    pension: float,
    withdrawal_traditional: float,
    withdrawal_taxable: float,
    taxable_account_cost_basis_ratio: float,
    roth_taxable_withdrawal: float,
    roth_conversion_income: float,
    roth_qualified_withdrawal: float = 0.0,
    other_ordinary_income: float = 0.0,
) -> TaxBreakdown:
    """
    Compute annual taxes on retirement cash flows (simplified; not audit-grade).
    taxable_account_cost_basis_ratio: fraction of taxable withdrawal that is return of basis (not LTCG).
    roth_taxable_withdrawal: portion of Roth distribution subject to ordinary tax (pre-tax employer $).
    """
    filing = filing_status.lower()
    if filing not in ("single", "mfj"):
        filing = "single"

    basis_ratio = min(1.0, max(0.0, taxable_account_cost_basis_ratio))
    gain_portion = 1.0 - basis_ratio
    ltcg = max(0.0, withdrawal_taxable * gain_portion)

    other = pension + withdrawal_traditional + roth_conversion_income + roth_taxable_withdrawal + other_ordinary_income
    taxable_ss = taxable_social_security(ss_benefits, other, 0.0, filing)
    ordinary = other + taxable_ss

    ordinary_after_std = taxable_ordinary_after_standard(ordinary, filing)
    fed_ord = federal_ordinary_tax(ordinary_after_std, filing)
    fed_ltcg = federal_ltcg_tax(ltcg, ordinary_after_std, filing)

    state_taxable = max(0.0, ordinary_after_std + ltcg)
    st = state_income_tax(state_taxable, state_code, state_custom_rate)

    magi = ordinary + ltcg + ss_benefits  # simplified MAGI for IRMAA
    irmaa = irmaa_annual_surcharge(magi, filing, medicare_age, age)

    total = fed_ord + fed_ltcg + st + irmaa
    after_tax = (
        ss_benefits
        + pension
        + withdrawal_traditional
        + withdrawal_taxable
        + roth_qualified_withdrawal
        + roth_taxable_withdrawal
        - total
    )

    return TaxBreakdown(
        taxable_ss=taxable_ss,
        ordinary_income=ordinary,
        ltcg_income=ltcg,
        roth_taxable_withdrawal=roth_taxable_withdrawal,
        federal_ordinary=fed_ord,
        federal_ltcg=fed_ltcg,
        state_tax=st,
        irmaa_surcharge=irmaa,
        total_tax=total,
        magi=magi,
        after_tax_cash=after_tax,
    )
