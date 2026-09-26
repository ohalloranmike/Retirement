#!/usr/bin/env python3
"""CLI for retirement cash-flow projection and Excel workbook."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from retirement.excel_export import create_workbook, refresh_projection_in_workbook
from retirement.models import RetirementInputs
from retirement.projection import default_sample_inputs, inputs_from_dict, run_projection
from retirement.venv_guard import require_project_venv


def main(argv: list[str] | None = None) -> int:
    require_project_venv()
    parser = argparse.ArgumentParser(description="Retirement income & balance planner (v1)")
    parser.add_argument(
        "--excel",
        type=Path,
        help="Path to .xlsx workbook (create with --init, refresh with --refresh)",
    )
    parser.add_argument("--init", action="store_true", help="Create a new Excel workbook with sample inputs")
    parser.add_argument("--refresh", action="store_true", help="Re-run projection from Inputs sheet into workbook")
    parser.add_argument("--config", type=Path, help="JSON file with RetirementInputs fields")
    parser.add_argument("--csv", type=Path, help="Write projection CSV to this path")
    parser.add_argument("--charts", type=Path, help="Directory to write PNG charts")
    parser.add_argument("--summary", action="store_true", help="Print end-of-plan summary to stdout")
    parser.add_argument(
        "--monte-carlo",
        action="store_true",
        help="Run Monte Carlo using run_monte_carlo_trials from config (or 1000 default)",
    )
    args = parser.parse_args(argv)

    root = Path(__file__).resolve().parent
    default_xlsx = root / "retirement_planner.xlsx"

    if args.init:
        excel_path = args.excel or default_xlsx
        inputs = default_sample_inputs()
        if args.config:
            inputs = inputs_from_dict(json.loads(args.config.read_text(encoding="utf-8")))
        create_workbook(excel_path, inputs)
        print(f"Created workbook: {excel_path}")
        return 0

    if args.refresh and args.excel:
        df = refresh_projection_in_workbook(args.excel)
        print(f"Updated projection in {args.excel} ({len(df)} years)")
        if args.summary:
            _print_summary(df)
        return 0

    inputs: RetirementInputs | None = None
    if args.excel and args.excel.exists():
        df = refresh_projection_in_workbook(args.excel)
        print(f"Using inputs from {args.excel}")
    elif args.config:
        inputs = inputs_from_dict(json.loads(args.config.read_text(encoding="utf-8")))
        df = run_projection(inputs)
    else:
        inputs = default_sample_inputs()
        df = run_projection(inputs)
        if not args.excel:
            create_workbook(default_xlsx, inputs)
            print(f"Wrote sample workbook: {default_xlsx}")

    if args.csv:
        df.to_csv(args.csv, index=False)
        print(f"Wrote CSV: {args.csv}")

    if args.charts:
        from retirement.charts import save_charts

        paths = save_charts(df, args.charts)
        for p in paths:
            print(f"Wrote chart: {p}")

    if args.summary or (not args.csv and not args.charts):
        _print_summary(df)

    if args.monte_carlo:
        from retirement.monte_carlo import run_monte_carlo

        if inputs is None:
            inputs = default_sample_inputs()
        trials = inputs.run_monte_carlo_trials if inputs.run_monte_carlo_trials > 0 else 0
        if trials <= 0:
            trials = 1000
        mc = run_monte_carlo(inputs, trials=trials)
        print(f"\nMonte Carlo ({mc.trials} trials): success {mc.success_rate:.1%}")
        print(f"Ending balance median ${mc.median_ending_balance:,.0f} (p10 ${mc.p10_ending_balance:,.0f}, p90 ${mc.p90_ending_balance:,.0f})")

    return 0


def _print_summary(df) -> None:
    last = df.iloc[-1]
    ret = df[df["phase"] == "retirement"]
    broke = ret[ret["surplus_or_shortfall"] < -1]
    print("\n--- Summary ---")
    print(f"Plan years: {int(df['year'].iloc[0])} – {int(df['year'].iloc[-1])} (age {int(df['age'].iloc[0])} – {int(last['age'])})")
    print(f"Ending total balance: ${last['balance_total']:,.0f}")
    print(f"Cumulative shortfall (retirement): ${last['cumulative_shortfall']:,.0f}")
    if len(broke):
        print(f"First shortfall year: {int(broke.iloc[0]['year'])} (age {int(broke.iloc[0]['age'])})")
    else:
        print("No spending shortfalls in projection.")
    print("---\n")


if __name__ == "__main__":
    sys.exit(main())
