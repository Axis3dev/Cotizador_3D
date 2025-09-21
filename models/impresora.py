"""Impresora domain model."""

from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any, Dict, Literal

PrinterType = Literal["filamento", "resina"]


@dataclass(slots=True)
class Impresora:
    """Represents a printer entry stored in configuration."""

    nombre: str
    tipo: PrinterType
    costo_equipo: float
    vida_util_horas: float
    potencia_w: float

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Impresora":
        return cls(
            nombre=str(data["nombre"]),
            tipo=str(data.get("tipo", "filamento")),
            costo_equipo=float(data.get("costo_equipo", 0.0)),
            vida_util_horas=float(data.get("vida_util_horas", 0.0)),
            potencia_w=float(data.get("potencia_w", 0.0)),
        )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


__all__ = ["Impresora", "PrinterType"]
