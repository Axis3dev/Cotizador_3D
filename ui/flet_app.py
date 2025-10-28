"""Flet based user interface for the Axis 3D quotation system."""

from __future__ import annotations
"""Flet interface implementation for Axis 3D quotation app."""

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Dict, List, Optional

import flet as ft

from models.cliente import Cliente, ClienteInfo
from models.cotizacion import Cotizacion, PiezaCostos
from models.impresora import Impresora, PrinterType
from models.material import Material
from models.pedido import Pedido
from models.pieza import Pieza, combine_hours_minutes
from pricing import FinancialSettings, build_quote_breakdown
from storage.clients_store import ClientsStore
from storage.config_store import ConfigStore
from storage.orders_store import OrdersStore
from storage.quotes_store import QuoteStore
from utils.messaging import (
    MessagingError,
    send_email_with_pdf,
    send_whatsapp_placeholder,
)


@dataclass
class PieceRow:
    """UI representation of a piece within the quotation form."""

    pieza: Pieza
    costos: Optional[PiezaCostos] = None


@dataclass
class ProjectState:
    """Captures all data entered in the project screen."""

    proyecto: str = ""
    fecha: date = field(default_factory=date.today)
    tipo: PrinterType = PrinterType.FILAMENTO
    impresora: Optional[Impresora] = None
    material: Optional[Material] = None
    precio_material: float = 0.0
    cliente: ClienteInfo = field(default_factory=ClienteInfo)
    piezas: List[PieceRow] = field(default_factory=list)
    notas: str = ""
    folio: Optional[str] = None


