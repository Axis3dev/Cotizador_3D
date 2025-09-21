"""Tab to manage saved quotations."""

from __future__ import annotations

import datetime as dt
import tkinter as tk
from tkinter import messagebox, ttk
from typing import Callable, List, Optional

from tkcalendar import DateEntry

from models.cotizacion import Cotizacion
from storage.orders_store import OrdersStore
from storage.quotes_store import QuoteStore


class QuotesTab(ttk.Frame):
    def __init__(
        self,
        master: ttk.Notebook,
        quote_store: QuoteStore,
        orders_store: OrdersStore,
        on_view: Callable[[Cotizacion], None],
        on_edit: Callable[[Cotizacion], None],
        on_convert: Callable[[Cotizacion], None],
    ) -> None:
        super().__init__(master)
        self.quote_store = quote_store
        self.orders_store = orders_store
        self.on_view = on_view
        self.on_edit = on_edit
        self.on_convert = on_convert
        self.quotes: List[Cotizacion] = []
        self.filtered: List[Cotizacion] = []

        self.fecha_inicio_var = tk.StringVar()
        self.fecha_fin_var = tk.StringVar()

        self._build_ui()
        self.refresh()

    # ------------------------------------------------------------------
    def _build_ui(self) -> None:
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)
        self.rowconfigure(3, weight=1)

        filter_frame = ttk.Frame(self)
        filter_frame.grid(row=0, column=0, columnspan=2, sticky="ew", padx=8, pady=4)
        ttk.Label(filter_frame, text="Desde:").pack(side=tk.LEFT, padx=(0, 4))
        self.fecha_inicio_entry = DateEntry(
            filter_frame,
            textvariable=self.fecha_inicio_var,
            width=12,
            date_pattern="yyyy-mm-dd",
        )
        self.fecha_inicio_entry.pack(side=tk.LEFT)
        self.fecha_inicio_entry.delete(0, tk.END)
        ttk.Label(filter_frame, text="Hasta:").pack(side=tk.LEFT, padx=(8, 4))
        self.fecha_fin_entry = DateEntry(
            filter_frame,
            textvariable=self.fecha_fin_var,
            width=12,
            date_pattern="yyyy-mm-dd",
        )
        self.fecha_fin_entry.pack(side=tk.LEFT)
        self.fecha_fin_entry.delete(0, tk.END)
        ttk.Button(filter_frame, text="Aplicar", command=self.apply_filters).pack(side=tk.LEFT, padx=6)
        ttk.Button(filter_frame, text="Limpiar", command=self.clear_filters).pack(side=tk.LEFT)

        columns = ("estado", "folio", "fecha", "proyecto", "cliente", "correo", "celular")
        self.tree = ttk.Treeview(self, columns=columns, show="headings")
        headings = ["Estado", "Folio", "Fecha", "Proyecto", "Cliente", "Correo", "Celular"]
        for col, text in zip(columns, headings):
            self.tree.heading(col, text=text)
            width = 120 if col in {"folio", "fecha"} else 200
            if col == "estado":
                width = 110
            self.tree.column(col, width=width, anchor="center")
        self.tree.grid(row=1, column=0, sticky="nsew")

        scrollbar = ttk.Scrollbar(self, orient=tk.VERTICAL, command=self.tree.yview)
        scrollbar.grid(row=1, column=1, sticky="ns")
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.tag_configure("pedido", foreground="#15803d")
        self.tree.tag_configure("pendiente", foreground="#c2410c")

        button_frame = ttk.Frame(self)
        button_frame.grid(row=2, column=0, columnspan=2, pady=8)
        ttk.Button(button_frame, text="Ver", command=self.view_selected).pack(side=tk.LEFT, padx=4)
        ttk.Button(button_frame, text="Editar", command=self.edit_selected).pack(side=tk.LEFT, padx=4)
        ttk.Button(button_frame, text="Eliminar", command=self.delete_selected).pack(side=tk.LEFT, padx=4)
        ttk.Button(button_frame, text="Marcar como pedido", command=self.convert_selected).pack(side=tk.LEFT, padx=4)

        self.details = tk.Text(self, height=8, state=tk.DISABLED)
        self.details.grid(row=3, column=0, columnspan=2, sticky="nsew", padx=6, pady=6)

        self.tree.bind("<<TreeviewSelect>>", lambda _: self.show_details())

    # ------------------------------------------------------------------
    def refresh(self) -> None:
        self.quotes = self.quote_store.list_quotes()
        self.apply_filters()

    # ------------------------------------------------------------------
    def apply_filters(self) -> None:
        inicio = self._parse_date(self.fecha_inicio_var.get())
        fin = self._parse_date(self.fecha_fin_var.get())
        if inicio and fin and inicio > fin:
            messagebox.showerror("Rango inválido", "La fecha inicial no puede ser mayor que la final.", parent=self)
            return

        pedidos = {pedido.folio_cotizacion for pedido in self.orders_store.list_orders()}

        filtered: List[Cotizacion] = []
        self.tree.delete(*self.tree.get_children())
        for quote in self.quotes:
            fecha = self._parse_date(quote.fecha)
            if inicio and fecha and fecha < inicio:
                continue
            if fin and fecha and fecha > fin:
                continue
            filtered.append(quote)
            tag = "pedido" if quote.folio in pedidos else "pendiente"
            estado_text = "● Pedido" if tag == "pedido" else "● Pendiente"
            self.tree.insert(
                "",
                tk.END,
                values=(
                    estado_text,
                    quote.folio,
                    quote.fecha,
                    quote.proyecto,
                    quote.cliente.nombre,
                    quote.cliente.correo,
                    quote.cliente.celular,
                ),
                tags=(tag,),
            )
        self.filtered = filtered
        self.details.configure(state=tk.NORMAL)
        self.details.delete("1.0", tk.END)
        self.details.configure(state=tk.DISABLED)

    # ------------------------------------------------------------------
    def clear_filters(self) -> None:
        self.fecha_inicio_var.set("")
        self.fecha_fin_var.set("")
        self.fecha_inicio_entry.delete(0, tk.END)
        self.fecha_fin_entry.delete(0, tk.END)
        self.apply_filters()

    # ------------------------------------------------------------------
    def get_selected_quote(self) -> Optional[Cotizacion]:
        selection = self.tree.selection()
        if not selection:
            return None
        index = self.tree.index(selection[0])
        if index >= len(self.filtered):
            return None
        return self.filtered[index]

    # ------------------------------------------------------------------
    def view_selected(self) -> None:
        quote = self.get_selected_quote()
        if quote:
            self.on_view(quote)

    # ------------------------------------------------------------------
    def edit_selected(self) -> None:
        quote = self.get_selected_quote()
        if quote:
            self.on_edit(quote)

    # ------------------------------------------------------------------
    def delete_selected(self) -> None:
        quote = self.get_selected_quote()
        if not quote:
            return
        if messagebox.askyesno("Eliminar", f"¿Eliminar la cotización {quote.folio}?", parent=self):
            self.quote_store.delete(quote.folio)
            self.refresh()

    # ------------------------------------------------------------------
    def convert_selected(self) -> None:
        quote = self.get_selected_quote()
        if quote:
            self.on_convert(quote)

    # ------------------------------------------------------------------
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

    # ------------------------------------------------------------------
    @staticmethod
    def _parse_date(value: str) -> Optional[dt.date]:
        try:
            return dt.datetime.fromisoformat(value).date()
        except Exception:
            return None


__all__ = ["QuotesTab"]
