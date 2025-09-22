"""Simple JSON based CRM storage."""

from __future__ import annotations

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from models.cliente import Cliente, ClienteInfo
from models.cotizacion import Cotizacion
from models.pedido import Pedido

CLIENTS_PATH = Path("clientes.json")


class ClientsStore:
    """Manage clients and their aggregated metrics."""

    def __init__(self, path: Path | None = None) -> None:
        self.path = path or CLIENTS_PATH
        self.data: Dict[str, Dict[str, object]] = {}
        self.load()

    def load(self) -> None:
        if not self.path.exists():
            self.save()
        else:
            with self.path.open("r", encoding="utf-8") as fh:
                try:
                    self.data = json.load(fh)
                except json.JSONDecodeError:
                    self.data = {}

    def save(self) -> None:
        with self.path.open("w", encoding="utf-8") as fh:
            json.dump(self.data, fh, indent=2, ensure_ascii=False)

    def _key(self, correo: str, celular: str) -> Optional[str]:
        correo = correo.strip().lower()
        celular = celular.strip()
        for key, payload in self.data.items():
            if correo and payload.get("correo", "").lower() == correo:
                return key
            if celular and payload.get("celular", "") == celular:
                return key
        return None

    def get(self, client_id: str) -> Optional[Cliente]:
        payload = self.data.get(client_id)
        return Cliente.from_dict(payload) if payload else None

    def find(self, correo: str = "", celular: str = "") -> Optional[Cliente]:
        key = self._key(correo, celular)
        if not key:
            return None
        return Cliente.from_dict(self.data[key])

    def upsert(self, info: ClienteInfo, extra: Optional[Dict[str, object]] = None) -> Cliente:
        correo = info.correo.strip().lower()
        celular = info.celular.strip()
        key = info.id or self._key(correo, celular)
        if key and key in self.data:
            cliente = Cliente.from_dict(self.data[key])
        else:
            key = key or uuid.uuid4().hex
            cliente = Cliente(
                id=key,
                nombre=info.nombre,
                correo=correo,
                celular=celular,
                fecha_alta=datetime.utcnow().date().isoformat(),
                historial=[],
            )

        cliente.nombre = info.nombre or cliente.nombre
        if correo:
            cliente.correo = correo
        if celular:
            cliente.celular = celular
        if getattr(info, "rfc", ""):
            cliente.rfc = info.rfc

        if extra:
            cliente.rfc = str(extra.get("rfc", cliente.rfc))
            cliente.razon_social = str(extra.get("razon_social", cliente.razon_social))
            cliente.domicilio_fiscal = str(extra.get("domicilio_fiscal", cliente.domicilio_fiscal))
            cliente.codigo_postal = str(extra.get("codigo_postal", cliente.codigo_postal))
            cliente.regimen = str(extra.get("regimen", cliente.regimen))
            cliente.ciudad = str(extra.get("ciudad", cliente.ciudad))
            cliente.estado = str(extra.get("estado", cliente.estado))

        info.id = cliente.id
        self.data[cliente.id] = cliente.to_dict()
        self.save()
        return cliente

    def update_client(self, cliente: Cliente) -> None:
        self.data[cliente.id] = cliente.to_dict()
        self.save()

    def list_clients(self) -> List[Cliente]:
        clientes = [Cliente.from_dict(payload) for payload in self.data.values()]
        clientes.sort(key=lambda c: c.nombre.lower())
        return clientes

    def search(self, query: str) -> List[Cliente]:
        query = query.strip().lower()
        if not query:
            return self.list_clients()
        matches: List[Cliente] = []
        for payload in self.data.values():
            cliente = Cliente.from_dict(payload)
            haystack = [
                cliente.nombre.lower(),
                cliente.correo.lower(),
                cliente.celular.lower(),
            ]
            if any(query in value for value in haystack if value):
                matches.append(cliente)
        matches.sort(key=lambda c: c.nombre.lower())
        return matches

    def register_quote(self, info: ClienteInfo, quote: Cotizacion) -> Cliente:
        cliente = self.upsert(info)
        history_entry = f"Cotización {quote.folio} - {quote.total:.2f} {quote.moneda}"
        historial = cliente.historial or []
        historial.append(history_entry)
        cliente.historial = historial
        self.data[cliente.id] = cliente.to_dict()
        self.save()
        return cliente

    def register_order(self, info: ClienteInfo, pedido: Pedido) -> Cliente:
        cliente = self.upsert(info)
        cliente.pedidos += 1
        cliente.total_facturado += pedido.total
        cliente.total_costos += pedido.subtotal_base
        cliente.total_gastos += pedido.merma + pedido.riesgo
        cliente.total_ganancia += pedido.ganancia
        cliente.total_iva += pedido.iva
        cliente.total_retencion += pedido.retencion
        cliente.total_neto += pedido.total - pedido.retencion
        history_entry = f"Pedido {pedido.folio} - {pedido.total:.2f} {pedido.moneda}"
        historial = cliente.historial or []
        historial.append(history_entry)
        cliente.historial = historial
        self.data[cliente.id] = cliente.to_dict()
        self.save()
        return cliente

    def sync_totals(self, orders: List[Pedido]) -> None:
        """Recalculate aggregated totals from the persisted orders."""

        aggregates: Dict[str, Dict[str, float]] = {}
        for pedido in orders:
            cliente_id = pedido.cliente.id or self._key(pedido.cliente.correo, pedido.cliente.celular)
            if not cliente_id:
                continue
            bucket = aggregates.setdefault(
                cliente_id,
                {
                    "pedidos": 0,
                    "total_facturado": 0.0,
                    "total_costos": 0.0,
                    "total_gastos": 0.0,
                    "total_ganancia": 0.0,
                    "total_iva": 0.0,
                    "total_retencion": 0.0,
                    "total_neto": 0.0,
                },
            )
            bucket["pedidos"] += 1
            bucket["total_facturado"] += pedido.total
            bucket["total_costos"] += pedido.subtotal_base
            bucket["total_gastos"] += pedido.merma + pedido.riesgo
            bucket["total_ganancia"] += pedido.ganancia
            bucket["total_iva"] += pedido.iva
            bucket["total_retencion"] += pedido.retencion
            bucket["total_neto"] += pedido.total - pedido.retencion

        updated = False
        for client_id, payload in aggregates.items():
            cliente = self.get(client_id)
            if not cliente:
                continue
            cliente.pedidos = payload["pedidos"]
            cliente.total_facturado = payload["total_facturado"]
            cliente.total_costos = payload["total_costos"]
            cliente.total_gastos = payload["total_gastos"]
            cliente.total_ganancia = payload["total_ganancia"]
            cliente.total_iva = payload["total_iva"]
            cliente.total_retencion = payload["total_retencion"]
            cliente.total_neto = payload["total_neto"]
            self.data[client_id] = cliente.to_dict()
            updated = True

        if updated:
            self.save()


__all__ = ["ClientsStore", "CLIENTS_PATH"]
