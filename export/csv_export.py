"""CSV export helpers."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any, Dict


def export_quote_to_csv(file_path: str, data: Dict[str, Any]) -> Path:
    """Export the quotation summary to a CSV file."""

    path = Path(file_path)
    rows = [
        ("Cliente", data.get("client_name", "")),
        ("Notas", data.get("notes", "")),
        ("Modo", data.get("mode", "")),
        ("Archivo", data.get("file", {}).get("name", "")),
        ("Volumen cm3", f"{data.get('file', {}).get('volume_cm3', 0):.2f}"),
        ("Tiempo", data.get("print_time", "")),
        ("Material", f"${data.get('costs', {}).get('material', 0):.2f}"),
        ("Electricidad", f"${data.get('costs', {}).get('electricity', 0):.2f}"),
        ("Depreciación", f"${data.get('costs', {}).get('depreciation', 0):.2f}"),
        ("Mano de obra", f"${data.get('costs', {}).get('labor', 0):.2f}"),
        ("Subtotal", f"${data.get('costs', {}).get('subtotal', 0):.2f}"),
        ("Margen", f"${data.get('costs', {}).get('margin_amount', 0):.2f}"),
        ("IVA", f"${data.get('costs', {}).get('tax_amount', 0):.2f}"),
        ("Total", f"${data.get('costs', {}).get('total', 0):.2f}"),
    ]

    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(["Campo", "Valor"])
        writer.writerows(rows)

    return path


__all__ = ["export_quote_to_csv"]
