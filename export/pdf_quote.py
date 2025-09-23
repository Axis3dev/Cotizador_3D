"""PDF export for quotations."""

from __future__ import annotations

from datetime import datetime
import logging
from pathlib import Path
from typing import Dict

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

from models.cotizacion import Cotizacion
from models.pieza import format_hours_minutes


def _format_currency(value: float, moneda: str) -> str:
    return f"{moneda} ${value:,.2f}" if moneda else f"${value:,.2f}"


def export_quote_pdf(
    quote: Cotizacion,
    identity: Dict[str, object],
    directory: Path | None = None,
) -> Path:
    directory = directory or Path.cwd()
    directory.mkdir(parents=True, exist_ok=True)

    fecha = datetime.fromisoformat(quote.fecha)
    cliente_slug = quote.cliente.nombre.replace(" ", "_") or "Cliente"
    file_name = f"Cotizacion_{quote.folio}_{cliente_slug}_{fecha.strftime('%Y%m%d')}.pdf"
    path = directory / file_name

    c = canvas.Canvas(str(path), pagesize=letter)
    width, height = letter

    y = height - 40

    logo_path = identity.get("logo_path") or identity.get("logo")
    logo_drawn = False
    if logo_path:
        logo = Path(logo_path).expanduser()
        if not logo.is_absolute():
            logo = Path.cwd() / logo
        if logo.exists():
            try:
                c.drawImage(str(logo), 40, y - 40, width=60, preserveAspectRatio=True, mask="auto")
                logo_drawn = True
            except Exception as exc:
                logging.getLogger(__name__).warning("No se pudo dibujar el logo en PDF: %s", exc)
        else:
            logging.getLogger(__name__).info("Logo no encontrado en %s, se omite en PDF", logo)
    text_x = 120 if logo_drawn else 40
    c.setFont("Helvetica-Bold", 14)
    c.drawString(text_x, y, identity.get("nombre_comercial", "Cotización 3D"))
    c.setFont("Helvetica", 10)
    c.drawString(text_x, y - 14, identity.get("direccion", ""))
    c.drawString(text_x, y - 28, identity.get("telefono", ""))
    c.drawString(400, y, f"Fecha: {quote.fecha}")
    c.drawString(400, y - 14, f"Folio: {quote.folio}")
    c.drawString(400, y - 28, "Validez: 12 días")

    y -= 70
    c.setFont("Helvetica-Bold", 12)
    c.drawString(40, y, "Datos del cliente")
    c.setFont("Helvetica", 10)
    y -= 16
    c.drawString(40, y, f"Nombre: {quote.cliente.nombre}")
    y -= 14
    c.drawString(40, y, f"Correo: {quote.cliente.correo}")
    y -= 14
    c.drawString(40, y, f"Celular: {quote.cliente.celular}")

    y -= 24
    c.setFont("Helvetica-Bold", 12)
    c.drawString(40, y, "Proyecto")
    c.setFont("Helvetica", 10)
    y -= 16
    c.drawString(40, y, f"Nombre: {quote.proyecto}")
    y -= 14
    c.drawString(40, y, f"Tipo: {quote.tipo}")
    y -= 14
    c.drawString(40, y, f"Impresora: {quote.impresora}")
    y -= 14
    c.drawString(40, y, f"Material: {quote.material} @ {quote.material_precio_kg:.2f} {quote.moneda}/kg")

    y -= 24
    c.setFont("Helvetica-Bold", 12)
    c.drawString(40, y, "Detalle de piezas")
    y -= 18

    table_top = y
    c.setFillColor(colors.lightgrey)
    c.rect(40, y - 4, width - 80, 18, fill=1, stroke=0)
    c.setFillColor(colors.black)
    c.setFont("Helvetica-Bold", 10)
    c.drawString(50, y, "Pieza")
    c.drawRightString(300, y, "Cantidad")
    c.drawString(320, y, "Tiempo (h:mm)")
    c.drawRightString(460, y, "Precio unitario")
    c.drawRightString(520, y, "Total")

    y -= 24
    c.setFont("Helvetica", 10)
    for pieza in quote.piezas:
        if y < 120:
            c.showPage()
            y = height - 80
            c.setFont("Helvetica", 10)
        c.drawString(50, y, pieza.pieza.nombre)
        c.drawRightString(300, y, str(pieza.pieza.cantidad))
        c.drawString(320, y, format_hours_minutes(pieza.pieza.horas, pieza.pieza.minutos))
        c.drawRightString(460, y, _format_currency(pieza.total_unit, quote.moneda))
        c.drawRightString(520, y, _format_currency(pieza.total_total, quote.moneda))
        y -= 16

    y -= 16
    c.setFont("Helvetica-Bold", 11)
    c.drawRightString(400, y, "Subtotal base:")
    c.drawRightString(520, y, _format_currency(quote.subtotal_base, quote.moneda))
    y -= 14
    c.setFont("Helvetica", 10)
    c.drawRightString(400, y, "Merma:")
    c.drawRightString(520, y, _format_currency(quote.merma, quote.moneda))
    y -= 14
    c.drawRightString(400, y, "Riesgo:")
    c.drawRightString(520, y, _format_currency(quote.riesgo, quote.moneda))
    y -= 14
    c.drawRightString(400, y, "Ganancia:")
    c.drawRightString(520, y, _format_currency(quote.ganancia, quote.moneda))
    y -= 14
    c.drawRightString(400, y, "Subtotal post riesgo:")
    c.drawRightString(520, y, _format_currency(quote.subtotal_post_riesgo, quote.moneda))
    y -= 14
    c.drawRightString(400, y, "Total sin IVA:")
    c.drawRightString(520, y, _format_currency(quote.total_sin_iva, quote.moneda))
    y -= 14
    c.setFont("Helvetica-Bold", 11)
    c.drawRightString(400, y, "IVA:")
    c.drawRightString(520, y, _format_currency(quote.iva, quote.moneda))
    y -= 16
    c.setFont("Helvetica-Bold", 12)
    c.drawRightString(400, y, "Total:")
    c.drawRightString(520, y, _format_currency(quote.total, quote.moneda))

    y -= 40
    c.setFont("Helvetica", 9)
    politicas = identity.get("politicas", "")
    if politicas:
        for line in str(politicas).splitlines():
            c.drawString(40, y, line)
            y -= 12

    c.showPage()
    c.save()
    return path


__all__ = ["export_quote_pdf"]
