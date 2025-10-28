"""Piece model for multi-part quotations."""

from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any, Dict, Optional, Tuple


def combine_hours_minutes(hours: int, minutes: int) -> float:
    """Return fractional hours from ``hours`` and ``minutes`` ensuring non-negative."""

    hours = max(int(hours), 0)
    minutes = max(int(minutes), 0)
    extra_hours, minutes = divmod(minutes, 60)
    hours += extra_hours
    return hours + minutes / 60.0


def split_hours_minutes(total_hours: float) -> Tuple[int, int]:
    """Split fractional ``total_hours`` into hours and minutes."""

    if total_hours <= 0:
        return 0, 0
    total_minutes = int(round(total_hours * 60))
    if total_minutes < 0:
        total_minutes = 0
    hours, minutes = divmod(total_minutes, 60)
    return hours, minutes


def format_hours_minutes(hours: int, minutes: int) -> str:
    """Format ``hours`` and ``minutes`` using the ``H:MM`` pattern."""

    hours = max(int(hours), 0)
    minutes = max(int(minutes), 0)
    _, minutes = divmod(minutes, 60)
    return f"{hours}:{minutes:02d}"


def _normalise_time_fields(hours: int, minutes: int, tiempo_horas: float) -> Tuple[int, int, float]:
    """Return coherent (hours, minutes, fractional hours) trio."""

    if tiempo_horas > 0:
        hours, minutes = split_hours_minutes(tiempo_horas)
    else:
        total_minutes = max(int(hours), 0) * 60 + max(int(minutes), 0)
        hours, minutes = divmod(total_minutes, 60)
    tiempo = hours + minutes / 60.0
    return hours, minutes, tiempo


@dataclass(slots=True)
class Pieza:
    """Represents a single item within a quotation."""

    nombre: str
    cantidad: int
    masa_g: float
    horas: int
    minutos: int
    tiempo_horas: float
    costo_stl: float
    extras: float
    prep_min: float
    supervision_h: float
    stl_path: Optional[str] = None
    volumen_mm3: float = 0.0
    notas: str | None = None

    def __post_init__(self) -> None:
        hours, minutes, tiempo = _normalise_time_fields(self.horas, self.minutos, self.tiempo_horas)
        self.horas = hours
        self.minutos = minutes
        self.tiempo_horas = tiempo

    @property
    def horas_impresion(self) -> float:
        """Backward compatible alias returning ``tiempo_horas``."""

        return self.tiempo_horas

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Pieza":
        horas_raw = data.get("horas")
        minutos_raw = data.get("minutos")
        tiempo_horas = float(data.get("tiempo_horas") or data.get("horas_impresion") or 0.0)

        try:
            horas = int(float(horas_raw)) if horas_raw is not None else 0
        except (TypeError, ValueError):
            horas = 0
        try:
            minutos = int(float(minutos_raw)) if minutos_raw is not None else 0
        except (TypeError, ValueError):
            minutos = 0

        if horas_raw is None and minutos_raw is None and tiempo_horas:
            horas, minutos = split_hours_minutes(tiempo_horas)

        return cls(
            nombre=str(data.get("nombre", "")),
            cantidad=int(data.get("cantidad", 1)),
            masa_g=float(data.get("masa_g", 0.0)),
            horas=horas,
            minutos=minutos,
            tiempo_horas=tiempo_horas,
            costo_stl=float(data.get("costo_stl", 0.0)),
            extras=float(data.get("extras", 0.0)),
            prep_min=float(data.get("prep_min", 0.0)),
            supervision_h=float(data.get("supervision_h", 0.0)),
            stl_path=data.get("stl_path"),
            volumen_mm3=float(data.get("volumen_mm3", 0.0)),
            notas=data.get("notas"),
        )

    def to_dict(self) -> Dict[str, Any]:
        payload = asdict(self)
        payload["horas_impresion"] = self.tiempo_horas
        return payload


__all__ = [
    "Pieza",
    "combine_hours_minutes",
    "split_hours_minutes",
    "format_hours_minutes",
]
