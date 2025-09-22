"""Orders management tab with filters, segmentation and editing tools."""

from __future__ import annotations

import datetime as dt
import shutil
import tkinter as tk
import webbrowser
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Dict, List, Optional

from tkcalendar import DateEntry

from export.pdf_invoice_request import export_invoice_request_pdf
from models.cliente import Cliente, ClienteInfo
from models.cotizacion import Cotizacion
from models.pedido import Pedido
from storage.clients_store import ClientsStore
from storage.config_store import ConfigStore
from storage.orders_store import OrdersStore
from storage.quotes_store import QuoteStore
from utils import MessagingError, send_email_with_attachment


FACTURAS_DIR = Path("facturas")
SOLICITUDES_DIR = Path("solicitudes_facturacion")
FACTURAS_DIR.mkdir(parents=True, exist_ok=True)
SOLICITUDES_DIR.mkdir(parents=True, exist_ok=True)


class InvoiceRequestDialog(tk.Toplevel):
    """Modal dialog to capture billing data and generate invoice requests."""

    def __init__(
        self,
        master: tk.Widget,
        pedido: Pedido,
        quote: Optional[Cotizacion],
        cliente: Optional[Cliente],
        clients_store: ClientsStore,
        config_store: ConfigStore,
    ) -> None:
        super().__init__(master)
        self.title("Solicitud de facturación")
        self.geometry("900x650")
        self.resizable(False, False)
        self.transient(master)
        self.grab_set()

        self.pedido = pedido
        self.quote = quote
        self.cliente = cliente
        self.clients_store = clients_store
        self.config_store = config_store
        self.generated_path: Optional[Path] = None
        self.updated_cliente: Optional[Cliente] = None

        self.nombre_var = tk.StringVar(value=(cliente.nombre if cliente else pedido.cliente.nombre))
        self.correo_var = tk.StringVar(value=(cliente.correo if cliente else pedido.cliente.correo))
        self.telefono_var = tk.StringVar(value=(cliente.celular if cliente else pedido.cliente.celular))
        self.rfc_var = tk.StringVar(value=(cliente.rfc if cliente else ""))
        self.razon_var = tk.StringVar(value=(cliente.razon_social if cliente else ""))
        self.domicilio_var = tk.StringVar(value=(cliente.domicilio_fiscal if cliente else ""))
        self.cp_var = tk.StringVar(value=(cliente.codigo_postal if cliente else ""))
        self.regimen_var = tk.StringVar(value=(cliente.regimen if cliente else ""))
        self.ciudad_var = tk.StringVar(value=(cliente.ciudad if cliente else ""))
        self.estado_var = tk.StringVar(value=(cliente.estado if cliente else ""))

        self._build_ui()

    def _build_ui(self) -> None:
        frame = ttk.Frame(self)
        frame.pack(fill=tk.BOTH, expand=True, padx=12, pady=12)
        labels = [
            ("Nombre", self.nombre_var),
            ("Correo", self.correo_var),
            ("Teléfono", self.telefono_var),
            ("RFC", self.rfc_var),
            ("Razón social", self.razon_var),
            ("Domicilio fiscal", self.domicilio_var),
            ("Código postal", self.cp_var),
            ("Régimen", self.regimen_var),
            ("Ciudad", self.ciudad_var),
            ("Estado", self.estado_var),
        ]
        for idx, (label, var) in enumerate(labels):
            ttk.Label(frame, text=f"{label}:").grid(row=idx, column=0, sticky="w", padx=6, pady=4)
            ttk.Entry(frame, textvariable=var, width=40).grid(row=idx, column=1, sticky="ew", padx=6, pady=4)
        frame.columnconfigure(1, weight=1)

        buttons = ttk.Frame(self)
        buttons.pack(fill=tk.X, padx=12, pady=12)
        ttk.Button(buttons, text="Guardar y generar PDF", command=self.generate_pdf).pack(side=tk.LEFT, padx=4)
        ttk.Button(buttons, text="Enviar a contador", command=self.send_to_accountant).pack(side=tk.LEFT, padx=4)
        ttk.Button(buttons, text="Cerrar", command=self.destroy).pack(side=tk.RIGHT, padx=4)

    def _update_client(self) -> Cliente:
        cliente_id = self.cliente.id if self.cliente else self.pedido.cliente.id
        info = ClienteInfo(
            id=cliente_id,
            nombre=self.nombre_var.get().strip() or self.pedido.cliente.nombre,
            correo=self.correo_var.get().strip(),
            celular=self.telefono_var.get().strip(),
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
        self.cliente = cliente
        self.updated_cliente = cliente
        return cliente

    def generate_pdf(self) -> None:
        cliente = self._update_client()
        identity = self.config_store.get_identity()
        path = export_invoice_request_pdf(self.pedido, self.quote, identity, cliente, SOLICITUDES_DIR)
        self.generated_path = path
        messagebox.showinfo("Solicitud", f"Se generó la solicitud en {path}", parent=self)

    def send_to_accountant(self) -> None:
        if not self.generated_path:
            self.generate_pdf()
        if not self.generated_path:
            return
        integrations = self.config_store.get_integrations()
        email_cfg = dict(integrations.get("email", {}))
        destino = email_cfg.get("contador") or email_cfg.get("contador_email")
        if not destino:
            messagebox.showerror("Integración", "Configura el correo del contador en Integraciones.", parent=self)
            return
        asunto = f"Solicitud de facturación {self.pedido.folio}"
        cuerpo = email_cfg.get("mensaje_contador", "Adjuntamos la solicitud de facturación.")
        try:
            send_email_with_attachment(email_cfg, destino, asunto, cuerpo, self.generated_path)
        except MessagingError as exc:  # pragma: no cover - network
            messagebox.showerror("Correo", str(exc), parent=self)
            return
        messagebox.showinfo("Correo", "Solicitud enviada al contador.", parent=self)
class OrdersTab(ttk.Frame):
    def __init__(
        self,
        master: ttk.Notebook,
        orders_store: OrdersStore,
        on_status_change=None,
        *,
        clients_store: ClientsStore,
        config_store: ConfigStore,
        quote_store: QuoteStore,
    ) -> None:
        super().__init__(master)
        self.orders_store = orders_store
        self.clients_store = clients_store
        self.config_store = config_store
        self.quote_store = quote_store
        self.on_status_change = on_status_change

        self.orders: List[Pedido] = []
        self.filtered_active: List[Pedido] = []
        self.filtered_completed: List[Pedido] = []

        self.estado_var = tk.StringVar(value="todos")
        self.tipo_var = tk.StringVar(value="todos")
        self.impresora_var = tk.StringVar(value="todas")
        self.facturado_var = tk.StringVar(value="todos")
        self.fecha_inicio_var = tk.StringVar()
        self.fecha_fin_var = tk.StringVar()

        self.detalle_estado_var = tk.StringVar()
        self.detalle_anticipo_var = tk.StringVar()
        self.detalle_liquidado_var = tk.StringVar()
        self.detalle_fecha_var = tk.StringVar()
        self.detalle_facturado_var = tk.StringVar()
        self.detalle_retencion_var = tk.StringVar(value="0.0")
        self.detalle_factura_num_var = tk.StringVar()

        self.selected_order: Optional[Pedido] = None
        self._selected_tree: Optional[ttk.Treeview] = None
        self._active_map: Dict[str, Pedido] = {}
        self._completed_map: Dict[str, Pedido] = {}
        self._printer_options: List[str] = ["todas"]
        self._factura_temp: Optional[Path] = None

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

        ttk.Label(filter_frame, text="Impresora:").pack(side=tk.LEFT, padx=(8, 4))
        self.impresora_combo = ttk.Combobox(
            filter_frame,
            textvariable=self.impresora_var,
            state="readonly",
            values=self._printer_options,
            width=18,
        )
        self.impresora_combo.pack(side=tk.LEFT)
        self.impresora_combo.bind("<<ComboboxSelected>>", lambda _: self.apply_filters())

        ttk.Label(filter_frame, text="Facturado:").pack(side=tk.LEFT, padx=(8, 4))
        facturado_combo = ttk.Combobox(
            filter_frame,
            textvariable=self.facturado_var,
            state="readonly",
            values=["todos", "sí", "no"],
            width=10,
        )
        facturado_combo.pack(side=tk.LEFT)
        facturado_combo.bind("<<ComboboxSelected>>", lambda _: self.apply_filters())

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
        lists_frame.rowconfigure(0, weight=1)
        lists_frame.rowconfigure(1, weight=1)

        active_frame, self.active_tree = self._create_tree(lists_frame, "Activos")
        active_frame.grid(row=0, column=0, sticky="nsew", pady=(0, 8))
        completed_frame, self.completed_tree = self._create_tree(lists_frame, "Completados")
        completed_frame.grid(row=1, column=0, sticky="nsew")

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

        ttk.Label(detail_frame, text="Facturado:").grid(row=1, column=3, sticky="w", padx=4, pady=4)
        self.facturado_combo = ttk.Combobox(
            detail_frame,
            textvariable=self.detalle_facturado_var,
            state="disabled",
            values=["Sí", "No"],
            width=8,
        )
        self.facturado_combo.grid(row=1, column=4, padx=4, pady=4)

        ttk.Label(detail_frame, text="No. factura:").grid(row=1, column=5, sticky="w", padx=4, pady=4)
        self.factura_num_entry = ttk.Entry(detail_frame, textvariable=self.detalle_factura_num_var, state="disabled", width=18)
        self.factura_num_entry.grid(row=1, column=6, padx=4, pady=4)

        ttk.Label(detail_frame, text="Retención:").grid(row=2, column=0, sticky="w", padx=4, pady=4)
        self.retencion_entry = ttk.Entry(detail_frame, textvariable=self.detalle_retencion_var, state="disabled", width=12)
        self.retencion_entry.grid(row=2, column=1, padx=4, pady=4)

        self.adjuntar_factura_btn = ttk.Button(detail_frame, text="Adjuntar factura", command=self.choose_invoice_file, state="disabled")
        self.adjuntar_factura_btn.grid(row=2, column=2, padx=4, pady=4)
        self.abrir_factura_btn = ttk.Button(detail_frame, text="Abrir factura", command=self.open_invoice, state="disabled")
        self.abrir_factura_btn.grid(row=2, column=3, padx=4, pady=4)

        ttk.Button(detail_frame, text="Facturar", command=self.facturar_pedido).grid(row=2, column=4, padx=4, pady=4)
        ttk.Button(detail_frame, text="Guardar cambios", command=self.save_changes).grid(row=2, column=5, padx=4, pady=4)
        ttk.Button(detail_frame, text="Eliminar", command=self.delete_selected).grid(row=2, column=6, padx=4, pady=4)

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
            "facturado",
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
            "Facturado",
        ]
        for col, text in zip(columns, headings):
            tree.heading(col, text=text)
            width = 110 if col in {"estado", "fecha", "estimada", "tipo"} else 140
            if col in {"folio", "total", "estatus", "anticipo", "liquidado", "facturado"}:
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
        self.clients_store.sync_totals(self.orders)
        self._update_printer_options()
        self.apply_filters()

    def _update_printer_options(self) -> None:
        printers = sorted({pedido.impresora for pedido in self.orders if pedido.impresora})
        self._printer_options = ["todas", *printers]
        if hasattr(self, "impresora_combo"):
            self.impresora_combo.configure(values=self._printer_options)
            if self.impresora_var.get() not in self._printer_options:
                self.impresora_var.set("todas")

    # ------------------------------------------------------------------
    def apply_filters(self) -> None:
        inicio = self._parse_date(self.fecha_inicio_var.get())
        fin = self._parse_date(self.fecha_fin_var.get())
        if inicio and fin and inicio > fin:
            messagebox.showerror("Rango inválido", "La fecha inicial no puede ser mayor que la final.", parent=self)
            return

        estado = self.estado_var.get()
        tipo = self.tipo_var.get()
        impresora = self.impresora_var.get()
        facturado = self.facturado_var.get()

        activos: List[Pedido] = []
        completados: List[Pedido] = []
        for pedido in self.orders:
            if estado != "todos" and pedido.estatus != estado:
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
        self.impresora_var.set("todas")
        self.facturado_var.set("todos")
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
            "Sí" if pedido.facturado else "No",
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
        self.detalle_facturado_var.set("Sí" if pedido.facturado else "No")
        self.detalle_retencion_var.set(f"{pedido.retencion:.2f}")
        self.detalle_factura_num_var.set(pedido.numero_factura or "")
        self._factura_temp = None
        self._update_invoice_buttons(pedido)

    # ------------------------------------------------------------------
    def _clear_detail(self) -> None:
        self.selected_order = None
        self._selected_tree = None
        self.detalle_estado_var.set("")
        self.detalle_anticipo_var.set("")
        self.detalle_liquidado_var.set("")
        self.detalle_fecha_var.set("")
        self.fecha_detalle_entry.delete(0, tk.END)
        self.detalle_facturado_var.set("")
        self.detalle_retencion_var.set("0.0")
        self.detalle_factura_num_var.set("")
        self._factura_temp = None
        self._update_invoice_buttons(None)
        self._set_detail_state(False)

    # ------------------------------------------------------------------
    def _set_detail_state(self, enabled: bool) -> None:
        state_combo = "readonly" if enabled else "disabled"
        state_entry = "normal" if enabled else "disabled"
        self.estado_combo.config(state=state_combo)
        self.anticipo_combo.config(state=state_combo)
        self.liquidado_combo.config(state=state_combo)
        self.fecha_detalle_entry.config(state=state_entry)
        self.facturado_combo.config(state=state_combo)
        self.factura_num_entry.config(state=state_entry)
        self.retencion_entry.config(state=state_entry)
        self.adjuntar_factura_btn.config(state="normal" if enabled else "disabled")
        if not enabled:
            self.abrir_factura_btn.config(state="disabled")

    def _update_invoice_buttons(self, pedido: Optional[Pedido]) -> None:
        if pedido and pedido.factura_path:
            path = Path(pedido.factura_path)
            self.abrir_factura_btn.config(state="normal" if path.exists() else "disabled")
        else:
            self.abrir_factura_btn.config(state="disabled")

    def _copy_invoice_file(self, pedido: Pedido, numero_factura: str) -> Path:
        if not self._factura_temp:
            raise ValueError("No hay archivo temporal de factura")
        destino = FACTURAS_DIR / f"FAC_{pedido.folio}_{numero_factura}.pdf"
        destino.parent.mkdir(parents=True, exist_ok=True)
        try:
            shutil.copy(self._factura_temp, destino)
        except Exception as exc:  # pragma: no cover - filesystem
            messagebox.showerror("Factura", f"No se pudo copiar la factura: {exc}", parent=self)
            raise
        return destino

    # ------------------------------------------------------------------
    def clear_detalle_fecha(self) -> None:
        if self.fecha_detalle_entry.cget("state") == "disabled":
            return
        self.detalle_fecha_var.set("")
        self.fecha_detalle_entry.delete(0, tk.END)

    def choose_invoice_file(self) -> None:
        if not self.selected_order or self.adjuntar_factura_btn.cget("state") == "disabled":
            return
        path = filedialog.askopenfilename(parent=self, filetypes=[("PDF", "*.pdf")])
        if not path:
            return
        self._factura_temp = Path(path)
        messagebox.showinfo("Factura", f"Archivo seleccionado: {self._factura_temp.name}", parent=self)

    def open_invoice(self) -> None:
        pedido = self.selected_order
        if not pedido or not pedido.factura_path:
            return
        path = Path(pedido.factura_path)
        if not path.exists():
            messagebox.showerror("Factura", "No se encontró el PDF de la factura.", parent=self)
            return
        webbrowser.open(path.as_uri())

    def facturar_pedido(self) -> None:
        pedido = self.selected_order
        if not pedido:
            messagebox.showinfo("Pedidos", "Selecciona un pedido para facturar.", parent=self)
            return
        quote = self.quote_store.load(pedido.folio_cotizacion)
        cliente = None
        if pedido.cliente.id:
            cliente = self.clients_store.get(pedido.cliente.id)
        if not cliente:
            cliente = self.clients_store.find(pedido.cliente.correo, pedido.cliente.celular)
        dialog = InvoiceRequestDialog(self, pedido, quote, cliente, self.clients_store, self.config_store)
        self.wait_window(dialog)
        if dialog.updated_cliente:
            updated = dialog.updated_cliente
            pedido.cliente.id = updated.id
            pedido.cliente.nombre = updated.nombre
            pedido.cliente.correo = updated.correo
            pedido.cliente.celular = updated.celular
            self.orders_store.save(pedido)
            self.clients_store.sync_totals(self.orders_store.list_orders())
        self.refresh()

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

        facturado_val = self.detalle_facturado_var.get().strip().lower()
        if facturado_val not in {"sí", "no"}:
            messagebox.showerror("Dato inválido", "Selecciona Sí o No para facturado.", parent=self)
            return
        numero_factura = self.detalle_factura_num_var.get().strip()
        try:
            retencion = float(self.detalle_retencion_var.get() or 0.0)
        except ValueError:
            messagebox.showerror("Dato inválido", "La retención debe ser numérica.", parent=self)
            return
        if retencion < 0:
            messagebox.showerror("Dato inválido", "La retención no puede ser negativa.", parent=self)
            return
        if facturado_val == "sí" and not numero_factura:
            messagebox.showerror("Dato faltante", "Indica el número de factura.", parent=self)
            return

        pedido.estatus = estado
        pedido.anticipo = anticipo == "Sí"
        pedido.liquidado = liquidado == "Sí"
        pedido.fecha_estimada = fecha_iso
        pedido.retencion = retencion

        if facturado_val == "sí":
            pedido.facturado = True
            pedido.numero_factura = numero_factura
            if self._factura_temp:
                try:
                    copied = self._copy_invoice_file(pedido, numero_factura)
                except Exception:
                    return
                pedido.factura_path = str(copied)
            elif not pedido.factura_path or not Path(pedido.factura_path).exists():
                messagebox.showerror(
                    "Factura",
                    "Adjunta el PDF de la factura para marcar como facturado.",
                    parent=self,
                )
                return
        else:
            pedido.facturado = False
            pedido.numero_factura = None
            pedido.factura_path = None

        self._factura_temp = None

        self.orders_store.save(pedido)
        self.clients_store.sync_totals(self.orders_store.list_orders())
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
