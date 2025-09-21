"""Client domain model."""

from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Any, Dict, List


@dataclass(slots=True)
class Cliente:
    """Basic CRM entry."""

    id: str
    nombre: str
    correo: str
    celular: str
    fecha_alta: str
    pedidos: int = 0
    total_facturado: float = 0.0
    total_ganancia: float = 0.0
    historial: List[str] | None = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Cliente":
        return cls(
            id=str(data.get("id")),
            nombre=str(data.get("nombre", "")),
            correo=str(data.get("correo", "")),
            celular=str(data.get("celular", "")),
            fecha_alta=str(data.get("fecha_alta", datetime.utcnow().date().isoformat())),
            pedidos=int(data.get("pedidos", 0)),
            total_facturado=float(data.get("total_facturado", 0.0)),
            total_ganancia=float(data.get("total_ganancia", 0.0)),
            historial=list(data.get("historial", [])),
        )

    def to_dict(self) -> Dict[str, Any]:
        payload = asdict(self)
        payload["historial"] = list(self.historial or [])
        return payload


@dataclass(slots=True)
class ClienteInfo:
    """Lightweight client info attached to quotes or orders."""

    nombre: str
    correo: str
    celular: str

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ClienteInfo":
        return cls(
            nombre=str(data.get("nombre", "")),
            correo=str(data.get("correo", "")),
            celular=str(data.get("celular", "")),
        )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


__all__ = ["Cliente", "ClienteInfo"]
