"""CSV export for quotations."""

from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path

from models.cotizacion import Cotizacion


def export_quote_csv(quote: Cotizacion, directory: Path | None = None) -> Path:
    directory = directory or Path.cwd()
    directory.mkdir(parents=True, exist_ok=True)
    fecha = datetime.fromisoformat(quote.fecha)
    cliente_slug = quote.cliente.nombre.replace(" ", "_") or "Cliente"
    file_name = f"Cotizacion_{quote.folio}_{cliente_slug}_{fecha.strftime('%Y%m%d')}.csv"
    path = directory / file_name

    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(["Folio", quote.folio])
        writer.writerow(["Fecha", quote.fecha])
        writer.writerow(["Proyecto", quote.proyecto])
        writer.writerow(["Tipo", quote.tipo])
        writer.writerow(["Impresora", quote.impresora])
        writer.writerow(["Material", quote.material])
        writer.writerow(["Precio material kg", f"{quote.material_precio_kg:.2f}"])
        writer.writerow([])
        writer.writerow(["Cliente", quote.cliente.nombre])
        writer.writerow(["Correo", quote.cliente.correo])
        writer.writerow(["Celular", quote.cliente.celular])
        writer.writerow([])
        writer.writerow(["Pieza", "Cantidad", "Subtotal", "Total"])
        for pieza in quote.piezas:
            writer.writerow(
                [
                    pieza.pieza.nombre,
                    pieza.pieza.cantidad,
                    f"{pieza.subtotal_total:.2f}",
                    f"{pieza.total_total:.2f}",
                ]
            )
        writer.writerow([])
        writer.writerow(["Subtotal base", f"{quote.subtotal_base:.2f}"])
        writer.writerow(["Merma", f"{quote.merma:.2f}"])
        writer.writerow(["Riesgo", f"{quote.riesgo:.2f}"])
        writer.writerow(["Ganancia", f"{quote.ganancia:.2f}"])
        writer.writerow(["Subtotal post riesgo", f"{quote.subtotal_post_riesgo:.2f}"])
        writer.writerow(["Total sin IVA", f"{quote.total_sin_iva:.2f}"])
        writer.writerow(["IVA", f"{quote.iva:.2f}"])
        writer.writerow(["Total", f"{quote.total:.2f}"])
    return path


__all__ = ["export_quote_csv"]
