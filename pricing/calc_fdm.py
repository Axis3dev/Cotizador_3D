"""Heuristics to estimate FDM material usage and print time."""

from __future__ import annotations

from dataclasses import dataclass

from models.geometry import MeshInfo


@dataclass(slots=True)
class FDMHeuristicSettings:
    infill_percent: float = 20.0
    shell_factor: float = 0.18
    layer_height_mm: float = 0.2
    nozzle_mm: float = 0.4
    perimeter_speed_mms: float = 150.0
    infill_speed_mms: float = 200.0
    top_bottom_speed_mms: float = 150.0
    overhead_per_layer_s: float = 2.0


def estimate_mass_and_time(mesh: MeshInfo, densidad_g_cm3: float, settings: FDMHeuristicSettings) -> tuple[float, float]:
    """Return a tuple ``(masa_g, horas)`` using quick heuristics."""

    volumen_cm3 = max(mesh.volume_cm3, 0.0)
    infill_ratio = max(settings.infill_percent, 0.0) / 100.0
    shell_factor = max(settings.shell_factor, 0.0)
    uso_cm3 = volumen_cm3 * (infill_ratio + shell_factor)
    masa_g = uso_cm3 * max(densidad_g_cm3, 0.0)

    layer_height = max(settings.layer_height_mm, 0.01)
    nozzle_mm = max(settings.nozzle_mm, 0.1)
    layers = max(mesh.height_mm / layer_height, 1.0)

    extrusion_mm3 = uso_cm3 * 1000.0
    section_mm2 = nozzle_mm * layer_height
    path_length_mm = extrusion_mm3 / section_mm2 if section_mm2 else 0.0
    avg_speed = max((settings.perimeter_speed_mms + settings.infill_speed_mms + settings.top_bottom_speed_mms) / 3.0, 1.0)
    motion_seconds = path_length_mm / avg_speed if avg_speed else 0.0
    overhead_seconds = layers * max(settings.overhead_per_layer_s, 0.0)
    horas = (motion_seconds + overhead_seconds) / 3600.0

    return masa_g, horas


__all__ = ["FDMHeuristicSettings", "estimate_mass_and_time"]
