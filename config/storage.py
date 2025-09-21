"""Persistence helpers for application configuration."""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, Iterable, List

# Default configuration mirrors the structure requested by the client.
DEFAULT_CONFIG: Dict[str, Any] = {
    "moneda": "MXN",
    "electricidad": {"kwh_precio": 3.0},
    "mano_obra": {
        "costo_hora": 120.0,
        "post_min": 20.0,
        "supervision_h": 0.0,
    },
    "porcentajes": {
        "merma": 0.02,
        "riesgo": 0.05,
        "ganancia": 0.3,
        "iva": 0.16,
    },
    "materiales": {
        "PLA": {"densidad_g_cm3": 1.24, "precio_kg": 360.0},
        "PETG": {"densidad_g_cm3": 1.27, "precio_kg": 420.0},
        "ABS": {"densidad_g_cm3": 1.04, "precio_kg": 450.0},
    },
    "impresoras": [
        {
            "nombre": "Bambu Lab A1",
            "tipo": "filamento",
            "costo_equipo": 16000.0,
            "vida_util_horas": 5000.0,
            "potencia_w": 220.0,
        },
        {
            "nombre": "Elegoo Mars 3",
            "tipo": "resina",
            "costo_equipo": 9000.0,
            "vida_util_horas": 4000.0,
            "potencia_w": 120.0,
        },
    ],
}


class ConfigStorage:
    """Utility wrapper around the JSON configuration file."""

    def __init__(self, path: Path | None = None) -> None:
        self.path = Path(path) if path else Path(__file__).resolve().parent.parent / "config.json"
        self._data: Dict[str, Any] = {}
        self.reload()

    # ------------------------------------------------------------------
    def reload(self) -> None:
        """Load configuration from disk, creating defaults if necessary."""

        if not self.path.exists():
            self._data = deepcopy(DEFAULT_CONFIG)
            self.save()
            return

        try:
            with self.path.open("r", encoding="utf-8") as fh:
                self._data = json.load(fh)
        except json.JSONDecodeError:
            # If the file is corrupt, fall back to defaults but keep a backup.
            backup = self.path.with_suffix(".bak")
            self.path.replace(backup)
            self._data = deepcopy(DEFAULT_CONFIG)
            self.save()

    # ------------------------------------------------------------------
    def save(self) -> None:
        """Persist the current configuration to disk."""

        with self.path.open("w", encoding="utf-8") as fh:
            json.dump(self._data, fh, indent=2, ensure_ascii=False, sort_keys=True)

    # ------------------------------------------------------------------
    @property
    def data(self) -> Dict[str, Any]:
        """Return a deep copy of the configuration dictionary."""

        return deepcopy(self._data)

    # ------------------------------------------------------------------
    def update_section(self, section: str, values: Dict[str, Any]) -> None:
        """Replace a configuration section and save the file."""

        self._data[section] = deepcopy(values)
        self.save()

    # ------------------------------------------------------------------
    def upsert_material(self, name: str, values: Dict[str, Any]) -> None:
        """Create or update a material entry."""

        materials = self._data.setdefault("materiales", {})
        materials[name] = deepcopy(values)
        self.save()

    # ------------------------------------------------------------------
    def delete_material(self, name: str) -> None:
        """Remove a material from configuration if present."""

        materials = self._data.setdefault("materiales", {})
        if name in materials:
            del materials[name]
            self.save()

    # ------------------------------------------------------------------
    def set_printers(self, printers: Iterable[Dict[str, Any]]) -> None:
        """Persist the provided iterable of printers."""

        self._data["impresoras"] = [deepcopy(p) for p in printers]
        self.save()

    # ------------------------------------------------------------------
    def get_printers(self) -> List[Dict[str, Any]]:
        """Return the list of printers from configuration."""

        return [deepcopy(p) for p in self._data.get("impresoras", [])]


__all__ = ["ConfigStorage", "DEFAULT_CONFIG"]
