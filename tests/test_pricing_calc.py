"""Unit tests for pricing calculations."""

from __future__ import annotations

import unittest

from pricing.calc import (
    CostInputs,
    FinancialContext,
    MaterialInfo,
    PrinterContext,
    calculate_costs,
    grams_from_volume,
)


class PricingCalcTests(unittest.TestCase):
    """Ensure the Excel-aligned formulas behave as expected."""

    def test_calculate_costs_breakdown(self) -> None:
        material = MaterialInfo(nombre="PLA", densidad_g_cm3=1.24, precio_kg=400.0)
        printer = PrinterContext(
            nombre="Test FDM",
            tipo="filamento",
            costo_equipo=10000.0,
            vida_util_horas=2000.0,
            potencia_w=200.0,
        )
        financial = FinancialContext(
            precio_kwh=3.0,
            costo_hora_hombre=120.0,
            merma=0.10,
            riesgo=0.05,
            ganancia=0.25,
            iva=0.16,
        )
        inputs = CostInputs(
            masa_g=100.0,
            horas_impresion=2.0,
            minutos_mano_obra=30.0,
            horas_supervision=1.0,
            costo_stl=50.0,
            extras=20.0,
        )

        breakdown = calculate_costs(material, printer, financial, inputs)

        self.assertAlmostEqual(breakdown.material, 40.0)
        self.assertAlmostEqual(breakdown.energia, 1.2)
        self.assertAlmostEqual(breakdown.depreciacion, 10.0)
        self.assertAlmostEqual(breakdown.mano_obra, 180.0)
        self.assertAlmostEqual(breakdown.subtotal_base, 301.2)
        self.assertAlmostEqual(breakdown.merma, 30.12)
        self.assertAlmostEqual(breakdown.riesgo, 16.566)
        self.assertAlmostEqual(breakdown.ganancia, 86.9715)
        self.assertAlmostEqual(breakdown.total_sin_iva, 434.8575)
        self.assertAlmostEqual(breakdown.iva, 69.5772)
        self.assertAlmostEqual(breakdown.total, 504.4347)

    def test_grams_from_volume(self) -> None:
        self.assertAlmostEqual(grams_from_volume(1000.0, 1.24), 1.24)
        self.assertEqual(grams_from_volume(-1, 1.0), 0.0)
        self.assertEqual(grams_from_volume(1000.0, 0.0), 0.0)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
