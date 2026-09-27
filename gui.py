#!/usr/bin/env python3
"""Standalone desktop GUI for retirement planning. Run: python gui.py"""

from __future__ import annotations

import tkinter as tk
import webbrowser
from pathlib import Path
from tkinter import filedialog, font as tkfont, messagebox, ttk
from typing import Any

import customtkinter as ctk

import matplotlib

matplotlib.use("TkAgg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg  # noqa: E402

import pandas as pd

from retirement.charts import balance_chart_figure, income_chart_figure
from retirement.gui_prefs import get_sidebar_sash_fraction, set_sidebar_sash_fraction
from retirement.gui_theme import FONT_CTK_SIZE, FONT_FAMILY, FONT_MENU_MIN_PT, FONT_TABLE_DISPLAY, apply_theme
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

def _ui_font(weight: str = "normal") -> ctk.CTkFont:
    return ctk.CTkFont(size=FONT_CTK_SIZE, weight=weight)


# CTkScrollableFrame defaults to width=200; inner content must match a real sidebar width.
_SIDEBAR_SCROLL_WIDTH = 440
_SIDEBAR_WRAP = 400
# CTk radio/checkbox default width=100; long labels need explicit width (within sidebar).
_SIDEBAR_OPTION_WIDTH = 390
_SIDEBAR_PANE_MINSIZE = 420
_RESULTS_PANE_MINSIZE = 360


def _format_yearly_table_parts(df: pd.DataFrame) -> tuple[str, str]:
    table = report_dataframe(df)
    money_cols = {c for c in table.columns if c not in ("Year", "Age", "Phase")}
    fixed_lines = [f"{'Year':>6}  {'Age':>4}"]
    for _, row in table.iterrows():
        year = row["Year"] if "Year" in row else ""
        age = row["Age"] if "Age" in row else ""
        fixed_lines.append(f"{year!s:>6}  {age!s:>4}")
    scroll_cols = [c for c in table.columns if c not in ("Year", "Age")]
    scroll = table[scroll_cols].copy()
    for col in scroll.columns:
        if col in money_cols:
            scroll[col] = scroll[col].map(lambda v: f"${float(v):,.0f}" if pd.notna(v) else "")
    scroll_text = scroll.to_string(index=False, col_space=12)
    return "\n".join(fixed_lines), scroll_text


_TOOLBAR_SECONDARY_BTN: dict[str, Any] = {
    "height": 34,
    "corner_radius": 10,
    "fg_color": ("#e8ecf1", "#343638"),
    "border_width": 1,
    "border_color": ("#8b929a", "#565b61"),
    "text_color": ("#1a1d21", "#f3f4f6"),
    "hover_color": ("#d8dce3", "#404448"),
}

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
        ctk.CTkLabel(
            self,
            text=label,
            anchor="w",
            justify="left",
            wraplength=_SIDEBAR_WRAP,
            font=_ui_font(),
        ).pack(fill="x", pady=(0, 1))
        ctk.CTkEntry(
            self,
            textvariable=self.var,
            height=28,
            corner_radius=8,
            border_width=1,
            font=_ui_font(),
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
        self._withdrawal_var = tk.StringVar(value=list(WITHDRAWAL_LABELS.keys())[0])
        self._filing_var = tk.StringVar(value="single")
        self._refresh_job: str | None = None
        self._closing = False
        self._input_error_label: ctk.CTkLabel | None = None
        self._metric_labels: dict[str, ctk.CTkLabel] = {}
        self._summary_status_label: ctk.CTkLabel | None = None
        self._summary_detail_label: ctk.CTkLabel | None = None
        self._table_fixed: tk.Text | None = None
        self._table_scroll: tk.Text | None = None
        self._table_vsb: ttk.Scrollbar | None = None
        self._table_hsb: ttk.Scrollbar | None = None
        self._table_tkfont: tkfont.Font | None = None
        self._paned: tk.PanedWindow | None = None

        ctk.set_appearance_mode("light")
        ctk.set_default_color_theme("blue")
        self._colors = apply_theme(self, self._theme_name)
        self._build_header()
        self._build_menu()
        self._build_toolbar()
        self._build_body()
        self._apply_widget_colors()
        self._bind_auto_refresh()
        self.load_sample_inputs()
        self._schedule_refresh()
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.after(150, self._position_paned_sash)

    def _position_paned_sash(self, attempt: int = 0) -> None:
        if self._closing or not self._paned:
            return
        try:
            total = self._paned.winfo_width()
            if total <= 500:
                if attempt < 25:
                    self.after(100, lambda: self._position_paned_sash(attempt + 1))
                return
            frac = get_sidebar_sash_fraction()
            if frac is not None:
                sash_x = int(total * frac)
            else:
                sash_x = _SIDEBAR_SCROLL_WIDTH + 36
            sash_x = self._clamp_sidebar_sash_x(sash_x, total)
            self._paned.sash_place(0, sash_x, 0)
        except tk.TclError:
            pass

    def _clamp_sidebar_sash_x(self, sash_x: int, total_width: int) -> int:
        sash_w = 6
        max_x = total_width - _RESULTS_PANE_MINSIZE - sash_w
        return max(_SIDEBAR_PANE_MINSIZE, min(sash_x, max_x))

    def _persist_sidebar_width(self, *_args: object) -> None:
        if self._closing or not self._paned:
            return
        try:
            total = self._paned.winfo_width()
            if total <= 1:
                return
            sash_x = self._paned.sash_coord(0)[0]
            set_sidebar_sash_fraction(sash_x / total)
        except (tk.TclError, ZeroDivisionError):
            pass

    def _on_close(self) -> None:
        if self._closing:
            return
        self._closing = True
        self._persist_sidebar_width()
        if self._refresh_job is not None:
            try:
                self.after_cancel(self._refresh_job)
            except tk.TclError:
                pass
            self._refresh_job = None
        for canvas in self._chart_canvases:
            try:
                plt.close(canvas.figure)
            except (AttributeError, ValueError):
                pass
        self._chart_canvases.clear()
        try:
            self.quit()
        except tk.TclError:
            pass
        try:
            super().destroy()
        except tk.TclError:
            pass

    def _build_header(self) -> None:
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=16, pady=(14, 6))
        ctk.CTkLabel(
            header,
            text="Retirement cash-flow planner",
            font=_ui_font(weight="bold"),
            anchor="w",
        ).pack(anchor="w")
        ctk.CTkLabel(
            header,
            text="Enter assumptions on the left. Results update automatically. Not investment or tax advice.",
            font=_ui_font(),
            text_color=("#5c6370", "#9aa0a6"),
            anchor="w",
        ).pack(anchor="w", pady=(4, 0))

    def set_theme(self, theme: str) -> None:
        self._theme_name = theme
        self._colors = apply_theme(self, theme)
        if self._paned is not None:
            self._paned.configure(bg=self._colors.get("window", "#d8dce3"))
        self._apply_widget_colors()
        self._apply_table_text_theme()
        if self._disclaimer:
            self._disclaimer.configure(text_color=("#5c6370", "#9aa0a6"))
        if self._df is not None and self._inputs is not None:
            self._refresh_charts(self._df)

    def _apply_widget_colors(self) -> None:
        pass

    def _scaled_table_pixels(self) -> int:
        # Match CTk entry text: logical px × widget scaling (do not multiply window scaling twice).
        scale = ctk.ScalingTracker.get_widget_scaling(self)
        return max(FONT_TABLE_DISPLAY, int(round(FONT_TABLE_DISPLAY * scale)))

    def _ensure_table_tkfont(self) -> tkfont.Font:
        px = self._scaled_table_pixels()
        if self._table_tkfont is None:
            self._table_tkfont = tkfont.Font(
                root=self,
                family=FONT_FAMILY,
                size=-px,
            )
        else:
            self._table_tkfont.configure(size=-px)
        return self._table_tkfont

    def _apply_table_text_theme(self) -> None:
        if not self._table_fixed or not self._table_scroll:
            return
        c = self._colors
        table_font = self._ensure_table_tkfont()
        for widget in (self._table_fixed, self._table_scroll):
            widget.configure(
                font=table_font,
                bg=c["text_bg"],
                fg=c["text_fg"],
                insertbackground=c["text_insert"],
                highlightbackground=c.get("canvas", c["text_bg"]),
                highlightcolor=c.get("accent", "#2563eb"),
            )

    def _table_yscroll_set(self, first: str, last: str) -> None:
        if self._table_fixed and self._table_scroll:
            self._table_fixed.yview_moveto(first)
            self._table_scroll.yview_moveto(first)
        if self._table_vsb:
            self._table_vsb.set(first, last)

    def _table_yscroll_mov(self, *args: str) -> None:
        if self._table_fixed:
            self._table_fixed.yview(*args)
        if self._table_scroll:
            self._table_scroll.yview(*args)

    def _on_table_mousewheel(self, event: tk.Event) -> None:
        if not self._table_scroll:
            return
        if event.num == 4:
            self._table_scroll.yview_scroll(-3, "units")
        elif event.num == 5:
            self._table_scroll.yview_scroll(3, "units")
        elif event.delta:
            self._table_scroll.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def _menu_font(self) -> tuple[str, int]:
        scale = ctk.ScalingTracker.get_widget_scaling(self)
        pt = max(FONT_MENU_MIN_PT, int(round(FONT_CTK_SIZE * scale)))
        return (FONT_FAMILY, pt)

    def _build_menu(self) -> None:
        menu_font = self._menu_font()
        menubar = tk.Menu(self, font=menu_font)
        file_menu = tk.Menu(menubar, tearoff=0, font=menu_font)
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
        file_menu.add_command(label="Exit", command=self._on_close)
        menubar.add_cascade(label="File", menu=file_menu)

        run_menu = tk.Menu(menubar, tearoff=0, font=menu_font)
        run_menu.add_command(label="Refresh now", command=self._auto_refresh)
        run_menu.add_command(label="Run projection (with Monte Carlo notice)", command=self.run_projection)
        menubar.add_cascade(label="Run", menu=run_menu)

        view_menu = tk.Menu(menubar, tearoff=0, font=menu_font)
        view_menu.add_command(label="Dark theme", command=lambda: self.set_theme("dark"))
        view_menu.add_command(label="Light theme", command=lambda: self.set_theme("light"))
        menubar.add_cascade(label="View", menu=view_menu)

        self.config(menu=menubar)

    def _build_toolbar(self) -> None:
        bar = ctk.CTkFrame(self, fg_color="transparent")
        bar.pack(fill="x", padx=12, pady=(0, 8))
        self._disclaimer = ctk.CTkLabel(
            bar,
            text="Educational model only — not investment or tax advice.",
            font=_ui_font(),
            text_color=("#5c6370", "#9aa0a6"),
        )
        self._disclaimer.pack(side="right")

    def _build_body(self) -> None:
        pane_bg = self._colors.get("window", "#d8dce3")
        self._paned = tk.PanedWindow(
            self,
            orient=tk.HORIZONTAL,
            sashwidth=6,
            opaqueresize=True,
            bg=pane_bg,
            bd=0,
            relief=tk.FLAT,
        )
        self._paned.pack(fill="both", expand=True, padx=12, pady=(0, 12))

        inputs_outer = ctk.CTkFrame(self._paned, corner_radius=12)
        self._paned.add(inputs_outer, minsize=_SIDEBAR_PANE_MINSIZE, stretch="never")
        self._paned.bind("<ButtonRelease-1>", self._persist_sidebar_width)
        inputs_frame = ctk.CTkScrollableFrame(
            inputs_outer,
            width=_SIDEBAR_SCROLL_WIDTH,
            label_text="Your plan",
            corner_radius=12,
            label_font=_ui_font(weight="bold"),
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
            width=_SIDEBAR_OPTION_WIDTH,
            font=_ui_font(),
            command=self._schedule_refresh,
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
        ctk.CTkLabel(
            wo_frame,
            text="Withdrawal order",
            anchor="w",
            justify="left",
            wraplength=_SIDEBAR_WRAP,
            font=_ui_font(weight="bold"),
        ).pack(anchor="w", padx=12, pady=(8, 2))
        choice_inner = ctk.CTkFrame(wo_frame, fg_color="transparent")
        choice_inner.pack(fill="x", padx=12, pady=(0, 8))
        for label in WITHDRAWAL_LABELS:
            ctk.CTkRadioButton(
                choice_inner,
                text=label,
                variable=self._withdrawal_var,
                value=label,
                width=_SIDEBAR_OPTION_WIDTH,
                font=_ui_font(),
                command=self._schedule_refresh,
            ).pack(anchor="w", fill="x", pady=3)

        adv = ctk.CTkFrame(inputs_frame, corner_radius=12)
        adv.pack(fill="x", pady=(0, 6), padx=4)
        ctk.CTkLabel(
            adv,
            text="Advanced (v2): tax, Roth pools, conversions",
            anchor="w",
            justify="left",
            wraplength=_SIDEBAR_WRAP,
            font=_ui_font(weight="bold"),
        ).pack(anchor="w", fill="x", padx=12, pady=(8, 2))
        inner_adv = ctk.CTkFrame(adv, fg_color="transparent")
        inner_adv.pack(fill="x", padx=8, pady=(0, 6))
        ctk.CTkCheckBox(
            inner_adv,
            text="Model federal / state tax, IRMAA (after-tax spending)",
            variable=self._use_tax_var,
            width=_SIDEBAR_OPTION_WIDTH,
            font=_ui_font(),
            command=self._schedule_refresh,
        ).pack(anchor="w", fill="x", pady=0)
        ctk.CTkCheckBox(
            inner_adv,
            text="Employee 401(k) deferrals → Roth (post-tax pool)",
            variable=self._emp_roth_var,
            width=_SIDEBAR_OPTION_WIDTH,
            font=_ui_font(),
            command=self._schedule_refresh,
        ).pack(anchor="w", fill="x", pady=0)
        ctk.CTkCheckBox(
            inner_adv,
            text="Employer match → Roth (pre-tax pool)",
            variable=self._match_roth_var,
            width=_SIDEBAR_OPTION_WIDTH,
            font=_ui_font(),
            command=self._schedule_refresh,
        ).pack(anchor="w", fill="x", pady=0)
        fil = ctk.CTkFrame(inner_adv, fg_color="transparent")
        fil.pack(fill="x", pady=(2, 0))
        ctk.CTkLabel(fil, text="Filing status", font=_ui_font()).pack(side="left", padx=(0, 8))
        ctk.CTkSegmentedButton(
            fil,
            values=["single", "mfj"],
            variable=self._filing_var,
            font=_ui_font(),
            command=self._schedule_refresh,
        ).pack(side="left")
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

        results_outer = ctk.CTkFrame(self._paned, corner_radius=12, fg_color="transparent")
        self._paned.add(results_outer, minsize=_RESULTS_PANE_MINSIZE, stretch="always")
        self._input_error_label = ctk.CTkLabel(
            results_outer,
            text="",
            font=_ui_font(),
            text_color=("#b91c1c", "#fca5a5"),
            anchor="w",
            wraplength=520,
        )
        self._input_error_label.pack(fill="x", padx=8, pady=(4, 0))

        self._tabview = ctk.CTkTabview(
            results_outer,
            corner_radius=12,
            segmented_button_font=_ui_font(),
        )
        self._tabview.pack(fill="both", expand=True, padx=0, pady=4)

        summary_tab = self._tabview.add("Summary")
        self._build_summary_tab(summary_tab)

        table_tab = self._tabview.add("Year-by-year")
        table_outer = ctk.CTkFrame(table_tab, fg_color="transparent")
        table_outer.pack(fill="both", expand=True, padx=8, pady=8)
        grid = tk.Frame(table_outer, borderwidth=0, highlightthickness=0)
        grid.pack(fill="both", expand=True)

        table_font = self._ensure_table_tkfont()
        text_kw: dict[str, Any] = {
            "font": table_font,
            "wrap": "none",
            "borderwidth": 0,
            "relief": "flat",
            "state": "disabled",
            "cursor": "arrow",
            "highlightthickness": 1,
        }
        self._table_fixed = tk.Text(grid, width=11, **text_kw)
        self._table_scroll = tk.Text(grid, **text_kw)
        self._table_vsb = ttk.Scrollbar(grid, orient="vertical", command=self._table_yscroll_mov)
        self._table_hsb = ttk.Scrollbar(grid, orient="horizontal", command=self._table_scroll.xview)
        self._table_fixed.configure(yscrollcommand=self._table_yscroll_set)
        self._table_scroll.configure(yscrollcommand=self._table_yscroll_set, xscrollcommand=self._table_hsb.set)

        self._table_fixed.grid(row=0, column=0, sticky="ns")
        self._table_scroll.grid(row=0, column=1, sticky="nsew")
        self._table_vsb.grid(row=0, column=2, sticky="ns")
        self._table_hsb.grid(row=1, column=1, sticky="ew")
        grid.columnconfigure(1, weight=1)
        grid.rowconfigure(0, weight=1)

        for widget in (self._table_fixed, self._table_scroll):
            widget.bind("<MouseWheel>", self._on_table_mousewheel)
            widget.bind("<Button-4>", self._on_table_mousewheel)
            widget.bind("<Button-5>", self._on_table_mousewheel)
        self._apply_table_text_theme()

        charts_tab = self._tabview.add("Charts")
        self._charts_frame = ctk.CTkFrame(charts_tab, fg_color="transparent")
        self._charts_frame.pack(fill="both", expand=True)

        export_tab = self._tabview.add("Save & print")
        self._build_export_tab(export_tab)

    def _build_summary_tab(self, parent: ctk.CTkFrame) -> None:
        wrap = ctk.CTkFrame(parent, fg_color="transparent")
        wrap.pack(fill="both", expand=True, padx=12, pady=12)
        metrics = ctk.CTkFrame(wrap, fg_color="transparent")
        metrics.pack(fill="x", pady=(0, 12))
        for col, (key, title) in enumerate(
            [
                ("ending", "Ending balance"),
                ("retirement", "Balance at retirement"),
                ("shortfall", "Cumulative shortfall"),
                ("years", "Plan years"),
            ]
        ):
            card = ctk.CTkFrame(metrics, corner_radius=10)
            card.grid(row=0, column=col, padx=6, pady=4, sticky="nsew")
            metrics.columnconfigure(col, weight=1)
            ctk.CTkLabel(
                card,
                text=title,
                font=_ui_font(),
                text_color=("#5c6370", "#9aa0a6"),
            ).pack(anchor="w", padx=12, pady=(10, 0))
            self._metric_labels[key] = ctk.CTkLabel(
                card,
                text="—",
                font=_ui_font(weight="bold"),
                anchor="w",
            )
            self._metric_labels[key].pack(anchor="w", padx=12, pady=(2, 12))
        self._summary_status_label = ctk.CTkLabel(
            wrap,
            text="",
            font=_ui_font(),
            anchor="w",
            justify="left",
            wraplength=640,
        )
        self._summary_status_label.pack(fill="x", pady=(0, 8))
        ctk.CTkLabel(
            wrap,
            text="First year of retirement",
            font=_ui_font(weight="bold"),
            anchor="w",
        ).pack(anchor="w", pady=(8, 4))
        self._summary_detail_label = ctk.CTkLabel(
            wrap,
            text="",
            font=_ui_font(),
            anchor="w",
            justify="left",
            wraplength=640,
        )
        self._summary_detail_label.pack(fill="x")

    def _build_export_tab(self, parent: ctk.CTkFrame) -> None:
        wrap = ctk.CTkFrame(parent, fg_color="transparent")
        wrap.pack(fill="both", expand=True, padx=12, pady=12)
        ctk.CTkLabel(wrap, text="Download", font=_ui_font(weight="bold"), anchor="w").pack(
            anchor="w", pady=(0, 8)
        )
        row = ctk.CTkFrame(wrap, fg_color="transparent")
        row.pack(fill="x", pady=(0, 16))
        ctk.CTkButton(
            row, text="Download CSV", command=self.export_csv, font=_ui_font(), **_TOOLBAR_SECONDARY_BTN
        ).pack(side="left", padx=(0, 8))
        ctk.CTkButton(
            row, text="Download Excel", command=self.export_excel, font=_ui_font(), **_TOOLBAR_SECONDARY_BTN
        ).pack(side="left", padx=8)
        ctk.CTkButton(
            row, text="Download HTML report", command=self.export_html, font=_ui_font(), **_TOOLBAR_SECONDARY_BTN
        ).pack(side="left", padx=8)
        ctk.CTkButton(
            row, text="Export all to folder…", command=self.export_all, font=_ui_font(), **_TOOLBAR_SECONDARY_BTN
        ).pack(side="left", padx=8)
        ctk.CTkLabel(wrap, text="Print", font=_ui_font(weight="bold"), anchor="w").pack(anchor="w", pady=(8, 4))
        ctk.CTkLabel(
            wrap,
            text=(
                "Open the HTML report in your browser (File → Open HTML report in browser), "
                "then use Print or Save as PDF.\n"
                "Chart images: File → Export chart images."
            ),
            font=_ui_font(),
            text_color=("#5c6370", "#9aa0a6"),
            anchor="w",
            justify="left",
            wraplength=640,
        ).pack(anchor="w")
        ctk.CTkButton(
            wrap,
            text="Open HTML report in browser (print / PDF)",
            command=self.open_html_for_print,
            font=_ui_font(),
            **_TOOLBAR_SECONDARY_BTN,
        ).pack(anchor="w", pady=(12, 0))

    def _bind_auto_refresh(self) -> None:
        for entry in self._fields.values():
            entry.var.trace_add("write", self._schedule_refresh)

    def _schedule_refresh(self, *_args: object) -> None:
        if self._closing:
            return
        if self._refresh_job is not None:
            try:
                self.after_cancel(self._refresh_job)
            except tk.TclError:
                pass
        try:
            self._refresh_job = self.after(450, self._auto_refresh)
        except tk.TclError:
            self._refresh_job = None

    def _set_input_error(self, message: str) -> None:
        if self._input_error_label:
            self._input_error_label.configure(text=message)

    def _clear_input_error(self) -> None:
        if self._input_error_label:
            self._input_error_label.configure(text="")

    def _auto_refresh(self) -> None:
        self._refresh_job = None
        if self._closing:
            return
        try:
            inputs = self.collect_inputs()
            df = run_projection(inputs)
        except ValueError as exc:
            self._set_input_error(str(exc))
            return
        self._clear_input_error()
        self._inputs = inputs
        self._df = df
        self._refresh_summary(df, inputs)
        self._refresh_table(df)
        self._refresh_charts(df)

    def _add_section(self, parent: ctk.CTkScrollableFrame, title: str, rows: list[tuple[str, str]]) -> None:
        frame = ctk.CTkFrame(parent, corner_radius=12)
        frame.pack(fill="x", pady=(0, 6), padx=4)
        ctk.CTkLabel(
            frame,
            text=title,
            anchor="w",
            justify="left",
            wraplength=_SIDEBAR_WRAP,
            font=_ui_font(weight="bold"),
        ).pack(anchor="w", fill="x", padx=12, pady=(8, 2))
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
        self._filing_var.set(sample.filing_status)
        for label, enum in WITHDRAWAL_LABELS.items():
            if enum == sample.withdrawal_order:
                self._withdrawal_var.set(label)
                break
        self._schedule_refresh()

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
            use_tax_modeling=self._use_tax_var.get(),
            filing_status=self._filing_var.get(),
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
        self._auto_refresh()
        if self._df is None or self._inputs is None:
            return
        inputs = self._inputs
        df = self._df
        msg = f"Calculated {len(df)} years. Use Save & print tab or File menu to export."
        if inputs.run_monte_carlo_trials > 0:
            from retirement.monte_carlo import run_monte_carlo

            mc = run_monte_carlo(inputs, trials=inputs.run_monte_carlo_trials)
            msg += f"\n\nMonte Carlo ({mc.trials} runs): {mc.success_rate:.1%} success, median ending ${mc.median_ending_balance:,.0f}."
        messagebox.showinfo("Projection complete", msg)

    def _require_results(self) -> tuple[pd.DataFrame, RetirementInputs] | None:
        if self._df is None or self._inputs is None:
            self._auto_refresh()
        if self._df is None or self._inputs is None:
            messagebox.showwarning("No projection", "Fix input errors shown above the results tabs.")
            return None
        return self._df, self._inputs

    def _refresh_summary(self, df: pd.DataFrame, inputs: RetirementInputs) -> None:
        s = summarize_projection(df, inputs)
        self._metric_labels["ending"].configure(text=f"${s['ending_balance']:,.0f}")
        if s["balance_at_retirement"] is not None:
            self._metric_labels["retirement"].configure(text=f"${s['balance_at_retirement']:,.0f}")
        else:
            self._metric_labels["retirement"].configure(text="—")
        self._metric_labels["shortfall"].configure(text=f"${s['cumulative_shortfall']:,.0f}")
        self._metric_labels["years"].configure(
            text=f"{s['plan_start_year']}–{s['plan_end_year']}"
        )
        if self._summary_status_label:
            if s["first_shortfall"]:
                fs = s["first_shortfall"]
                self._summary_status_label.configure(
                    text=f"Spending shortfall begins in {fs['year']} (age {fs['age']}).",
                    text_color=("#b45309", "#fbbf24"),
                )
            else:
                self._summary_status_label.configure(
                    text="No spending shortfalls in the retirement years of this projection.",
                    text_color=("#15803d", "#86efac"),
                )
        if self._summary_detail_label:
            ret = df[df["phase"] == "retirement"]
            if ret.empty:
                self._summary_detail_label.configure(text="No retirement years in this plan horizon.")
            else:
                row = ret.iloc[0]
                self._summary_detail_label.configure(
                    text=(
                        f"In {int(row['year'])} (age {int(row['age'])}): "
                        f"spending need ${row['spending_need']:,.0f}, "
                        f"income ${row['income_total']:,.0f} "
                        f"(pension ${row['pension_income']:,.0f}, "
                        f"SS ${row['ss_income'] + row['spouse_ss_income']:,.0f}, "
                        f"withdrawals ${row['withdrawal_total']:,.0f})."
                    )
                )

    def _refresh_table(self, df: pd.DataFrame) -> None:
        if not self._table_fixed or not self._table_scroll:
            return
        fixed_text, scroll_text = _format_yearly_table_parts(df)
        for widget, content in ((self._table_fixed, fixed_text), (self._table_scroll, scroll_text)):
            widget.configure(state="normal")
            widget.delete("1.0", "end")
            widget.insert("1.0", content)
            widget.configure(state="disabled")
        self._table_fixed.yview_moveto(0)
        self._table_scroll.yview_moveto(0)
        self._table_scroll.xview_moveto(0)

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
    try:
        app.mainloop()
    finally:
        plt.close("all")


if __name__ == "__main__":
    main()
