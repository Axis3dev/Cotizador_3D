"""PDF export for quotations styled to the provided specification."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Dict

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.platypus import (
    HRFlowable,
    Image,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet

from models.cotizacion import Cotizacion
from models.pieza import format_hours_minutes
from .branding import resolve_logo_path


MAIN_TEXT = colors.HexColor("#111111")
LIGHT_BG = colors.HexColor("#F2F2F2")
HEADER_BLUE = colors.HexColor("#007ACC")
TOTAL_PURPLE = colors.HexColor("#6A0DAD")


def _format_currency(value: float) -> str:
    """Return currency formatted with two decimals and thousands separators."""

    return f"${value:,.2f}"


def _format_time(hours: int, minutes: int) -> str:
    """Return time formatted as ``H:MM`` using stored hours/minutes."""

    return format_hours_minutes(hours, minutes)


def _build_styles() -> dict[str, ParagraphStyle]:
    """Create the paragraph styles used across the PDF."""

    styles = getSampleStyleSheet()
    body = ParagraphStyle(
        "Body",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=10,
        leading=12,
        textColor=MAIN_TEXT,
    )
    subtitle = ParagraphStyle(
        "Subtitle",
        parent=body,
        fontName="Helvetica-Bold",
        fontSize=12,
        leading=14,
        textColor=HEADER_BLUE,
    )
    title = ParagraphStyle(
        "Title",
        parent=body,
        fontName="Helvetica-Bold",
        fontSize=18,
        leading=22,
        alignment=1,
    )
    header_block = ParagraphStyle(
        "HeaderBlock",
        parent=body,
        fontSize=11,
        leading=14,
    )
    footer_center = ParagraphStyle(
        "FooterCenter",
        parent=body,
        alignment=1,
    )
    table_cell = ParagraphStyle(
        "TableCell",
        parent=body,
        alignment=1,
    )
    return {
        "body": body,
        "subtitle": subtitle,
        "title": title,
        "header": header_block,
        "footer_center": footer_center,
        "table_cell": table_cell,
    }


def export_quote_pdf(
    quote: Cotizacion,
    identity: Dict[str, object],
    directory: Path | None = None,
) -> Path:
    """Export the quotation to PDF following the requested layout."""

    directory = directory or Path.cwd()
    directory.mkdir(parents=True, exist_ok=True)

    try:
        fecha = datetime.fromisoformat(quote.fecha)
    except ValueError:
        fecha = datetime.now()
    cliente_slug = quote.cliente.nombre.replace(" ", "_") or "Cliente"
    file_name = f"Cotizacion_{quote.folio}_{cliente_slug}_{fecha.strftime('%Y%m%d')}.pdf"
    path = directory / file_name

    doc = SimpleDocTemplate(
        str(path),
        pagesize=A4,
        topMargin=1 * cm,
        bottomMargin=1.5 * cm,
        leftMargin=1.7 * cm,
        rightMargin=1.7 * cm,
    )

    styles = _build_styles()
    story: list = []

    logo_path = resolve_logo_path(identity)
    logo_size = 2.2 * cm
    if logo_path:
        try:
            logo_image = Image(str(logo_path), width=logo_size, height=logo_size)
        except Exception:
            logo_image = Spacer(logo_size, logo_size)
    else:
        logo_image = Spacer(logo_size, logo_size)

    header_text = "<b>AXIS 3D</b><br/>RFC: XXX010203ABC<br/>Culiacán, Sinaloa<br/>Tel: 667-123-4567<br/>Email: contacto@axis3d.com"
    header_table = Table(
        [[logo_image, Paragraph(header_text, styles["header"])]],
        colWidths=[2.6 * cm, None],
        hAlign="LEFT",
    )
    header_table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ]
        )
    )
    story.append(header_table)
    story.append(Spacer(1, 10))

    story.append(Paragraph("COTIZACIÓN", styles["title"]))
    story.append(Spacer(1, 18))

    general_data = [
        [
            Paragraph("Folio:", styles["body"]),
            Paragraph(quote.folio, styles["body"]),
            Paragraph("Fecha:", styles["body"]),
            Paragraph(fecha.strftime("%d/%m/%Y"), styles["body"]),
        ],
        [
            Paragraph("Validez:", styles["body"]),
            Paragraph("12 días", styles["body"]),
            Paragraph("Moneda:", styles["body"]),
            Paragraph("MXN", styles["body"]),
        ],
    ]

    general_table = Table(
        general_data,
        colWidths=[2 * cm, 6 * cm, 2 * cm, 6 * cm],
        hAlign="LEFT",
    )
    general_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), LIGHT_BG),
                ("BOX", (0, 0), (-1, -1), 0.25, colors.grey),
                ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.grey),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ]
        )
    )
    story.append(general_table)
    story.append(Spacer(1, 15))

    story.append(Paragraph("Datos del cliente", styles["subtitle"]))
    story.append(Spacer(1, 6))

    client_data = [
        [Paragraph("Nombre:", styles["body"]), Paragraph(quote.cliente.nombre, styles["body"])],
        [Paragraph("Correo:", styles["body"]), Paragraph(quote.cliente.correo, styles["body"])],
        [Paragraph("Teléfono:", styles["body"]), Paragraph(quote.cliente.celular, styles["body"])],
    ]
    client_table = Table(client_data, colWidths=[3 * cm, None], hAlign="LEFT")
    client_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), LIGHT_BG),
                ("BOX", (0, 0), (-1, -1), 0.25, colors.grey),
                ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.grey),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ]
        )
    )
    story.append(client_table)
    story.append(Spacer(1, 15))

    story.append(Paragraph("Detalle de piezas", styles["subtitle"]))
    story.append(Spacer(1, 6))

    pieces_rows = [
        [
            Paragraph("Pieza", styles["table_cell"]),
            Paragraph("Cantidad", styles["table_cell"]),
            Paragraph("Tiempo (h:mm)", styles["table_cell"]),
            Paragraph("Precio unitario", styles["table_cell"]),
            Paragraph("Total", styles["table_cell"]),
        ]
    ]

    for pieza in quote.piezas:
        piezas_row = [
            Paragraph(pieza.pieza.nombre, styles["table_cell"]),
            Paragraph(str(pieza.pieza.cantidad), styles["table_cell"]),
            Paragraph(_format_time(pieza.pieza.horas, pieza.pieza.minutos), styles["table_cell"]),
            Paragraph(_format_currency(pieza.total_unit), styles["table_cell"]),
            Paragraph(_format_currency(pieza.total_total), styles["table_cell"]),
        ]
        pieces_rows.append(piezas_row)

    if len(pieces_rows) == 1:
        pieces_rows.append(
            [
                Paragraph("-", styles["table_cell"]),
                Paragraph("-", styles["table_cell"]),
                Paragraph("-", styles["table_cell"]),
                Paragraph("-", styles["table_cell"]),
                Paragraph("-", styles["table_cell"]),
            ]
        )

    pieces_table = Table(
        pieces_rows,
        colWidths=[None, 3 * cm, 3 * cm, 4 * cm, 4 * cm],
        hAlign="LEFT",
    )
    pieces_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), HEADER_BLUE),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("BACKGROUND", (0, 1), (-1, -1), colors.white),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
            ]
        )
    )
    story.append(pieces_table)
    story.append(Spacer(1, 15))

    subtotal_value = quote.total_sin_iva
    if abs(subtotal_value) < 1e-9 and quote.total:
        subtotal_value = max(quote.total - quote.iva, 0.0)

    totals_data = [
        [Paragraph("Subtotal:", styles["body"]), Paragraph(_format_currency(subtotal_value), styles["body"])],
        [Paragraph("IVA (16%):", styles["body"]), Paragraph(_format_currency(quote.iva), styles["body"])],
        [Paragraph("", styles["body"]), Paragraph("", styles["body"])],
        [
            Paragraph("Total:", styles["body"]),
            Paragraph(f"{_format_currency(quote.total)} MXN", styles["body"]),
        ],
    ]
    totals_table = Table(totals_data, colWidths=[10 * cm, 5 * cm], hAlign="RIGHT")
    totals_table.setStyle(
        TableStyle(
            [
                ("ALIGN", (0, 0), (-1, -1), "RIGHT"),
                ("FONTNAME", (0, 3), (-1, 3), "Helvetica-Bold"),
                ("TEXTCOLOR", (0, 3), (-1, 3), TOTAL_PURPLE),
                ("LINEABOVE", (0, 3), (-1, 3), 0.5, TOTAL_PURPLE),
            ]
        )
    )
    story.append(totals_table)
    story.append(Spacer(1, 40))

    story.append(Paragraph("Condiciones comerciales", styles["subtitle"]))
    story.append(Spacer(1, 6))
    story.append(Paragraph("Forma de pago: Transferencia bancaria", styles["body"]))
    story.append(Paragraph("Anticipo: 50% al iniciar producción", styles["body"]))
    story.append(Spacer(1, 10))
    story.append(HRFlowable(width="100%", thickness=0.5, color=MAIN_TEXT))
    story.append(Spacer(1, 8))
    story.append(Paragraph("Responsable: Ing. Iván Beltrán", styles["footer_center"]))

    doc.build(story)
    return path


__all__ = ["export_quote_pdf"]
