"""Modal to display quotation results."""

from __future__ import annotations

import tempfile
import tkinter as tk
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
        self.geometry("900x650")
        self.resizable(False, False)
        self.transient(master)
        self.grab_set()

        self.quote = quote
        self.config_store = config_store
        self.quote_store = quote_store
        self.clients_store = clients_store
        self.on_saved = on_saved
        self.saved_path: Optional[Path] = None

        self._build_ui()

    def _build_ui(self) -> None:
        header = ttk.Frame(self)
        header.pack(fill=tk.X, padx=12, pady=8)

        ttk.Label(header, text=f"Folio: {self.quote.folio}", font=("TkDefaultFont", 12, "bold")).grid(row=0, column=0, sticky="w")
        ttk.Label(header, text=f"Fecha: {self.quote.fecha}").grid(row=0, column=1, sticky="w", padx=12)
        ttk.Label(header, text=f"Proyecto: {self.quote.proyecto}").grid(row=1, column=0, sticky="w")
        ttk.Label(header, text=f"Cliente: {self.quote.cliente.nombre}").grid(row=1, column=1, sticky="w", padx=12)
        ttk.Label(header, text=f"Correo: {self.quote.cliente.correo}").grid(row=2, column=0, sticky="w")
        ttk.Label(header, text=f"Celular: {self.quote.cliente.celular}").grid(row=2, column=1, sticky="w", padx=12)
        ttk.Label(header, text=f"Impresora: {self.quote.impresora}").grid(row=3, column=0, sticky="w")
        ttk.Label(header, text=f"Tipo: {self.quote.tipo}").grid(row=3, column=1, sticky="w", padx=12)
        ttk.Label(header, text=f"Material: {self.quote.material}").grid(row=4, column=0, sticky="w")

        tree_frame = ttk.Frame(self)
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=12, pady=8)

        columns = ("cantidad", "unitario", "total")
        self.tree = ttk.Treeview(tree_frame, columns=columns, show="headings")
        self.tree.heading("cantidad", text="Cantidad")
        self.tree.heading("unitario", text="Precio unitario")
        self.tree.heading("total", text="Total")
        self.tree.column("cantidad", width=100, anchor="center")
        self.tree.column("unitario", width=150, anchor="e")
        self.tree.column("total", width=150, anchor="e")
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.tree.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.configure(yscrollcommand=scrollbar.set)

        for pieza in self.quote.piezas:
            self.tree.insert(
                "",
                tk.END,
                values=(
                    pieza.pieza.cantidad,
                    _format_currency(pieza.total_unit, self.quote.moneda),
                    _format_currency(pieza.total_total, self.quote.moneda),
                ),
                text=pieza.pieza.nombre,
            )

        summary = ttk.Frame(self)
        summary.pack(fill=tk.X, padx=12, pady=4)
        self._add_summary_row(summary, "Subtotal base", self.quote.subtotal_base)
        self._add_summary_row(summary, "Merma", self.quote.merma)
        self._add_summary_row(summary, "Riesgo", self.quote.riesgo)
        self._add_summary_row(summary, "Ganancia", self.quote.ganancia)
        self._add_summary_row(summary, "Subtotal post riesgo", self.quote.subtotal_post_riesgo)
        self._add_summary_row(summary, "Total sin IVA", self.quote.total_sin_iva)
        self._add_summary_row(summary, "IVA", self.quote.iva)
        self._add_summary_row(summary, "Total", self.quote.total, bold=True)

        button_bar = ttk.Frame(self)
        button_bar.pack(fill=tk.X, padx=12, pady=12)
        ttk.Button(button_bar, text="Exportar PDF", command=self.export_pdf).pack(side=tk.LEFT, padx=4)
        ttk.Button(button_bar, text="Exportar CSV", command=self.export_csv).pack(side=tk.LEFT, padx=4)
        ttk.Button(button_bar, text="Enviar por Email", command=self.send_email).pack(side=tk.LEFT, padx=4)
        ttk.Button(button_bar, text="Enviar por WhatsApp", command=self.send_whatsapp).pack(side=tk.LEFT, padx=4)
        ttk.Button(button_bar, text="Guardar", command=self.save_quote).pack(side=tk.RIGHT, padx=4)
        ttk.Button(button_bar, text="Salir", command=self.destroy).pack(side=tk.RIGHT, padx=4)

    def _add_summary_row(self, frame: ttk.Frame, label: str, value: float, bold: bool = False) -> None:
        row = frame.grid_size()[1]
        font = ("TkDefaultFont", 10, "bold") if bold else ("TkDefaultFont", 10)
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
        self.saved_path = path
        messagebox.showinfo("Guardado", f"Cotización guardada en {path}", parent=self)
        if self.on_saved:
            self.on_saved(self.quote)

    def _ensure_pdf(self) -> Path:
        if self.saved_path:
            pdf = self.saved_path.with_suffix(".pdf")
            if pdf.exists():
                return pdf
        identity = self.config_store.get_identity()
        output_dir = self.saved_path.parent if self.saved_path else Path(tempfile.gettempdir())
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
