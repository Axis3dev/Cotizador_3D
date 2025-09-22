"""Clients catalog tab."""

from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk
from typing import Dict, List, Optional

from models.cliente import Cliente, ClienteInfo
from models.pedido import Pedido
from storage.clients_store import ClientsStore
from storage.config_store import ConfigStore
from storage.orders_store import OrdersStore


class ClientsTab(ttk.Frame):
    def __init__(
        self,
        master: ttk.Notebook,
        clients_store: ClientsStore,
        orders_store: OrdersStore,
        config_store: ConfigStore,
    ) -> None:
        super().__init__(master)
        self.clients_store = clients_store
        self.orders_store = orders_store
        self.config_store = config_store

        self.clients: List[Cliente] = []
        self.orders: List[Pedido] = []
        self.metrics: Dict[str, Dict[str, float]] = {}
        self._client_map: Dict[str, Cliente] = {}
        self.selected_client_id: Optional[str] = None

        self.nombre_var = tk.StringVar()
        self.correo_var = tk.StringVar()
        self.telefono_var = tk.StringVar()
        self.rfc_var = tk.StringVar()
        self.razon_var = tk.StringVar()
        self.domicilio_var = tk.StringVar()
        self.cp_var = tk.StringVar()
        self.regimen_var = tk.StringVar()
        self.ciudad_var = tk.StringVar()
        self.estado_var = tk.StringVar()

        self._build_ui()
        self.refresh()

    def _build_ui(self) -> None:
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        clients_frame = ttk.LabelFrame(self, text="Clientes")
        clients_frame.grid(row=0, column=0, sticky="nsew", padx=8, pady=6)
        clients_frame.columnconfigure(0, weight=1)
        clients_frame.rowconfigure(0, weight=1)

        columns = (
            "nombre",
            "telefono",
            "correo",
            "rfc",
            "ingresos",
            "costos",
            "gastos",
            "ganancia",
            "iva",
            "retencion",
            "neto",
        )
        headings = [
            "Nombre",
            "Teléfono",
            "Correo",
            "RFC",
            "Total Ingresos",
            "Total Costos",
            "Total Gastos",
            "Total Ganancia",
            "IVA",
            "Retención",
            "Total Neto",
        ]
        self.clients_tree = ttk.Treeview(clients_frame, columns=columns, show="headings")
        for col, text in zip(columns, headings):
            self.clients_tree.heading(col, text=text)
            width = 150
            if col in {"nombre", "correo"}:
                width = 200
            self.clients_tree.column(col, width=width, anchor="center")
        self.clients_tree.grid(row=0, column=0, sticky="nsew")
        scrollbar = ttk.Scrollbar(clients_frame, orient=tk.VERTICAL, command=self.clients_tree.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.clients_tree.configure(yscrollcommand=scrollbar.set)
        self.clients_tree.bind("<<TreeviewSelect>>", lambda _: self._on_client_select())

        orders_frame = ttk.LabelFrame(self, text="Historial de pedidos")
        orders_frame.grid(row=1, column=0, sticky="nsew", padx=8, pady=6)
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
                width = 150
            self.orders_tree.column(col, width=width, anchor="center")
        self.orders_tree.grid(row=0, column=0, sticky="nsew")
        order_scroll = ttk.Scrollbar(orders_frame, orient=tk.VERTICAL, command=self.orders_tree.yview)
        order_scroll.grid(row=0, column=1, sticky="ns")
        self.orders_tree.configure(yscrollcommand=order_scroll.set)

        buttons = ttk.Frame(orders_frame)
        buttons.grid(row=1, column=0, sticky="e", pady=6)
        ttk.Button(buttons, text="Abrir factura", command=self._open_invoice).pack(side=tk.LEFT, padx=4)

        form = ttk.LabelFrame(self, text="Datos del cliente")
        form.grid(row=2, column=0, sticky="ew", padx=8, pady=6)
        for col in range(4):
            form.columnconfigure(col, weight=1)

        fields = [
            ("Nombre", self.nombre_var),
            ("Correo", self.correo_var),
            ("Teléfono", self.telefono_var),
            ("RFC", self.rfc_var),
            ("Razón social", self.razon_var),
            ("Domicilio", self.domicilio_var),
            ("CP", self.cp_var),
            ("Régimen", self.regimen_var),
            ("Ciudad", self.ciudad_var),
            ("Estado", self.estado_var),
        ]
        for idx, (label, var) in enumerate(fields):
            ttk.Label(form, text=f"{label}:").grid(row=idx // 2, column=(idx % 2) * 2, sticky="w", padx=6, pady=4)
            ttk.Entry(form, textvariable=var, width=32).grid(row=idx // 2, column=(idx % 2) * 2 + 1, sticky="ew", padx=6, pady=4)

        action_frame = ttk.Frame(form)
        action_frame.grid(row=5, column=0, columnspan=4, sticky="e", pady=8)
        ttk.Button(action_frame, text="Nuevo", command=self._new_client).pack(side=tk.LEFT, padx=4)
        ttk.Button(action_frame, text="Guardar", command=self._save_client).pack(side=tk.LEFT, padx=4)

    # ------------------------------------------------------------------
    def refresh(self) -> None:
        self.orders = self.orders_store.list_orders()
        self.clients = self.clients_store.list_clients()
        self.metrics = self._build_metrics()
        self._client_map = {client.id: client for client in self.clients}

        self.clients_tree.delete(*self.clients_tree.get_children())
        for client in sorted(self.clients, key=lambda c: c.nombre.lower()):
            data = self.metrics.get(client.id, {})
            self.clients_tree.insert(
                "",
                tk.END,
                iid=client.id,
                values=(
                    client.nombre,
                    client.celular,
                    client.correo,
                    client.rfc,
                    f"${data.get('ingresos', 0.0):,.2f}",
                    f"${data.get('costos', 0.0):,.2f}",
                    f"${data.get('gastos', 0.0):,.2f}",
                    f"${data.get('ganancia', 0.0):,.2f}",
                    f"${data.get('iva', 0.0):,.2f}",
                    f"${data.get('retencion', 0.0):,.2f}",
                    f"${data.get('neto', 0.0):,.2f}",
                ),
            )
        self._clear_form()
        self.orders_tree.delete(*self.orders_tree.get_children())

    # ------------------------------------------------------------------
    def _build_metrics(self) -> Dict[str, Dict[str, float]]:
        metrics: Dict[str, Dict[str, float]] = {}
        for pedido in self.orders:
            cliente_id = pedido.cliente.id or self._find_client_id(pedido)
            if not cliente_id:
                continue
            bucket = metrics.setdefault(
                cliente_id,
                {
                    "ingresos": 0.0,
                    "costos": 0.0,
                    "gastos": 0.0,
                    "ganancia": 0.0,
                    "iva": 0.0,
                    "retencion": 0.0,
                    "neto": 0.0,
                },
            )
            bucket["ingresos"] += pedido.total
            bucket["costos"] += pedido.subtotal_base
            bucket["gastos"] += pedido.merma + pedido.riesgo
            bucket["ganancia"] += pedido.ganancia
            bucket["iva"] += pedido.iva
            bucket["retencion"] += pedido.retencion
            bucket["neto"] += pedido.total - pedido.retencion
        return metrics

    def _find_client_id(self, pedido: Pedido) -> Optional[str]:
        cliente = self.clients_store.find(pedido.cliente.correo, pedido.cliente.celular)
        return cliente.id if cliente else None

    # ------------------------------------------------------------------
    def _on_client_select(self) -> None:
        selection = self.clients_tree.selection()
        if not selection:
            self.selected_client_id = None
            self._clear_form()
            self.orders_tree.delete(*self.orders_tree.get_children())
            return
        client_id = selection[0]
        client = self._client_map.get(client_id)
        if not client:
            return
        self.selected_client_id = client_id
        self.nombre_var.set(client.nombre)
        self.correo_var.set(client.correo)
        self.telefono_var.set(client.celular)
        self.rfc_var.set(client.rfc)
        self.razon_var.set(client.razon_social)
        self.domicilio_var.set(client.domicilio_fiscal)
        self.cp_var.set(client.codigo_postal)
        self.regimen_var.set(client.regimen)
        self.ciudad_var.set(client.ciudad)
        self.estado_var.set(client.estado)

        self.orders_tree.delete(*self.orders_tree.get_children())
        moneda = self.config_store.moneda()
        for pedido in self._orders_for_client(client_id):
            self.orders_tree.insert(
                "",
                tk.END,
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
                iid=pedido.folio,
            )

    def _orders_for_client(self, client_id: str) -> List[Pedido]:
        result: List[Pedido] = []
        for pedido in self.orders:
            pid = pedido.cliente.id or self._find_client_id(pedido)
            if pid == client_id:
                result.append(pedido)
        return result

    # ------------------------------------------------------------------
    def _open_invoice(self) -> None:
        selection = self.orders_tree.selection()
        if not selection:
            return
        pedido_id = selection[0]
        pedido = next((p for p in self.orders if p.folio == pedido_id), None)
        if not pedido or not pedido.factura_path:
            messagebox.showinfo("Factura", "No hay factura asociada a este pedido.", parent=self)
            return
        path = Path(pedido.factura_path)
        if not path.exists():
            messagebox.showerror("Factura", "El archivo de la factura no se encuentra disponible.", parent=self)
            return
        import webbrowser

        webbrowser.open(path.as_uri())

    # ------------------------------------------------------------------
    def _new_client(self) -> None:
        self.selected_client_id = None
        self._clear_form()

    def _save_client(self) -> None:
        nombre = self.nombre_var.get().strip()
        if not nombre:
            messagebox.showerror("Dato faltante", "El nombre es obligatorio.", parent=self)
            return
        correo = self.correo_var.get().strip()
        celular = self.telefono_var.get().strip()
        info = ClienteInfo(
            id=self.selected_client_id,
            nombre=nombre,
            correo=correo,
            celular=celular,
            rfc=self.rfc_var.get().strip(),
        )
        extra = {
            "rfc": self.rfc_var.get().strip(),
            "razon_social": self.razon_var.get().strip(),
            "domicilio_fiscal": self.domicilio_var.get().strip(),
            "codigo_postal": self.cp_var.get().strip(),
            "regimen": self.regimen_var.get().strip(),
            "ciudad": self.ciudad_var.get().strip(),
            "estado": self.estado_var.get().strip(),
        }
        cliente = self.clients_store.upsert(info, extra=extra)
        self.selected_client_id = cliente.id
        self.refresh()
        messagebox.showinfo("Clientes", "Los datos del cliente se guardaron correctamente.", parent=self)

    def _clear_form(self) -> None:
        self.nombre_var.set("")
        self.correo_var.set("")
        self.telefono_var.set("")
        self.rfc_var.set("")
        self.razon_var.set("")
        self.domicilio_var.set("")
        self.cp_var.set("")
        self.regimen_var.set("")
        self.ciudad_var.set("")
        self.estado_var.set("")


__all__ = ["ClientsTab"]
