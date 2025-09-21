"""Resin (SLA/MSLA) printing cost estimations."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict

from models.geometry import MeshInfo
from pricing.common import (
    CostSettings,
    FinanceSettings,
    build_cost_summary,
    compute_depreciation_cost,
    compute_electricity_cost,
    compute_labor_cost,
    format_hours_minutes,
)


@dataclass
class ResinParameters:
    """Parameters describing a resin print profile."""

    material_name: str
    density_g_cm3: float
    price_per_liter: float
    price_per_kg: float
    layer_height_mm: float
    exposure_time_s: float
    lift_time_s: float
    base_layers: int
    base_exposure_time_s: float
    base_lift_time_s: float
    hollow_percentage: float
    wall_thickness_mm: float


@dataclass
class ResinEstimate:
    """Result of a resin cost estimate."""

    volume_used_cm3: float
    mass_g: float
    material_cost: float
    print_time_hours: float
    print_time_text: str
    layers: int
    cost_breakdown: Dict[str, float]


RESIN_SAFETY_FACTOR = 1.02


def estimate_resin_costs(
    mesh: MeshInfo, params: ResinParameters, costs: CostSettings, finance: FinanceSettings
) -> ResinEstimate:
    """Estimate costs for a resin print job."""

    layer_height = max(params.layer_height_mm, 0.01)
    layers = max(int(math.ceil(mesh.height_mm / layer_height)), 1)
    base_layers = min(params.base_layers, layers)
    normal_layers = max(layers - base_layers, 0)

    normal_time_s = normal_layers * (params.exposure_time_s + params.lift_time_s)
    base_time_s = base_layers * (params.base_exposure_time_s + params.base_lift_time_s)
    total_time_hours = (normal_time_s + base_time_s) / 3600.0

    hollow_ratio = max(0.0, min(params.hollow_percentage, 100.0)) / 100.0
    hollow_volume_mm3 = mesh.volume_mm3 * hollow_ratio
    wall_volume_mm3 = mesh.surface_area_mm2 * params.wall_thickness_mm
    effective_volume_mm3 = max(mesh.volume_mm3 - hollow_volume_mm3 + wall_volume_mm3, 0.0)
    effective_volume_cm3 = (effective_volume_mm3 / 1000.0) * RESIN_SAFETY_FACTOR

    mass_g = effective_volume_cm3 * params.density_g_cm3

    if params.price_per_liter > 0:
        material_cost = (effective_volume_cm3 / 1000.0) * params.price_per_liter
    elif params.price_per_kg > 0:
        material_cost = (mass_g / 1000.0) * params.price_per_kg
    else:
        material_cost = 0.0

    electricity_cost = compute_electricity_cost(costs.printer_power_w, total_time_hours, costs.electricity_mxn_per_kwh)
    depreciation_cost = compute_depreciation_cost(
        costs.printer_cost_mxn, costs.printer_life_hours, costs.maintenance_per_hour, total_time_hours
    )
    labor_cost = compute_labor_cost(costs.labor_rate_mxn_per_hour, costs.prep_time_minutes, total_time_hours)

    cost_breakdown = build_cost_summary(
        material_cost=material_cost,
        electricity_cost=electricity_cost,
        depreciation_cost=depreciation_cost,
        labor_cost=labor_cost,
        finance=finance,
    )

    return ResinEstimate(
        volume_used_cm3=effective_volume_cm3,
        mass_g=mass_g,
        material_cost=material_cost,
        print_time_hours=total_time_hours,
        print_time_text=format_hours_minutes(total_time_hours),
        layers=layers,
        cost_breakdown=cost_breakdown,
    )


__all__ = ["ResinParameters", "ResinEstimate", "estimate_resin_costs"]
