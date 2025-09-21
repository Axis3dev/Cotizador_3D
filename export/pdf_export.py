"""PDF export utilities for quotation summaries."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable

from reportlab.lib.pagesizes import letter
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas


def _draw_text_block(pdf: canvas.Canvas, lines: Iterable[str], x: float, y: float, line_height: float) -> float:
    """Draw ``lines`` starting at ``x``, ``y`` returning the final y position."""

    current_y = y
    for line in lines:
        pdf.drawString(x, current_y, line)
        current_y -= line_height
    return current_y


def export_quote_to_pdf(file_path: str, data: Dict[str, Any]) -> Path:
    """Create a PDF file containing the quotation summary."""

    path = Path(file_path)
    pdf = canvas.Canvas(str(path), pagesize=letter)
    _, height = letter
    margin = 20 * mm

    pdf.setTitle("Cotización de impresión 3D")

    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawString(margin, height - margin, "Cotización de impresión 3D")
    pdf.setFont("Helvetica", 10)
    pdf.drawString(margin, height - margin - 15, f"Fecha: {datetime.now():%d/%m/%Y %H:%M}")

    y = height - margin - 40
    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(margin, y, "Datos del cliente")
    pdf.setFont("Helvetica", 10)
    y -= 14
    client_lines = [
        f"Cliente: {data.get('client_name', 'N/A')}",
        f"Notas: {data.get('notes', '')}",
    ]
    y = _draw_text_block(pdf, client_lines, margin, y, 12)

    y -= 10
    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(margin, y, "Archivo STL")
    y -= 14
    pdf.setFont("Helvetica", 10)
    file_info = data.get("file", {})
    file_lines = [
        f"Nombre: {file_info.get('name', 'N/A')}",
        f"Volumen: {file_info.get('volume_cm3', 0):.2f} cm³ ({file_info.get('volume_mm3', 0):.0f} mm³)",
        (
            "Dimensiones: "
            f"X={file_info.get('bbox', [0, 0, 0])[0]:.1f} mm, "
            f"Y={file_info.get('bbox', [0, 0, 0])[1]:.1f} mm, "
            f"Z={file_info.get('bbox', [0, 0, 0])[2]:.1f} mm"
        ),
        f"Modo: {data.get('mode', 'N/A')}",
    ]
    y = _draw_text_block(pdf, file_lines, margin, y, 12)

    y -= 10
    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(margin, y, "Parámetros")
    y -= 14
    pdf.setFont("Helvetica", 10)
    parameters = data.get("parameters", {})
    parameter_lines = [f"{key}: {value}" for key, value in parameters.items()]
    y = _draw_text_block(pdf, parameter_lines, margin, y, 12)

    y -= 10
    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(margin, y, "Costos")
    y -= 14
    pdf.setFont("Helvetica", 10)
    costs = data.get("costs", {})
    cost_lines = [
        f"Material: ${costs.get('material', 0):.2f}",
        f"Electricidad: ${costs.get('electricity', 0):.2f}",
        f"Depreciación/Mantenimiento: ${costs.get('depreciation', 0):.2f}",
        f"Mano de obra: ${costs.get('labor', 0):.2f}",
        f"Subtotal: ${costs.get('subtotal', 0):.2f}",
        f"Margen: ${costs.get('margin_amount', 0):.2f}",
        f"IVA: ${costs.get('tax_amount', 0):.2f}",
        f"Total sugerido: ${costs.get('total', 0):.2f}",
    ]
    y = _draw_text_block(pdf, cost_lines, margin, y, 12)

    y -= 10
    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(margin, y, "Tiempo estimado")
    y -= 14
    pdf.setFont("Helvetica", 10)
    pdf.drawString(margin, y, f"Duración aproximada: {data.get('print_time', 'N/A')}")

    pdf.showPage()
    pdf.save()
    return path


__all__ = ["export_quote_to_pdf"]
