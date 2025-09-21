"""Quotation models."""

from __future__ import annotations

from dataclasses import dataclass, asdict, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from models.cliente import ClienteInfo
from models.pieza import Pieza


@dataclass(slots=True)
class PiezaCostos:
    """Detailed cost allocation for a piece within a quotation."""

    pieza: Pieza
    material_unit: float
    energia_unit: float
    depreciacion_unit: float
    mano_obra_unit: float
    costo_stl_unit: float
    extras_unit: float
    subtotal_unit: float
    subtotal_total: float
    merma_total: float
    riesgo_total: float
    ganancia_total: float
    iva_total: float
    total_unit: float
    total_total: float

    def to_dict(self) -> Dict[str, Any]:
        payload = {
            "pieza": self.pieza.to_dict(),
            "material_unit": self.material_unit,
            "energia_unit": self.energia_unit,
            "depreciacion_unit": self.depreciacion_unit,
            "mano_obra_unit": self.mano_obra_unit,
            "costo_stl_unit": self.costo_stl_unit,
            "extras_unit": self.extras_unit,
            "subtotal_unit": self.subtotal_unit,
            "subtotal_total": self.subtotal_total,
            "merma_total": self.merma_total,
            "riesgo_total": self.riesgo_total,
            "ganancia_total": self.ganancia_total,
            "iva_total": self.iva_total,
            "total_unit": self.total_unit,
            "total_total": self.total_total,
        }
        return payload

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PiezaCostos":
        return cls(
            pieza=Pieza.from_dict(data["pieza"]),
            material_unit=float(data.get("material_unit", 0.0)),
            energia_unit=float(data.get("energia_unit", 0.0)),
            depreciacion_unit=float(data.get("depreciacion_unit", 0.0)),
            mano_obra_unit=float(data.get("mano_obra_unit", 0.0)),
            costo_stl_unit=float(data.get("costo_stl_unit", 0.0)),
            extras_unit=float(data.get("extras_unit", 0.0)),
            subtotal_unit=float(data.get("subtotal_unit", 0.0)),
            subtotal_total=float(data.get("subtotal_total", 0.0)),
            merma_total=float(data.get("merma_total", 0.0)),
            riesgo_total=float(data.get("riesgo_total", 0.0)),
            ganancia_total=float(data.get("ganancia_total", 0.0)),
            iva_total=float(data.get("iva_total", 0.0)),
            total_unit=float(data.get("total_unit", 0.0)),
            total_total=float(data.get("total_total", 0.0)),
        )


@dataclass(slots=True)
class Cotizacion:
    """Quotation persisted in disk."""

    folio: str
    fecha: str
    proyecto: str
    tipo: str
    impresora: str
    material: str
    material_precio_kg: float
    cliente: ClienteInfo
    piezas: List[PiezaCostos] = field(default_factory=list)
    subtotal_base: float = 0.0
    merma: float = 0.0
    riesgo: float = 0.0
    ganancia: float = 0.0
    subtotal_post_riesgo: float = 0.0
    total_sin_iva: float = 0.0
    iva: float = 0.0
    total: float = 0.0
    moneda: str = "MXN"
    notas: str | None = None
    validez_dias: int = 12
    config_version: str | None = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "folio": self.folio,
            "fecha": self.fecha,
            "proyecto": self.proyecto,
            "tipo": self.tipo,
            "impresora": self.impresora,
            "material": self.material,
            "material_precio_kg": self.material_precio_kg,
            "cliente": self.cliente.to_dict(),
            "piezas": [p.to_dict() for p in self.piezas],
            "subtotal_base": self.subtotal_base,
            "merma": self.merma,
            "riesgo": self.riesgo,
            "ganancia": self.ganancia,
            "subtotal_post_riesgo": self.subtotal_post_riesgo,
            "total_sin_iva": self.total_sin_iva,
            "iva": self.iva,
            "total": self.total,
            "moneda": self.moneda,
            "notas": self.notas,
            "validez_dias": self.validez_dias,
            "config_version": self.config_version,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Cotizacion":
        return cls(
            folio=str(data.get("folio", "")),
            fecha=str(data.get("fecha", datetime.utcnow().date().isoformat())),
            proyecto=str(data.get("proyecto", "")),
            tipo=str(data.get("tipo", "filamento")),
            impresora=str(data.get("impresora", "")),
            material=str(data.get("material", "")),
            material_precio_kg=float(data.get("material_precio_kg", 0.0)),
            cliente=ClienteInfo.from_dict(data.get("cliente", {})),
            piezas=[PiezaCostos.from_dict(item) for item in data.get("piezas", [])],
            subtotal_base=float(data.get("subtotal_base", 0.0)),
            merma=float(data.get("merma", 0.0)),
            riesgo=float(data.get("riesgo", 0.0)),
            ganancia=float(data.get("ganancia", 0.0)),
            subtotal_post_riesgo=float(data.get("subtotal_post_riesgo", 0.0)),
            total_sin_iva=float(data.get("total_sin_iva", 0.0)),
            iva=float(data.get("iva", 0.0)),
            total=float(data.get("total", 0.0)),
            moneda=str(data.get("moneda", "MXN")),
            notas=data.get("notas"),
            validez_dias=int(data.get("validez_dias", 12)),
            config_version=data.get("config_version"),
        )


__all__ = ["Cotizacion", "PiezaCostos"]
