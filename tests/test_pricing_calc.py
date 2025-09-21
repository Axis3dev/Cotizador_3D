"""Unit tests for pricing calculations."""

from __future__ import annotations

import unittest

from models.impresora import Impresora
from models.material import Material
from models.pieza import Pieza
from pricing import FinancialSettings, build_quote_breakdown, compute_piece_base, grams_from_volume


class PricingCalcTests(unittest.TestCase):
    def test_build_quote_breakdown(self) -> None:
        material = Material(nombre="PLA", densidad_g_cm3=1.24, precio_kg=400.0)
        printer = Impresora(
            nombre="Test FDM",
            tipo="filamento",
            costo_equipo=10000.0,
            vida_util_horas=2000.0,
            potencia_w=200.0,
        )
        financials = FinancialSettings(
            precio_kwh=3.0,
            costo_hora=120.0,
            merma=0.10,
            riesgo=0.05,
            ganancia=0.25,
            iva=0.16,
        )
        pieza = Pieza(
            nombre="Pieza A",
            cantidad=1,
            masa_g=100.0,
            horas_impresion=2.0,
            costo_stl=50.0,
            extras=20.0,
            prep_min=30.0,
            supervision_h=1.0,
        )

        base = compute_piece_base(pieza, material, printer, financials)
        breakdown = build_quote_breakdown([base], financials)
        pieza_costos = breakdown.piezas[0]

        self.assertAlmostEqual(pieza_costos.material_unit, 40.0)
        self.assertAlmostEqual(pieza_costos.energia_unit, 1.2)
        self.assertAlmostEqual(pieza_costos.depreciacion_unit, 10.0)
        self.assertAlmostEqual(pieza_costos.mano_obra_unit, 180.0)
        self.assertAlmostEqual(pieza_costos.subtotal_total, 301.2)
        self.assertAlmostEqual(breakdown.merma, 30.12)
        self.assertAlmostEqual(breakdown.riesgo, 16.566)
        self.assertAlmostEqual(breakdown.ganancia, 86.9715)
        self.assertAlmostEqual(breakdown.total_sin_iva, 434.8575)
        self.assertAlmostEqual(breakdown.iva, 69.5772)
        self.assertAlmostEqual(breakdown.total, 504.4347)
        self.assertAlmostEqual(pieza_costos.total_total, breakdown.total)

    def test_grams_from_volume(self) -> None:
        self.assertAlmostEqual(grams_from_volume(1000.0, 1.24), 1.24)
        self.assertEqual(grams_from_volume(-1, 1.0), 0.0)
        self.assertEqual(grams_from_volume(1000.0, 0.0), 0.0)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
