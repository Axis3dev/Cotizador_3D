"""Client domain model."""

from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Any, Dict, List


@dataclass(slots=True)
class Cliente:
    """Basic CRM entry with billing metadata and aggregated totals."""

    id: str
    nombre: str
    correo: str
    celular: str
    fecha_alta: str
    pedidos: int = 0
    total_facturado: float = 0.0
    total_costos: float = 0.0
    total_gastos: float = 0.0
    total_ganancia: float = 0.0
    total_iva: float = 0.0
    total_retencion: float = 0.0
    total_neto: float = 0.0
    historial: List[str] | None = None
    rfc: str = ""
    razon_social: str = ""
    domicilio_fiscal: str = ""
    codigo_postal: str = ""
    regimen: str = ""
    ciudad: str = ""
    estado: str = ""

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
            total_costos=float(data.get("total_costos", data.get("total_coste", 0.0))),
            total_gastos=float(data.get("total_gastos", 0.0)),
            total_ganancia=float(data.get("total_ganancia", 0.0)),
            total_iva=float(data.get("total_iva", 0.0)),
            total_retencion=float(data.get("total_retencion", 0.0)),
            total_neto=float(data.get("total_neto", 0.0)),
            historial=list(data.get("historial", [])),
            rfc=str(data.get("rfc", "")),
            razon_social=str(data.get("razon_social", "")),
            domicilio_fiscal=str(data.get("domicilio_fiscal", "")),
            codigo_postal=str(data.get("codigo_postal", "")),
            regimen=str(data.get("regimen", "")),
            ciudad=str(data.get("ciudad", "")),
            estado=str(data.get("estado", "")),
        )

    def to_dict(self) -> Dict[str, Any]:
        payload = asdict(self)
        payload["historial"] = list(self.historial or [])
        return payload


@dataclass(slots=True)
class ClienteInfo:
    """Lightweight client info attached to quotes or orders."""

    id: str | None = None
    nombre: str = ""
    correo: str = ""
    celular: str = ""

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ClienteInfo":
        return cls(
            id=data.get("id"),
            nombre=str(data.get("nombre", "")),
            correo=str(data.get("correo", "")),
            celular=str(data.get("celular", "")),
        )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


__all__ = ["Cliente", "ClienteInfo"]
