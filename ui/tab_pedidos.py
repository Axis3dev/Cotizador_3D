"""Orders management tab with filters, segmentation and editing tools."""

from __future__ import annotations

import datetime as dt
import tkinter as tk
from tkinter import messagebox, ttk
from typing import Dict, List, Optional

from tkcalendar import DateEntry

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
        self.filtered_active: List[Pedido] = []
        self.filtered_completed: List[Pedido] = []

        self.estado_var = tk.StringVar(value="todos")
        self.tipo_var = tk.StringVar(value="todos")
        self.fecha_inicio_var = tk.StringVar()
        self.fecha_fin_var = tk.StringVar()

        self.detalle_estado_var = tk.StringVar()
        self.detalle_anticipo_var = tk.StringVar()
        self.detalle_liquidado_var = tk.StringVar()
        self.detalle_fecha_var = tk.StringVar()

        self.selected_order: Optional[Pedido] = None
        self._selected_tree: Optional[ttk.Treeview] = None
        self._active_map: Dict[str, Pedido] = {}
        self._completed_map: Dict[str, Pedido] = {}

        self._build_ui()
        self.refresh()

    # ------------------------------------------------------------------
    def _build_ui(self) -> None:
        self.columnconfigure(0, weight=1)

        filter_frame = ttk.Frame(self)
        filter_frame.grid(row=0, column=0, sticky="ew", padx=8, pady=4)

        ttk.Label(filter_frame, text="Estado:").pack(side=tk.LEFT)
        estado_combo = ttk.Combobox(
            filter_frame,
            textvariable=self.estado_var,
            state="readonly",
            values=["todos", "pendiente", "realizado", "cancelado"],
            width=12,
        )
        estado_combo.pack(side=tk.LEFT, padx=4)
        estado_combo.bind("<<ComboboxSelected>>", lambda _: self.apply_filters())

        ttk.Label(filter_frame, text="Tipo:").pack(side=tk.LEFT)
        tipo_combo = ttk.Combobox(
            filter_frame,
            textvariable=self.tipo_var,
            state="readonly",
            values=["todos", "filamento", "resina"],
            width=12,
        )
        tipo_combo.pack(side=tk.LEFT, padx=4)
        tipo_combo.bind("<<ComboboxSelected>>", lambda _: self.apply_filters())

        ttk.Label(filter_frame, text="Desde:").pack(side=tk.LEFT, padx=(8, 4))
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

        lists_frame = ttk.Frame(self)
        lists_frame.grid(row=1, column=0, sticky="nsew", padx=8, pady=4)
        lists_frame.columnconfigure(0, weight=1)
        lists_frame.columnconfigure(1, weight=1)
        lists_frame.rowconfigure(0, weight=1)

        active_frame, self.active_tree = self._create_tree(lists_frame, "Activos")
        active_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
        completed_frame, self.completed_tree = self._create_tree(lists_frame, "Completados")
        completed_frame.grid(row=0, column=1, sticky="nsew", padx=(6, 0))

        detail_frame = ttk.LabelFrame(self, text="Detalle del pedido")
        detail_frame.grid(row=2, column=0, sticky="ew", padx=8, pady=6)
        detail_frame.columnconfigure(5, weight=1)

        ttk.Label(detail_frame, text="Estado:").grid(row=0, column=0, sticky="w", padx=4, pady=4)
        self.estado_combo = ttk.Combobox(
            detail_frame,
            textvariable=self.detalle_estado_var,
            state="disabled",
            values=["Pendiente", "Realizado", "Cancelado"],
            width=12,
        )
        self.estado_combo.grid(row=0, column=1, padx=4, pady=4)

        ttk.Label(detail_frame, text="Anticipo:").grid(row=0, column=2, sticky="w", padx=4, pady=4)
        self.anticipo_combo = ttk.Combobox(
            detail_frame,
            textvariable=self.detalle_anticipo_var,
            state="disabled",
            values=["Sí", "No"],
            width=8,
        )
        self.anticipo_combo.grid(row=0, column=3, padx=4, pady=4)

        ttk.Label(detail_frame, text="Liquidado:").grid(row=0, column=4, sticky="w", padx=4, pady=4)
        self.liquidado_combo = ttk.Combobox(
            detail_frame,
            textvariable=self.detalle_liquidado_var,
            state="disabled",
            values=["Sí", "No"],
            width=8,
        )
        self.liquidado_combo.grid(row=0, column=5, padx=4, pady=4)

        ttk.Label(detail_frame, text="Fecha estimada:").grid(row=1, column=0, sticky="w", padx=4, pady=4)
        self.fecha_detalle_entry = DateEntry(
            detail_frame,
            textvariable=self.detalle_fecha_var,
            width=12,
            date_pattern="yyyy-mm-dd",
            state="disabled",
        )
        self.fecha_detalle_entry.grid(row=1, column=1, padx=4, pady=4)
        ttk.Button(detail_frame, text="Limpiar fecha", command=self.clear_detalle_fecha).grid(row=1, column=2, padx=4, pady=4)

        ttk.Button(detail_frame, text="Guardar cambios", command=self.save_changes).grid(row=1, column=3, padx=4, pady=4)
        ttk.Button(detail_frame, text="Eliminar", command=self.delete_selected).grid(row=1, column=4, padx=4, pady=4)

    # ------------------------------------------------------------------
    def _create_tree(self, master: ttk.Frame, title: str) -> tuple[ttk.LabelFrame, ttk.Treeview]:
        frame = ttk.LabelFrame(master, text=title)
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(0, weight=1)

        columns = (
            "estado",
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
        tree = ttk.Treeview(frame, columns=columns, show="headings")
        headings = [
            "Estado",
            "Folio",
            "Creación",
            "Entrega",
            "Proyecto",
            "Cliente",
            "Tipo",
            "Impresora",
            "Total",
            "Estatus",
            "Anticipo",
            "Liquidado",
        ]
        for col, text in zip(columns, headings):
            tree.heading(col, text=text)
            width = 110 if col in {"estado", "fecha", "estimada", "tipo"} else 140
            if col in {"folio", "total", "estatus", "anticipo", "liquidado"}:
                width = 120
            tree.column(col, width=width, anchor="center")
        tree.grid(row=0, column=0, sticky="nsew")

        scrollbar = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=tree.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        tree.configure(yscrollcommand=scrollbar.set)

        tree.tag_configure("completado", foreground="#15803d")
        tree.tag_configure("pendiente", foreground="#c2410c")
        tree.tag_configure("vencido", foreground="#b91c1c")

        tree.bind("<<TreeviewSelect>>", lambda _: self._on_tree_select(tree))

        return frame, tree

    # ------------------------------------------------------------------
    def refresh(self) -> None:
        self.orders = self.orders_store.list_orders()
        self.apply_filters()

    # ------------------------------------------------------------------
    def apply_filters(self) -> None:
        inicio = self._parse_date(self.fecha_inicio_var.get())
        fin = self._parse_date(self.fecha_fin_var.get())
        if inicio and fin and inicio > fin:
            messagebox.showerror("Rango inválido", "La fecha inicial no puede ser mayor que la final.", parent=self)
            return

        estado = self.estado_var.get()
        tipo = self.tipo_var.get()

        activos: List[Pedido] = []
        completados: List[Pedido] = []
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
            if self._is_completed(pedido):
                completados.append(pedido)
            else:
                activos.append(pedido)

        self.filtered_active = activos
        self.filtered_completed = completados

        self._active_map = {}
        self._completed_map = {}
        self.active_tree.delete(*self.active_tree.get_children())
        for pedido in activos:
            item = self._insert_order(self.active_tree, pedido)
            self._active_map[item] = pedido
        self.completed_tree.delete(*self.completed_tree.get_children())
        for pedido in completados:
            item = self._insert_order(self.completed_tree, pedido)
            self._completed_map[item] = pedido

        self._clear_detail()

    # ------------------------------------------------------------------
    def clear_filters(self) -> None:
        self.estado_var.set("todos")
        self.tipo_var.set("todos")
        self.fecha_inicio_var.set("")
        self.fecha_fin_var.set("")
        self.fecha_inicio_entry.delete(0, tk.END)
        self.fecha_fin_entry.delete(0, tk.END)
        self.apply_filters()

    # ------------------------------------------------------------------
    def _insert_order(self, tree: ttk.Treeview, pedido: Pedido) -> str:
        tag, estado_text = self._status_tag(pedido)
        values = (
            estado_text,
            pedido.folio,
            pedido.fecha_creacion,
            pedido.fecha_estimada or "-",
            pedido.proyecto,
            pedido.cliente.nombre,
            pedido.tipo,
            pedido.impresora,
            f"{pedido.total:.2f} {pedido.moneda}",
            pedido.estatus.capitalize(),
            "Sí" if pedido.anticipo else "No",
            "Sí" if pedido.liquidado else "No",
        )
        return tree.insert("", tk.END, values=values, tags=(tag,))

    # ------------------------------------------------------------------
    def _status_tag(self, pedido: Pedido) -> tuple[str, str]:
        today = dt.date.today()
        estimada = self._parse_date(pedido.fecha_estimada or "")
        if pedido.estatus == "realizado" and pedido.liquidado:
            return "completado", "● Realizado"
        if pedido.estatus != "realizado":
            if estimada and estimada < today:
                return "vencido", "● Vencido"
            return "pendiente", "● Pendiente"
        if pedido.estatus == "cancelado":
            return "pendiente", "● Cancelado"
        return "pendiente", "● Por cobrar"

    # ------------------------------------------------------------------
    def _on_tree_select(self, tree: ttk.Treeview) -> None:
        mapping = self._active_map if tree is self.active_tree else self._completed_map
        selection = tree.selection()
        if not selection:
            self._clear_detail()
            return
        item = selection[0]
        pedido = mapping.get(item)
        if not pedido:
            self._clear_detail()
            return
        self.selected_order = pedido
        self._selected_tree = tree
        self._set_detail_state(True)
        self.detalle_estado_var.set(pedido.estatus.capitalize())
        self.detalle_anticipo_var.set("Sí" if pedido.anticipo else "No")
        self.detalle_liquidado_var.set("Sí" if pedido.liquidado else "No")
        if pedido.fecha_estimada:
            self.detalle_fecha_var.set(pedido.fecha_estimada)
        else:
            self.detalle_fecha_var.set("")
            self.fecha_detalle_entry.delete(0, tk.END)

    # ------------------------------------------------------------------
    def _clear_detail(self) -> None:
        self.selected_order = None
        self._selected_tree = None
        self.detalle_estado_var.set("")
        self.detalle_anticipo_var.set("")
        self.detalle_liquidado_var.set("")
        self.detalle_fecha_var.set("")
        self.fecha_detalle_entry.delete(0, tk.END)
        self._set_detail_state(False)

    # ------------------------------------------------------------------
    def _set_detail_state(self, enabled: bool) -> None:
        state_combo = "readonly" if enabled else "disabled"
        state_entry = "normal" if enabled else "disabled"
        self.estado_combo.config(state=state_combo)
        self.anticipo_combo.config(state=state_combo)
        self.liquidado_combo.config(state=state_combo)
        self.fecha_detalle_entry.config(state=state_entry)

    # ------------------------------------------------------------------
    def clear_detalle_fecha(self) -> None:
        if self.fecha_detalle_entry.cget("state") == "disabled":
            return
        self.detalle_fecha_var.set("")
        self.fecha_detalle_entry.delete(0, tk.END)

    # ------------------------------------------------------------------
    def save_changes(self) -> None:
        pedido = self.selected_order
        if not pedido:
            return
        estado = self.detalle_estado_var.get().strip().lower()
        if estado not in {"pendiente", "realizado", "cancelado"}:
            messagebox.showerror("Dato inválido", "Selecciona un estado válido.", parent=self)
            return
        anticipo = self.detalle_anticipo_var.get().strip()
        liquidado = self.detalle_liquidado_var.get().strip()
        if anticipo not in {"Sí", "No"} or liquidado not in {"Sí", "No"}:
            messagebox.showerror("Dato inválido", "Selecciona Sí o No para anticipo y liquidado.", parent=self)
            return
        fecha_val = self.detalle_fecha_var.get().strip()
        if fecha_val:
            try:
                fecha_iso = dt.datetime.fromisoformat(fecha_val).date().isoformat()
            except ValueError:
                messagebox.showerror("Fecha inválida", "Usa el formato AAAA-MM-DD.", parent=self)
                return
        else:
            fecha_iso = None

        pedido.estatus = estado
        pedido.anticipo = anticipo == "Sí"
        pedido.liquidado = liquidado == "Sí"
        pedido.fecha_estimada = fecha_iso

        self.orders_store.save(pedido)
        if self.on_status_change:
            self.on_status_change(pedido)
        self.refresh()

    # ------------------------------------------------------------------
    def delete_selected(self) -> None:
        pedido = self.selected_order
        if not pedido:
            return
        if not messagebox.askyesno("Eliminar", f"¿Eliminar el pedido {pedido.folio}?", parent=self):
            return
        self.orders_store.delete(pedido.folio)
        if self.on_status_change:
            self.on_status_change(pedido)
        self.refresh()

    # ------------------------------------------------------------------
    @staticmethod
    def _is_completed(pedido: Pedido) -> bool:
        return pedido.estatus == "realizado" and pedido.liquidado

    # ------------------------------------------------------------------
    @staticmethod
    def _parse_date(value: str) -> Optional[dt.date]:
        if not value:
            return None
        try:
            return dt.datetime.fromisoformat(value).date()
        except Exception:
            return None


__all__ = ["OrdersTab"]
