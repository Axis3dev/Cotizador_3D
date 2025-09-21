"""Shared cost utilities used by both FDM and resin pricing modules."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Tuple


@dataclass
class CostSettings:
    """Generic cost parameters common to both printing technologies."""

    electricity_mxn_per_kwh: float
    printer_power_w: float
    printer_cost_mxn: float
    printer_life_hours: float
    maintenance_per_hour: float
    labor_rate_mxn_per_hour: float
    prep_time_minutes: float


@dataclass
class FinanceSettings:
    """Financial parameters such as margin and taxes."""

    margin_percent: float
    tax_percent: float


def compute_electricity_cost(power_w: float, hours: float, price_per_kwh: float) -> float:
    """Return the cost of electricity in MXN."""

    kwh = (power_w * hours) / 1000.0
    return kwh * price_per_kwh


def compute_depreciation_cost(
    printer_cost: float, life_hours: float, maintenance_per_hour: float, hours: float
) -> float:
    """Estimate printer depreciation and maintenance cost for a job."""

    if life_hours <= 0:
        return maintenance_per_hour * hours
    depreciation_per_hour = printer_cost / life_hours
    return (depreciation_per_hour + maintenance_per_hour) * hours


def compute_labor_cost(hourly_rate: float, prep_minutes: float, print_hours: float) -> float:
    """Estimate labour cost including preparation and supervision time."""

    prep_hours = prep_minutes / 60.0
    return hourly_rate * (prep_hours + print_hours)


def apply_margin_and_tax(subtotal: float, margin: float, tax: float) -> Tuple[float, float, float]:
    """Apply profit margin and tax to obtain total price."""

    margin_amount = subtotal * margin
    taxed_subtotal = subtotal + margin_amount
    tax_amount = taxed_subtotal * tax
    total = taxed_subtotal + tax_amount
    return margin_amount, tax_amount, total


def build_cost_summary(
    material_cost: float,
    electricity_cost: float,
    depreciation_cost: float,
    labor_cost: float,
    finance: FinanceSettings,
) -> Dict[str, float]:
    """Return a dictionary with the subtotal, margin, tax and total."""

    subtotal = material_cost + electricity_cost + depreciation_cost + labor_cost
    margin_amount, tax_amount, total = apply_margin_and_tax(subtotal, finance.margin_percent, finance.tax_percent)
    return {
        "material": material_cost,
        "electricity": electricity_cost,
        "depreciation": depreciation_cost,
        "labor": labor_cost,
        "subtotal": subtotal,
        "margin_amount": margin_amount,
        "tax_amount": tax_amount,
        "total": total,
    }


def format_hours_minutes(hours: float) -> str:
    """Return a human readable representation of ``hours`` as H:MM."""

    total_minutes = int(round(hours * 60))
    h, m = divmod(total_minutes, 60)
    return f"{h:d}h {m:02d}m"


__all__ = [
    "CostSettings",
    "FinanceSettings",
    "compute_electricity_cost",
    "compute_depreciation_cost",
    "compute_labor_cost",
    "apply_margin_and_tax",
    "build_cost_summary",
    "format_hours_minutes",
]
