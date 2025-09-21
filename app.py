"""Aplicación principal del cotizador 3D."""

from __future__ import annotations

import tkinter as tk
from datetime import datetime
from tkinter import messagebox, ttk
from typing import Optional

from tkcalendar import DateEntry

from models.cotizacion import Cotizacion
from models.pedido import Pedido
from pricing import FinancialSettings, build_quote_breakdown, compute_piece_base
from storage.clients_store import ClientsStore
from storage.config_store import ConfigStore
from storage.orders_store import OrdersStore
from storage.quotes_store import QuoteStore
from ui.config_window import ConfigWindow
from ui.modal_cotizacion import QuoteModal
from ui.tab_contabilidad import AccountingTab
from ui.tab_cotizaciones import QuotesTab
from ui.tab_pedidos import OrdersTab
from ui.tabs_proyecto import ProjectTab, QuoteContext


class CotizadorApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Cotizador 3D")
        self.geometry("1200x820")

        menubar = tk.Menu(self)
        menubar.add_command(label="Configuraciones", command=lambda: self.open_config(None))
        self.config(menu=menubar)

        self.config_store = ConfigStore()
        self.clients_store = ClientsStore()
        self.quote_store = QuoteStore()
        self.orders_store = OrdersStore()

        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill=tk.BOTH, expand=True)

        self.project_tab = ProjectTab(
            self.notebook,
            self.config_store,
            self.clients_store,
            open_config_callback=self.open_config,
            calculate_callback=self.calculate_quote,
        )
        self.quotes_tab = QuotesTab(
            self.notebook,
            self.quote_store,
            self.orders_store,
            on_view=self.view_quote,
            on_edit=self.edit_quote,
            on_convert=self.convert_quote_to_order,
        )
        self.orders_tab = OrdersTab(
            self.notebook,
            self.orders_store,
            on_status_change=self.on_order_status_change,
        )
        self.accounting_tab = AccountingTab(
            self.notebook,
            self.orders_store,
            self.config_store,
        )

        self.notebook.add(self.project_tab, text="Proyecto")
        self.notebook.add(self.quotes_tab, text="Cotizaciones")
        self.notebook.add(self.orders_tab, text="Pedidos")
        self.notebook.add(self.accounting_tab, text="Contabilidad")

        self.last_quote: Optional[Cotizacion] = None

    # ------------------------------------------------------------------
    def open_config(self, section: str | None = None) -> None:
        window = ConfigWindow(self, self.config_store, focus_section=section)
        self.wait_window(window)
        self.project_tab.refresh_materials()
        self.project_tab.refresh_printers()

    # ------------------------------------------------------------------
    def calculate_quote(self, context: QuoteContext) -> None:
        try:
            fecha_dt = datetime.fromisoformat(context.fecha)
        except ValueError:
            fecha_dt = datetime.utcnow()
        folio = self.quote_store.generate_folio(fecha_dt)

        financial_raw = self.config_store.get_financials()
        financials = FinancialSettings(
            precio_kwh=financial_raw.get("precio_kwh", 0.0),
            costo_hora=financial_raw.get("costo_hora", 0.0),
            merma=financial_raw.get("merma", 0.0),
            riesgo=financial_raw.get("riesgo", 0.0),
            ganancia=financial_raw.get("ganancia", 0.0),
            iva=financial_raw.get("iva", 0.0),
        )

        bases = [
            compute_piece_base(
                pieza,
                context.material,
                context.impresora,
                financials,
                precio_material_override=context.precio_material,
            )
            for pieza in context.piezas
        ]
        breakdown = build_quote_breakdown(bases, financials)

        quote = Cotizacion(
            folio=folio,
            fecha=context.fecha,
            proyecto=context.proyecto,
            tipo=context.tipo,
            impresora=context.impresora.nombre,
            material=context.material.nombre,
            material_precio_kg=context.precio_material,
            cliente=context.cliente,
            piezas=breakdown.piezas,
            subtotal_base=breakdown.subtotal_base,
            merma=breakdown.merma,
            riesgo=breakdown.riesgo,
            ganancia=breakdown.ganancia,
            subtotal_post_riesgo=breakdown.subtotal_post_riesgo,
            total_sin_iva=breakdown.total_sin_iva,
            iva=breakdown.iva,
            total=breakdown.total,
            moneda=self.config_store.moneda(),
            notas=context.notas,
            config_version=self.config_store.get_config_version(),
        )
        self.last_quote = quote

        modal = QuoteModal(
            self,
            quote,
            self.config_store,
            self.quote_store,
            self.clients_store,
            on_saved=self.on_quote_saved,
        )
        self.wait_window(modal)

    # ------------------------------------------------------------------
    def on_quote_saved(self, quote: Cotizacion) -> None:
        self.last_quote = quote
        self.quotes_tab.refresh()
        self.accounting_tab.refresh()
        self.project_tab.clear()

    # ------------------------------------------------------------------
    def view_quote(self, quote: Cotizacion) -> None:
        modal = QuoteModal(
            self,
            quote,
            self.config_store,
            self.quote_store,
            self.clients_store,
            on_saved=self.on_quote_saved,
        )
        self.wait_window(modal)

    # ------------------------------------------------------------------
    def edit_quote(self, quote: Cotizacion) -> None:
        self.project_tab.load_quote(quote)
        self.notebook.select(self.project_tab)

    # ------------------------------------------------------------------
    def convert_quote_to_order(self, quote: Cotizacion) -> None:
        fecha_estimada = self._ask_fecha_estimada()
        folio = self.orders_store.generate_folio()
        pedido = Pedido(
            folio=folio,
            folio_cotizacion=quote.folio,
            fecha_creacion=datetime.utcnow().date().isoformat(),
            fecha_estimada=fecha_estimada,
            proyecto=quote.proyecto,
            tipo=quote.tipo,
            impresora=quote.impresora,
            cliente=quote.cliente,
            subtotal_base=quote.subtotal_base,
            total=quote.total,
            merma=quote.merma,
            riesgo=quote.riesgo,
            ganancia=quote.ganancia,
            iva=quote.iva,
            moneda=quote.moneda,
        )
        self.orders_store.save(pedido)
        self.clients_store.register_order(quote.cliente, pedido)
        messagebox.showinfo("Pedido", f"Se registró el pedido {pedido.folio}.", parent=self)
        self.quotes_tab.refresh()
        self.orders_tab.refresh()
        self.accounting_tab.refresh()

    # ------------------------------------------------------------------
    def on_order_status_change(self, pedido: Pedido) -> None:
        self.accounting_tab.refresh()
        self.quotes_tab.refresh()

    # ------------------------------------------------------------------
    def _ask_fecha_estimada(self) -> str | None:
        dialog = tk.Toplevel(self)
        dialog.title("Fecha estimada de entrega")
        dialog.transient(self)
        dialog.grab_set()

        ttk.Label(dialog, text="Selecciona la fecha estimada de entrega:").grid(row=0, column=0, columnspan=2, padx=12, pady=8)

        fecha_var = tk.StringVar()
        date_entry = DateEntry(dialog, textvariable=fecha_var, width=12, date_pattern="yyyy-mm-dd")
        date_entry.grid(row=1, column=0, columnspan=2, padx=12, pady=4)

        result: str | None = None

        def aceptar() -> None:
            nonlocal result
            value = fecha_var.get().strip()
            if value:
                try:
                    result_date = datetime.fromisoformat(value).date()
                    result = result_date.isoformat()
                except ValueError:
                    messagebox.showerror("Fecha inválida", "Usa el formato AAAA-MM-DD.", parent=dialog)
                    return
            else:
                result = None
            dialog.destroy()

        ttk.Button(dialog, text="Aceptar", command=aceptar).grid(row=2, column=0, padx=12, pady=8)
        ttk.Button(dialog, text="Sin fecha", command=dialog.destroy).grid(row=2, column=1, padx=12, pady=8)
        dialog.wait_window(dialog)
        return result


def main() -> None:
    app = CotizadorApp()
    app.mainloop()


if __name__ == "__main__":
    main()
