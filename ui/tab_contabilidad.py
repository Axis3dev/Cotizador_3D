"""Accounting overview tab."""

from __future__ import annotations

import datetime as dt
import tkinter as tk
import webbrowser
from pathlib import Path
from tkinter import messagebox, ttk
from typing import Dict, List, Optional

from tkcalendar import DateEntry

from export.excel_accounting import export_accounting_excel
from export.pdf_accounting import export_accounting_pdf
from models.pedido import Pedido
from storage.config_store import ConfigStore
from storage.orders_store import OrdersStore


class AccountingTab(ttk.Frame):
    def __init__(
        self,
        master: ttk.Notebook,
        orders_store: OrdersStore,
        config_store: ConfigStore,
    ) -> None:
        super().__init__(master)
        self.orders_store = orders_store
        self.config_store = config_store
        self.orders: List[Pedido] = []
        self.summary: List[Dict[str, float]] = []

        self.tipo_var = tk.StringVar(value="todos")
        self.impresora_var = tk.StringVar(value="todas")
        self.facturado_var = tk.StringVar(value="todos")
        self.fecha_inicio_var = tk.StringVar()
        self.fecha_fin_var = tk.StringVar()

        self._printer_options: List[str] = ["todas"]

        self._build_ui()
        self.refresh()

    def _build_ui(self) -> None:
        filter_frame = ttk.Frame(self)
        filter_frame.pack(fill=tk.X, padx=8, pady=4)

        ttk.Label(filter_frame, text="Tipo:").pack(side=tk.LEFT)
        tipo_combo = ttk.Combobox(
            filter_frame,
            textvariable=self.tipo_var,
            state="readonly",
            values=["todos", "filamento", "resina"],
            width=12,
        )
        tipo_combo.pack(side=tk.LEFT, padx=4)
        tipo_combo.bind("<<ComboboxSelected>>", lambda _: self.update_summary())

        ttk.Label(filter_frame, text="Impresora:").pack(side=tk.LEFT, padx=(8, 4))
        self.impresora_combo = ttk.Combobox(
            filter_frame,
            textvariable=self.impresora_var,
            state="readonly",
            values=self._printer_options,
            width=18,
        )
        self.impresora_combo.pack(side=tk.LEFT)
        self.impresora_combo.bind("<<ComboboxSelected>>", lambda _: self.update_summary())

        ttk.Label(filter_frame, text="Facturado:").pack(side=tk.LEFT, padx=(8, 4))
        facturado_combo = ttk.Combobox(
            filter_frame,
            textvariable=self.facturado_var,
            state="readonly",
            values=["todos", "sí", "no"],
            width=10,
        )
        facturado_combo.pack(side=tk.LEFT)
        facturado_combo.bind("<<ComboboxSelected>>", lambda _: self.update_summary())

        ttk.Label(filter_frame, text="Desde:").pack(side=tk.LEFT, padx=(8, 2))
        self.fecha_inicio_entry = DateEntry(filter_frame, textvariable=self.fecha_inicio_var, width=12, date_pattern="yyyy-mm-dd")
        self.fecha_inicio_entry.pack(side=tk.LEFT)
        self.fecha_inicio_entry.delete(0, tk.END)
        ttk.Label(filter_frame, text="Hasta:").pack(side=tk.LEFT, padx=(8, 2))
        self.fecha_fin_entry = DateEntry(filter_frame, textvariable=self.fecha_fin_var, width=12, date_pattern="yyyy-mm-dd")
        self.fecha_fin_entry.pack(side=tk.LEFT)
        self.fecha_fin_entry.delete(0, tk.END)
        ttk.Button(filter_frame, text="Aplicar", command=self.update_summary).pack(side=tk.LEFT, padx=6)

        columns = ("periodo", "ingresos", "costos", "gastos", "ganancia", "iva")
        self.tree = ttk.Treeview(self, columns=columns, show="headings")
        for col, text in zip(columns, ["Periodo", "Ingresos", "Costos", "Gastos", "Ganancia", "IVA"]):
            self.tree.heading(col, text=text)
            self.tree.column(col, width=140, anchor="center")
        self.tree.pack(fill=tk.BOTH, expand=True, padx=8, pady=4)

        orders_frame = ttk.LabelFrame(self, text="Pedidos filtrados")
        orders_frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=4)
        orders_frame.columnconfigure(0, weight=1)
        orders_frame.rowconfigure(0, weight=1)

        order_columns = (
            "fecha",
            "folio",
            "tipo",
            "impresora",
            "total",
            "costos",
            "gastos",
            "ganancia",
            "iva",
            "retencion",
            "facturado",
        )
        order_headings = [
            "Fecha",
            "Folio",
            "Tipo",
            "Impresora",
            "Total",
            "Costos",
            "Gastos",
            "Ganancia",
            "IVA",
            "Retención",
            "Facturado",
        ]
        self.orders_tree = ttk.Treeview(orders_frame, columns=order_columns, show="headings", height=6)
        for col, text in zip(order_columns, order_headings):
            self.orders_tree.heading(col, text=text)
            width = 120
            if col in {"fecha", "folio"}:
                width = 140
            self.orders_tree.column(col, width=width, anchor="center")
        self.orders_tree.grid(row=0, column=0, sticky="nsew")
        orders_scroll = ttk.Scrollbar(orders_frame, orient=tk.VERTICAL, command=self.orders_tree.yview)
        orders_scroll.grid(row=0, column=1, sticky="ns")
        self.orders_tree.configure(yscrollcommand=orders_scroll.set)

        orders_buttons = ttk.Frame(orders_frame)
        orders_buttons.grid(row=1, column=0, sticky="e", pady=6)
        ttk.Button(orders_buttons, text="Abrir factura", command=self._open_invoice).pack(side=tk.LEFT, padx=4)

        button_frame = ttk.Frame(self)
        button_frame.pack(fill=tk.X, padx=8, pady=4)
        ttk.Button(button_frame, text="Exportar PDF", command=self.export_pdf).pack(side=tk.LEFT, padx=4)
        ttk.Button(button_frame, text="Exportar Excel", command=self.export_excel).pack(side=tk.LEFT, padx=4)

    def refresh(self) -> None:
        self.orders = self.orders_store.list_orders()
        self._update_printer_options()
        self.update_summary()

    def update_summary(self) -> None:
        inicio = self._parse_date(self.fecha_inicio_var.get())
        fin = self._parse_date(self.fecha_fin_var.get())
        tipo = self.tipo_var.get()
        impresora = self.impresora_var.get()
        facturado = self.facturado_var.get()

        if inicio and fin and inicio > fin:
            messagebox.showerror("Rango inválido", "La fecha inicial no puede ser mayor que la final.", parent=self)
            return

        grouped: Dict[str, Dict[str, float]] = {}
        filtered_orders: List[Pedido] = []
        for pedido in self.orders:
            if pedido.estatus != "realizado":
                continue
            if tipo != "todos" and pedido.tipo != tipo:
                continue
            if impresora != "todas" and pedido.impresora != impresora:
                continue
            if facturado == "sí" and not pedido.facturado:
                continue
            if facturado == "no" and pedido.facturado:
                continue
            fecha = self._parse_date(pedido.fecha_creacion)
            if inicio and fecha and fecha < inicio:
                continue
            if fin and fecha and fecha > fin:
                continue
            filtered_orders.append(pedido)
            periodo = fecha.strftime("%Y-%m") if fecha else pedido.fecha_creacion[:7]
            bucket = grouped.setdefault(
                periodo,
                {"ingresos": 0.0, "costos": 0.0, "gastos": 0.0, "ganancia": 0.0, "iva": 0.0},
            )
            bucket["ingresos"] += pedido.total
            bucket["costos"] += pedido.subtotal_base
            bucket["gastos"] += pedido.merma + pedido.riesgo
            bucket["ganancia"] += pedido.ganancia
            bucket["iva"] += pedido.iva

        rows = []
        for periodo in sorted(grouped):
            data = grouped[periodo]
            rows.append({"periodo": periodo, **data})

        self.summary = rows
        self.tree.delete(*self.tree.get_children())
        for row in rows:
            self.tree.insert(
                "",
                tk.END,
                values=(
                    row["periodo"],
                    f"${row['ingresos']:,.2f}",
                    f"${row['costos']:,.2f}",
                    f"${row['gastos']:,.2f}",
                    f"${row['ganancia']:,.2f}",
                    f"${row['iva']:,.2f}",
                ),
            )

        self.orders_tree.delete(*self.orders_tree.get_children())
        moneda = self.config_store.moneda()
        for pedido in filtered_orders:
            self.orders_tree.insert(
                "",
                tk.END,
                iid=pedido.folio,
                values=(
                    pedido.fecha_creacion,
                    pedido.folio,
                    pedido.tipo,
                    pedido.impresora,
                    f"{pedido.total:.2f} {moneda}",
                    f"{pedido.subtotal_base:.2f}",
                    f"{(pedido.merma + pedido.riesgo):.2f}",
                    f"{pedido.ganancia:.2f}",
                    f"{pedido.iva:.2f}",
                    f"{pedido.retencion:.2f}",
                    "Sí" if pedido.facturado else "No",
                ),
            )

    def export_pdf(self) -> None:
        if not self.summary:
            messagebox.showinfo("Exportación", "No hay datos para exportar.", parent=self)
            return
        identity = self.config_store.get_identity()
        filters = self._filters_dict()
        path = export_accounting_pdf(self.summary, filters, identity, Path("reportes"))
        messagebox.showinfo("Exportación", f"PDF generado en {path}", parent=self)

    def export_excel(self) -> None:
        if not self.summary:
            messagebox.showinfo("Exportación", "No hay datos para exportar.", parent=self)
            return
        filters = self._filters_dict()
        identity = self.config_store.get_identity()
        path = export_accounting_excel(self.summary, filters, identity, Path("reportes"))
        messagebox.showinfo("Exportación", f"Archivo generado en {path}", parent=self)

    def _filters_dict(self) -> Dict[str, str]:
        return {
            "Tipo": self.tipo_var.get(),
            "Impresora": self.impresora_var.get(),
            "Facturado": self.facturado_var.get(),
            "Desde": self.fecha_inicio_var.get() or "-",
            "Hasta": self.fecha_fin_var.get() or "-",
        }

    @staticmethod
    def _parse_date(value: str) -> Optional[dt.date]:
        try:
            return dt.datetime.fromisoformat(value).date()
        except Exception:
            return None

    def _update_printer_options(self) -> None:
        printers = sorted({pedido.impresora for pedido in self.orders if pedido.impresora})
        self._printer_options = ["todas", *printers]
        if hasattr(self, "impresora_combo"):
            self.impresora_combo.configure(values=self._printer_options)
            if self.impresora_var.get() not in self._printer_options:
                self.impresora_var.set("todas")

    def _open_invoice(self) -> None:
        selection = self.orders_tree.selection()
        if not selection:
            return
        pedido_id = selection[0]
        pedido = next((order for order in self.orders if order.folio == pedido_id), None)
        if not pedido or not pedido.factura_path:
            messagebox.showinfo("Factura", "El pedido seleccionado no tiene factura adjunta.", parent=self)
            return
        path = Path(pedido.factura_path)
        if not path.exists():
            messagebox.showerror("Factura", "El archivo de la factura no se encontró.", parent=self)
            return
        webbrowser.open(path.as_uri())


__all__ = ["AccountingTab"]
