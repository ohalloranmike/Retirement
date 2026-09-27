"""Modern ttk styling (Sun Valley theme + typography)."""

from __future__ import annotations

import sys
import tkinter as tk
from tkinter import ttk

THEMES = ("dark", "light")

PALETTE = {
    "dark": {
        "window": "#1c1c1c",
        "text_bg": "#252526",
        "text_fg": "#e8eaed",
        "text_insert": "#ffffff",
        "muted": "#9aa0a6",
        "canvas": "#1c1c1c",
        "mpl_style": "dark_background",
    },
    "light": {
        "window": "#d8dce3",
        "text_bg": "#e4e8ee",
        "text_fg": "#1a1d21",
        "text_insert": "#1a1d21",
        "muted": "#4b5563",
        "canvas": "#cdd2da",
        "accent": "#2563eb",
        "mpl_style": "ggplot",
    },
}

FONT_FAMILY = "Segoe UI" if sys.platform == "win32" else "Helvetica Neue"
# CustomTkinter widgets default to 13px; match that everywhere for consistency.
FONT_CTK_SIZE = 13
FONT_UI = (FONT_FAMILY, FONT_CTK_SIZE)
FONT_UI_SMALL = (FONT_FAMILY, FONT_CTK_SIZE)
FONT_HEADING = (FONT_FAMILY, FONT_CTK_SIZE, "bold")
FONT_SECTION = (FONT_FAMILY, FONT_CTK_SIZE, "bold")
# tk.Menu uses points and does not follow CTk scaling; gui._menu_font() computes size.
FONT_MENU_MIN_PT = 16
FONT_TABLE_DISPLAY = FONT_CTK_SIZE  # tk.Text: use negative size (pixels) in gui
FONT_TABLE = (FONT_FAMILY, FONT_CTK_SIZE)
FONT_TABLE_HEADING = (FONT_FAMILY, FONT_CTK_SIZE, "bold")
TREE_ROW_HEIGHT = 32


def apply_theme(root: tk.Misc, theme: str = "light") -> dict[str, str]:
    """Apply CustomTkinter + ttk styling; return palette for any classic tk widgets."""
    if theme not in THEMES:
        theme = "light"

    colors = PALETTE[theme]

    try:
        import customtkinter as ctk

        ctk.set_appearance_mode(theme)
        ctk.set_default_color_theme("blue")
    except ImportError:
        pass

    if isinstance(root, tk.Tk):
        root.configure(bg=colors["window"])

    style = ttk.Style(root)
    try:
        import sv_ttk

        sv_ttk.set_theme(theme)
    except ImportError:
        if sys.platform == "win32":
            style.theme_use("vista")
        else:
            style.theme_use("clam")
    style.configure(".", font=FONT_UI)
    style.configure("TLabel", font=FONT_UI)
    style.configure("Muted.TLabel", font=FONT_UI_SMALL, foreground=colors["muted"])
    style.configure("Heading.TLabel", font=FONT_HEADING, foreground=colors["text_fg"])
    style.configure("TLabelframe.Label", font=FONT_SECTION)
    style.configure("TButton", padding=(10, 6))
    style.configure("Accent.TButton", padding=(14, 8), font=(FONT_FAMILY, FONT_CTK_SIZE, "bold"))
    style.configure("TNotebook", padding=2)
    style.configure("TNotebook.Tab", padding=(14, 8), font=FONT_UI)
    style.configure("Treeview", rowheight=TREE_ROW_HEIGHT, font=FONT_TABLE)
    style.configure("Treeview.Heading", font=FONT_TABLE_HEADING)
    style.configure("Results.Treeview", rowheight=TREE_ROW_HEIGHT, font=FONT_TABLE)
    style.configure("Results.Treeview.Heading", font=FONT_TABLE_HEADING)
    style.configure("TEntry", padding=4)

    if theme == "light":
        style.configure("TFrame", background=colors["window"])
        style.configure("TLabelframe", background=colors["window"])
        for name in ("Treeview", "Results.Treeview"):
            style.configure(
                name,
                background="#e8ecf1",
                fieldbackground="#e8ecf1",
                foreground=colors["text_fg"],
            )
            style.map(name, background=[("selected", "#b8cce8")], foreground=[("selected", "#1e3a5f")])

    return colors
