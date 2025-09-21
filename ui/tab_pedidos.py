"""Tab to manage accepted orders."""

from __future__ import annotations

import datetime as dt
import tkinter as tk
from tkinter import messagebox, simpledialog, ttk
from typing import List, Optional

from models.pedido import Pedido
from storage.orders_store import OrdersStore


class OrdersTab(ttk.Frame):
    def __init__(
        self,
        master: ttk.Notebook,
        orders_store: OrdersStore,
        on_status_change=None,
    ) -> None:
        super().__init__(master)
        self.orders_store = orders_store
        self.on_status_change = on_status_change
        self.orders: List[Pedido] = []
        self.filtered: List[Pedido] = []

        self.estado_var = tk.StringVar(value="todos")
        self.tipo_var = tk.StringVar(value="todos")
        self.fecha_inicio_var = tk.StringVar()
        self.fecha_fin_var = tk.StringVar()

        self._build_ui()
        self.refresh()

    def _build_ui(self) -> None:
        filter_frame = ttk.Frame(self)
        filter_frame.pack(fill=tk.X, padx=8, pady=4)

        ttk.Label(filter_frame, text="Estado:").pack(side=tk.LEFT)
        estado_combo = ttk.Combobox(filter_frame, textvariable=self.estado_var, state="readonly", values=["todos", "pendiente", "realizado", "cancelado"], width=12)
        estado_combo.pack(side=tk.LEFT, padx=4)
        estado_combo.bind("<<ComboboxSelected>>", lambda _: self.apply_filters())

        ttk.Label(filter_frame, text="Tipo:").pack(side=tk.LEFT)
        tipo_combo = ttk.Combobox(filter_frame, textvariable=self.tipo_var, state="readonly", values=["todos", "filamento", "resina"], width=12)
        tipo_combo.pack(side=tk.LEFT, padx=4)
        tipo_combo.bind("<<ComboboxSelected>>", lambda _: self.apply_filters())

        ttk.Label(filter_frame, text="Desde (AAAA-MM-DD):").pack(side=tk.LEFT, padx=(8, 2))
        ttk.Entry(filter_frame, textvariable=self.fecha_inicio_var, width=12).pack(side=tk.LEFT)
        ttk.Label(filter_frame, text="Hasta:").pack(side=tk.LEFT, padx=(8, 2))
        ttk.Entry(filter_frame, textvariable=self.fecha_fin_var, width=12).pack(side=tk.LEFT)
        ttk.Button(filter_frame, text="Filtrar", command=self.apply_filters).pack(side=tk.LEFT, padx=6)

        columns = (
            "folio",
            "fecha",
            "estimada",
            "proyecto",
            "cliente",
            "tipo",
            "impresora",
            "total",
            "estatus",
            "anticipo",
            "liquidado",
        )
        self.tree = ttk.Treeview(self, columns=columns, show="headings")
        for col, text in zip(
            columns,
            [
                "Folio",
                "Fecha",
                "Entrega",
                "Proyecto",
                "Cliente",
                "Tipo",
                "Impresora",
                "Total",
                "Estatus",
                "Anticipo",
                "Liquidado",
            ],
        ):
            self.tree.heading(col, text=text)
            self.tree.column(col, width=120, anchor="center")
        self.tree.pack(fill=tk.BOTH, expand=True, padx=8, pady=4)

        button_frame = ttk.Frame(self)
        button_frame.pack(fill=tk.X, padx=8, pady=4)
        ttk.Button(button_frame, text="Cambiar estatus", command=self.change_status).pack(side=tk.LEFT, padx=4)
        ttk.Button(button_frame, text="Fecha estimada", command=self.edit_fecha_estimada).pack(side=tk.LEFT, padx=4)
        ttk.Button(button_frame, text="Alternar anticipo", command=self.toggle_anticipo).pack(side=tk.LEFT, padx=4)
        ttk.Button(button_frame, text="Alternar liquidado", command=self.toggle_liquidado).pack(side=tk.LEFT, padx=4)
        ttk.Button(button_frame, text="Eliminar", command=self.delete_selected).pack(side=tk.RIGHT, padx=4)

    def refresh(self) -> None:
        self.orders = self.orders_store.list_orders()
        self.apply_filters()

    def apply_filters(self) -> None:
        estado = self.estado_var.get()
        tipo = self.tipo_var.get()
        inicio = self._parse_date(self.fecha_inicio_var.get())
        fin = self._parse_date(self.fecha_fin_var.get())

        filtered: List[Pedido] = []
        for pedido in self.orders:
            if estado != "todos" and pedido.estatus != estado:
                continue
            if tipo != "todos" and pedido.tipo != tipo:
                continue
            fecha = self._parse_date(pedido.fecha_creacion)
            if inicio and fecha and fecha < inicio:
                continue
            if fin and fecha and fecha > fin:
                continue
            filtered.append(pedido)

        self.filtered = filtered
        self.tree.delete(*self.tree.get_children())
        for pedido in filtered:
            self.tree.insert(
                "",
                tk.END,
                values=(
                    pedido.folio,
                    pedido.fecha_creacion,
                    pedido.fecha_estimada or "-",
                    pedido.proyecto,
                    pedido.cliente.nombre,
                    pedido.tipo,
                    pedido.impresora,
                    f"{pedido.total:.2f} {pedido.moneda}",
                    pedido.estatus,
                    "Sí" if pedido.anticipo else "No",
                    "Sí" if pedido.liquidado else "No",
                ),
            )

    def get_selected(self) -> Optional[Pedido]:
        selection = self.tree.selection()
        if not selection:
            return None
        index = self.tree.index(selection[0])
        if index >= len(self.filtered):
            return None
        return self.filtered[index]

    def change_status(self) -> None:
        pedido = self.get_selected()
        if not pedido:
            return
        new_status = simpledialog.askstring(
            "Estatus",
            "Nuevo estatus (pendiente/realizado/cancelado):",
            parent=self,
            initialvalue=pedido.estatus,
        )
        if not new_status:
            return
        new_status = new_status.strip().lower()
        if new_status not in {"pendiente", "realizado", "cancelado"}:
            messagebox.showerror("Estatus inválido", "Ingresa pendiente, realizado o cancelado.", parent=self)
            return
        pedido.estatus = new_status
        self.orders_store.save(pedido)
        if self.on_status_change:
            self.on_status_change(pedido)
        self.refresh()

    def edit_fecha_estimada(self) -> None:
        pedido = self.get_selected()
        if not pedido:
            return
        nueva_fecha = simpledialog.askstring(
            "Fecha estimada",
            "Nueva fecha estimada (AAAA-MM-DD):",
            parent=self,
            initialvalue=pedido.fecha_estimada or "",
        )
        if nueva_fecha is None:
            return
        nueva_fecha = nueva_fecha.strip()
        if nueva_fecha and not self._parse_date(nueva_fecha):
            messagebox.showerror("Fecha inválida", "Usa el formato AAAA-MM-DD.", parent=self)
            return
        pedido.fecha_estimada = nueva_fecha or None
        self.orders_store.save(pedido)
        self.refresh()

    def toggle_anticipo(self) -> None:
        pedido = self.get_selected()
        if not pedido:
            return
        pedido.anticipo = not pedido.anticipo
        self.orders_store.save(pedido)
        self.refresh()

    def toggle_liquidado(self) -> None:
        pedido = self.get_selected()
        if not pedido:
            return
        pedido.liquidado = not pedido.liquidado
        self.orders_store.save(pedido)
        self.refresh()

    def delete_selected(self) -> None:
        pedido = self.get_selected()
        if not pedido:
            return
        if messagebox.askyesno("Eliminar", f"¿Eliminar el pedido {pedido.folio}?", parent=self):
            self.orders_store.delete(pedido.folio)
            self.refresh()

    @staticmethod
    def _parse_date(value: str) -> Optional[dt.date]:
        try:
            return dt.datetime.fromisoformat(value).date()
        except Exception:
            return None


__all__ = ["OrdersTab"]
