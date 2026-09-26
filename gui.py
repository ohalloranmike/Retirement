#!/usr/bin/env python3
"""Standalone desktop GUI for retirement planning. Run: python gui.py"""

from __future__ import annotations

from bootstrap_venv import relaunch_with_project_venv

relaunch_with_project_venv(__file__)

import sys
import webbrowser

try:
    import tkinter as tk
except ImportError:
    sys.stderr.write(
        "Tkinter is not available for this Python.\n"
        "On Linux Mint / Ubuntu, install it with:\n"
        "  sudo apt install python3-tk\n"
        "Then recreate or reuse .venv and run:  ./run-gui.sh\n"
    )
    raise SystemExit(1) from None
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Any

import customtkinter as ctk

import matplotlib

matplotlib.use("TkAgg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg  # noqa: E402

import pandas as pd

from retirement.charts import balance_chart_figure, income_chart_figure
from retirement.gui_theme import FONT_MONO, apply_theme
from retirement.venv_guard import require_project_venv
from retirement.models import RetirementInputs, WithdrawalOrder
from retirement.projection import default_sample_inputs, run_projection
from retirement.report import (
    build_html_report,
    export_report_bundle,
    report_dataframe,
    save_excel,
    summarize_projection,
)

WITHDRAWAL_LABELS: dict[str, WithdrawalOrder] = {
    "Taxable, then traditional, then Roth": WithdrawalOrder.TAXABLE_TRADITIONAL_ROTH,
    "Traditional, then taxable, then Roth": WithdrawalOrder.TRADITIONAL_TAXABLE_ROTH,
    "Proportional across accounts": WithdrawalOrder.PROPORTIONAL,
}


def _parse_float(text: str, field: str) -> float:
    raw = text.strip().replace(",", "").replace("$", "")
    if not raw:
        return 0.0
    try:
        return float(raw)
    except ValueError:
        raise ValueError(f"{field} must be a number.") from None


def _parse_int(text: str, field: str) -> int:
    raw = text.strip().replace(",", "")
    if not raw:
        raise ValueError(f"{field} is required.")
    try:
        return int(float(raw))
    except ValueError:
        raise ValueError(f"{field} must be a whole number.") from None


class LabeledEntry(ctk.CTkFrame):
    def __init__(self, master: tk.Misc, label: str, **kwargs: Any) -> None:
        super().__init__(master, fg_color="transparent", **kwargs)
        self.var = tk.StringVar()
        ctk.CTkLabel(self, text=label, anchor="w", font=ctk.CTkFont(size=12)).pack(fill="x", pady=(0, 1))
        ctk.CTkEntry(
            self,
            textvariable=self.var,
            height=28,
            corner_radius=8,
            border_width=1,
        ).pack(fill="x", pady=(0, 2))

    def set(self, value: str | float | int) -> None:
        self.var.set(str(value))


class RetirementPlannerApp(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Retirement Planner")
        self.minsize(960, 640)
        self.geometry("1100x720")

        self._df: pd.DataFrame | None = None
        self._inputs: RetirementInputs | None = None
        self._chart_canvases: list[FigureCanvasTkAgg] = []

        self._fields: dict[str, LabeledEntry] = {}
        self._ira_roth_var = tk.BooleanVar(value=True)
        self._use_tax_var = tk.BooleanVar(value=False)
        self._emp_roth_var = tk.BooleanVar(value=False)
        self._match_roth_var = tk.BooleanVar(value=False)
        self._theme_name = "light"
        self._colors: dict[str, str] = {}
        self._disclaimer: ctk.CTkLabel | None = None
        self._withdrawal_combo: ctk.CTkComboBox | None = None
        self._filing_combo: ctk.CTkComboBox | None = None

        ctk.set_appearance_mode("light")
        ctk.set_default_color_theme("blue")
        self._colors = apply_theme(self, self._theme_name)
        self._build_header()
        self._build_menu()
        self._build_toolbar()
        self._build_body()
        self._apply_widget_colors()
        self.load_sample_inputs()

    def _build_header(self) -> None:
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=16, pady=(14, 6))
        ctk.CTkLabel(
            header,
            text="Retirement Planner",
            font=ctk.CTkFont(size=22, weight="bold"),
            anchor="w",
        ).pack(anchor="w")
        ctk.CTkLabel(
            header,
            text="Model income, balances, and withdrawals — then export or print your reports.",
            font=ctk.CTkFont(size=12),
            text_color=("#5c6370", "#9aa0a6"),
            anchor="w",
        ).pack(anchor="w", pady=(4, 0))

    def set_theme(self, theme: str) -> None:
        self._theme_name = theme
        self._colors = apply_theme(self, theme)
        self._apply_widget_colors()
        if self._disclaimer:
            self._disclaimer.configure(text_color=("#5c6370", "#9aa0a6"))
        if self._df is not None and self._inputs is not None:
            self._refresh_charts(self._df)

    def _apply_widget_colors(self) -> None:
        pass

    def _build_menu(self) -> None:
        menubar = tk.Menu(self)
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="Load sample values", command=self.load_sample_inputs)
        file_menu.add_separator()
        file_menu.add_command(label="Export Excel workbook…", command=self.export_excel)
        file_menu.add_command(label="Export CSV…", command=self.export_csv)
        file_menu.add_command(label="Export HTML report…", command=self.export_html)
        file_menu.add_command(label="Export chart images…", command=self.export_charts)
        file_menu.add_separator()
        file_menu.add_command(label="Export all reports to folder…", command=self.export_all)
        file_menu.add_command(label="Open HTML report in browser (print / PDF)", command=self.open_html_for_print)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.destroy)
        menubar.add_cascade(label="File", menu=file_menu)

        run_menu = tk.Menu(menubar, tearoff=0)
        run_menu.add_command(label="Run projection", command=self.run_projection)
        menubar.add_cascade(label="Run", menu=run_menu)

        view_menu = tk.Menu(menubar, tearoff=0)
        view_menu.add_command(label="Dark theme", command=lambda: self.set_theme("dark"))
        view_menu.add_command(label="Light theme", command=lambda: self.set_theme("light"))
        menubar.add_cascade(label="View", menu=view_menu)

        self.config(menu=menubar)

    def _build_toolbar(self) -> None:
        bar = ctk.CTkFrame(self, fg_color="transparent")
        bar.pack(fill="x", padx=12, pady=8)
        ctk.CTkButton(
            bar,
            text="Run projection",
            command=self.run_projection,
            height=36,
            corner_radius=10,
            font=ctk.CTkFont(size=13, weight="bold"),
        ).pack(side="left", padx=(0, 10))
        ctk.CTkButton(
            bar, text="Export Excel…", command=self.export_excel, height=34, corner_radius=10, fg_color="transparent", border_width=1
        ).pack(side="left", padx=4)
        ctk.CTkButton(
            bar, text="Export all…", command=self.export_all, height=34, corner_radius=10, fg_color="transparent", border_width=1
        ).pack(side="left", padx=4)
        self._disclaimer = ctk.CTkLabel(
            bar,
            text="Educational model only — not investment or tax advice.",
            font=ctk.CTkFont(size=11),
            text_color=("#5c6370", "#9aa0a6"),
        )
        self._disclaimer.pack(side="right")

    def _build_body(self) -> None:
        paned = ttk.Panedwindow(self, orient=tk.HORIZONTAL)
        paned.pack(fill="both", expand=True, padx=12, pady=(0, 12))

        inputs_outer = ctk.CTkFrame(paned, width=440, corner_radius=12)
        paned.add(inputs_outer, weight=0)
        inputs_frame = ctk.CTkScrollableFrame(
            inputs_outer,
            label_text="Assumptions",
            corner_radius=12,
            label_font=ctk.CTkFont(size=13, weight="bold"),
        )
        inputs_frame.pack(fill="both", expand=True, padx=4, pady=4)

        self._add_section(inputs_frame, "Timeline", [
            ("birth_year", "Birth year"),
            ("planning_start_year", "Planning start year"),
            ("retirement_age", "Retirement age"),
            ("life_expectancy_age", "Life expectancy (age)"),
        ])
        self._add_section(inputs_frame, "Account balances ($)", [
            ("balance_401k", "401(k) / 403(b)"),
            ("balance_traditional_ira", "Traditional IRA"),
            ("balance_roth_ira", "Roth IRA"),
            ("balance_taxable", "Taxable investments"),
        ])
        self._add_section(inputs_frame, "Saving (pre-retirement)", [
            ("annual_salary", "Annual salary"),
            ("employee_401k_contribution", "Your 401(k) deferral / year"),
            ("employer_match_rate", "Employer match rate (0–1)"),
            ("employer_match_up_to_pct_of_salary", "Match on first fraction of salary"),
            ("annual_ira_contribution", "IRA contribution / year"),
        ])
        ctk.CTkCheckBox(
            inputs_frame,
            text="IRA contributions go to Roth",
            variable=self._ira_roth_var,
            corner_radius=6,
            font=ctk.CTkFont(size=12),
        ).pack(anchor="w", pady=(0, 4), padx=4)

        self._add_section(inputs_frame, "Returns (annual, as decimal)", [
            ("annual_return_pre_retirement", "Before retirement"),
            ("annual_return_post_retirement", "In retirement"),
        ])
        self._add_section(inputs_frame, "Pension", [
            ("pension_monthly_at_start", "Monthly benefit at start"),
            ("pension_start_age", "Start age"),
            ("pension_cola_pct", "COLA (0–1)"),
        ])
        self._add_section(inputs_frame, "Social Security", [
            ("ss_monthly_at_fra", "Your monthly at full retirement age"),
            ("ss_fra_age", "Your full retirement age"),
            ("ss_claim_age", "Your claim age (62–70)"),
            ("ss_cola_pct", "Your SS COLA (0–1)"),
            ("spouse_ss_monthly_at_fra", "Spouse monthly at FRA"),
            ("spouse_ss_claim_age", "Spouse claim age"),
        ])
        self._add_section(inputs_frame, "Spending", [
            ("annual_spending_goal_today", "Annual spending (today's dollars)"),
            ("inflation_pct", "Inflation (0–1)"),
        ])
        wo_frame = ctk.CTkFrame(inputs_frame, corner_radius=12)
        wo_frame.pack(fill="x", pady=(0, 6), padx=4)
        ctk.CTkLabel(wo_frame, text="Withdrawal order", font=ctk.CTkFont(size=13, weight="bold")).pack(
            anchor="w", padx=12, pady=(8, 2)
        )
        self._withdrawal_combo = ctk.CTkComboBox(
            wo_frame,
            values=list(WITHDRAWAL_LABELS.keys()),
            state="readonly",
            height=28,
            corner_radius=8,
            dropdown_hover_color=("#dbeafe", "#1e3a5f"),
        )
        self._withdrawal_combo.pack(fill="x", padx=12, pady=(0, 8))
        self._withdrawal_combo.set(list(WITHDRAWAL_LABELS.keys())[0])

        adv = ctk.CTkFrame(inputs_frame, corner_radius=12)
        adv.pack(fill="x", pady=(0, 6), padx=4)
        ctk.CTkLabel(
            adv,
            text="Advanced (v2): tax, Roth pools, conversions",
            font=ctk.CTkFont(size=13, weight="bold"),
        ).pack(anchor="w", padx=12, pady=(8, 2))
        inner_adv = ctk.CTkFrame(adv, fg_color="transparent")
        inner_adv.pack(fill="x", padx=8, pady=(0, 6))
        ctk.CTkCheckBox(
            inner_adv,
            text="Model federal / state tax, IRMAA (after-tax spending)",
            variable=self._use_tax_var,
            font=ctk.CTkFont(size=12),
        ).pack(anchor="w", pady=0)
        ctk.CTkCheckBox(
            inner_adv,
            text="Employee 401(k) deferrals → Roth (post-tax pool)",
            variable=self._emp_roth_var,
            font=ctk.CTkFont(size=12),
        ).pack(anchor="w", pady=0)
        ctk.CTkCheckBox(
            inner_adv,
            text="Employer match → Roth (pre-tax pool)",
            variable=self._match_roth_var,
            font=ctk.CTkFont(size=12),
        ).pack(anchor="w", pady=0)
        fil = ctk.CTkFrame(inner_adv, fg_color="transparent")
        fil.pack(fill="x", pady=(2, 0))
        ctk.CTkLabel(fil, text="Filing status", font=ctk.CTkFont(size=12)).pack(side="left")
        self._filing_combo = ctk.CTkComboBox(
            fil,
            values=["single", "mfj"],
            state="readonly",
            width=120,
            height=28,
            corner_radius=8,
        )
        self._filing_combo.pack(side="left", padx=8)
        self._filing_combo.set("single")
        for key, label in [
            ("state_code", "State code (e.g. OR, none, custom)"),
            ("state_custom_tax_rate", "Custom state rate (if state=custom)"),
            ("taxable_cost_basis_ratio", "Taxable acct cost basis ratio (0–1)"),
            ("roth_posttax_opening_balance", "Roth post-tax $ before employer match"),
            ("roth_conversion_annual", "Roth conversion $ / year"),
            ("roth_conversion_start_age", "Conversion start age (0=off)"),
            ("roth_conversion_end_age", "Conversion end age"),
            ("run_monte_carlo_trials", "Monte Carlo trials (0=skip)"),
        ]:
            entry = LabeledEntry(inner_adv, label)
            entry.pack(fill="x", pady=0)
            self._fields[key] = entry

        results_outer = ctk.CTkFrame(paned, corner_radius=12, fg_color="transparent")
        paned.add(results_outer, weight=1)
        self._tabview = ctk.CTkTabview(results_outer, corner_radius=12)
        self._tabview.pack(fill="both", expand=True)

        summary_tab = self._tabview.add("Summary")
        self._summary_text = ctk.CTkTextbox(summary_tab, font=ctk.CTkFont(family=FONT_MONO[0], size=11), corner_radius=10)
        self._summary_text.pack(fill="both", expand=True, padx=8, pady=8)

        table_tab = self._tabview.add("Year-by-year")
        table_frame = ctk.CTkFrame(table_tab, fg_color="transparent")
        table_frame.pack(fill="both", expand=True, padx=4, pady=4)
        self._tree = ttk.Treeview(table_frame, show="headings")
        vsb = ttk.Scrollbar(table_frame, orient="vertical", command=self._tree.yview)
        hsb = ttk.Scrollbar(table_frame, orient="horizontal", command=self._tree.xview)
        self._tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        self._tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        table_frame.rowconfigure(0, weight=1)
        table_frame.columnconfigure(0, weight=1)

        charts_tab = self._tabview.add("Charts")
        self._charts_frame = ctk.CTkFrame(charts_tab, fg_color="transparent")
        self._charts_frame.pack(fill="both", expand=True)

    def _add_section(self, parent: ctk.CTkScrollableFrame, title: str, rows: list[tuple[str, str]]) -> None:
        frame = ctk.CTkFrame(parent, corner_radius=12)
        frame.pack(fill="x", pady=(0, 6), padx=4)
        ctk.CTkLabel(frame, text=title, font=ctk.CTkFont(size=13, weight="bold")).pack(anchor="w", padx=12, pady=(8, 2))
        inner = ctk.CTkFrame(frame, fg_color="transparent")
        inner.pack(fill="x", padx=8, pady=(0, 6))
        for key, label in rows:
            entry = LabeledEntry(inner, label)
            entry.pack(fill="x", pady=0)
            self._fields[key] = entry

    def load_sample_inputs(self) -> None:
        sample = default_sample_inputs()
        for key, entry in self._fields.items():
            val = getattr(sample, key)
            if isinstance(val, float) and (key.endswith("_pct") or "return" in key or "rate" in key):
                entry.set(val)
            elif isinstance(val, float):
                entry.set(int(val) if val == int(val) else val)
            else:
                entry.set(val)
        self._ira_roth_var.set(sample.ira_is_roth)
        self._use_tax_var.set(sample.use_tax_modeling)
        self._emp_roth_var.set(sample.employee_401k_to_roth)
        self._match_roth_var.set(sample.employer_match_to_roth)
        if self._filing_combo:
            self._filing_combo.set(sample.filing_status)
        if self._withdrawal_combo:
            for label, enum in WITHDRAWAL_LABELS.items():
                if enum == sample.withdrawal_order:
                    self._withdrawal_combo.set(label)
                    break

    def collect_inputs(self) -> RetirementInputs:
        wo_label = self._withdrawal_combo.get() if self._withdrawal_combo else ""
        wo = WITHDRAWAL_LABELS.get(wo_label, WithdrawalOrder.TAXABLE_TRADITIONAL_ROTH)
        return RetirementInputs(
            birth_year=_parse_int(self._fields["birth_year"].var.get(), "Birth year"),
            planning_start_year=_parse_int(self._fields["planning_start_year"].var.get(), "Planning start year"),
            retirement_age=_parse_int(self._fields["retirement_age"].var.get(), "Retirement age"),
            life_expectancy_age=_parse_int(self._fields["life_expectancy_age"].var.get(), "Life expectancy"),
            balance_401k=_parse_float(self._fields["balance_401k"].var.get(), "401(k) balance"),
            balance_traditional_ira=_parse_float(self._fields["balance_traditional_ira"].var.get(), "Traditional IRA"),
            balance_roth_ira=_parse_float(self._fields["balance_roth_ira"].var.get(), "Roth IRA"),
            balance_taxable=_parse_float(self._fields["balance_taxable"].var.get(), "Taxable balance"),
            annual_salary=_parse_float(self._fields["annual_salary"].var.get(), "Salary"),
            employee_401k_contribution=_parse_float(
                self._fields["employee_401k_contribution"].var.get(), "401(k) deferral"
            ),
            employer_match_rate=_parse_float(self._fields["employer_match_rate"].var.get(), "Employer match rate"),
            employer_match_up_to_pct_of_salary=_parse_float(
                self._fields["employer_match_up_to_pct_of_salary"].var.get(), "Match salary cap"
            ),
            annual_ira_contribution=_parse_float(self._fields["annual_ira_contribution"].var.get(), "IRA contribution"),
            ira_is_roth=self._ira_roth_var.get(),
            annual_return_pre_retirement=_parse_float(
                self._fields["annual_return_pre_retirement"].var.get(), "Pre-retirement return"
            ),
            annual_return_post_retirement=_parse_float(
                self._fields["annual_return_post_retirement"].var.get(), "Retirement return"
            ),
            pension_monthly_at_start=_parse_float(self._fields["pension_monthly_at_start"].var.get(), "Pension"),
            pension_start_age=_parse_int(self._fields["pension_start_age"].var.get(), "Pension start age"),
            pension_cola_pct=_parse_float(self._fields["pension_cola_pct"].var.get(), "Pension COLA"),
            ss_monthly_at_fra=_parse_float(self._fields["ss_monthly_at_fra"].var.get(), "SS at FRA"),
            ss_fra_age=_parse_int(self._fields["ss_fra_age"].var.get(), "SS FRA age"),
            ss_claim_age=_parse_int(self._fields["ss_claim_age"].var.get(), "SS claim age"),
            ss_cola_pct=_parse_float(self._fields["ss_cola_pct"].var.get(), "SS COLA"),
            spouse_ss_monthly_at_fra=_parse_float(
                self._fields["spouse_ss_monthly_at_fra"].var.get(), "Spouse SS"
            ),
            spouse_ss_claim_age=_parse_int(self._fields["spouse_ss_claim_age"].var.get(), "Spouse claim age"),
            annual_spending_goal_today=_parse_float(
                self._fields["annual_spending_goal_today"].var.get(), "Spending goal"
            ),
            inflation_pct=_parse_float(self._fields["inflation_pct"].var.get(), "Inflation"),
            withdrawal_order=wo,
            use_tax_modeling=self._use_tax_var.get(),
            filing_status=self._filing_combo.get() if self._filing_combo else "single",
            state_code=self._fields["state_code"].var.get().strip() or "none",
            state_custom_tax_rate=_parse_float(
                self._fields["state_custom_tax_rate"].var.get(), "State tax rate"
            ),
            taxable_cost_basis_ratio=_parse_float(
                self._fields["taxable_cost_basis_ratio"].var.get(), "Cost basis ratio"
            ),
            roth_posttax_opening_balance=_parse_float(
                self._fields["roth_posttax_opening_balance"].var.get(), "Roth post-tax opening"
            ),
            employee_401k_to_roth=self._emp_roth_var.get(),
            employer_match_to_roth=self._match_roth_var.get(),
            roth_conversion_annual=_parse_float(self._fields["roth_conversion_annual"].var.get(), "Conversion amount"),
            roth_conversion_start_age=_parse_int(
                self._fields["roth_conversion_start_age"].var.get(), "Conversion start age"
            ),
            roth_conversion_end_age=_parse_int(
                self._fields["roth_conversion_end_age"].var.get(), "Conversion end age"
            ),
            run_monte_carlo_trials=_parse_int(
                self._fields["run_monte_carlo_trials"].var.get(), "Monte Carlo trials"
            ),
        )

    def run_projection(self) -> None:
        try:
            inputs = self.collect_inputs()
            df = run_projection(inputs)
        except ValueError as exc:
            messagebox.showerror("Invalid input", str(exc))
            return

        self._inputs = inputs
        self._df = df
        self._refresh_summary(df, inputs)
        self._refresh_table(df)
        self._refresh_charts(df)
        msg = f"Calculated {len(df)} years. Use File → Export to save reports."
        if inputs.run_monte_carlo_trials > 0:
            from retirement.monte_carlo import run_monte_carlo

            mc = run_monte_carlo(inputs, trials=inputs.run_monte_carlo_trials)
            msg += f"\n\nMonte Carlo ({mc.trials} runs): {mc.success_rate:.1%} success, median ending ${mc.median_ending_balance:,.0f}."
        messagebox.showinfo("Projection complete", msg)

    def _require_results(self) -> tuple[pd.DataFrame, RetirementInputs] | None:
        if self._df is None or self._inputs is None:
            messagebox.showwarning("No projection", "Run a projection first (Run → Run projection).")
            return None
        return self._df, self._inputs

    def _refresh_summary(self, df: pd.DataFrame, inputs: RetirementInputs) -> None:
        s = summarize_projection(df, inputs)
        lines = [
            "RETIREMENT PROJECTION SUMMARY",
            "",
            f"Plan horizon: {s['plan_start_year']} – {s['plan_end_year']} (ages {s['start_age']} – {s['end_age']})",
            f"Balance at retirement: ${s['balance_at_retirement']:,.0f}" if s["balance_at_retirement"] else "",
            f"Ending total balance: ${s['ending_balance']:,.0f}",
            f"Cumulative shortfall (retirement years): ${s['cumulative_shortfall']:,.0f}",
            "",
        ]
        if s["first_shortfall"]:
            fs = s["first_shortfall"]
            lines.append(f"WARNING: Shortfall begins in {fs['year']} (age {fs['age']}).")
        else:
            lines.append("No spending shortfalls in retirement years for this scenario.")
        lines.extend(["", "Use File menu to export Excel, CSV, HTML, charts, or everything at once."])
        self._summary_text.delete("1.0", "end")
        self._summary_text.insert("1.0", "\n".join(lines))

    def _refresh_table(self, df: pd.DataFrame) -> None:
        table = report_dataframe(df)
        self._tree.delete(*self._tree.get_children())
        cols = list(table.columns)
        self._tree["columns"] = cols
        for col in cols:
            self._tree.heading(col, text=col)
            self._tree.column(col, width=100, anchor="e" if col not in ("Year", "Age", "Phase") else "w")
        money_cols = {c for c in cols if c not in ("Year", "Age", "Phase")}
        for _, row in table.iterrows():
            values = []
            for col in cols:
                val = row[col]
                if col in money_cols and pd.notna(val):
                    values.append(f"${float(val):,.0f}")
                else:
                    values.append(val)
            self._tree.insert("", tk.END, values=values)

    def _matplotlib_style(self) -> None:
        style = self._colors.get("mpl_style", "default")
        try:
            plt.style.use(style)
        except OSError:
            plt.style.use("dark_background" if self._theme_name == "dark" else "default")

    def _refresh_charts(self, df: pd.DataFrame) -> None:
        for child in self._charts_frame.winfo_children():
            child.destroy()
        self._chart_canvases.clear()
        self._matplotlib_style()

        for row, maker in enumerate((income_chart_figure, balance_chart_figure)):
            fig = maker(df)
            if not fig:
                continue
            canvas = FigureCanvasTkAgg(fig, master=self._charts_frame)
            canvas.draw()
            widget = canvas.get_tk_widget()
            widget.pack(fill="both", expand=True, pady=8)
            self._chart_canvases.append(canvas)

    def export_excel(self) -> None:
        pair = self._require_results()
        if not pair:
            return
        _, inputs = pair
        path = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel workbook", "*.xlsx")],
            initialfile="retirement_planner.xlsx",
        )
        if not path:
            return
        try:
            save_excel(Path(path), inputs)
            messagebox.showinfo("Saved", f"Excel workbook saved:\n{path}")
        except OSError as exc:
            messagebox.showerror("Save failed", str(exc))

    def export_csv(self) -> None:
        pair = self._require_results()
        if not pair:
            return
        df, _ = pair
        path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV", "*.csv")],
            initialfile="retirement_projection.csv",
        )
        if not path:
            return
        report_dataframe(df).to_csv(path, index=False)
        messagebox.showinfo("Saved", f"CSV saved:\n{path}")

    def export_html(self) -> None:
        pair = self._require_results()
        if not pair:
            return
        df, inputs = pair
        path = filedialog.asksaveasfilename(
            defaultextension=".html",
            filetypes=[("HTML report", "*.html")],
            initialfile="retirement_report.html",
        )
        if not path:
            return
        Path(path).write_text(build_html_report(df, inputs), encoding="utf-8")
        messagebox.showinfo("Saved", f"HTML report saved:\n{path}")

    def export_charts(self) -> None:
        pair = self._require_results()
        if not pair:
            return
        df, _ = pair
        folder = filedialog.askdirectory(title="Choose folder for chart images")
        if not folder:
            return
        from retirement.charts import save_charts

        paths = save_charts(df, Path(folder))
        if paths:
            messagebox.showinfo("Saved", "Charts saved:\n" + "\n".join(str(p) for p in paths))
        else:
            messagebox.showinfo("Charts", "No retirement years to chart.")

    def export_all(self) -> None:
        pair = self._require_results()
        if not pair:
            return
        df, inputs = pair
        folder = filedialog.askdirectory(title="Choose folder for all reports")
        if not folder:
            return
        try:
            paths = export_report_bundle(Path(folder), df, inputs)
            messagebox.showinfo("Saved", f"Wrote {len(paths)} files to:\n{folder}")
        except OSError as exc:
            messagebox.showerror("Export failed", str(exc))

    def open_html_for_print(self) -> None:
        pair = self._require_results()
        if not pair:
            return
        df, inputs = pair
        import tempfile

        tmp = Path(tempfile.gettempdir()) / "retirement_report_preview.html"
        tmp.write_text(build_html_report(df, inputs), encoding="utf-8")
        webbrowser.open(tmp.as_uri())
        messagebox.showinfo(
            "Print / PDF",
            "The report opened in your browser.\nUse Print (Ctrl+P) or Save as PDF from the browser menu.",
        )


def _check_desktop_session() -> None:
    import os

    if sys.platform == "win32":
        return
    if os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"):
        return
    sys.stderr.write(
        "No graphical display detected (DISPLAY / WAYLAND_DISPLAY not set).\n"
        "Run the GUI from a desktop terminal, not over plain SSH without X forwarding.\n"
        "For a browser UI on Linux, use:  ./run-streamlit.sh\n"
    )
    raise SystemExit(1)


def main() -> None:
    require_project_venv()
    _check_desktop_session()
    try:
        app = RetirementPlannerApp()
        app.mainloop()
    except tk.TclError as exc:
        sys.stderr.write(
            f"Tkinter could not start the window: {exc}\n\n"
            "On Linux Mint, try:\n"
            "  sudo apt install python3-tk\n"
            "If you use Wayland and the window still fails, try:\n"
            "  GDK_BACKEND=x11 ./run-gui.sh\n"
        )
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
