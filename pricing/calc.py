"""Core cost calculation utilities."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict


@dataclass(slots=True)
class MaterialInfo:
    """Data required to estimate material cost."""

    nombre: str
    densidad_g_cm3: float
    precio_kg: float


@dataclass(slots=True)
class PrinterContext:
    """Subset of printer data required for the cost model."""

    nombre: str
    tipo: str
    costo_equipo: float
    vida_util_horas: float
    potencia_w: float


@dataclass(slots=True)
class FinancialContext:
    """Global economic parameters configurable by the user."""

    precio_kwh: float
    costo_hora_hombre: float
    merma: float
    riesgo: float
    ganancia: float
    iva: float


@dataclass(slots=True)
class CostInputs:
    """Project-level values entered for each quotation."""

    masa_g: float
    horas_impresion: float
    minutos_mano_obra: float
    horas_supervision: float
    costo_stl: float
    extras: float


@dataclass(slots=True)
class CostBreakdown:
    """Detailed breakdown of every cost component."""

    material: float
    energia: float
    depreciacion: float
    mano_obra: float
    costo_stl: float
    extras: float
    subtotal_base: float
    merma: float
    subtotal_post_merma: float
    riesgo: float
    subtotal_post_riesgo: float
    ganancia: float
    total_sin_iva: float
    iva: float
    total: float

    def to_dict(self) -> Dict[str, float]:
        return {
            "material": self.material,
            "energia": self.energia,
            "depreciacion": self.depreciacion,
            "mano_obra": self.mano_obra,
            "costo_stl": self.costo_stl,
            "extras": self.extras,
            "subtotal_base": self.subtotal_base,
            "merma": self.merma,
            "subtotal_post_merma": self.subtotal_post_merma,
            "riesgo": self.riesgo,
            "subtotal_post_riesgo": self.subtotal_post_riesgo,
            "ganancia": self.ganancia,
            "total_sin_iva": self.total_sin_iva,
            "iva": self.iva,
            "total": self.total,
        }


def grams_from_volume(volume_mm3: float, densidad_g_cm3: float) -> float:
    """Convert ``volume_mm3`` to grams given the material density."""

    if volume_mm3 <= 0 or densidad_g_cm3 <= 0:
        return 0.0
    volumen_cm3 = volume_mm3 / 1000.0
    return volumen_cm3 * densidad_g_cm3


def calculate_costs(
    material: MaterialInfo,
    printer: PrinterContext,
    financial: FinancialContext,
    inputs: CostInputs,
) -> CostBreakdown:
    """Compute the full cost breakdown for the provided inputs."""

    masa_kg = max(inputs.masa_g, 0.0) / 1000.0
    material_cost = masa_kg * max(material.precio_kg, 0.0)

    horas_impresion = max(inputs.horas_impresion, 0.0)
    energia_cost = (max(printer.potencia_w, 0.0) * horas_impresion / 1000.0) * max(
        financial.precio_kwh, 0.0
    )

    if printer.vida_util_horas > 0:
        depreciacion_hora = max(printer.costo_equipo, 0.0) / printer.vida_util_horas
    else:
        depreciacion_hora = 0.0
    depreciacion_cost = depreciacion_hora * horas_impresion

    minutos_mano_obra = max(inputs.minutos_mano_obra, 0.0)
    horas_supervision = max(inputs.horas_supervision, 0.0)
    mano_obra_cost = (
        (minutos_mano_obra / 60.0 + horas_supervision) * max(financial.costo_hora_hombre, 0.0)
    )

    costo_stl = max(inputs.costo_stl, 0.0)
    extras = max(inputs.extras, 0.0)

    subtotal_base = material_cost + energia_cost + depreciacion_cost + mano_obra_cost + costo_stl + extras

    merma_amount = subtotal_base * max(financial.merma, 0.0)
    subtotal_post_merma = subtotal_base + merma_amount

    riesgo_amount = subtotal_post_merma * max(financial.riesgo, 0.0)
    subtotal_post_riesgo = subtotal_post_merma + riesgo_amount

    ganancia_amount = subtotal_post_riesgo * max(financial.ganancia, 0.0)
    total_sin_iva = subtotal_post_riesgo + ganancia_amount

    iva_amount = total_sin_iva * max(financial.iva, 0.0)
    total = total_sin_iva + iva_amount

    return CostBreakdown(
        material=material_cost,
        energia=energia_cost,
        depreciacion=depreciacion_cost,
        mano_obra=mano_obra_cost,
        costo_stl=costo_stl,
        extras=extras,
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


__all__ = [
    "MaterialInfo",
    "PrinterContext",
    "FinancialContext",
    "CostInputs",
    "CostBreakdown",
    "grams_from_volume",
    "calculate_costs",
]
