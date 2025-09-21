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

    def find(self, correo: str = "", celular: str = "") -> Optional[Cliente]:
        key = self._key(correo, celular)
        if not key:
            return None
        return Cliente.from_dict(self.data[key])

    def upsert(self, info: ClienteInfo) -> Cliente:
        correo = info.correo.strip().lower()
        celular = info.celular.strip()
        key = self._key(correo, celular)
        if key:
            cliente = Cliente.from_dict(self.data[key])
            cliente.nombre = info.nombre or cliente.nombre
            cliente.correo = correo or cliente.correo
            cliente.celular = celular or cliente.celular
        else:
            key = uuid.uuid4().hex
            cliente = Cliente(
                id=key,
                nombre=info.nombre,
                correo=correo,
                celular=celular,
                fecha_alta=datetime.utcnow().date().isoformat(),
                historial=[],
            )
        self.data[key] = cliente.to_dict()
        self.save()
        return cliente

    def list_clients(self) -> List[Cliente]:
        return [Cliente.from_dict(payload) for payload in self.data.values()]

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
        cliente.total_ganancia += pedido.ganancia
        history_entry = f"Pedido {pedido.folio} - {pedido.total:.2f} {pedido.moneda}"
        historial = cliente.historial or []
        historial.append(history_entry)
        cliente.historial = historial
        self.data[cliente.id] = cliente.to_dict()
        self.save()
        return cliente


__all__ = ["ClientsStore", "CLIENTS_PATH"]
