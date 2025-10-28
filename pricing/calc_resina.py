"""Heuristics for resin printing."""

from __future__ import annotations

from dataclasses import dataclass

from models.geometry import MeshInfo


@dataclass(slots=True)
class ResinHeuristicSettings:
    layer_height_mm: float = 0.05
    normal_exposure_s: float = 2.5
    lift_s: float = 5.0
    base_layers: int = 6
    base_exposure_s: float = 35.0
    base_lift_s: float = 8.0
    hollow_percent: float = 0.0
    wall_thickness_mm: float = 2.0


def estimate_mass_and_time(mesh: MeshInfo, densidad_g_cm3: float, settings: ResinHeuristicSettings) -> tuple[float, float]:
    """Return ``(masa_g, horas)`` for resin printers."""

    layer_height = max(settings.layer_height_mm, 0.01)
    layers = max(int(mesh.height_mm / layer_height), 1)

    base_layers = min(settings.base_layers, layers)
    normal_layers = max(layers - base_layers, 0)

    normal_time = normal_layers * (max(settings.normal_exposure_s, 0.0) + max(settings.lift_s, 0.0))
    base_time = base_layers * (max(settings.base_exposure_s, 0.0) + max(settings.base_lift_s, settings.lift_s))
    horas = (normal_time + base_time) / 3600.0

    volumen_cm3 = max(mesh.volume_cm3, 0.0)
    hollow_ratio = max(min(settings.hollow_percent / 100.0, 0.95), 0.0)
    hollowed_volume = volumen_cm3 * (1.0 - hollow_ratio)
    shell_volume = volumen_cm3 * hollow_ratio * min(settings.wall_thickness_mm / 10.0, 1.0)
    uso_cm3 = hollowed_volume + shell_volume
    masa_g = uso_cm3 * max(densidad_g_cm3, 0.0)

    return masa_g, horas


__all__ = ["ResinHeuristicSettings", "estimate_mass_and_time"]
