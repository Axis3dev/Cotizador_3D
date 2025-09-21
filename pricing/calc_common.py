"""Shared cost calculation utilities."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List

from models.cotizacion import PiezaCostos
from models.impresora import Impresora
from models.material import Material
from models.pieza import Pieza


@dataclass(slots=True)
class FinancialSettings:
    """Economic parameters applied over every piece."""

    precio_kwh: float
    costo_hora: float
    merma: float
    riesgo: float
    ganancia: float
    iva: float


@dataclass(slots=True)
class PieceBaseCost:
    """Base costs for a single piece before margins."""

    pieza: Pieza
    material_unit: float
    energia_unit: float
    depreciacion_unit: float
    mano_obra_unit: float
    costo_stl_unit: float
    extras_unit: float
    subtotal_unit: float
    subtotal_total: float


@dataclass(slots=True)
class QuoteBreakdown:
    """Aggregated cost totals for a quotation."""

    piezas: List[PiezaCostos]
    subtotal_base: float
    merma: float
    subtotal_post_merma: float
    riesgo: float
    subtotal_post_riesgo: float
    ganancia: float
    total_sin_iva: float
    iva: float
    total: float


def compute_piece_base(
    pieza: Pieza,
    material: Material,
    impresora: Impresora,
    financial: FinancialSettings,
    precio_material_override: float | None = None,
) -> PieceBaseCost:
    """Compute base costs for a single piece."""

    cantidad = max(pieza.cantidad, 1)
    masa_kg = max(pieza.masa_g, 0.0) / 1000.0
    precio_material = precio_material_override if precio_material_override is not None else material.precio_kg
    material_unit = masa_kg * max(precio_material, 0.0)

    horas = max(pieza.horas_impresion, 0.0)
    energia_unit = (max(impresora.potencia_w, 0.0) * horas / 1000.0) * max(
        financial.precio_kwh, 0.0
    )

    if impresora.vida_util_horas > 0:
        depreciacion_hora = max(impresora.costo_equipo, 0.0) / impresora.vida_util_horas
    else:
        depreciacion_hora = 0.0
    depreciacion_unit = depreciacion_hora * horas

    mano_obra_unit = (
        max(pieza.prep_min, 0.0) / 60.0 + max(pieza.supervision_h, 0.0)
    ) * max(financial.costo_hora, 0.0)

    costo_stl_unit = max(pieza.costo_stl, 0.0)
    extras_unit = max(pieza.extras, 0.0)

    subtotal_unit = (
        material_unit
        + energia_unit
        + depreciacion_unit
        + mano_obra_unit
        + costo_stl_unit
        + extras_unit
    )
    subtotal_total = subtotal_unit * cantidad

    return PieceBaseCost(
        pieza=pieza,
        material_unit=material_unit,
        energia_unit=energia_unit,
        depreciacion_unit=depreciacion_unit,
        mano_obra_unit=mano_obra_unit,
        costo_stl_unit=costo_stl_unit,
        extras_unit=extras_unit,
        subtotal_unit=subtotal_unit,
        subtotal_total=subtotal_total,
    )


def build_quote_breakdown(
    bases: List[PieceBaseCost], financial: FinancialSettings
) -> QuoteBreakdown:
    """Aggregate totals applying merma, riesgo, ganancia e IVA."""

    subtotal_base = sum(item.subtotal_total for item in bases)
    merma_amount = subtotal_base * max(financial.merma, 0.0)
    subtotal_post_merma = subtotal_base + merma_amount
    riesgo_amount = subtotal_post_merma * max(financial.riesgo, 0.0)
    subtotal_post_riesgo = subtotal_post_merma + riesgo_amount
    ganancia_amount = subtotal_post_riesgo * max(financial.ganancia, 0.0)
    total_sin_iva = subtotal_post_riesgo + ganancia_amount
    iva_amount = total_sin_iva * max(financial.iva, 0.0)
    total = total_sin_iva + iva_amount

    piezas: List[PiezaCostos] = []
    if subtotal_base <= 0:
        for base in bases:
            piezas.append(
                PiezaCostos(
                    pieza=base.pieza,
                    material_unit=base.material_unit,
                    energia_unit=base.energia_unit,
                    depreciacion_unit=base.depreciacion_unit,
                    mano_obra_unit=base.mano_obra_unit,
                    costo_stl_unit=base.costo_stl_unit,
                    extras_unit=base.extras_unit,
                    subtotal_unit=base.subtotal_unit,
                    subtotal_total=base.subtotal_total,
                    merma_total=0.0,
                    riesgo_total=0.0,
                    ganancia_total=0.0,
                    iva_total=0.0,
                    total_unit=base.subtotal_unit,
                    total_total=base.subtotal_total,
                )
            )
        return QuoteBreakdown(
            piezas=piezas,
            subtotal_base=subtotal_base,
            merma=merma_amount,
            subtotal_post_merma=subtotal_post_merma,
            riesgo=riesgo_amount,
            subtotal_post_riesgo=subtotal_post_riesgo,
            ganancia=ganancia_amount,
            total_sin_iva=total_sin_iva,
            iva=iva_amount,
            total=total,
        )

    for base in bases:
        share = base.subtotal_total / subtotal_base if subtotal_base else 0.0
        merma_total = merma_amount * share
        riesgo_total = riesgo_amount * share
        ganancia_total = ganancia_amount * share
        iva_total = iva_amount * share
        cantidad = max(base.pieza.cantidad, 1)
        total_total = base.subtotal_total + merma_total + riesgo_total + ganancia_total + iva_total
        total_unit = total_total / cantidad
        piezas.append(
            PiezaCostos(
                pieza=base.pieza,
                material_unit=base.material_unit,
                energia_unit=base.energia_unit,
                depreciacion_unit=base.depreciacion_unit,
                mano_obra_unit=base.mano_obra_unit,
                costo_stl_unit=base.costo_stl_unit,
                extras_unit=base.extras_unit,
                subtotal_unit=base.subtotal_unit,
                subtotal_total=base.subtotal_total,
                merma_total=merma_total,
                riesgo_total=riesgo_total,
                ganancia_total=ganancia_total,
                iva_total=iva_total,
                total_unit=total_unit,
                total_total=total_total,
            )
        )

    return QuoteBreakdown(
        piezas=piezas,
        subtotal_base=subtotal_base,
        merma=merma_amount,
        subtotal_post_merma=subtotal_post_merma,
        riesgo=riesgo_amount,
        subtotal_post_riesgo=subtotal_post_riesgo,
        ganancia=ganancia_amount,
        total_sin_iva=total_sin_iva,
        iva=iva_amount,
        total=total,
    )


def grams_from_volume(volume_mm3: float, densidad_g_cm3: float) -> float:
    """Utility conversion shared with the geometry helpers."""

    if volume_mm3 <= 0 or densidad_g_cm3 <= 0:
        return 0.0
    return (volume_mm3 / 1000.0) * densidad_g_cm3


__all__ = [
    "FinancialSettings",
    "PieceBaseCost",
    "QuoteBreakdown",
    "compute_piece_base",
    "build_quote_breakdown",
    "grams_from_volume",
]
