from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


def save_charts(df: pd.DataFrame, out_dir: Path) -> list[Path]:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []

    ret = df[df["phase"] == "retirement"].copy()
    if ret.empty:
        return paths

    fig, ax = plt.subplots(figsize=(10, 5))
    years = ret["year"]
    ax.bar(years, ret["pension_income"], label="Pension", width=0.8)
    ax.bar(years, ret["ss_income"] + ret["spouse_ss_income"], bottom=ret["pension_income"], label="Social Security", width=0.8)
    bottom = ret["pension_income"] + ret["ss_income"] + ret["spouse_ss_income"]
    ax.bar(years, ret["withdrawal_total"], bottom=bottom, label="Portfolio withdrawals", width=0.8)
    ax.plot(years, ret["spending_need"], color="black", linewidth=2, label="Spending need")
    ax.set_xlabel("Year")
    ax.set_ylabel("Dollars")
    ax.set_title("Retirement income by source vs spending")
    ax.legend()
    fig.tight_layout()
    p1 = out_dir / "income_by_source.png"
    fig.savefig(p1, dpi=120)
    plt.close(fig)
    paths.append(p1)

    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(df["year"], df["balance_total"], label="Total balance")
    ax.axvline(ret["year"].iloc[0], color="gray", linestyle="--", label="Retirement start")
    ax.set_xlabel("Year")
    ax.set_ylabel("Dollars")
    ax.set_title("Portfolio balance over time")
    ax.legend()
    fig.tight_layout()
    p2 = out_dir / "balance_over_time.png"
    fig.savefig(p2, dpi=120)
    plt.close(fig)
    paths.append(p2)

    return paths
