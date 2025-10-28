"""Persistent configuration management."""

from __future__ import annotations

import json
import os
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from typing import Callable, Dict, List

from models.impresora import Impresora, PrinterType
from models.material import Material

CONFIG_PATH = Path("config.json")

DEFAULT_CONFIG: Dict[str, object] = {
    "version": datetime.utcnow().isoformat(),
    "moneda": "MXN",
    "materiales": {
        "PLA": {"densidad_g_cm3": 1.24, "precio_kg": 350.0},
        "PETG": {"densidad_g_cm3": 1.27, "precio_kg": 420.0},
        "ABS": {"densidad_g_cm3": 1.04, "precio_kg": 480.0},
    },
    "impresoras": [
        {
            "nombre": "Bambu Lab A1",
            "tipo": "filamento",
            "costo_equipo": 15000.0,
            "vida_util_horas": 6000.0,
            "potencia_w": 350.0,
        },
        {
            "nombre": "Anycubic Photon M3",
            "tipo": "resina",
            "costo_equipo": 12000.0,
            "vida_util_horas": 4500.0,
            "potencia_w": 120.0,
        },
    ],
    "electricidad": {"kwh_precio": 3.0},
    "mano_obra": {"costo_hora": 120.0, "post_min": 20.0, "supervision_h": 0.0},
    "porcentajes": {"merma": 0.02, "riesgo": 0.05, "ganancia": 0.30, "iva": 0.16},
    "identidad": {
        "nombre_comercial": "Mi Taller 3D",
        "rfc": "",
        "direccion": "",
        "telefono": "",
        "logo_path": "assets/logo_negocio.png",
        "politicas": "Válida por 12 días a partir de la fecha.\nPrecios sujetos a cambios sin previo aviso.",
    },
    "integraciones": {
        "email": {
            "host": "smtp.example.com",
            "puerto": 587,
            "usuario": "",
            "password": "",
            "remitente": "cotizaciones@example.com",
            "usar_tls": True,
            "contador": "",
            "mensaje": "Adjuntamos la cotización solicitada.",
            "mensaje_contador": "Adjuntamos la solicitud de facturación.",
        },
        "whatsapp": {
            "endpoint": "https://api.whatsapp.example.com/send",
            "token": "",
            "numero": "",
            "mensaje_base": "Hola {cliente}, adjuntamos tu cotización {folio}.",
        },
    },
    "folios": {"cotizaciones": 1, "pedidos": 1, "padding": 3},
}


