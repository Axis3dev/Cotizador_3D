"""Printer catalog management."""

from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import List, Literal

from config.storage import ConfigStorage

PrinterType = Literal["filamento", "resina"]


@dataclass(slots=True)
class Printer:
    """Represents a 3D printer with economic data used in the quote."""

    nombre: str
    tipo: PrinterType
    costo_equipo: float
    vida_util_horas: float
    potencia_w: float

    @classmethod
    def from_dict(cls, data: dict) -> "Printer":
        return cls(
            nombre=data["nombre"],
            tipo=data["tipo"],
            costo_equipo=float(data["costo_equipo"]),
            vida_util_horas=float(data["vida_util_horas"]),
            potencia_w=float(data["potencia_w"]),
        )

    def to_dict(self) -> dict:
        return asdict(self)


class PrinterManager:
    """Helper class to manipulate printers persisted in configuration."""

    def __init__(self, storage: ConfigStorage) -> None:
        self.storage = storage

    # ------------------------------------------------------------------
    def list_printers(self, tipo: PrinterType | None = None) -> List[Printer]:
        printers = [Printer.from_dict(p) for p in self.storage.get_printers()]
        if tipo:
            printers = [p for p in printers if p.tipo == tipo]
        return printers

    # ------------------------------------------------------------------
    def save_printer(self, printer: Printer) -> None:
        """Add a new printer or update it if the name already exists."""

        printers = {p["nombre"]: p for p in self.storage.get_printers()}
        printers[printer.nombre] = printer.to_dict()
        self.storage.set_printers(printers.values())

    # ------------------------------------------------------------------
    def delete_printer(self, nombre: str) -> None:
        printers = [p for p in self.storage.get_printers() if p["nombre"] != nombre]
        self.storage.set_printers(printers)

    # ------------------------------------------------------------------
    def get(self, nombre: str) -> Printer | None:
        for printer in self.list_printers():
            if printer.nombre == nombre:
                return printer
        return None


__all__ = ["Printer", "PrinterManager", "PrinterType"]
