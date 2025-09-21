"""Persistence helpers for quotations."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from models.cotizacion import Cotizacion

QUOTES_DIR = Path("cotizaciones_guardadas")


class QuoteStore:
    """Store and retrieve quotations serialized as JSON files."""

    def __init__(self, directory: Path | None = None) -> None:
        self.directory = directory or QUOTES_DIR
        self.directory.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    def _quote_path(self, folio: str) -> Path:
        return self.directory / f"{folio}.json"

    # ------------------------------------------------------------------
    def generate_folio(self, fecha: datetime | None = None) -> str:
        fecha = fecha or datetime.utcnow()
        prefix = fecha.strftime("CTZ-%Y%m%d")
        counter = 1
        while True:
            folio = f"{prefix}-{counter:03d}"
            if not self._quote_path(folio).exists():
                return folio
            counter += 1

    # ------------------------------------------------------------------
    def save(self, quote: Cotizacion) -> Path:
        path = self._quote_path(quote.folio)
        with path.open("w", encoding="utf-8") as fh:
            json.dump(quote.to_dict(), fh, indent=2, ensure_ascii=False)
        return path

    # ------------------------------------------------------------------
    def load(self, folio: str) -> Optional[Cotizacion]:
        path = self._quote_path(folio)
        if not path.exists():
            return None
        with path.open("r", encoding="utf-8") as fh:
            data = json.load(fh)
        return Cotizacion.from_dict(data)

    # ------------------------------------------------------------------
    def delete(self, folio: str) -> None:
        path = self._quote_path(folio)
        if path.exists():
            path.unlink()

    # ------------------------------------------------------------------
    def list_quotes(self) -> List[Cotizacion]:
        quotes: List[Cotizacion] = []
        for file in sorted(self.directory.glob("*.json")):
            try:
                with file.open("r", encoding="utf-8") as fh:
                    data = json.load(fh)
                quotes.append(Cotizacion.from_dict(data))
            except json.JSONDecodeError:
                continue
        return quotes


__all__ = ["QuoteStore", "QUOTES_DIR"]
