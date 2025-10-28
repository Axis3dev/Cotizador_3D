"""Material domain model."""

from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any, Dict


@dataclass(slots=True)
class Material:
    """Represents a printable material with pricing and density information."""

    nombre: str
    densidad_g_cm3: float
    precio_kg: float

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Material":
        return cls(
            nombre=str(data["nombre"]),
            densidad_g_cm3=float(data.get("densidad_g_cm3", 0.0)),
            precio_kg=float(data.get("precio_kg", 0.0)),
        )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


__all__ = ["Material"]
