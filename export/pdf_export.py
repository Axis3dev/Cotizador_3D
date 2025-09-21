"""PDF export utilities for the cotización."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, Tuple

from reportlab.lib.pagesizes import letter
from reportlab.lib.units import mm
from reportlab.pdfgen.canvas import Canvas


def _draw_lines(canvas: Canvas, lines: Iterable[str], x: float, y: float, height: float) -> float:
    """Draw ``lines`` of text starting at ``x``, ``y`` and return the new ``y``."""

    current_y = y
    for line in lines:
        canvas.drawString(x, current_y, line)
        current_y -= height
    return current_y


def _fmt_currency(value: float, currency: str) -> str:
    return f"{currency} ${value:,.2f}"


def export_quote_to_pdf(file_path: str | Path, data: Dict[str, Any]) -> Path:
    """Generate a PDF summarising the quotation."""

    path = Path(file_path)
    pdf = Canvas(str(path), pagesize=letter)
    _, height = letter
    margin = 18 * mm

    currency = data.get("moneda", "MXN")
    fecha: datetime = data.get("fecha") or datetime.now()
    cliente = data.get("cliente", {})
    proyecto = data.get("proyecto", {})
    costos = data.get("costos", {})
    notas = data.get("notas", "")

    pdf.setTitle("Cotización de impresión 3D")
    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawString(margin, height - margin, "Cotización de impresión 3D")

    pdf.setFont("Helvetica", 10)
    pdf.drawString(margin, height - margin - 16, f"Fecha: {fecha:%d/%m/%Y %H:%M}")

    y = height - margin - 40
    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(margin, y, "Datos del cliente")
    y -= 14
    pdf.setFont("Helvetica", 10)
    y = _draw_lines(
        pdf,
        [
            f"Nombre: {cliente.get('nombre', 'N/D')}",
            f"Correo: {cliente.get('correo', 'N/D')}",
            f"Celular: {cliente.get('celular', 'N/D')}",
        ],
        margin,
        y,
        12,
    )

    y -= 10
    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(margin, y, "Proyecto")
    y -= 14
    pdf.setFont("Helvetica", 10)
    proyecto_lines = [
        f"Nombre: {proyecto.get('nombre', 'N/D')}",
        f"Tipo: {proyecto.get('tipo', 'N/D')} - Impresora: {proyecto.get('impresora', 'N/D')}",
        f"Material: {proyecto.get('material', 'N/D')}",
        f"Masa estimada: {proyecto.get('masa_g', 0):.2f} g",
        f"Tiempo impresión: {proyecto.get('horas_impresion', 0):.2f} h",
    ]
    y = _draw_lines(pdf, proyecto_lines, margin, y, 12)

    y -= 10
    stl_info = data.get("stl")
    if stl_info:
        pdf.setFont("Helvetica-Bold", 12)
        pdf.drawString(margin, y, "Datos STL")
        y -= 14
        pdf.setFont("Helvetica", 10)
        bbox: Tuple[float, float, float] = tuple(stl_info.get("bbox", (0.0, 0.0, 0.0)))  # type: ignore[arg-type]
        stl_lines = [
            f"Archivo: {stl_info.get('archivo', 'N/D')}",
            f"Volumen: {stl_info.get('volumen_cm3', 0):.2f} cm³ ({stl_info.get('volumen_mm3', 0):.0f} mm³)",
            f"Dimensiones: {bbox[0]:.1f} x {bbox[1]:.1f} x {bbox[2]:.1f} mm",
            "Malla cerrada" if stl_info.get("watertight", False) else "Malla abierta",
        ]
        y = _draw_lines(pdf, stl_lines, margin, y, 12)
        y -= 10

    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(margin, y, "Desglose de costos")
    y -= 16

    pdf.setFont("Helvetica", 10)
    cost_rows = [
        ("Material", costos.get("material", 0.0)),
        ("Energía eléctrica", costos.get("energia", 0.0)),
        ("Depreciación", costos.get("depreciacion", 0.0)),
        ("Mano de obra", costos.get("mano_obra", 0.0)),
        ("Costo STL", costos.get("costo_stl", 0.0)),
        ("Extras", costos.get("extras", 0.0)),
        ("Subtotal base", costos.get("subtotal_base", 0.0)),
        ("Merma", costos.get("merma", 0.0)),
        ("Subtotal tras merma", costos.get("subtotal_post_merma", 0.0)),
        ("Riesgo", costos.get("riesgo", 0.0)),
        ("Subtotal tras riesgo", costos.get("subtotal_post_riesgo", 0.0)),
        ("Ganancia", costos.get("ganancia", 0.0)),
        ("Total sin IVA", costos.get("total_sin_iva", 0.0)),
        ("IVA", costos.get("iva", 0.0)),
    ]

    x_concept = margin
    x_amount = margin + 200
    line_height = 12
    current_y = y
    for concept, value in cost_rows:
        pdf.drawString(x_concept, current_y, concept)
        pdf.drawRightString(x_amount + 120, current_y, _fmt_currency(value, currency))
        current_y -= line_height

    total = costos.get("total", costos.get("total_sin_iva", 0.0) + costos.get("iva", 0.0))
    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(x_concept, current_y - 4, "Total")
    pdf.drawRightString(x_amount + 120, current_y - 4, _fmt_currency(total, currency))
    current_y -= 24

    if notas:
        pdf.setFont("Helvetica-Bold", 12)
        pdf.drawString(margin, current_y, "Notas")
        current_y -= 14
        pdf.setFont("Helvetica", 10)
        for paragraph in notas.splitlines():
            current_y = _draw_lines(pdf, [paragraph], margin, current_y, 12)

    pdf.showPage()
    pdf.save()
    return path


__all__ = ["export_quote_to_pdf"]
