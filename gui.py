#!/usr/bin/env python3
"""Standalone desktop GUI for retirement planning. Run: python gui.py"""

from __future__ import annotations

import tkinter as tk
import webbrowser
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Any

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


class LabeledEntry(ttk.Frame):
    def __init__(self, master: tk.Misc, label: str, width: int = 16, **kwargs: Any) -> None:
        super().__init__(master)
        ttk.Label(self, text=label, anchor="w").grid(row=0, column=0, sticky="nw", padx=(0, 8))
        self.var = tk.StringVar()
        ttk.Entry(self, textvariable=self.var, width=width, **kwargs).grid(row=0, column=1, sticky="ew")
        self.columnconfigure(1, weight=1)

    def set(self, value: str | float | int) -> None:
        self.var.set(str(value))


class RetirementPlannerApp(tk.Tk):
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
        self._withdrawal_var = tk.StringVar(value=list(WITHDRAWAL_LABELS.keys())[0])
        self._theme_name = "dark"
        self._colors: dict[str, str] = {}
        self._scroll_canvas: tk.Canvas | None = None
        self._disclaimer: ttk.Label | None = None

        self._colors = apply_theme(self, self._theme_name)
        self._build_header()
        self._build_menu()
        self._build_toolbar()
        self._build_body()
        self._apply_widget_colors()
        self.load_sample_inputs()

    def _build_header(self) -> None:
        header = ttk.Frame(self, padding=(16, 14, 16, 6))
        header.pack(fill="x")
        ttk.Label(header, text="Retirement Planner", style="Heading.TLabel").pack(anchor="w")
        ttk.Label(
            header,
            text="Model income, balances, and withdrawals — then export or print your reports.",
            style="Muted.TLabel",
        ).pack(anchor="w", pady=(4, 0))

    def set_theme(self, theme: str) -> None:
        self._theme_name = theme
        self._colors = apply_theme(self, theme)
        self._apply_widget_colors()
        if self._disclaimer:
            self._disclaimer.configure(style="Muted.TLabel")
        if self._df is not None and self._inputs is not None:
            self._refresh_charts(self._df)

    def _apply_widget_colors(self) -> None:
        c = self._colors
        self._summary_text.configure(
            bg=c["text_bg"],
            fg=c["text_fg"],
            insertbackground=c["text_insert"],
            relief="flat",
            borderwidth=0,
            highlightthickness=0,
            padx=12,
            pady=12,
        )
        if self._scroll_canvas:
            self._scroll_canvas.configure(bg=c["canvas"])

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
        bar = ttk.Frame(self, padding=(12, 8))
        bar.pack(fill="x")
        ttk.Button(bar, text="Run projection", style="Accent.TButton", command=self.run_projection).pack(
            side="left", padx=(0, 10)
        )
        ttk.Button(bar, text="Export Excel…", command=self.export_excel).pack(side="left", padx=4)
        ttk.Button(bar, text="Export all…", command=self.export_all).pack(side="left", padx=4)
        self._disclaimer = ttk.Label(
            bar,
            text="Educational model only — not investment or tax advice.",
            style="Muted.TLabel",
        )
        self._disclaimer.pack(side="right")

    def _build_body(self) -> None:
        paned = ttk.Panedwindow(self, orient=tk.HORIZONTAL)
        paned.pack(fill="both", expand=True, padx=12, pady=(0, 12))

        inputs_outer = ttk.LabelFrame(paned, text="Assumptions", padding=4, width=440)
        paned.add(inputs_outer, weight=0)

        canvas = tk.Canvas(inputs_outer, highlightthickness=0, borderwidth=0)
        self._scroll_canvas = canvas
        scroll = ttk.Scrollbar(inputs_outer, orient="vertical", command=canvas.yview)
        inputs_frame = ttk.Frame(canvas, padding=(8, 4))
        inputs_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=inputs_frame, anchor="nw", width=400)
        canvas.configure(yscrollcommand=scroll.set)
        canvas.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")

        def _on_mousewheel(event: tk.Event) -> None:
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        inputs_frame.bind("<Enter>", lambda _: canvas.bind_all("<MouseWheel>", _on_mousewheel))
        inputs_frame.bind("<Leave>", lambda _: canvas.unbind_all("<MouseWheel>"))

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
        ira_row = ttk.Frame(inputs_frame)
        ira_row.pack(fill="x", pady=(0, 8))
        ttk.Checkbutton(ira_row, text="IRA contributions go to Roth", variable=self._ira_roth_var).pack(anchor="w")

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
        wo_frame = ttk.LabelFrame(inputs_frame, text="Withdrawal order", padding=10)
        wo_frame.pack(fill="x", pady=(0, 12))
        ttk.Combobox(
            wo_frame,
            textvariable=self._withdrawal_var,
            values=list(WITHDRAWAL_LABELS.keys()),
            state="readonly",
        ).pack(fill="x")

        results_notebook = ttk.Notebook(paned, padding=4)
        paned.add(results_notebook, weight=1)

        summary_frame = ttk.Frame(results_notebook, padding=4)
        results_notebook.add(summary_frame, text="  Summary  ")
        self._summary_text = tk.Text(summary_frame, wrap="word", font=FONT_MONO)
        self._summary_text.pack(fill="both", expand=True)

        table_frame = ttk.Frame(results_notebook)
        results_notebook.add(table_frame, text="  Year-by-year  ")
        self._tree = ttk.Treeview(table_frame, show="headings")
        vsb = ttk.Scrollbar(table_frame, orient="vertical", command=self._tree.yview)
        hsb = ttk.Scrollbar(table_frame, orient="horizontal", command=self._tree.xview)
        self._tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        self._tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        table_frame.rowconfigure(0, weight=1)
        table_frame.columnconfigure(0, weight=1)

        self._charts_frame = ttk.Frame(results_notebook)
        results_notebook.add(self._charts_frame, text="  Charts  ")

    def _add_section(self, parent: ttk.Frame, title: str, rows: list[tuple[str, str]]) -> None:
        frame = ttk.LabelFrame(parent, text=title, padding=10)
        frame.pack(fill="x", pady=(0, 10))
        for key, label in rows:
            entry = LabeledEntry(frame, label)
            entry.pack(fill="x", pady=2)
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
        for label, enum in WITHDRAWAL_LABELS.items():
            if enum == sample.withdrawal_order:
                self._withdrawal_var.set(label)
                break

    def collect_inputs(self) -> RetirementInputs:
        wo = WITHDRAWAL_LABELS.get(self._withdrawal_var.get(), WithdrawalOrder.TAXABLE_TRADITIONAL_ROTH)
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
        messagebox.showinfo("Projection complete", f"Calculated {len(df)} years. Use File → Export to save reports.")

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
        self._summary_text.delete("1.0", tk.END)
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


def main() -> None:
    require_project_venv()
    app = RetirementPlannerApp()
    app.mainloop()


if __name__ == "__main__":
    main()
