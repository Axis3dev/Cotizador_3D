"""Order model."""

from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Any, Dict, Optional

from models.cliente import ClienteInfo


@dataclass(slots=True)
class Pedido:
    """Represents an accepted quotation scheduled for production."""

    folio: str
    folio_cotizacion: str
    fecha_creacion: str
    fecha_estimada: str | None
    proyecto: str
    tipo: str
    impresora: str
    cliente: ClienteInfo
    subtotal_base: float
    total: float
    merma: float
    riesgo: float
    ganancia: float
    iva: float
    moneda: str
    estatus: str = "pendiente"
    anticipo: bool = False
    liquidado: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "folio": self.folio,
            "folio_cotizacion": self.folio_cotizacion,
            "fecha_creacion": self.fecha_creacion,
            "fecha_estimada": self.fecha_estimada,
            "proyecto": self.proyecto,
            "tipo": self.tipo,
            "impresora": self.impresora,
            "cliente": self.cliente.to_dict(),
            "subtotal_base": self.subtotal_base,
            "total": self.total,
            "merma": self.merma,
            "riesgo": self.riesgo,
            "ganancia": self.ganancia,
            "iva": self.iva,
            "moneda": self.moneda,
            "estatus": self.estatus,
            "anticipo": self.anticipo,
            "liquidado": self.liquidado,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Pedido":
        return cls(
            folio=str(data.get("folio", "")),
            folio_cotizacion=str(data.get("folio_cotizacion", "")),
            fecha_creacion=str(data.get("fecha_creacion", datetime.utcnow().date().isoformat())),
            fecha_estimada=data.get("fecha_estimada"),
            proyecto=str(data.get("proyecto", "")),
            tipo=str(data.get("tipo", "filamento")),
            impresora=str(data.get("impresora", "")),
            cliente=ClienteInfo.from_dict(data.get("cliente", {})),
            subtotal_base=float(data.get("subtotal_base", 0.0)),
            total=float(data.get("total", 0.0)),
            merma=float(data.get("merma", 0.0)),
            riesgo=float(data.get("riesgo", 0.0)),
            ganancia=float(data.get("ganancia", 0.0)),
            iva=float(data.get("iva", 0.0)),
            moneda=str(data.get("moneda", "MXN")),
            estatus=str(data.get("estatus", "pendiente")),
            anticipo=bool(data.get("anticipo", False)),
            liquidado=bool(data.get("liquidado", False)),
        )


__all__ = ["Pedido"]
