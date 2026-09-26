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
        "window": "#f3f3f3",
        "text_bg": "#ffffff",
        "text_fg": "#202124",
        "text_insert": "#202124",
        "muted": "#5f6368",
        "canvas": "#f3f3f3",
        "mpl_style": "ggplot",
    },
}

FONT_FAMILY = "Segoe UI" if sys.platform == "win32" else "Helvetica Neue"
FONT_UI = (FONT_FAMILY, 10)
FONT_UI_SMALL = (FONT_FAMILY, 9)
FONT_HEADING = (FONT_FAMILY, 18, "bold")
FONT_SECTION = (FONT_FAMILY, 10, "bold")
FONT_MONO = ("Cascadia Mono", 10) if sys.platform == "win32" else ("Menlo", 10)


def apply_theme(root: tk.Tk, theme: str = "dark") -> dict[str, str]:
    """Apply Sun Valley ttk theme and return palette colors for classic tk widgets."""
    if theme not in THEMES:
        theme = "dark"

    import sv_ttk

    sv_ttk.set_theme(theme)
    colors = PALETTE[theme]

    root.configure(bg=colors["window"])

    style = ttk.Style(root)
    style.configure(".", font=FONT_UI)
    style.configure("TLabel", font=FONT_UI)
    style.configure("Muted.TLabel", font=FONT_UI_SMALL, foreground=colors["muted"])
    style.configure("Heading.TLabel", font=FONT_HEADING)
    style.configure("TLabelframe.Label", font=FONT_SECTION)
    style.configure("TButton", padding=(10, 6))
    style.configure("Accent.TButton", padding=(14, 8), font=(FONT_FAMILY, 10, "bold"))
    style.configure("TNotebook.Tab", padding=(14, 8), font=FONT_UI)
    style.configure("Treeview", rowheight=26, font=FONT_UI_SMALL)
    style.configure("Treeview.Heading", font=(FONT_FAMILY, 9, "bold"))
    style.configure("TEntry", padding=4)

    return colors
