"""FDM pricing heuristics for estimating material usage, time and costs."""

from __future__ import annotations

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
class FDMParameters:
    """Parameters describing an FDM print job."""

    material_name: str
    density_g_cm3: float
    price_per_kg: float
    infill_percentage: float
    layer_height_mm: float
    perimeters: int
    nozzle_diameter_mm: float
    line_width_mm: float
    shell_factor: float
    top_bottom_factor: float
    overhead_per_layer_s: float
    perimeter_speed_mm_s: float
    infill_speed_mm_s: float
    top_bottom_speed_mm_s: float


@dataclass
class FDMEstimate:
    """Result of an FDM cost estimate."""

    extruded_volume_cm3: float
    mass_g: float
    material_cost: float
    print_time_hours: float
    print_time_text: str
    total_length_mm: float
    cost_breakdown: Dict[str, float]


EXTRUSION_SAFETY_FACTOR = 1.03  # compensate for slicer over-extrusion tweaks


def _volume_to_length(volume_mm3: float, line_width: float, layer_height: float) -> float:
    """Approximate filament path length for a given extruded volume."""

    extrusion_area = max(line_width * layer_height, 1e-6)
    return volume_mm3 / extrusion_area


def estimate_fdm_costs(
    mesh: MeshInfo, params: FDMParameters, costs: CostSettings, finance: FinanceSettings
) -> FDMEstimate:
    """Estimate the costs to print ``mesh`` with FDM technology."""

    model_volume_cm3 = mesh.volume_cm3
    model_volume_mm3 = mesh.volume_mm3

    shell_volume_mm3 = model_volume_mm3 * params.shell_factor
    top_bottom_volume_mm3 = model_volume_mm3 * params.top_bottom_factor
    infill_volume_mm3 = model_volume_mm3 * (params.infill_percentage / 100.0)

    total_extruded_volume_mm3 = (
        shell_volume_mm3 + top_bottom_volume_mm3 + infill_volume_mm3
    ) * EXTRUSION_SAFETY_FACTOR
    total_extruded_volume_cm3 = total_extruded_volume_mm3 / 1000.0

    mass_g = total_extruded_volume_cm3 * params.density_g_cm3
    material_cost = (mass_g / 1000.0) * params.price_per_kg

    # Time estimation
    perimeter_length_mm = _volume_to_length(shell_volume_mm3, params.line_width_mm, params.layer_height_mm)
    top_bottom_length_mm = _volume_to_length(
        top_bottom_volume_mm3, params.line_width_mm, params.layer_height_mm
    )
    infill_length_mm = _volume_to_length(infill_volume_mm3, params.line_width_mm, params.layer_height_mm)

    perimeter_time_s = perimeter_length_mm / max(params.perimeter_speed_mm_s, 1e-3)
    top_bottom_time_s = top_bottom_length_mm / max(params.top_bottom_speed_mm_s, 1e-3)
    infill_time_s = infill_length_mm / max(params.infill_speed_mm_s, 1e-3)

    layer_count = max(mesh.height_mm / max(params.layer_height_mm, 1e-6), 1.0)
    overhead_time_s = layer_count * params.overhead_per_layer_s

    total_time_hours = (perimeter_time_s + top_bottom_time_s + infill_time_s + overhead_time_s) / 3600.0
    total_length_mm = perimeter_length_mm + top_bottom_length_mm + infill_length_mm

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

    return FDMEstimate(
        extruded_volume_cm3=total_extruded_volume_cm3,
        mass_g=mass_g,
        material_cost=material_cost,
        print_time_hours=total_time_hours,
        print_time_text=format_hours_minutes(total_time_hours),
        total_length_mm=total_length_mm,
        cost_breakdown=cost_breakdown,
    )


__all__ = ["FDMParameters", "FDMEstimate", "estimate_fdm_costs"]
