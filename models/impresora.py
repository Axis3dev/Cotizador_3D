"""Impresora domain model."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict


class PrinterType(Enum):
    """Supported printer technologies."""

    FILAMENTO = "filamento"
    RESINA = "resina"

    @classmethod
    def from_value(cls, value: Any) -> "PrinterType":
        """Return a valid printer type for the provided value."""

        if isinstance(value, cls):
            return value
        try:
            return cls(str(value))
        except ValueError:
            return cls.FILAMENTO


@dataclass(slots=True)
class Impresora:
    """Represents a printer entry stored in configuration."""

    nombre: str
    tipo: PrinterType
    costo_equipo: float
    vida_util_horas: float
    potencia_w: float

    def __post_init__(self) -> None:  # pragma: no cover - simple normalization
        self.tipo = PrinterType.from_value(self.tipo)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Impresora":
        return cls(
            nombre=str(data["nombre"]),
            tipo=PrinterType.from_value(data.get("tipo", PrinterType.FILAMENTO.value)),
            costo_equipo=float(data.get("costo_equipo", 0.0)),
            vida_util_horas=float(data.get("vida_util_horas", 0.0)),
            potencia_w=float(data.get("potencia_w", 0.0)),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "nombre": self.nombre,
            "tipo": self.tipo.value,
            "costo_equipo": self.costo_equipo,
            "vida_util_horas": self.vida_util_horas,
            "potencia_w": self.potencia_w,
        }


__all__ = ["Impresora", "PrinterType"]
