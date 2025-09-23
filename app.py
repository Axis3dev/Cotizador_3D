"""Aplicación principal del cotizador 3D."""

from __future__ import annotations

import tkinter as tk
import tkinter.font as tkfont
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
from ui.tab_clientes import ClientsTab
from ui.tab_contabilidad import AccountingTab
from ui.tab_cotizaciones import QuotesTab
from ui.tab_pedidos import OrdersTab
from ui.tabs_proyecto import ProjectTab, QuoteContext


class CotizadorApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Cotizador 3D")
        self.geometry("1200x800")
        self.resizable(False, False)
        try:
            self.state("zoomed")
        except Exception:  # pragma: no cover - platform specific
            try:
                self.attributes("-zoomed", True)
            except Exception:
                pass

        self._setup_fonts()

        self.config_store = ConfigStore()
        self.clients_store = ClientsStore()
        self.quote_store = QuoteStore()
        self.orders_store = OrdersStore()

        container = ttk.Frame(self)
        container.pack(fill=tk.BOTH, expand=True)

        toolbar = ttk.Frame(container)
        toolbar.pack(fill=tk.X, padx=12, pady=6)

        self.brand_label = ttk.Label(toolbar, text=self._brand_name(), anchor="w")
        self.brand_label.pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(toolbar, text="Configuraciones", command=lambda: self.open_config(None)).pack(side=tk.RIGHT)

        self.notebook = ttk.Notebook(container)
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
            self.config_store,
            on_view=self.view_quote,
            on_edit=self.edit_quote,
            on_convert=self.convert_quote_to_order,
        )
        self.orders_tab = OrdersTab(
            self.notebook,
            self.orders_store,
            on_status_change=self.on_order_status_change,
            clients_store=self.clients_store,
            config_store=self.config_store,
            quote_store=self.quote_store,
        )
        self.clients_tab = ClientsTab(
            self.notebook,
            self.clients_store,
            self.orders_store,
            self.config_store,
        )
        self.accounting_tab = AccountingTab(
            self.notebook,
            self.orders_store,
            self.config_store,
        )

        self.notebook.add(self.project_tab, text="Proyecto")
        self.notebook.add(self.quotes_tab, text="Cotizaciones")
        self.notebook.add(self.orders_tab, text="Pedidos")
        self.notebook.add(self.clients_tab, text="Clientes")
        self.notebook.add(self.accounting_tab, text="Contabilidad")

        self.last_quote: Optional[Cotizacion] = None

    def _setup_fonts(self) -> None:
        for name in ("TkDefaultFont", "TkTextFont", "TkHeadingFont"):
            try:
                font_obj = tkfont.nametofont(name)
            except tk.TclError:  # pragma: no cover - platform dependent
                continue
            size = font_obj.cget("size")
            if isinstance(size, int) and size != 0:
                scaled = int(round(size * 1.5))
                if size > 0:
                    font_obj.configure(size=max(1, scaled))
                else:
                    font_obj.configure(size=min(-1, scaled))
        style = ttk.Style(self)
        default_font = tkfont.nametofont("TkDefaultFont")
        heading_font = tkfont.nametofont("TkHeadingFont")
        text_font = tkfont.nametofont("TkTextFont")
        style.configure("TLabel", font=default_font)
        style.configure("TButton", font=default_font)
        style.configure("Treeview", font=text_font)
        style.configure("Treeview.Heading", font=heading_font)

    def _brand_name(self) -> str:
        identidad = self.config_store.get_identity()
        return str(identidad.get("nombre_comercial", "Cotizador 3D")) or "Cotizador 3D"

    # ------------------------------------------------------------------
    def open_config(self, section: str | None = None) -> None:
        window = ConfigWindow(self, self.config_store, focus_section=section)
        self.wait_window(window)
        self.project_tab.refresh_materials()
        self.project_tab.refresh_printers()
        self.brand_label.config(text=self._brand_name())
        self.clients_tab.refresh()

    # ------------------------------------------------------------------
    def calculate_quote(self, context: QuoteContext) -> None:
        try:
            fecha_dt = datetime.fromisoformat(context.fecha)
        except ValueError:
            fecha_dt = datetime.utcnow()
        folio = context.folio or self.config_store.next_quote_folio(self.quote_store.exists)

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
        quote.cliente.id = context.cliente.id
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
        self.clients_tab.refresh()
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
        if fecha_estimada is None:
            return
        folio = self.config_store.next_order_folio(self.orders_store.exists)
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
        cliente = self.clients_store.register_order(quote.cliente, pedido)
        pedido.cliente.id = cliente.id
        self.orders_store.save(pedido)
        messagebox.showinfo("Pedido", f"Se registró el pedido {pedido.folio}.", parent=self)
        self.quotes_tab.refresh()
        self.orders_tab.refresh()
        self.accounting_tab.refresh()
        self.clients_tab.refresh()

    # ------------------------------------------------------------------
    def on_order_status_change(self, pedido: Pedido) -> None:
        self.accounting_tab.refresh()
        self.quotes_tab.refresh()
        self.clients_tab.refresh()

    # ------------------------------------------------------------------
    def _ask_fecha_estimada(self) -> str | None:
        dialog = tk.Toplevel(self)
        dialog.title("Fecha estimada de entrega")
        dialog.transient(self)
        dialog.grab_set()
        dialog.geometry("380x220")
        dialog.resizable(False, False)
        dialog.columnconfigure(0, weight=1)
        dialog.rowconfigure(0, weight=1)

        container = ttk.Frame(dialog, padding=16)
        container.grid(row=0, column=0, sticky="nsew")
        container.columnconfigure(0, weight=1)

        ttk.Label(container, text="Fecha estimada de entrega:").grid(
            row=0, column=0, sticky="w", pady=(0, 8)
        )

        today = datetime.utcnow().date()
        fecha_var = tk.StringVar()
        date_entry = DateEntry(
            container,
            textvariable=fecha_var,
            width=16,
            date_pattern="yyyy-mm-dd",
            mindate=today,
        )
        date_entry.grid(row=1, column=0, sticky="ew")
        date_entry.set_date(today)

        footer = ttk.Frame(dialog, padding=(8, 4))
        footer.grid(row=1, column=0, sticky="ew")

        result: str | None = None

        def guardar() -> None:
            nonlocal result
            try:
                selected = date_entry.get_date()
            except Exception:
                messagebox.showerror(
                    "Fecha inválida",
                    "Selecciona una fecha válida.",
                    parent=dialog,
                )
                return
            current_today = datetime.utcnow().date()
            if selected < current_today:
                messagebox.showerror(
                    "Fecha inválida",
                    "La fecha estimada debe ser hoy o posterior.",
                    parent=dialog,
                )
                return
            result = selected.isoformat()
            dialog.destroy()

        ttk.Button(footer, text="Cancelar", command=dialog.destroy).pack(
            side="right", padx=6
        )
        ttk.Button(footer, text="Guardar", command=guardar).pack(
            side="right", padx=6
        )

        dialog.update_idletasks()
        parent_x = self.winfo_rootx()
        parent_y = self.winfo_rooty()
        parent_w = self.winfo_width()
        parent_h = self.winfo_height()
        dialog_w = dialog.winfo_width()
        dialog_h = dialog.winfo_height()
        x = parent_x + (parent_w - dialog_w) // 2
        y = parent_y + (parent_h - dialog_h) // 2
        dialog.geometry(f"{dialog_w}x{dialog_h}+{x}+{y}")

        date_entry.focus_set()
        dialog.wait_window(dialog)
        return result


def main() -> None:
    app = CotizadorApp()
    app.mainloop()


if __name__ == "__main__":
    main()
