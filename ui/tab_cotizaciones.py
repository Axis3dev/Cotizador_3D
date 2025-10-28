"""Tab to manage saved quotations."""

from __future__ import annotations

import datetime as dt
import tempfile
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Callable, Dict, List, Optional

from tkcalendar import DateEntry

from export.csv_quote import export_quote_csv
from export.pdf_quote import export_quote_pdf
from models.cotizacion import Cotizacion
from storage.config_store import ConfigStore
from storage.orders_store import OrdersStore
from storage.quotes_store import QuoteStore
from utils import MessagingError, send_email_with_pdf, send_whatsapp_placeholder


class QuotesTab(ttk.Frame):
    def __init__(
        self,
        master: ttk.Notebook,
        quote_store: QuoteStore,
        orders_store: OrdersStore,
        config_store: ConfigStore,
        on_view: Callable[[Cotizacion], None],
        on_edit: Callable[[Cotizacion], None],
        on_convert: Callable[[Cotizacion], None],
    ) -> None:
        super().__init__(master)
        self.quote_store = quote_store
        self.orders_store = orders_store
        self.config_store = config_store
        self.on_view = on_view
        self.on_edit = on_edit
        self.on_convert = on_convert
        self.quotes: List[Cotizacion] = []
        self.filtered: List[Cotizacion] = []
        self._active_map: Dict[str, Cotizacion] = {}
        self._completed_map: Dict[str, Cotizacion] = {}
        self._selected_tree: Optional[ttk.Treeview] = None
        self._action_buttons: List[ttk.Button] = []

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

        lists_frame = ttk.Frame(self)
        lists_frame.grid(row=1, column=0, columnspan=2, sticky="nsew", padx=6, pady=4)
        lists_frame.columnconfigure(0, weight=1)
        lists_frame.rowconfigure(0, weight=1)
        lists_frame.rowconfigure(1, weight=1)

        columns = ("estado", "folio", "fecha", "proyecto", "cliente", "correo", "celular")
        headings = ["Estado", "Folio", "Fecha", "Proyecto", "Cliente", "Correo", "Celular"]

        active_frame = ttk.LabelFrame(lists_frame, text="Pendientes")
        active_frame.columnconfigure(0, weight=1)
        active_frame.rowconfigure(0, weight=1)
        self.active_tree = ttk.Treeview(active_frame, columns=columns, show="headings")
        for col, text in zip(columns, headings):
            self.active_tree.heading(col, text=text)
            width = 120 if col in {"folio", "fecha"} else 200
            if col == "estado":
                width = 110
            self.active_tree.column(col, width=width, anchor="center")
        self.active_tree.grid(row=0, column=0, sticky="nsew")
        active_scroll = ttk.Scrollbar(active_frame, orient=tk.VERTICAL, command=self.active_tree.yview)
        active_scroll.grid(row=0, column=1, sticky="ns")
        self.active_tree.configure(yscrollcommand=active_scroll.set)

        completed_frame = ttk.LabelFrame(lists_frame, text="Convertidas a pedido")
        completed_frame.columnconfigure(0, weight=1)
        completed_frame.rowconfigure(0, weight=1)
        self.completed_tree = ttk.Treeview(completed_frame, columns=columns, show="headings")
        for col, text in zip(columns, headings):
            self.completed_tree.heading(col, text=text)
            width = 120 if col in {"folio", "fecha"} else 200
            if col == "estado":
                width = 110
            self.completed_tree.column(col, width=width, anchor="center")
        self.completed_tree.grid(row=0, column=0, sticky="nsew")
        completed_scroll = ttk.Scrollbar(completed_frame, orient=tk.VERTICAL, command=self.completed_tree.yview)
        completed_scroll.grid(row=0, column=1, sticky="ns")
        self.completed_tree.configure(yscrollcommand=completed_scroll.set)
        self.completed_tree.tag_configure("pedido", foreground="#15803d")

        active_frame.grid(row=0, column=0, sticky="nsew", pady=(0, 6))
        completed_frame.grid(row=1, column=0, sticky="nsew")
        self.active_tree.tag_configure("pendiente", foreground="#c2410c")
        self.completed_tree.tag_configure("pedido", foreground="#15803d")

        button_frame = ttk.Frame(self)
        button_frame.grid(row=2, column=0, columnspan=2, pady=8)
        ttk.Button(button_frame, text="Ver", command=self.view_selected).pack(side=tk.LEFT, padx=4)
        ttk.Button(button_frame, text="Editar", command=self.edit_selected).pack(side=tk.LEFT, padx=4)
        ttk.Button(button_frame, text="Eliminar", command=self.delete_selected).pack(side=tk.LEFT, padx=4)
        ttk.Button(button_frame, text="Marcar como pedido", command=self.convert_selected).pack(side=tk.LEFT, padx=4)
        self.export_pdf_btn = ttk.Button(
            button_frame,
            text="Exportar PDF",
            command=self.export_selected_pdf,
            state=tk.DISABLED,
        )
        self.export_pdf_btn.pack(side=tk.LEFT, padx=4)
        self.export_csv_btn = ttk.Button(
            button_frame,
            text="Exportar Excel/CSV",
            command=self.export_selected_csv,
            state=tk.DISABLED,
        )
        self.export_csv_btn.pack(side=tk.LEFT, padx=4)
        self.send_whatsapp_btn = ttk.Button(
            button_frame,
            text="Enviar por WhatsApp",
            command=self.send_selected_whatsapp,
            state=tk.DISABLED,
        )
        self.send_whatsapp_btn.pack(side=tk.LEFT, padx=4)
        self.send_email_btn = ttk.Button(
            button_frame,
            text="Enviar por Correo",
            command=self.send_selected_email,
            state=tk.DISABLED,
        )
        self.send_email_btn.pack(side=tk.LEFT, padx=4)
        self._action_buttons.extend(
            [
                self.export_pdf_btn,
                self.export_csv_btn,
                self.send_whatsapp_btn,
                self.send_email_btn,
            ]
        )

        self.details = tk.Text(self, height=8, state=tk.DISABLED)
        self.details.grid(row=3, column=0, columnspan=2, sticky="nsew", padx=6, pady=6)

        self.active_tree.bind("<<TreeviewSelect>>", lambda _: self._on_tree_select(self.active_tree))
        self.completed_tree.bind("<<TreeviewSelect>>", lambda _: self._on_tree_select(self.completed_tree))

    # ------------------------------------------------------------------
    def refresh(self) -> None:
        self.quotes = self.quote_store.list_quotes()
        self._selected_tree = None
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
        self.active_tree.delete(*self.active_tree.get_children())
        self.completed_tree.delete(*self.completed_tree.get_children())
        self._active_map = {}
        self._completed_map = {}
        for quote in self.quotes:
            fecha = self._parse_date(quote.fecha)
            if inicio and fecha and fecha < inicio:
                continue
            if fin and fecha and fecha > fin:
                continue
            filtered.append(quote)
            tag = "pedido" if quote.folio in pedidos else "pendiente"
            estado_text = "● Pedido" if tag == "pedido" else "● Pendiente"
            target_tree = self.completed_tree if tag == "pedido" else self.active_tree
            item = target_tree.insert(
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
            if tag == "pedido":
                self._completed_map[item] = quote
            else:
                self._active_map[item] = quote
        self.filtered = filtered
        self._selected_tree = None
        self.details.configure(state=tk.NORMAL)
        self.details.delete("1.0", tk.END)
        self.details.configure(state=tk.DISABLED)
        self._update_action_buttons(False)

    # ------------------------------------------------------------------
    def clear_filters(self) -> None:
        self.fecha_inicio_var.set("")
        self.fecha_fin_var.set("")
        self.fecha_inicio_entry.delete(0, tk.END)
        self.fecha_fin_entry.delete(0, tk.END)
        self._selected_tree = None
        self.apply_filters()

    # ------------------------------------------------------------------
    def get_selected_quote(self) -> Optional[Cotizacion]:
        tree = self._selected_tree
        if not tree:
            return None
        selection = tree.selection()
        if not selection:
            return None
        item = selection[0]
        mapping = self._active_map if tree is self.active_tree else self._completed_map
        return mapping.get(item)

    # ------------------------------------------------------------------
    def _update_action_buttons(self, enabled: bool) -> None:
        state = tk.NORMAL if enabled else tk.DISABLED
        for button in self._action_buttons:
            button.configure(state=state)

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
    def export_selected_pdf(self) -> None:
        quote = self.get_selected_quote()
        if not quote:
            return
        directory = filedialog.askdirectory(parent=self) or ""
        if not directory:
            return
        identity = self.config_store.get_identity()
        path = export_quote_pdf(quote, identity, Path(directory))
        messagebox.showinfo("Exportación", f"PDF generado en {path}", parent=self)

    # ------------------------------------------------------------------
    def export_selected_csv(self) -> None:
        quote = self.get_selected_quote()
        if not quote:
            return
        directory = filedialog.askdirectory(parent=self) or ""
        if not directory:
            return
        path = export_quote_csv(quote, Path(directory))
        messagebox.showinfo("Exportación", f"CSV generado en {path}", parent=self)

    # ------------------------------------------------------------------
    def send_selected_whatsapp(self) -> None:
        quote = self.get_selected_quote()
        if not quote:
            return
        try:
            pdf_path = self._ensure_pdf(quote)
            whatsapp_cfg = self.config_store.get_integrations().get("whatsapp", {})
            send_whatsapp_placeholder(whatsapp_cfg, quote, pdf_path)
            messagebox.showinfo("Envío", "Se generó la salida para WhatsApp.", parent=self)
        except MessagingError as exc:
            messagebox.showerror("Error al enviar", str(exc), parent=self)

    # ------------------------------------------------------------------
    def send_selected_email(self) -> None:
        quote = self.get_selected_quote()
        if not quote:
            return
        try:
            pdf_path = self._ensure_pdf(quote)
            email_cfg = self.config_store.get_integrations().get("email", {})
            send_email_with_pdf(email_cfg, quote, pdf_path)
            messagebox.showinfo("Envío", "Correo enviado correctamente.", parent=self)
        except MessagingError as exc:
            messagebox.showerror("Error al enviar", str(exc), parent=self)

    # ------------------------------------------------------------------
    def _ensure_pdf(self, quote: Cotizacion) -> Path:
        stored_path = self.quote_store.path_for(quote.folio)
        output_dir = stored_path.parent if stored_path.exists() else Path(tempfile.gettempdir())
        identity = self.config_store.get_identity()
        return export_quote_pdf(quote, identity, output_dir)

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
    def _on_tree_select(self, tree: ttk.Treeview) -> None:
        self._selected_tree = tree
        self.show_details()
        self._update_action_buttons(self.get_selected_quote() is not None)

    # ------------------------------------------------------------------
    @staticmethod
    def _parse_date(value: str) -> Optional[dt.date]:
        try:
            return dt.datetime.fromisoformat(value).date()
        except Exception:
            return None


__all__ = ["QuotesTab"]
