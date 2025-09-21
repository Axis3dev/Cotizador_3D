"""Reusable Tkinter widget components."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Callable, Optional


class LabeledEntry(ttk.Frame):
    """A label with an entry widget that validates numeric input."""

    def __init__(
        self,
        master: tk.Widget,
        text: str,
        textvariable: tk.StringVar,
        *,
        validate: Optional[str] = None,
        width: int = 10,
        tooltip: Optional[str] = None,
    ) -> None:
        super().__init__(master)
        self._variable = textvariable

        label = ttk.Label(self, text=text)
        label.pack(side=tk.LEFT, padx=(0, 6))

        vcmd: Optional[Callable[[str], bool]] = None
        if validate == "float":
            vcmd = (self.register(self._validate_float), "%P")
        elif validate == "int":
            vcmd = (self.register(self._validate_int), "%P")

        self.entry = ttk.Entry(self, textvariable=self._variable, width=width, validate="key")
        if vcmd:
            self.entry.configure(validatecommand=vcmd)
        self.entry.pack(side=tk.LEFT, fill=tk.X, expand=True)

        if tooltip:
            create_tooltip(self.entry, tooltip)

    @staticmethod
    def _validate_float(value: str) -> bool:
        if value in {"", "-", "."}:
            return True
        try:
            float(value)
        except ValueError:
            return False
        return True

    @staticmethod
    def _validate_int(value: str) -> bool:
        if value in {"", "-"}:
            return True
        try:
            int(value)
        except ValueError:
            return False
        return True

    def get(self) -> str:
        return self._variable.get()

    def set(self, value: str) -> None:
        self._variable.set(value)


class LabeledCombobox(ttk.Frame):
    """A label with a combobox widget."""

    def __init__(
        self,
        master: tk.Widget,
        text: str,
        textvariable: tk.StringVar,
        values: list[str],
        width: int = 15,
        tooltip: Optional[str] = None,
    ) -> None:
        super().__init__(master)
        ttk.Label(self, text=text).pack(side=tk.LEFT, padx=(0, 6))
        self.combobox = ttk.Combobox(self, textvariable=textvariable, values=values, state="readonly", width=width)
        self.combobox.pack(side=tk.LEFT, fill=tk.X, expand=True)
        if tooltip:
            create_tooltip(self.combobox, tooltip)

    def set_values(self, values: list[str]) -> None:
        self.combobox.configure(values=values)


class ToolTip(tk.Toplevel):
    """Very small tooltip implementation for Tkinter widgets."""

    def __init__(self, widget: tk.Widget, text: str):
        super().__init__(widget)
        self.withdraw()
        self.overrideredirect(True)
        self.label = ttk.Label(self, text=text, relief=tk.SOLID, borderwidth=1, padding=(4, 2))
        self.label.pack()

    def show(self, widget: tk.Widget) -> None:
        if self.winfo_viewable():
            return
        x = widget.winfo_rootx() + 20
        y = widget.winfo_rooty() + 20
        self.geometry(f"+{x}+{y}")
        self.deiconify()

    def hide(self) -> None:
        self.withdraw()


def create_tooltip(widget: tk.Widget, text: str) -> None:
    """Attach a tooltip to ``widget`` with the provided ``text``."""

    tooltip = ToolTip(widget, text)

    def enter(_: tk.Event) -> None:
        tooltip.show(widget)

    def leave(_: tk.Event) -> None:
        tooltip.hide()

    widget.bind("<Enter>", enter)
    widget.bind("<Leave>", leave)


__all__ = ["LabeledEntry", "LabeledCombobox", "create_tooltip"]
