"""Tab to manage saved quotations."""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk
from typing import Callable, List, Optional

from models.cotizacion import Cotizacion
from storage.quotes_store import QuoteStore


class QuotesTab(ttk.Frame):
    def __init__(
        self,
        master: ttk.Notebook,
        quote_store: QuoteStore,
        on_view: Callable[[Cotizacion], None],
        on_edit: Callable[[Cotizacion], None],
        on_convert: Callable[[Cotizacion], None],
    ) -> None:
        super().__init__(master)
        self.quote_store = quote_store
        self.on_view = on_view
        self.on_edit = on_edit
        self.on_convert = on_convert
        self.quotes: List[Cotizacion] = []

        self._build_ui()
        self.refresh()

    def _build_ui(self) -> None:
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        columns = ("folio", "fecha", "proyecto", "cliente", "correo", "celular")
        self.tree = ttk.Treeview(self, columns=columns, show="headings")
        for col, text in zip(columns, ["Folio", "Fecha", "Proyecto", "Cliente", "Correo", "Celular"]):
            self.tree.heading(col, text=text)
            self.tree.column(col, width=140 if col in {"folio", "fecha"} else 180, anchor="center")
        self.tree.grid(row=0, column=0, sticky="nsew")

        scrollbar = ttk.Scrollbar(self, orient=tk.VERTICAL, command=self.tree.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.tree.configure(yscrollcommand=scrollbar.set)

        button_frame = ttk.Frame(self)
        button_frame.grid(row=1, column=0, columnspan=2, pady=8)
        ttk.Button(button_frame, text="Ver", command=self.view_selected).pack(side=tk.LEFT, padx=4)
        ttk.Button(button_frame, text="Editar", command=self.edit_selected).pack(side=tk.LEFT, padx=4)
        ttk.Button(button_frame, text="Eliminar", command=self.delete_selected).pack(side=tk.LEFT, padx=4)
        ttk.Button(button_frame, text="Marcar como pedido", command=self.convert_selected).pack(side=tk.LEFT, padx=4)

        self.details = tk.Text(self, height=8, state=tk.DISABLED)
        self.details.grid(row=2, column=0, columnspan=2, sticky="nsew", padx=6, pady=6)
        self.rowconfigure(2, weight=1)

        self.tree.bind("<<TreeviewSelect>>", lambda _: self.show_details())

    def refresh(self) -> None:
        self.quotes = self.quote_store.list_quotes()
        self.tree.delete(*self.tree.get_children())
        for quote in self.quotes:
            self.tree.insert(
                "",
                tk.END,
                values=(
                    quote.folio,
                    quote.fecha,
                    quote.proyecto,
                    quote.cliente.nombre,
                    quote.cliente.correo,
                    quote.cliente.celular,
                ),
            )
        self.details.configure(state=tk.NORMAL)
        self.details.delete("1.0", tk.END)
        self.details.configure(state=tk.DISABLED)

    def get_selected_quote(self) -> Optional[Cotizacion]:
        selection = self.tree.selection()
        if not selection:
            return None
        index = self.tree.index(selection[0])
        if index >= len(self.quotes):
            return None
        return self.quotes[index]

    def view_selected(self) -> None:
        quote = self.get_selected_quote()
        if quote:
            self.on_view(quote)

    def edit_selected(self) -> None:
        quote = self.get_selected_quote()
        if quote:
            self.on_edit(quote)

    def delete_selected(self) -> None:
        quote = self.get_selected_quote()
        if not quote:
            return
        if messagebox.askyesno("Eliminar", f"¿Eliminar la cotización {quote.folio}?", parent=self):
            self.quote_store.delete(quote.folio)
            self.refresh()

    def convert_selected(self) -> None:
        quote = self.get_selected_quote()
        if quote:
            self.on_convert(quote)

    def show_details(self) -> None:
        quote = self.get_selected_quote()
        self.details.configure(state=tk.NORMAL)
        self.details.delete("1.0", tk.END)
        if quote:
            lines = [
                f"Folio: {quote.folio}",
                f"Fecha: {quote.fecha}",
                f"Proyecto: {quote.proyecto}",
                f"Cliente: {quote.cliente.nombre}",
                f"Correo: {quote.cliente.correo}",
                f"Celular: {quote.cliente.celular}",
                f"Total: {quote.total:.2f} {quote.moneda}",
                "Piezas:",
            ]
            for pieza in quote.piezas:
                lines.append(f"  - {pieza.pieza.nombre} x{pieza.pieza.cantidad}: {pieza.total_total:.2f} {quote.moneda}")
            self.details.insert(tk.END, "\n".join(lines))
        self.details.configure(state=tk.DISABLED)


__all__ = ["QuotesTab"]
