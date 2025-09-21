"""Persistence helpers for orders."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from models.pedido import Pedido

ORDERS_DIR = Path("pedidos_guardados")


class OrdersStore:
    """Manage orders persisted as JSON files."""

    def __init__(self, directory: Path | None = None) -> None:
        self.directory = directory or ORDERS_DIR
        self.directory.mkdir(parents=True, exist_ok=True)

    def _order_path(self, folio: str) -> Path:
        return self.directory / f"{folio}.json"

    def generate_folio(self, fecha: datetime | None = None) -> str:
        fecha = fecha or datetime.utcnow()
        prefix = fecha.strftime("PED-%Y%m%d")
        counter = 1
        while True:
            folio = f"{prefix}-{counter:03d}"
            if not self._order_path(folio).exists():
                return folio
            counter += 1

    def save(self, pedido: Pedido) -> Path:
        path = self._order_path(pedido.folio)
        with path.open("w", encoding="utf-8") as fh:
            json.dump(pedido.to_dict(), fh, indent=2, ensure_ascii=False)
        return path

    def load(self, folio: str) -> Optional[Pedido]:
        path = self._order_path(folio)
        if not path.exists():
            return None
        with path.open("r", encoding="utf-8") as fh:
            data = json.load(fh)
        return Pedido.from_dict(data)

    def delete(self, folio: str) -> None:
        path = self._order_path(folio)
        if path.exists():
            path.unlink()

    def list_orders(self) -> List[Pedido]:
        pedidos: List[Pedido] = []
        for file in sorted(self.directory.glob("*.json")):
            try:
                with file.open("r", encoding="utf-8") as fh:
                    data = json.load(fh)
                pedidos.append(Pedido.from_dict(data))
            except json.JSONDecodeError:
                continue
        return pedidos


__all__ = ["OrdersStore", "ORDERS_DIR"]
