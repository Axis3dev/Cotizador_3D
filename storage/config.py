"""Utilities for loading and persisting application configuration."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

CONFIG_FILE = Path("config.json")
PRESETS_DIR = Path("presets")


DEFAULT_CONFIG: Dict[str, Any] = {
    "general": {
        "currency": "MXN",
    },
    "materials": {
        "FDM": {
            "PLA": {"density": 1.24, "price_per_kg": 450.0},
            "PETG": {"density": 1.27, "price_per_kg": 520.0},
            "ABS": {"density": 1.04, "price_per_kg": 500.0},
        },
        "Resin": {
            "Resina Estándar": {"density": 1.1, "price_per_liter": 1200.0},
            "Resina Dura": {"density": 1.2, "price_per_liter": 1600.0},
        },
    },
    "fdm": {
        "defaults": {
            "material": "PLA",
            "infill_percentage": 20.0,
            "layer_height_mm": 0.2,
            "perimeters": 3,
            "nozzle_diameter_mm": 0.4,
            "line_width_mm": 0.42,
            "shell_factor": 0.18,
            "top_bottom_factor": 0.08,
            "overhead_per_layer_s": 3.0,
        },
        "speeds": {
            "profile": "Bambu Lab A1",
            "perimeter_mm_s": 150.0,
            "infill_mm_s": 200.0,
            "top_bottom_mm_s": 150.0,
        },
    },
    "resin": {
        "defaults": {
            "material": "Resina Estándar",
            "layer_height_mm": 0.05,
            "exposure_time_s": 2.5,
            "lift_time_s": 3.0,
            "base_layers": 6,
            "base_exposure_time_s": 30.0,
            "base_lift_time_s": 6.0,
            "hollow_percentage": 0.0,
            "wall_thickness_mm": 2.0,
        },
    },
    "costs": {
        "electricity_mxn_per_kwh": 2.8,
        "printer_power_w": 220.0,
        "printer_cost_mxn": 12000.0,
        "printer_life_hours": 5000.0,
        "maintenance_per_hour": 5.0,
        "labor_rate_mxn_per_hour": 120.0,
        "prep_time_minutes": 20.0,
    },
    "finance": {
        "margin_percent": 0.3,
        "tax_percent": 0.16,
    },
}


@dataclass
class ConfigManager:
    """Simple configuration manager that persists data in a JSON file."""

    path: Path = CONFIG_FILE

    def __post_init__(self) -> None:
        PRESETS_DIR.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self.path.write_text(json.dumps(DEFAULT_CONFIG, indent=2, ensure_ascii=False), encoding="utf-8")
        self.data: Dict[str, Any] = {}
        self.load()

    def load(self) -> None:
        """Load configuration from disk."""
        with self.path.open("r", encoding="utf-8") as fh:
            self.data = json.load(fh)

    def save(self) -> None:
        """Persist the current configuration to disk."""
        with self.path.open("w", encoding="utf-8") as fh:
            json.dump(self.data, fh, indent=2, ensure_ascii=False)

    def get(self, *keys: str, default: Optional[Any] = None) -> Any:
        """Retrieve a nested value by keys, optionally returning a default."""
        node: Any = self.data
        for key in keys:
            if isinstance(node, dict) and key in node:
                node = node[key]
            else:
                return default
        return node

    def set(self, value: Any, *keys: str) -> None:
        """Set a nested value identified by ``keys`` to ``value``."""
        if not keys:
            raise ValueError("At least one key must be provided")
        node = self.data
        for key in keys[:-1]:
            node = node.setdefault(key, {})
        node[keys[-1]] = value
        self.save()

    # Preset management -------------------------------------------------
    def preset_path(self, mode: str, name: str) -> Path:
        """Return the file path for a preset name and mode."""
        safe_name = name.strip().replace(" ", "_")
        return PRESETS_DIR / f"{mode.lower()}_{safe_name}.json"

    def list_presets(self, mode: str) -> List[str]:
        """List available presets for the given mode."""
        suffix = f"{mode.lower()}_"
        presets: List[str] = []
        for file in PRESETS_DIR.glob(f"{mode.lower()}_*.json"):
            name = file.stem
            if name.startswith(suffix):
                presets.append(name[len(suffix):].replace("_", " "))
        return sorted(presets)

    def save_preset(self, mode: str, name: str, data: Dict[str, Any]) -> Path:
        """Persist a preset for FDM or resin mode."""
        path = self.preset_path(mode, name)
        with path.open("w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2, ensure_ascii=False)
        return path

    def load_preset(self, mode: str, name: str) -> Dict[str, Any]:
        """Load preset data for a given mode."""
        path = self.preset_path(mode, name)
        with path.open("r", encoding="utf-8") as fh:
            return json.load(fh)


__all__ = [
    "CONFIG_FILE",
    "PRESETS_DIR",
    "DEFAULT_CONFIG",
    "ConfigManager",
]