class Axis3DFletApp:
    """Main coordinator for the Flet application."""

    def __init__(
        self,
        page: ft.Page,
        config_store: ConfigStore,
        clients_store: ClientsStore,
        quote_store: QuoteStore,
        orders_store: OrdersStore,
    ) -> None:
        self.page = page
        self.config_store = config_store
        self.clients_store = clients_store
        self.quote_store = quote_store
        self.orders_store = orders_store

        self.project_state = ProjectState()
        self.current_view = "proyecto"

        self._navigation: Optional[ft.NavigationRail] = None
        self._content_container: Optional[ft.Container] = None

    # ------------------------------------------------------------------
    def mount(self) -> None:
        """Configure page defaults and build the layout."""

        self.page.title = "Axis 3D | Cotizador"
        self.page.horizontal_alignment = ft.CrossAxisAlignment.STRETCH
        self.page.theme = ft.Theme(color_scheme_seed="#007ACC")
        self.page.padding = 0
        self.page.window_width = 1200
        self.page.window_height = 800
        self.page.window_resizable = True
        try:
            self.page.window_maximized = True
        except AttributeError:  # pragma: no cover - platform dependent
            pass

        brand = self.config_store.get_identity().get("nombre_comercial", "Axis 3D")
        logo_path = self.config_store.get_identity().get("logo_path")
        if logo_path and Path(logo_path).exists():
            logo_control: ft.Control = ft.Container(
                content=ft.Image(src=logo_path, width=64, height=64, fit=ft.ImageFit.CONTAIN),
                padding=8,
            )
        else:
            logo_control = ft.Container(content=ft.Icon(ft.icons.PRINT), padding=8)

        header = ft.Container(
            bgcolor="#F2F2F2",
            content=ft.Row(
                [
                    logo_control,
                    ft.Text(brand, size=24, weight=ft.FontWeight.BOLD, color="#111111"),
                    ft.Container(expand=True),
                ],
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                height=80,
                expand=True,
            ),
        )

        self._navigation = ft.NavigationRail(
            selected_index=0,
            label_type=ft.NavigationRailLabelType.ALL,
            bgcolor=ft.colors.WHITE,
            min_width=72,
            extended=True,
            group_alignment=-0.8,
            destinations=[
                ft.NavigationRailDestination(icon=ft.icons.DASHBOARD, label="Proyecto"),
                ft.NavigationRailDestination(icon=ft.icons.DESCRIPTION, label="Cotizaciones"),
                ft.NavigationRailDestination(icon=ft.icons.SHOPPING_CART, label="Pedidos"),
                ft.NavigationRailDestination(icon=ft.icons.ANALYTICS, label="Contabilidad"),
                ft.NavigationRailDestination(icon=ft.icons.PEOPLE, label="Clientes"),
                ft.NavigationRailDestination(icon=ft.icons.SETTINGS, label="Configuración"),
            ],
            on_change=self._on_nav_change,
        )

        self._content_container = ft.Container(expand=True, padding=20)
        body = ft.Row(
            [self._navigation, ft.VerticalDivider(width=1), self._content_container],
            expand=True,
        )

        self.page.add(header, body)
        self._render_view("proyecto")

    # ------------------------------------------------------------------
    def _on_nav_change(self, event: ft.ControlEvent) -> None:
        mapping = {
            0: "proyecto",
            1: "cotizaciones",
            2: "pedidos",
            3: "contabilidad",
            4: "clientes",
            5: "configuracion",
        }
        view = mapping.get(int(event.control.selected_index), "proyecto")
        self._render_view(view)

    # ------------------------------------------------------------------
    def _render_view(self, name: str) -> None:
        if not self._content_container:
            return
        self.current_view = name
        if name == "proyecto":
            control = self._build_project_view()
        elif name == "cotizaciones":
            control = self._build_quotes_view()
        elif name == "pedidos":
            control = self._build_orders_view()
        elif name == "contabilidad":
            control = self._build_accounting_view()
        elif name == "clientes":
            control = self._build_clients_view()
        else:
            control = self._build_configuration_view()
        self._content_container.content = control
        self._content_container.update()

    # ------------------------------------------------------------------
    # Project view ------------------------------------------------------
    def _build_project_view(self) -> ft.Control:
        identity = self.config_store.get_identity()
        moneda = identity.get("moneda", "MXN")

        tipo_dropdown = ft.Dropdown(
            label="Tipo de impresión",
            options=[
                ft.dropdown.Option(PrinterType.FILAMENTO.value, "Filamento"),
                ft.dropdown.Option(PrinterType.RESINA.value, "Resina"),
            ],
            value=self.project_state.tipo.value,
            on_change=lambda e: self._on_tipo_change(e.value),
        )

        impresoras = self.config_store.get_printers(self.project_state.tipo)
        if impresoras and not self.project_state.impresora:
            self.project_state.impresora = impresoras[0]
        printer_options = [
            ft.dropdown.Option(item.nombre, item.nombre) for item in impresoras
        ]
        printer_dropdown = ft.Dropdown(
            label="Impresora",
            value=self.project_state.impresora.nombre if self.project_state.impresora else None,
            options=printer_options,
            on_change=lambda e: self._select_printer(e.value),
        )

        materiales = self.config_store.get_materials()
        if materiales and not self.project_state.material:
            self.project_state.material = materiales[0]
            self.project_state.precio_material = materiales[0].precio_kg
        material_options = [ft.dropdown.Option(mat.nombre) for mat in materiales]
        material_dropdown = ft.Dropdown(
            label="Material",
            value=self.project_state.material.nombre if self.project_state.material else None,
            options=material_options,
            on_change=lambda e: self._select_material(e.value),
        )

        precio_field = ft.TextField(
            label=f"Precio material ({moneda}/kg)",
            value=f"{self.project_state.precio_material:.2f}" if self.project_state.precio_material else "",
            keyboard_type=ft.KeyboardType.NUMBER,
            on_change=lambda e: self._update_precio_material(e.value),
        )

        cliente_nombre = ft.TextField(
            label="Cliente",
            value=self.project_state.cliente.nombre,
            on_submit=lambda e: self._search_client(e.control.value),
            on_change=lambda e: self._update_client_field("nombre", e.value),
        )
        cliente_correo = ft.TextField(
            label="Correo",
            value=self.project_state.cliente.correo,
            on_change=lambda e: self._update_client_field("correo", e.value),
        )
        cliente_cel = ft.TextField(
            label="Celular",
            value=self.project_state.cliente.celular,
            on_change=lambda e: self._update_client_field("celular", e.value),
        )

        piezas_table = self._build_pieces_table()

        add_piece_button = ft.ElevatedButton(
            "Agregar pieza",
            icon=ft.icons.ADD,
            on_click=lambda _: self._open_piece_dialog(),
        )
        calcular_button = ft.FilledButton(
            "Calcular cotización",
            icon=ft.icons.CALCULATE,
            on_click=lambda _: self._calculate_quote_from_state(),
        )

        layout = ft.Column(
            controls=[
                ft.Text("Proyecto", size=20, weight=ft.FontWeight.BOLD, color="#007ACC"),
                ft.ResponsiveRow(
                    controls=[
                        ft.Container(ft.TextField(label="Nombre del proyecto", value=self.project_state.proyecto, on_change=lambda e: self._set_project_field("proyecto", e.value)), col={"sm": 12, "md": 6}),
                        ft.Container(ft.TextField(label="Fecha", value=self.project_state.fecha.isoformat(), read_only=True), col={"sm": 12, "md": 3}),
                        ft.Container(tipo_dropdown, col={"sm": 12, "md": 3}),
                    ],
                ),
                ft.ResponsiveRow(
                    controls=[
                        ft.Container(printer_dropdown, col={"sm": 12, "md": 6}),
                        ft.Container(material_dropdown, col={"sm": 12, "md": 6}),
                        ft.Container(precio_field, col={"sm": 12, "md": 6}),
                    ]
                ),
                ft.Divider(),
                ft.Text("Datos del cliente", size=18, weight=ft.FontWeight.BOLD, color="#007ACC"),
                ft.ResponsiveRow(
                    controls=[
                        ft.Container(cliente_nombre, col={"sm": 12, "md": 4}),
                        ft.Container(cliente_correo, col={"sm": 12, "md": 4}),
                        ft.Container(cliente_cel, col={"sm": 12, "md": 4}),
                    ]
                ),
                ft.Row(
                    [
                        ft.ElevatedButton(
                            "Buscar cliente",
                            icon=ft.icons.SEARCH,
                            on_click=lambda _: self._open_client_search(cliente_nombre, cliente_correo, cliente_cel),
                        ),
                    ]
                ),
                ft.Divider(),
                ft.Text("Piezas", size=18, weight=ft.FontWeight.BOLD, color="#007ACC"),
                piezas_table,
                ft.Row([add_piece_button, calcular_button], alignment=ft.MainAxisAlignment.END),
            ],
            expand=True,
            scroll=ft.ScrollMode.AUTO,
        )

        return layout

    # ------------------------------------------------------------------
    def _set_project_field(self, name: str, value: str) -> None:
        if name == "proyecto":
            self.project_state.proyecto = value

    def _update_client_field(self, name: str, value: str) -> None:
        setattr(self.project_state.cliente, name, value)

    def _on_tipo_change(self, value: str) -> None:
        if value == PrinterType.RESINA.value:
            self.project_state.tipo = PrinterType.RESINA
        else:
            self.project_state.tipo = PrinterType.FILAMENTO
        printers = self.config_store.get_printers(self.project_state.tipo)
        self.project_state.impresora = printers[0] if printers else None
        self._render_view("proyecto")

    def _select_printer(self, nombre: str | None) -> None:
        if not nombre:
            self.project_state.impresora = None
            return
        printers = self.config_store.get_printers(self.project_state.tipo)
        for printer in printers:
            if printer.nombre == nombre:
                self.project_state.impresora = printer
                break

    def _select_material(self, nombre: str | None) -> None:
        if not nombre:
            self.project_state.material = None
            return
        for material in self.config_store.get_materials():
            if material.nombre == nombre:
                self.project_state.material = material
                self.project_state.precio_material = material.precio_kg
                break
        self._render_view("proyecto")

    def _update_precio_material(self, value: str) -> None:
        try:
            self.project_state.precio_material = float(value)
        except ValueError:
            pass

    # ------------------------------------------------------------------
    def _build_pieces_table(self) -> ft.Control:
        if not self.project_state.piezas:
            return ft.Container(
                content=ft.Text("No se han agregado piezas", color="#6A0DAD"),
                padding=ft.padding.all(12),
                bgcolor="#F2F2F2",
                border_radius=8,
            )

        rows: List[ft.DataRow] = []
        for idx, pieza_row in enumerate(self.project_state.piezas):
            pieza = pieza_row.pieza
            time_display = f"{pieza.horas}:{pieza.minutos:02d}"
            rows.append(
                ft.DataRow(
                    cells=[
                        ft.DataCell(ft.Text(pieza.nombre)),
                        ft.DataCell(ft.Text(str(pieza.cantidad))),
                        ft.DataCell(ft.Text(time_display)),
                        ft.DataCell(ft.Text(f"{pieza.masa_g:.2f}")),
                        ft.DataCell(ft.Text(f"${pieza_row.costos.total_total:,.2f}" if pieza_row.costos else "-")),
                        ft.DataCell(
                            ft.Row(
                                [
                                    ft.IconButton(
                                        icon=ft.icons.EDIT,
                                        tooltip="Editar",
                                        on_click=lambda _, index=idx: self._open_piece_dialog(index),
                                    ),
                                    ft.IconButton(
                                        icon=ft.icons.DELETE,
                                        tooltip="Eliminar",
                                        on_click=lambda _, index=idx: self._delete_piece(index),
                                    ),
                                ]
                            )
                        ),
                    ]
                )
            )

        table = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("Pieza")),
                ft.DataColumn(ft.Text("Cantidad")),
                ft.DataColumn(ft.Text("Tiempo (h:mm)")),
                ft.DataColumn(ft.Text("Masa (g)")),
                ft.DataColumn(ft.Text("Total")),
                ft.DataColumn(ft.Text("Acciones")),
            ],
            rows=rows,
            column_spacing=16,
            heading_row_color=ft.colors.with_opacity(0.08, "#007ACC"),
        )
        return ft.Container(content=table, expand=True)

    def _delete_piece(self, index: int) -> None:
        if 0 <= index < len(self.project_state.piezas):
            self.project_state.piezas.pop(index)
            self._render_view("proyecto")

    # ------------------------------------------------------------------
    def _open_piece_dialog(self, index: Optional[int] = None) -> None:
        editing = index is not None
        pieza = self.project_state.piezas[index].pieza if editing else None

        nombre_field = ft.TextField(label="Nombre", value=pieza.nombre if pieza else "")
        cantidad_field = ft.TextField(label="Cantidad", value=str(pieza.cantidad if pieza else 1), keyboard_type=ft.KeyboardType.NUMBER)
        horas_field = ft.TextField(label="Horas", value=str(pieza.horas if pieza else 0), keyboard_type=ft.KeyboardType.NUMBER)
        minutos_field = ft.TextField(label="Minutos", value=str(pieza.minutos if pieza else 0), keyboard_type=ft.KeyboardType.NUMBER)
        masa_field = ft.TextField(label="Masa (g)", value=f"{pieza.masa_g:.2f}" if pieza else "", keyboard_type=ft.KeyboardType.NUMBER)
        costo_stl_field = ft.TextField(label="Costo STL", value=f"{pieza.costo_stl:.2f}" if pieza else "0.0", keyboard_type=ft.KeyboardType.NUMBER)
        extras_field = ft.TextField(label="Extras", value=f"{pieza.extras:.2f}" if pieza else "0.0", keyboard_type=ft.KeyboardType.NUMBER)
        prep_field = ft.TextField(label="Min. preparación", value=f"{pieza.prep_min:.1f}" if pieza else "0.0", keyboard_type=ft.KeyboardType.NUMBER)
        supervision_field = ft.TextField(label="Horas supervisión", value=f"{pieza.supervision_h:.2f}" if pieza else "0.0", keyboard_type=ft.KeyboardType.NUMBER)
        notas_field = ft.TextField(label="Notas", value=pieza.notas or "", multiline=True, min_lines=2, max_lines=4)

        dialog = ft.AlertDialog(modal=True)

        def save_piece(_: ft.ControlEvent) -> None:
            try:
                nombre = nombre_field.value.strip()
                if not nombre:
                    raise ValueError("El nombre es obligatorio")
                cantidad = max(1, int(float(cantidad_field.value or 1)))
                horas = int(float(horas_field.value or 0))
                minutos = int(float(minutos_field.value or 0))
                tiempo_horas = combine_hours_minutes(horas, minutos)
                masa = float(masa_field.value or 0.0)
                costo_stl = float(costo_stl_field.value or 0.0)
                extras = float(extras_field.value or 0.0)
                prep_min = float(prep_field.value or 0.0)
                supervision = float(supervision_field.value or 0.0)
            except ValueError as exc:  # pragma: no cover - UI validation
                self.page.snack_bar = ft.SnackBar(ft.Text(str(exc)))
                self.page.snack_bar.open = True
                self.page.update()
                return

            pieza_data = Pieza(
                nombre=nombre,
                cantidad=cantidad,
                masa_g=masa,
                horas=horas,
                minutos=minutos,
                tiempo_horas=tiempo_horas,
                costo_stl=costo_stl,
                extras=extras,
                prep_min=prep_min,
                supervision_h=supervision,
                notas=notas_field.value or None,
            )
            pieza_row = PieceRow(pieza=pieza_data)
            if editing and index is not None:
                self.project_state.piezas[index] = pieza_row
            else:
                self.project_state.piezas.append(pieza_row)
            dialog.open = False
            self.page.update()
            self._render_view("proyecto")

        dialog.content = ft.Container(
            width=520,
            content=ft.Column(
                [
                    ft.Text("Detalle de pieza", size=18, weight=ft.FontWeight.BOLD),
                    nombre_field,
                    ft.Row([horas_field, minutos_field, masa_field]),
                    cantidad_field,
                    costo_stl_field,
                    extras_field,
                    prep_field,
                    supervision_field,
                    notas_field,
                    ft.Row(
                        [
                            ft.TextButton("Cancelar", on_click=lambda _: self._close_dialog(dialog)),
                            ft.FilledButton("Guardar", on_click=save_piece),
                        ],
                        alignment=ft.MainAxisAlignment.END,
                    ),
                ],
                tight=True,
                scroll=ft.ScrollMode.AUTO,
            ),
        )
        dialog.actions_alignment = ft.MainAxisAlignment.END
        self.page.dialog = dialog
        dialog.open = True
        self.page.update()

    def _close_dialog(self, dialog: ft.AlertDialog) -> None:
        dialog.open = False
        self.page.update()

    # ------------------------------------------------------------------
    def _search_client(self, query: str) -> None:
        matches = self.clients_store.search(query)
        if not matches:
            self.page.snack_bar = ft.SnackBar(ft.Text("No se encontraron clientes"))
            self.page.snack_bar.open = True
            self.page.update()
            return
        cliente = matches[0]
        self.project_state.cliente = cliente.to_info()
        self._render_view("proyecto")

    def _open_client_search(
        self, nombre_field: ft.TextField, correo_field: ft.TextField, cel_field: ft.TextField
    ) -> None:
        def select(cliente: Cliente) -> None:
            self.project_state.cliente = cliente.to_info()
            nombre_field.value = cliente.nombre
            correo_field.value = cliente.correo
            cel_field.value = cliente.celular
            dialog.open = False
            self.page.update()

        matches = self.clients_store.search(nombre_field.value)
        options = [
            ft.ListTile(
                title=ft.Text(cli.nombre),
                subtitle=ft.Text(cli.correo or ""),
                on_click=lambda e, cliente=cli: select(cliente),
            )
            for cli in matches
        ]
        dialog = ft.AlertDialog(modal=True, title=ft.Text("Seleccionar cliente"))

        if not options:
            options = [ft.Text("No hay coincidencias")]
        dialog.content = ft.Container(width=400, height=300, content=ft.Column(options, scroll=ft.ScrollMode.AUTO))
        dialog.actions = [ft.TextButton("Cerrar", on_click=lambda _: self._close_dialog(dialog))]
        self.page.dialog = dialog
        dialog.open = True
        self.page.update()

    # ------------------------------------------------------------------
    def _calculate_quote_from_state(self) -> None:
        if not self.project_state.impresora or not self.project_state.material:
            self.page.snack_bar = ft.SnackBar(ft.Text("Seleccione impresora y material"))
            self.page.snack_bar.open = True
            self.page.update()
            return
        if not self.project_state.piezas:
            self.page.snack_bar = ft.SnackBar(ft.Text("Agregue al menos una pieza"))
            self.page.snack_bar.open = True
            self.page.update()
            return

        piezas = [row.pieza for row in self.project_state.piezas]

        folio = self.project_state.folio or self.config_store.next_quote_folio(self.quote_store.exists)
        financial_raw = self.config_store.get_financials()
        financials = FinancialSettings(
            precio_kwh=financial_raw.get("precio_kwh", 0.0),
            costo_hora=financial_raw.get("costo_hora", 0.0),
            merma=financial_raw.get("merma", 0.0),
            riesgo=financial_raw.get("riesgo", 0.0),
            ganancia=financial_raw.get("ganancia", 0.0),
            iva=financial_raw.get("iva", 0.0),
        )

        breakdown = build_quote_breakdown(
            piezas,
            self.project_state.impresora,
            self.project_state.material,
            material_precio_kg=self.project_state.precio_material or self.project_state.material.precio_kg,
            financials=financials,
        )

        cotizacion = Cotizacion(
            folio=folio,
            fecha=self.project_state.fecha.isoformat(),
            proyecto=self.project_state.proyecto,
            tipo=self.project_state.tipo.value,
            impresora=self.project_state.impresora.nombre,
            material=self.project_state.material.nombre,
            material_precio_kg=self.project_state.precio_material or self.project_state.material.precio_kg,
            cliente=self.project_state.cliente,
            piezas=[item for item in breakdown.piezas],
            subtotal_base=breakdown.subtotal_base,
            merma=breakdown.merma,
            riesgo=breakdown.riesgo,
            ganancia=breakdown.ganancia,
            subtotal_post_riesgo=breakdown.subtotal_post_riesgo,
            total_sin_iva=breakdown.total_sin_iva,
            iva=breakdown.iva,
            total=breakdown.total,
            moneda=breakdown.moneda,
            notas=self.project_state.notas or None,
        )

        for row, costos in zip(self.project_state.piezas, breakdown.piezas):
            row.costos = costos

        self._open_quote_summary(cotizacion)

    # ------------------------------------------------------------------
    def _open_quote_summary(self, cotizacion: Cotizacion) -> None:
        piezas_rows = [
            ft.DataRow(
                cells=[
                    ft.DataCell(ft.Text(item.pieza.nombre)),
                    ft.DataCell(ft.Text(str(item.pieza.cantidad))),
                    ft.DataCell(ft.Text(f"{item.pieza.horas}:{item.pieza.minutos:02d}")),
                    ft.DataCell(ft.Text(f"${item.total_unit:,.2f}")),
                    ft.DataCell(ft.Text(f"${item.total_total:,.2f}")),
                ]
            )
            for item in cotizacion.piezas
        ]

        if not piezas_rows:
            piezas_rows = [ft.DataRow(cells=[ft.DataCell(ft.Text("Sin piezas"))])]
            piezas_table = ft.DataTable(columns=[ft.DataColumn(ft.Text("Mensaje"))], rows=piezas_rows)
        else:
            piezas_table = ft.DataTable(
                columns=[
                    ft.DataColumn(ft.Text("Pieza")),
                    ft.DataColumn(ft.Text("Cantidad")),
                    ft.DataColumn(ft.Text("Tiempo")),
                    ft.DataColumn(ft.Text("Precio unitario")),
                    ft.DataColumn(ft.Text("Total")),
                ],
                rows=piezas_rows,
            )

        content = ft.Column(
            [
                ft.Text(f"Cotización {cotizacion.folio}", size=20, weight=ft.FontWeight.BOLD),
                ft.Text(f"Cliente: {cotizacion.cliente.nombre}", size=16),
                piezas_table,
                ft.Divider(),
                ft.Row(
                    [
                        ft.Text(f"Subtotal: ${cotizacion.subtotal_base:,.2f}"),
                        ft.Text(f"IVA: ${cotizacion.iva:,.2f}"),
                        ft.Text(f"Total: ${cotizacion.total:,.2f}"),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                ),
            ],
            expand=True,
            scroll=ft.ScrollMode.AUTO,
        )

        footer = ft.Row(
            [
                ft.TextButton("Cancelar", on_click=lambda _: self._close_dialog(dialog)),
                ft.ElevatedButton(
                    "Guardar",
                    icon=ft.icons.SAVE,
                    on_click=lambda _: self._save_quote(cotizacion, dialog),
                ),
                ft.ElevatedButton(
                    "Exportar PDF",
                    icon=ft.icons.PICTURE_AS_PDF,
                    on_click=lambda _: self._export_quote_pdf(cotizacion),
                ),
                ft.ElevatedButton(
                    "Exportar Excel/CSV",
                    icon=ft.icons.TABLE_VIEW,
                    on_click=lambda _: self._export_quote_excel(cotizacion),
                ),
                ft.IconButton(
                    icon=ft.icons.EMAIL,
                    tooltip="Enviar por correo",
                    on_click=lambda _: self._send_quote_email(cotizacion),
                ),
                ft.IconButton(
                    icon=ft.icons.CHAT,
                    tooltip="Enviar por WhatsApp",
                    on_click=lambda _: self._send_quote_whatsapp(cotizacion),
                ),
            ],
            alignment=ft.MainAxisAlignment.END,
        )

        dialog = ft.AlertDialog(modal=True)
        dialog.content = ft.Container(width=720, height=520, content=ft.Column([content, footer], tight=True))
        self.page.dialog = dialog
        dialog.open = True
        self.page.update()

    # ------------------------------------------------------------------
    def _save_quote(self, cotizacion: Cotizacion, dialog: ft.AlertDialog) -> None:
        self.quote_store.save(cotizacion)
        self.clients_store.register_quote(cotizacion.cliente, cotizacion)
        self.project_state.folio = cotizacion.folio
        self.page.snack_bar = ft.SnackBar(ft.Text("Cotización guardada"))
        self.page.snack_bar.open = True
        dialog.open = False
        self.page.update()
        self._render_view("cotizaciones")

    def _export_quote_pdf(self, cotizacion: Cotizacion) -> Path:
        from export.pdf_quote import export_quote_pdf

        path = export_quote_pdf(cotizacion, self.config_store.get_identity())
        self.page.snack_bar = ft.SnackBar(ft.Text(f"PDF exportado en {path}"))
        self.page.snack_bar.open = True
        self.page.update()
        return path

    def _export_quote_excel(self, cotizacion: Cotizacion) -> Path:
        from export.csv_quote import export_quote_csv

        path = export_quote_csv(cotizacion)
        self.page.snack_bar = ft.SnackBar(ft.Text(f"CSV exportado en {path}"))
        self.page.snack_bar.open = True
        self.page.update()
        return path

    def _send_quote_email(self, cotizacion: Cotizacion) -> None:
        from export.pdf_quote import export_quote_pdf

        integrations = self.config_store.get_integrations()
        email_cfg: Dict[str, object] = integrations.get("email", {})  # type: ignore[assignment]
        if not email_cfg:
            self.page.snack_bar = ft.SnackBar(ft.Text("Configura SMTP en Integraciones"))
            self.page.snack_bar.open = True
            self.page.update()
            return

        pdf_path = export_quote_pdf(cotizacion, self.config_store.get_identity())
        try:
            send_email_with_pdf(email_cfg, cotizacion, pdf_path)
            self.page.snack_bar = ft.SnackBar(ft.Text("Correo enviado"))
        except MessagingError as exc:  # pragma: no cover - network dependent
            self.page.snack_bar = ft.SnackBar(ft.Text(str(exc)))
        self.page.snack_bar.open = True
        self.page.update()

    def _send_quote_whatsapp(self, cotizacion: Cotizacion) -> None:
        from export.pdf_quote import export_quote_pdf

        integrations = self.config_store.get_integrations()
        whatsapp_cfg: Dict[str, object] = integrations.get("whatsapp", {})  # type: ignore[assignment]
        pdf_path = export_quote_pdf(cotizacion, self.config_store.get_identity())
        try:
            send_whatsapp_placeholder(whatsapp_cfg, cotizacion, pdf_path)
            self.page.snack_bar = ft.SnackBar(ft.Text("Solicitud enviada (placeholder)"))
        except MessagingError as exc:  # pragma: no cover - network dependent
            self.page.snack_bar = ft.SnackBar(ft.Text(str(exc)))
        self.page.snack_bar.open = True
        self.page.update()

    # ------------------------------------------------------------------
    def _build_quotes_view(self) -> ft.Control:
        quotes = self.quote_store.list_quotes()
        rows: List[ft.DataRow] = []
        for quote in quotes:
            rows.append(
                ft.DataRow(
                    cells=[
                        ft.DataCell(ft.Text(quote.folio)),
                        ft.DataCell(ft.Text(quote.fecha)),
                        ft.DataCell(ft.Text(quote.proyecto)),
                        ft.DataCell(ft.Text(quote.cliente.nombre)),
                        ft.DataCell(ft.Text(f"${quote.total:,.2f}")),
                        ft.DataCell(
                            ft.Row(
                                [
                                    ft.IconButton(
                                        icon=ft.icons.VISIBILITY,
                                        tooltip="Ver",
                                        on_click=lambda _, q=quote: self._open_quote_summary(q),
                                    ),
                                    ft.IconButton(
                                        icon=ft.icons.SWAP_HORIZ,
                                        tooltip="Convertir a pedido",
                                        on_click=lambda _, q=quote: self._convert_to_order(q),
                                    ),
                                ]
                            )
                        ),
                    ]
                )
            )

        table = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("Folio")),
                ft.DataColumn(ft.Text("Fecha")),
                ft.DataColumn(ft.Text("Proyecto")),
                ft.DataColumn(ft.Text("Cliente")),
                ft.DataColumn(ft.Text("Total")),
                ft.DataColumn(ft.Text("Acciones")),
            ],
            rows=rows,
            expand=True,
        )
        return ft.Column([ft.Text("Cotizaciones", size=20, weight=ft.FontWeight.BOLD), table], expand=True)

    def _convert_to_order(self, cotizacion: Cotizacion) -> None:
        delivery_picker = ft.DatePicker()

        def accept(_: ft.ControlEvent) -> None:
            if not delivery_picker.value:
                self.page.snack_bar = ft.SnackBar(ft.Text("Seleccione fecha"))
                self.page.snack_bar.open = True
                self.page.update()
                return
            fecha_estimada = delivery_picker.value.strftime("%Y-%m-%d")
            folio = self.config_store.next_order_folio(self.orders_store.exists)
            pedido = Pedido(
                folio=folio,
                folio_cotizacion=cotizacion.folio,
                fecha_creacion=datetime.utcnow().date().isoformat(),
                fecha_estimada=fecha_estimada,
                proyecto=cotizacion.proyecto,
                tipo=cotizacion.tipo,
                impresora=cotizacion.impresora,
                cliente=cotizacion.cliente,
                subtotal_base=cotizacion.subtotal_base,
                total=cotizacion.total,
                merma=cotizacion.merma,
                riesgo=cotizacion.riesgo,
                ganancia=cotizacion.ganancia,
                iva=cotizacion.iva,
                moneda=cotizacion.moneda,
            )
            self.orders_store.save(pedido)
            self.clients_store.register_order(cotizacion.cliente, pedido)
            self.page.snack_bar = ft.SnackBar(ft.Text(f"Pedido {pedido.folio} creado"))
            self.page.snack_bar.open = True
            dialog.open = False
            self.page.update()
            self._render_view("pedidos")

        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("Fecha estimada de entrega"),
            content=ft.Container(width=320, content=delivery_picker),
            actions=[
                ft.TextButton("Cancelar", on_click=lambda _: self._close_dialog(dialog)),
                ft.FilledButton("Aceptar", on_click=accept),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        self.page.dialog = dialog
        dialog.open = True
        self.page.update()

    # ------------------------------------------------------------------
    def _build_orders_view(self) -> ft.Control:
        pedidos = self.orders_store.list_orders()
        rows: List[ft.DataRow] = []
        for pedido in pedidos:
            rows.append(
                ft.DataRow(
                    cells=[
                        ft.DataCell(ft.Text(pedido.folio)),
                        ft.DataCell(ft.Text(pedido.estado)),
                        ft.DataCell(ft.Text(pedido.fecha_creacion)),
                        ft.DataCell(ft.Text(pedido.fecha_entrega or "-")),
                        ft.DataCell(ft.Text(f"${pedido.total:,.2f}")),
                    ]
                )
            )
        table = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("Folio")),
                ft.DataColumn(ft.Text("Estado")),
                ft.DataColumn(ft.Text("Creación")),
                ft.DataColumn(ft.Text("Entrega")),
                ft.DataColumn(ft.Text("Total")),
            ],
            rows=rows,
            expand=True,
        )
        return ft.Column([ft.Text("Pedidos", size=20, weight=ft.FontWeight.BOLD), table], expand=True)

    # ------------------------------------------------------------------
    def _build_clients_view(self) -> ft.Control:
        clients = self.clients_store.list_clients()
        rows = [
            ft.DataRow(
                cells=[
                    ft.DataCell(ft.Text(cli.nombre)),
                    ft.DataCell(ft.Text(cli.celular or "")),
                    ft.DataCell(ft.Text(cli.correo or "")),
                    ft.DataCell(ft.Text(f"${cli.total_facturado:,.2f}")),
                ]
            )
            for cli in clients
        ]
        table = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("Nombre")),
                ft.DataColumn(ft.Text("Celular")),
                ft.DataColumn(ft.Text("Correo")),
                ft.DataColumn(ft.Text("Total")),
            ],
            rows=rows,
            expand=True,
        )
        return ft.Column([ft.Text("Clientes", size=20, weight=ft.FontWeight.BOLD), table], expand=True)

    # ------------------------------------------------------------------
    def _build_accounting_view(self) -> ft.Control:
        pedidos = self.orders_store.list_orders()
        aggregates: Dict[str, Dict[str, float]] = defaultdict(
            lambda: {"ingresos": 0.0, "costos": 0.0, "ganancia": 0.0}
        )
        for pedido in pedidos:
            mes = (pedido.fecha_creacion or "")[:7] or "Sin fecha"
            bucket = aggregates[mes]
            bucket["ingresos"] += pedido.total
            bucket["costos"] += pedido.subtotal_base + pedido.merma + pedido.riesgo
            bucket["ganancia"] += pedido.ganancia

        rows: List[ft.DataRow] = []
        for mes in sorted(aggregates.keys()):
            item = aggregates[mes]
            rows.append(
                ft.DataRow(
                    cells=[
                        ft.DataCell(ft.Text(mes)),
                        ft.DataCell(ft.Text(f"${item['ingresos']:,.2f}")),
                        ft.DataCell(ft.Text(f"${item['costos']:,.2f}")),
                        ft.DataCell(ft.Text(f"${item['ganancia']:,.2f}")),
                    ]
                )
            )
        table = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("Mes")),
                ft.DataColumn(ft.Text("Ingresos")),
                ft.DataColumn(ft.Text("Costos")),
                ft.DataColumn(ft.Text("Ganancia")),
            ],
            rows=rows,
            expand=True,
        )
        return ft.Column([ft.Text("Contabilidad", size=20, weight=ft.FontWeight.BOLD), table], expand=True)

    # ------------------------------------------------------------------
    def _build_configuration_view(self) -> ft.Control:
        identity = self.config_store.get_identity()
        nombre_field = ft.TextField(label="Nombre comercial", value=identity.get("nombre_comercial", ""))
        rfc_field = ft.TextField(label="RFC", value=identity.get("rfc", ""))
        telefono_field = ft.TextField(label="Teléfono", value=identity.get("telefono", ""))
        email_field = ft.TextField(label="Correo", value=identity.get("correo", ""))

        def save(_: ft.ControlEvent) -> None:
            identity["nombre_comercial"] = nombre_field.value
            identity["rfc"] = rfc_field.value
            identity["telefono"] = telefono_field.value
            identity["correo"] = email_field.value
            self.config_store.update_identity(identity)
            self.page.snack_bar = ft.SnackBar(ft.Text("Identidad guardada"))
            self.page.snack_bar.open = True
            self.page.update()

        return ft.Column(
            [
                ft.Text("Configuración", size=20, weight=ft.FontWeight.BOLD),
                nombre_field,
                rfc_field,
                telefono_field,
                email_field,
                ft.Row([ft.FilledButton("Guardar", on_click=save)], alignment=ft.MainAxisAlignment.END),
            ],
            expand=True,
        )


__all__ = ["Axis3DFletApp"]
