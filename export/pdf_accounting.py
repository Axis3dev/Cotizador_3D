"""PDF export for accounting summaries."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Dict, Iterable

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas


def export_accounting_pdf(
    rows: Iterable[Dict[str, float]],
    filters: Dict[str, str],
    identity: Dict[str, object],
    directory: Path | None = None,
    file_name: str = "reporte_contable.pdf",
) -> Path:
    directory = directory or Path.cwd()
    directory.mkdir(parents=True, exist_ok=True)
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
                c.drawImage(str(logo), 40, y - 30, width=60, preserveAspectRatio=True, mask="auto")
                logo_drawn = True
            except Exception as exc:
                logging.getLogger(__name__).warning("No se pudo dibujar el logo contable: %s", exc)
        else:
            logging.getLogger(__name__).info("Logo no encontrado en %s, se omite en PDF contable", logo)
    text_x = 120 if logo_drawn else 40
    c.setFont("Helvetica-Bold", 14)
    c.drawString(text_x, y, identity.get("nombre_comercial", "Resumen contable"))
    c.setFont("Helvetica", 10)
    y -= 16
    c.drawString(text_x, y, identity.get("direccion", ""))
    y -= 14
    c.drawString(text_x, y, identity.get("telefono", ""))

    y -= 24
    c.setFont("Helvetica-Bold", 12)
    c.drawString(40, y, "Filtros aplicados")
    c.setFont("Helvetica", 10)
    y -= 16
    for key, value in filters.items():
        c.drawString(40, y, f"{key}: {value}")
        y -= 14

    y -= 10
    c.setFillColor(colors.lightgrey)
    c.rect(40, y - 4, width - 80, 18, fill=1, stroke=0)
    c.setFillColor(colors.black)
    c.setFont("Helvetica-Bold", 10)
    c.drawString(50, y, "Periodo")
    c.drawRightString(280, y, "Ingresos")
    c.drawRightString(360, y, "Costos")
    c.drawRightString(440, y, "Gastos")
    c.drawRightString(520, y, "Ganancia")
    c.drawRightString(580, y, "IVA")

    y -= 24
    c.setFont("Helvetica", 10)
    for row in rows:
        if y < 80:
            c.showPage()
            y = height - 80
            c.setFont("Helvetica", 10)
        c.drawString(50, y, str(row.get("periodo", "")))
        c.drawRightString(280, y, f"${row.get('ingresos', 0.0):,.2f}")
        c.drawRightString(360, y, f"${row.get('costos', 0.0):,.2f}")
        c.drawRightString(440, y, f"${row.get('gastos', 0.0):,.2f}")
        c.drawRightString(520, y, f"${row.get('ganancia', 0.0):,.2f}")
        c.drawRightString(580, y, f"${row.get('iva', 0.0):,.2f}")
        y -= 16

    c.showPage()
    c.save()
    return path


__all__ = ["export_accounting_pdf"]