class ConfigStore:
    """Read/write accessors for the main configuration file."""

    def __init__(self, path: Path | None = None) -> None:
        self.path = path or CONFIG_PATH
        self.data: Dict[str, object] = {}
        self.load()

    # ------------------------------------------------------------------
    def load(self) -> None:
        if not self.path.exists():
            self.data = deepcopy(DEFAULT_CONFIG)
            self.save()
        else:
            with self.path.open("r", encoding="utf-8") as fh:
                self.data = json.load(fh)
        # ensure new keys exist
        changed = False
        for key, value in DEFAULT_CONFIG.items():
            if key not in self.data:
                self.data[key] = deepcopy(value)
                changed = True
        identidad = self.data.get("identidad", {})
        if "logo_path" not in identidad and identidad.get("logo"):
            identidad["logo_path"] = identidad.pop("logo")
            changed = True
        if self._ensure_folio_defaults():
            changed = True
        if changed:
            self.save()

    # ------------------------------------------------------------------
    def save(self) -> None:
        self.data["version"] = datetime.utcnow().isoformat()
        with self.path.open("w", encoding="utf-8") as fh:
            json.dump(self.data, fh, indent=2, ensure_ascii=False)

    # ------------------------------------------------------------------
    def _ensure_folio_defaults(self) -> bool:
        folios = self.data.setdefault("folios", {})
        changed = False
        defaults = {"cotizaciones": 1, "pedidos": 1, "padding": 3}
        for key, default in defaults.items():
            value = folios.get(key)
            if not isinstance(value, int) or (key == "padding" and int(value) < 1):
                folios[key] = int(default)
                changed = True
        return changed

    def _next_folio(self, key: str, prefix: str, exists: Callable[[str], bool]) -> str:
        self._ensure_folio_defaults()
        folios = self.data.setdefault("folios", {})
        padding = int(folios.get("padding", 3) or 3)
        counter = int(folios.get(key, 1) or 1)
        while True:
            folio = f"{prefix} – {counter:0{padding}d}"
            if not exists(folio):
                folios[key] = counter + 1
                self.save()
                return folio
            counter += 1

    def next_quote_folio(self, exists: Callable[[str], bool]) -> str:
        return self._next_folio("cotizaciones", "COT", exists)

    def next_order_folio(self, exists: Callable[[str], bool]) -> str:
        return self._next_folio("pedidos", "PED", exists)

    # ------------------------------------------------------------------
    def get_materials(self) -> List[Material]:
        materiales = self.data.get("materiales", {})
        return [
            Material.from_dict({"nombre": nombre, **info})
            for nombre, info in materiales.items()
        ]

    # ------------------------------------------------------------------
    def material_exists(self, nombre: str) -> bool:
        materiales = self.data.get("materiales", {})
        return nombre in materiales

    # ------------------------------------------------------------------
    def upsert_material(self, material: Material, previous_name: str | None = None) -> None:
        materiales = self.data.setdefault("materiales", {})
        if previous_name and previous_name in materiales and previous_name != material.nombre:
            del materiales[previous_name]
        materiales[material.nombre] = {
            "densidad_g_cm3": material.densidad_g_cm3,
            "precio_kg": material.precio_kg,
        }
        self.save()

    # ------------------------------------------------------------------
    def delete_material(self, nombre: str) -> None:
        materiales = self.data.get("materiales", {})
        if nombre in materiales:
            del materiales[nombre]
            self.save()

    # ------------------------------------------------------------------
    def get_printers(self, tipo: PrinterType | str | None = None) -> List[Impresora]:
        impresoras = [Impresora.from_dict(p) for p in self.data.get("impresoras", [])]
        if tipo is not None:
            filtro = PrinterType.from_value(tipo)
            impresoras = [p for p in impresoras if p.tipo == filtro]
        return impresoras

    # ------------------------------------------------------------------
    def upsert_printer(self, impresora: Impresora) -> None:
        impresoras = {item["nombre"]: item for item in self.data.get("impresoras", [])}
        impresoras[impresora.nombre] = impresora.to_dict()
        self.data["impresoras"] = list(impresoras.values())
        self.save()

    # ------------------------------------------------------------------
    def delete_printer(self, nombre: str) -> None:
        impresoras = [p for p in self.data.get("impresoras", []) if p.get("nombre") != nombre]
        self.data["impresoras"] = impresoras
        self.save()

    # ------------------------------------------------------------------
    def get_financials(self) -> Dict[str, float]:
        electricidad = self.data.get("electricidad", {})
        mano_obra = self.data.get("mano_obra", {})
        porcentajes = self.data.get("porcentajes", {})
        return {
            "precio_kwh": float(electricidad.get("kwh_precio", 0.0)),
            "costo_hora": float(mano_obra.get("costo_hora", 0.0)),
            "post_min": float(mano_obra.get("post_min", 0.0)),
            "supervision_h": float(mano_obra.get("supervision_h", 0.0)),
            "merma": float(porcentajes.get("merma", 0.0)),
            "riesgo": float(porcentajes.get("riesgo", 0.0)),
            "ganancia": float(porcentajes.get("ganancia", 0.0)),
            "iva": float(porcentajes.get("iva", 0.0)),
        }

    # ------------------------------------------------------------------
    def update_financials(self, payload: Dict[str, float]) -> None:
        self.data.setdefault("electricidad", {})["kwh_precio"] = float(payload.get("precio_kwh", 0.0))
        mano = self.data.setdefault("mano_obra", {})
        mano["costo_hora"] = float(payload.get("costo_hora", 0.0))
        mano["post_min"] = float(payload.get("post_min", 0.0))
        mano["supervision_h"] = float(payload.get("supervision_h", 0.0))
        porcentajes = self.data.setdefault("porcentajes", {})
        porcentajes["merma"] = float(payload.get("merma", 0.0))
        porcentajes["riesgo"] = float(payload.get("riesgo", 0.0))
        porcentajes["ganancia"] = float(payload.get("ganancia", 0.0))
        porcentajes["iva"] = float(payload.get("iva", 0.0))
        self.save()

    # ------------------------------------------------------------------
    def get_identity(self) -> Dict[str, object]:
        identidad = dict(self.data.get("identidad", {}))
        if "logo_path" not in identidad:
            identidad["logo_path"] = identidad.get("logo", "")
        return identidad

    def update_identity(self, payload: Dict[str, object]) -> None:
        logo_path = str(payload.get("logo_path", "")).strip()
        if logo_path:
            abs_path = Path(os.path.abspath(os.path.expanduser(logo_path)))
            payload["logo_path"] = abs_path.as_posix()
        self.data["identidad"] = payload
        self.save()

    # ------------------------------------------------------------------
    def get_integrations(self) -> Dict[str, object]:
        return dict(self.data.get("integraciones", {}))

    def update_integrations(self, payload: Dict[str, object]) -> None:
        self.data["integraciones"] = payload
        self.save()

    # ------------------------------------------------------------------
    def moneda(self) -> str:
        return str(self.data.get("moneda", "MXN"))

    # ------------------------------------------------------------------
    def set_moneda(self, moneda: str) -> None:
        self.data["moneda"] = moneda
        self.save()

    # ------------------------------------------------------------------
    def get_config_version(self) -> str:
        return str(self.data.get("version", ""))

    # ------------------------------------------------------------------
    def resolve_path(self, path_str: str) -> Path:
        if not path_str:
            return Path()
        return Path(os.path.abspath(os.path.expanduser(path_str)))


__all__ = ["ConfigStore", "DEFAULT_CONFIG", "CONFIG_PATH"]
