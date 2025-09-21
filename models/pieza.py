"""Piece model for multi-part quotations."""

from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any, Dict, Optional


@dataclass(slots=True)
class Pieza:
    """Represents a single item within a quotation."""

    nombre: str
    cantidad: int
    masa_g: float
    horas_impresion: float
    costo_stl: float
    extras: float
    prep_min: float
    supervision_h: float
    stl_path: Optional[str] = None
    volumen_mm3: float = 0.0
    notas: str | None = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Pieza":
        return cls(
            nombre=str(data.get("nombre", "")),
            cantidad=int(data.get("cantidad", 1)),
            masa_g=float(data.get("masa_g", 0.0)),
            horas_impresion=float(data.get("horas_impresion", 0.0)),
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
        return payload


__all__ = ["Pieza"]
