"""Accounting overview tab."""

from __future__ import annotations

import datetime as dt
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk
from typing import Dict, List, Optional

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
        self.fecha_inicio_var = tk.StringVar()
        self.fecha_fin_var = tk.StringVar()

        self._build_ui()
        self.refresh()

    def _build_ui(self) -> None:
        filter_frame = ttk.Frame(self)
        filter_frame.pack(fill=tk.X, padx=8, pady=4)

        ttk.Label(filter_frame, text="Tipo:").pack(side=tk.LEFT)
        tipo_combo = ttk.Combobox(filter_frame, textvariable=self.tipo_var, state="readonly", values=["todos", "filamento", "resina"], width=12)
        tipo_combo.pack(side=tk.LEFT, padx=4)
        tipo_combo.bind("<<ComboboxSelected>>", lambda _: self.update_summary())

        ttk.Label(filter_frame, text="Desde (AAAA-MM-DD):").pack(side=tk.LEFT, padx=(8, 2))
        ttk.Entry(filter_frame, textvariable=self.fecha_inicio_var, width=12).pack(side=tk.LEFT)
        ttk.Label(filter_frame, text="Hasta:").pack(side=tk.LEFT, padx=(8, 2))
        ttk.Entry(filter_frame, textvariable=self.fecha_fin_var, width=12).pack(side=tk.LEFT)
        ttk.Button(filter_frame, text="Aplicar", command=self.update_summary).pack(side=tk.LEFT, padx=6)

        columns = ("periodo", "ingresos", "costos", "gastos", "ganancia", "iva")
        self.tree = ttk.Treeview(self, columns=columns, show="headings")
        for col, text in zip(columns, ["Periodo", "Ingresos", "Costos", "Gastos", "Ganancia", "IVA"]):
            self.tree.heading(col, text=text)
            self.tree.column(col, width=140, anchor="center")
        self.tree.pack(fill=tk.BOTH, expand=True, padx=8, pady=4)

        button_frame = ttk.Frame(self)
        button_frame.pack(fill=tk.X, padx=8, pady=4)
        ttk.Button(button_frame, text="Exportar PDF", command=self.export_pdf).pack(side=tk.LEFT, padx=4)
        ttk.Button(button_frame, text="Exportar Excel", command=self.export_excel).pack(side=tk.LEFT, padx=4)

    def refresh(self) -> None:
        self.orders = self.orders_store.list_orders()
        self.update_summary()

    def update_summary(self) -> None:
        inicio = self._parse_date(self.fecha_inicio_var.get())
        fin = self._parse_date(self.fecha_fin_var.get())
        tipo = self.tipo_var.get()

        grouped: Dict[str, Dict[str, float]] = {}
        for pedido in self.orders:
            if pedido.estatus != "realizado":
                continue
            if tipo != "todos" and pedido.tipo != tipo:
                continue
            fecha = self._parse_date(pedido.fecha_creacion)
            if inicio and fecha and fecha < inicio:
                continue
            if fin and fecha and fecha > fin:
                continue
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
        path = export_accounting_excel(self.summary, filters, Path("reportes"))
        messagebox.showinfo("Exportación", f"Archivo generado en {path}", parent=self)

    def _filters_dict(self) -> Dict[str, str]:
        return {
            "Tipo": self.tipo_var.get(),
            "Desde": self.fecha_inicio_var.get() or "-",
            "Hasta": self.fecha_fin_var.get() or "-",
        }

    @staticmethod
    def _parse_date(value: str) -> Optional[dt.date]:
        try:
            return dt.datetime.fromisoformat(value).date()
        except Exception:
            return None


__all__ = ["AccountingTab"]
