"""Modal to display quotation results."""

from __future__ import annotations

import tempfile
import tkinter as tk
import tkinter.font as tkfont
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Callable, Optional

from export.csv_quote import export_quote_csv
from export.pdf_quote import export_quote_pdf
from models.cotizacion import Cotizacion
from storage.clients_store import ClientsStore
from storage.config_store import ConfigStore
from storage.quotes_store import QuoteStore
from utils import MessagingError, send_email_with_pdf, send_whatsapp_placeholder


def _format_currency(value: float, moneda: str) -> str:
    return f"{moneda} ${value:,.2f}" if moneda else f"${value:,.2f}"


class QuoteModal(tk.Toplevel):
    """Modal window showing quotation summary and export actions."""

    def __init__(
        self,
        master: tk.Widget,
        quote: Cotizacion,
        config_store: ConfigStore,
        quote_store: QuoteStore,
        clients_store: ClientsStore,
        on_saved: Optional[Callable[[Cotizacion], None]] = None,
    ) -> None:
        super().__init__(master)
        self.title("Resumen de cotización")
        self.geometry("1000x720")
        self.resizable(False, False)
        self.transient(master)
        self.grab_set()

        self.quote = quote
        self.config_store = config_store
        self.quote_store = quote_store
        self.clients_store = clients_store
        self.on_saved = on_saved
        self.saved_path: Optional[Path] = None

        self._default_font = tkfont.nametofont("TkDefaultFont")
        self._bold_font = self._default_font.copy()
        self._bold_font.configure(weight="bold")

        self._build_ui()

    def _build_ui(self) -> None:
        container = ttk.Frame(self)
        container.grid(row=0, column=0, sticky="nsew")
        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)

        container.rowconfigure(0, weight=1)
        container.rowconfigure(1, weight=0)
        container.columnconfigure(0, weight=1)

        content = ttk.Frame(container, padding=(16, 12))
        content.grid(row=0, column=0, sticky="nsew")
        content.columnconfigure(0, weight=1)
        content.rowconfigure(1, weight=1)

        header = ttk.Frame(content)
        header.grid(row=0, column=0, sticky="ew", pady=(0, 12))
        for col in range(3):
            header.columnconfigure(col, weight=1)

        header_items = [
            ("Folio", self.quote.folio),
            ("Fecha", self.quote.fecha),
            ("Proyecto", self.quote.proyecto),
            ("Cliente", self.quote.cliente.nombre),
            ("Correo", self.quote.cliente.correo),
            ("Celular", self.quote.cliente.celular),
            ("Impresora", self.quote.impresora),
            ("Tipo", self.quote.tipo),
            ("Material", self.quote.material),
        ]

        for idx, (label, value) in enumerate(header_items):
            row = idx // 3
            col = idx % 3
            cell = ttk.Frame(header, padding=4)
            cell.grid(row=row, column=col, sticky="nsew")
            ttk.Label(cell, text=label, font=self._bold_font, anchor="center").pack(fill=tk.X)
            ttk.Label(
                cell,
                text=value or "-",
                anchor="center",
                justify="center",
                wraplength=260,
            ).pack(fill=tk.X, pady=(4, 0))

        tree_frame = ttk.Frame(content)
        tree_frame.grid(row=1, column=0, sticky="nsew")
        tree_frame.rowconfigure(0, weight=1)
        tree_frame.columnconfigure(0, weight=1)

        columns = ("pieza", "cantidad", "unitario", "total")
        self.tree = ttk.Treeview(tree_frame, columns=columns, show="headings")
        self.tree.heading("pieza", text="Pieza")
        self.tree.heading("cantidad", text="Cantidad")
        self.tree.heading("unitario", text="Precio unitario")
        self.tree.heading("total", text="Total")
        self.tree.column("pieza", width=280, anchor="w")
        self.tree.column("cantidad", width=100, anchor="center")
        self.tree.column("unitario", width=160, anchor="e")
        self.tree.column("total", width=160, anchor="e")
        self.tree.grid(row=0, column=0, sticky="nsew")

        scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.tree.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.tree.configure(yscrollcommand=scrollbar.set)

        for pieza in self.quote.piezas:
            self.tree.insert(
                "",
                tk.END,
                values=(
                    pieza.pieza.nombre,
                    pieza.pieza.cantidad,
                    _format_currency(pieza.total_unit, self.quote.moneda),
                    _format_currency(pieza.total_total, self.quote.moneda),
                ),
            )

        summary = ttk.Frame(content)
        summary.grid(row=2, column=0, sticky="ew", pady=(12, 0))
        summary.columnconfigure(0, weight=1)
        summary.columnconfigure(1, weight=1)
        self._add_summary_row(summary, "Subtotal base", self.quote.subtotal_base)
        self._add_summary_row(summary, "Merma", self.quote.merma)
        self._add_summary_row(summary, "Riesgo", self.quote.riesgo)
        self._add_summary_row(summary, "Ganancia", self.quote.ganancia)
        self._add_summary_row(summary, "Subtotal post riesgo", self.quote.subtotal_post_riesgo)
        self._add_summary_row(summary, "Total sin IVA", self.quote.total_sin_iva)
        self._add_summary_row(summary, "IVA", self.quote.iva)
        self._add_summary_row(summary, "Total", self.quote.total, bold=True)

        footer = ttk.Frame(container, padding=(16, 8))
        footer.grid(row=1, column=0, sticky="ew")
        footer_buttons = [
            ("Enviar por Correo", self.send_email),
            ("Enviar por WhatsApp", self.send_whatsapp),
            ("Cancelar/Salir", self.destroy),
            ("Guardar", self.save_quote),
            ("Exportar Excel/CSV", self.export_csv),
            ("Exportar PDF", self.export_pdf),
        ]
        for text, command in footer_buttons:
            ttk.Button(footer, text=text, command=command).pack(side="right", padx=6)
        footer.lift()

    def _add_summary_row(self, frame: ttk.Frame, label: str, value: float, bold: bool = False) -> None:
        row = frame.grid_size()[1]
        font = self._bold_font if bold else self._default_font
        ttk.Label(frame, text=label, font=font).grid(row=row, column=0, sticky="e", padx=6, pady=2)
        ttk.Label(frame, text=_format_currency(value, self.quote.moneda), font=font).grid(
            row=row, column=1, sticky="w", pady=2
        )

    def export_pdf(self) -> None:
        directory = filedialog.askdirectory(parent=self) or ""
        if not directory:
            return
        identity = self.config_store.get_identity()
        path = export_quote_pdf(self.quote, identity, Path(directory))
        messagebox.showinfo("Exportación", f"PDF generado en {path}", parent=self)

    def export_csv(self) -> None:
        directory = filedialog.askdirectory(parent=self) or ""
        if not directory:
            return
        path = export_quote_csv(self.quote, Path(directory))
        messagebox.showinfo("Exportación", f"CSV generado en {path}", parent=self)

    def save_quote(self) -> None:
        path = self.quote_store.save(self.quote)
        cliente = self.clients_store.register_quote(self.quote.cliente, self.quote)
        self.quote.cliente.id = cliente.id
        self.quote.cliente.nombre = cliente.nombre
        self.quote.cliente.correo = cliente.correo
        self.quote.cliente.celular = cliente.celular
        self.quote.cliente.rfc = cliente.rfc
        self.saved_path = path
        messagebox.showinfo("Guardado", f"Cotización guardada en {path}", parent=self)
        if self.on_saved:
            self.on_saved(self.quote)

    def _ensure_pdf(self) -> Path:
        output_dir: Path
        if self.saved_path:
            output_dir = self.saved_path.parent
        else:
            stored_path = self.quote_store.path_for(self.quote.folio)
            output_dir = stored_path.parent if stored_path.exists() else Path(tempfile.gettempdir())
        identity = self.config_store.get_identity()
        return export_quote_pdf(self.quote, identity, output_dir)

    def send_email(self) -> None:
        try:
            pdf_path = self._ensure_pdf()
            email_cfg = self.config_store.get_integrations().get("email", {})
            send_email_with_pdf(email_cfg, self.quote, pdf_path)
            messagebox.showinfo("Envío", "Correo enviado correctamente.", parent=self)
        except MessagingError as exc:
            messagebox.showerror("Error al enviar", str(exc), parent=self)

    def send_whatsapp(self) -> None:
        try:
            pdf_path = self._ensure_pdf()
            whatsapp_cfg = self.config_store.get_integrations().get("whatsapp", {})
            send_whatsapp_placeholder(whatsapp_cfg, self.quote, pdf_path)
            messagebox.showinfo("Envío", "Se generó la salida para WhatsApp.", parent=self)
        except MessagingError as exc:
            messagebox.showerror("Error al enviar", str(exc), parent=self)


__all__ = ["QuoteModal"]
