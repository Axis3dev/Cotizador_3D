"""CSV export helpers for quotation data."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any, Dict

from models.pieza import format_hours_minutes, split_hours_minutes


def _time_parts(data: Dict[str, Any]) -> tuple[int, int, float]:
    tiempo = float(data.get("tiempo_horas") or data.get("horas_impresion") or 0.0)
    horas_raw = data.get("horas")
    minutos_raw = data.get("minutos")

    def _to_int(value: Any) -> int:
        try:
            return int(float(value))
        except (TypeError, ValueError):
            return 0

    horas = _to_int(horas_raw)
    minutos = _to_int(minutos_raw)

    if horas_raw is None and minutos_raw is None and tiempo:
        horas, minutos = split_hours_minutes(tiempo)
    else:
        minutos = max(minutos, 0)
        extra_hours, minutos = divmod(minutos, 60)
        horas = max(horas, 0) + extra_hours
        if tiempo <= 0:
            tiempo = horas + minutos / 60.0

    return horas, minutos, tiempo


def export_quote_to_csv(file_path: str | Path, data: Dict[str, Any]) -> Path:
    """Export the quotation summary to ``file_path``."""

    path = Path(file_path)
    cliente = data.get("cliente", {})
    proyecto = data.get("proyecto", {})
    costos = data.get("costos", {})
    currency = data.get("moneda", "MXN")

    horas, minutos, tiempo_decimal = _time_parts(proyecto)
    tiempo_formateado = format_hours_minutes(horas, minutos)

    rows = [
        ("Cliente", cliente.get("nombre", "")),
        ("Correo", cliente.get("correo", "")),
        ("Celular", cliente.get("celular", "")),
        ("Proyecto", proyecto.get("nombre", "")),
        ("Tipo", proyecto.get("tipo", "")),
        ("Impresora", proyecto.get("impresora", "")),
        ("Material", proyecto.get("material", "")),
        ("Masa (g)", f"{proyecto.get('masa_g', 0):.2f}"),
        ("Tiempo impresión (h:mm)", tiempo_formateado),
        ("Horas impresión", horas),
        ("Minutos impresión", minutos),
        ("Tiempo impresión (decimal)", f"{tiempo_decimal:.2f}"),
        ("Min. mano de obra", f"{proyecto.get('minutos_mano_obra', 0):.2f}"),
        ("Horas supervisión", f"{proyecto.get('horas_supervision', 0):.2f}"),
        ("Costo STL", f"{currency} ${costos.get('costo_stl', 0.0):.2f}"),
        ("Extras", f"{currency} ${costos.get('extras', 0.0):.2f}"),
        ("Material", f"{currency} ${costos.get('material', 0.0):.2f}"),
        ("Energía", f"{currency} ${costos.get('energia', 0.0):.2f}"),
        ("Depreciación", f"{currency} ${costos.get('depreciacion', 0.0):.2f}"),
        ("Mano de obra", f"{currency} ${costos.get('mano_obra', 0.0):.2f}"),
        ("Subtotal base", f"{currency} ${costos.get('subtotal_base', 0.0):.2f}"),
        ("Merma", f"{currency} ${costos.get('merma', 0.0):.2f}"),
        ("Subtotal tras merma", f"{currency} ${costos.get('subtotal_post_merma', 0.0):.2f}"),
        ("Riesgo", f"{currency} ${costos.get('riesgo', 0.0):.2f}"),
        ("Subtotal tras riesgo", f"{currency} ${costos.get('subtotal_post_riesgo', 0.0):.2f}"),
        ("Ganancia", f"{currency} ${costos.get('ganancia', 0.0):.2f}"),
        ("Total sin IVA", f"{currency} ${costos.get('total_sin_iva', 0.0):.2f}"),
        ("IVA", f"{currency} ${costos.get('iva', 0.0):.2f}"),
        ("Total", f"{currency} ${costos.get('total', 0.0):.2f}"),
        ("Notas", data.get("notas", "")),
    ]

    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(["Campo", "Valor"])
        writer.writerows(rows)
    return path


__all__ = ["export_quote_to_csv"]
