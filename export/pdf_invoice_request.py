"""PDF generator for invoice requests."""

from __future__ import annotations

from datetime import datetime
import logging
from pathlib import Path
from typing import Dict, Optional

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

from models.cliente import Cliente
from models.cotizacion import Cotizacion
from models.pedido import Pedido


def _resolve_logo(identity: Dict[str, object]) -> Optional[Path]:
    logo_path = identity.get("logo_path") or identity.get("logo")
    if not logo_path:
        return None
    path = Path(str(logo_path)).expanduser()
    if not path.is_absolute():
        path = Path.cwd() / path
    return path if path.exists() else None


def export_invoice_request_pdf(
    pedido: Pedido,
    quote: Optional[Cotizacion],
    identity: Dict[str, object],
    cliente: Cliente,
    directory: Path | None = None,
) -> Path:
    directory = directory or Path.cwd()
    directory.mkdir(parents=True, exist_ok=True)
    file_name = f"Solicitud_Facturacion_{pedido.folio}.pdf"
    path = directory / file_name

    c = canvas.Canvas(str(path), pagesize=letter)
    width, height = letter

    y = height - 40
    logo = _resolve_logo(identity)
    if logo:
        try:
            c.drawImage(str(logo), 40, y - 40, width=80, preserveAspectRatio=True, mask="auto")
        except Exception as exc:  # pragma: no cover - reportlab
            logging.getLogger(__name__).warning("No se pudo dibujar el logo en solicitud: %s", exc)
    text_x = 140 if logo else 40
    c.setFont("Helvetica-Bold", 14)
    c.drawString(text_x, y, identity.get("nombre_comercial", "Cotizador 3D"))
    c.setFont("Helvetica", 10)
    c.drawString(text_x, y - 14, identity.get("direccion", ""))
    c.drawString(text_x, y - 28, identity.get("telefono", ""))
    c.drawRightString(width - 40, y, f"Fecha: {datetime.utcnow().date().isoformat()}")
    c.drawRightString(width - 40, y - 14, f"Pedido: {pedido.folio}")
    if pedido.folio_cotizacion:
        c.drawRightString(width - 40, y - 28, f"Cotización: {pedido.folio_cotizacion}")

    y -= 70
    c.setFont("Helvetica-Bold", 12)
    c.drawString(40, y, "Datos del cliente")
    c.setFont("Helvetica", 10)
    y -= 16
    c.drawString(40, y, f"Nombre: {cliente.nombre}")
    y -= 14
    c.drawString(40, y, f"Correo: {cliente.correo}")
    y -= 14
    c.drawString(40, y, f"Teléfono: {cliente.celular}")
    y -= 14
    c.drawString(40, y, f"RFC: {cliente.rfc}")
    y -= 14
    c.drawString(40, y, f"Razón social: {cliente.razon_social}")
    y -= 14
    c.drawString(40, y, f"Domicilio: {cliente.domicilio_fiscal}")
    y -= 14
    c.drawString(40, y, f"CP: {cliente.codigo_postal}  Régimen: {cliente.regimen}")

    y -= 24
    c.setFont("Helvetica-Bold", 12)
    c.drawString(40, y, "Detalle de piezas")
    y -= 18

    table_headers = ["Pieza", "Cantidad", "Subtotal", "IVA", "Total"]
    c.setFillColor(colors.lightgrey)
    c.rect(40, y - 4, width - 80, 18, fill=1, stroke=0)
    c.setFillColor(colors.black)
    c.setFont("Helvetica-Bold", 10)
    x_positions = [50, 250, 340, 430, 520]
    for col, text in zip(x_positions, table_headers):
        c.drawString(col, y, text)

    subtotal_sin_iva = pedido.total - pedido.iva
    c.setFont("Helvetica", 10)
    y -= 22
    if quote:
        for pieza in quote.piezas:
            if y < 120:
                c.showPage()
                y = height - 80
                c.setFont("Helvetica", 10)
            subtotal = pieza.total_total - pieza.iva_total
            c.drawString(50, y, pieza.pieza.nombre)
            c.drawRightString(310, y, str(pieza.pieza.cantidad))
            c.drawRightString(420, y, f"${subtotal:,.2f}")
            c.drawRightString(500, y, f"${pieza.iva_total:,.2f}")
            c.drawRightString(560, y, f"${pieza.total_total:,.2f}")
            y -= 16
    else:
        c.drawString(50, y, pedido.proyecto)
        c.drawRightString(310, y, "-")
        c.drawRightString(420, y, f"${subtotal_sin_iva:,.2f}")
        c.drawRightString(500, y, f"${pedido.iva:,.2f}")
        c.drawRightString(560, y, f"${pedido.total:,.2f}")
        y -= 16

    y -= 16
    c.setFont("Helvetica-Bold", 11)
    c.drawRightString(480, y, "Subtotal sin IVA:")
    c.drawRightString(560, y, f"${subtotal_sin_iva:,.2f}")
    y -= 14
    c.drawRightString(480, y, "IVA:")
    c.drawRightString(560, y, f"${pedido.iva:,.2f}")
    y -= 14
    c.drawRightString(480, y, "Retención:")
    c.drawRightString(560, y, f"${pedido.retencion:,.2f}")
    y -= 16
    c.setFont("Helvetica-Bold", 12)
    c.drawRightString(480, y, "Total a facturar:")
    c.drawRightString(560, y, f"${pedido.total:,.2f}")
    y -= 16
    c.drawRightString(480, y, "Total neto (menos retención):")
    c.drawRightString(560, y, f"${pedido.total - pedido.retencion:,.2f}")

    y -= 40
    c.setFont("Helvetica", 9)
    c.drawString(40, y, "Se solicita emitir la factura correspondiente al pedido descrito.")

    c.showPage()
    c.save()
    return path


__all__ = ["export_invoice_request_pdf"]
