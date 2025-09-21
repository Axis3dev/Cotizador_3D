"""Aplicación principal de cotización para impresiones 3D."""

from __future__ import annotations

import sys
from pathlib import Path
import tkinter as tk
from dataclasses import asdict
from tkinter import filedialog, messagebox, scrolledtext, ttk
from typing import Any, Dict, Optional

# Garantiza que el directorio raíz del proyecto esté en ``sys.path`` incluso cuando
# se ejecute el script desde ubicaciones relativas (p. ej., ``python Axis3dev/Cotizador_3D/app.py``)
# o mediante atajos de VS Code.
ROOT_DIR = Path(__file__).resolve().parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from export.csv_export import export_quote_to_csv
from export.pdf_export import export_quote_to_pdf
from models.geometry import MeshInfo, load_mesh
from pricing.common import CostSettings, FinanceSettings
from pricing.fdm import FDMEstimate, FDMParameters, estimate_fdm_costs
from pricing.resin import ResinEstimate, ResinParameters, estimate_resin_costs
from storage.config import ConfigManager
from ui.components.widgets import LabeledCombobox, LabeledEntry


def safe_float(value: str, default: float = 0.0) -> float:
    """Return ``value`` parsed as float, falling back to ``default``."""

    try:
        return float(value)
    except (TypeError, ValueError):
        return default


class CotizadorApp(tk.Tk):
    """Ventana principal con todas las pestañas y controles."""

    def __init__(self) -> None:
        super().__init__()
        self.title("Cotizador de Impresión 3D")
        self.geometry("1080x720")

        self.config_manager = ConfigManager()
        self.mesh_info: Optional[MeshInfo] = None
        self.last_quote: Optional[Dict[str, Any]] = None

        self.mode_var = tk.StringVar(value="FDM")
        self.client_name_var = tk.StringVar()
        self._setup_variables()
        self._build_ui()

        self.protocol("WM_DELETE_WINDOW", self.on_exit)

    # ------------------------------------------------------------------
    def _setup_variables(self) -> None:
        """Inicializa variables Tkinter para los formularios."""

        cfg = self.config_manager

        # Archivo tab info variables
        self.file_vars = {
            "name": tk.StringVar(value="Sin archivo"),
            "volume_mm3": tk.StringVar(value="0"),
            "volume_cm3": tk.StringVar(value="0"),
            "bbox": tk.StringVar(value="0 x 0 x 0"),
            "watertight": tk.StringVar(value="-"),
        }

        # FDM variables
        fdm_defaults = cfg.get("fdm", "defaults", default={})
        fdm_speeds = cfg.get("fdm", "speeds", default={})
        material_name = fdm_defaults.get("material", "PLA")

        self.fdm_material_var = tk.StringVar(value=material_name)
        material_data = cfg.get("materials", "FDM", material_name, default={})
        self.fdm_density_var = tk.StringVar(value=str(material_data.get("density", 1.24)))
        self.fdm_price_var = tk.StringVar(value=str(material_data.get("price_per_kg", 450.0)))
        self.fdm_infill_var = tk.StringVar(value=str(fdm_defaults.get("infill_percentage", 20.0)))
        self.fdm_layer_height_var = tk.StringVar(value=str(fdm_defaults.get("layer_height_mm", 0.2)))
        self.fdm_perimeters_var = tk.StringVar(value=str(fdm_defaults.get("perimeters", 3)))
        self.fdm_nozzle_var = tk.StringVar(value=str(fdm_defaults.get("nozzle_diameter_mm", 0.4)))
        self.fdm_line_width_var = tk.StringVar(value=str(fdm_defaults.get("line_width_mm", 0.42)))
        self.fdm_shell_factor_var = tk.StringVar(value=str(fdm_defaults.get("shell_factor", 0.18)))
        self.fdm_top_bottom_factor_var = tk.StringVar(value=str(fdm_defaults.get("top_bottom_factor", 0.08)))
        self.fdm_overhead_var = tk.StringVar(value=str(fdm_defaults.get("overhead_per_layer_s", 3.0)))
        self.fdm_speed_perimeter_var = tk.StringVar(value=str(fdm_speeds.get("perimeter_mm_s", 150.0)))
        self.fdm_speed_infill_var = tk.StringVar(value=str(fdm_speeds.get("infill_mm_s", 200.0)))
        self.fdm_speed_top_var = tk.StringVar(value=str(fdm_speeds.get("top_bottom_mm_s", 150.0)))

        # Resin variables
        resin_defaults = cfg.get("resin", "defaults", default={})
        resin_material_name = resin_defaults.get("material", "Resina Estándar")
        self.resin_material_var = tk.StringVar(value=resin_material_name)
        resin_material_data = cfg.get("materials", "Resin", resin_material_name, default={})
        self.resin_density_var = tk.StringVar(value=str(resin_material_data.get("density", 1.1)))
        self.resin_price_l_var = tk.StringVar(value=str(resin_material_data.get("price_per_liter", 1200.0)))
        self.resin_price_kg_var = tk.StringVar(value=str(resin_material_data.get("price_per_kg", 0.0)))
        self.resin_layer_height_var = tk.StringVar(value=str(resin_defaults.get("layer_height_mm", 0.05)))
        self.resin_exposure_var = tk.StringVar(value=str(resin_defaults.get("exposure_time_s", 2.5)))
        self.resin_lift_var = tk.StringVar(value=str(resin_defaults.get("lift_time_s", 3.0)))
        self.resin_base_layers_var = tk.StringVar(value=str(resin_defaults.get("base_layers", 6)))
        self.resin_base_exposure_var = tk.StringVar(value=str(resin_defaults.get("base_exposure_time_s", 30.0)))
        self.resin_base_lift_var = tk.StringVar(value=str(resin_defaults.get("base_lift_time_s", 6.0)))
        self.resin_hollow_var = tk.StringVar(value=str(resin_defaults.get("hollow_percentage", 0.0)))
        self.resin_wall_var = tk.StringVar(value=str(resin_defaults.get("wall_thickness_mm", 2.0)))

        # Costos generales
        cost_defaults = cfg.get("costs", default={})
        self.cost_electricity_var = tk.StringVar(value=str(cost_defaults.get("electricity_mxn_per_kwh", 2.8)))
        self.cost_power_var = tk.StringVar(value=str(cost_defaults.get("printer_power_w", 220.0)))
        self.cost_printer_var = tk.StringVar(value=str(cost_defaults.get("printer_cost_mxn", 12000.0)))
        self.cost_life_var = tk.StringVar(value=str(cost_defaults.get("printer_life_hours", 5000.0)))
        self.cost_maintenance_var = tk.StringVar(value=str(cost_defaults.get("maintenance_per_hour", 5.0)))
        self.cost_labor_var = tk.StringVar(value=str(cost_defaults.get("labor_rate_mxn_per_hour", 120.0)))
        self.cost_prep_var = tk.StringVar(value=str(cost_defaults.get("prep_time_minutes", 20.0)))

        finance_defaults = cfg.get("finance", default={})
        self.finance_margin_var = tk.StringVar(value=str(finance_defaults.get("margin_percent", 0.3)))
        self.finance_tax_var = tk.StringVar(value=str(finance_defaults.get("tax_percent", 0.16)))

        # Preset management
        self.fdm_preset_var = tk.StringVar()
        self.resin_preset_var = tk.StringVar()

    def _build_ui(self) -> None:
        notebook = ttk.Notebook(self)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        self.notebook = notebook

        self._build_file_tab()
        self._build_fdm_tab()
        self._build_resin_tab()
        self._build_cost_tab()
        self._build_summary_tab()

    # ------------------------------------------------------------------
    def _build_file_tab(self) -> None:
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="Archivo STL")

        instructions = ttk.Label(
            frame,
            text="Carga un archivo STL para calcular volumen, dimensiones y verificar si la malla es cerrada.",
            wraplength=480,
            justify=tk.LEFT,
        )
        instructions.grid(row=0, column=0, columnspan=2, sticky="w", pady=(10, 10))

        load_button = ttk.Button(frame, text="Cargar STL", command=self.load_stl)
        load_button.grid(row=1, column=0, sticky="w", padx=(0, 10))

        refresh_button = ttk.Button(frame, text="Recargar último", command=self.reload_stl)
        refresh_button.grid(row=1, column=1, sticky="w")

        info_frame = ttk.LabelFrame(frame, text="Datos del archivo")
        info_frame.grid(row=2, column=0, columnspan=2, pady=20, sticky="nsew")

        labels = [
            ("Nombre:", "name"),
            ("Volumen mm³:", "volume_mm3"),
            ("Volumen cm³:", "volume_cm3"),
            ("Bounding box (mm):", "bbox"),
            ("Malla cerrada:", "watertight"),
        ]
        for row, (label_text, key) in enumerate(labels):
            ttk.Label(info_frame, text=label_text).grid(row=row, column=0, sticky="w", padx=8, pady=4)
            ttk.Label(info_frame, textvariable=self.file_vars[key]).grid(row=row, column=1, sticky="w", padx=8, pady=4)

        info_frame.columnconfigure(1, weight=1)

    # ------------------------------------------------------------------
    def _build_fdm_tab(self) -> None:
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="FDM")

        materials = list(self.config_manager.get("materials", "FDM", default={}).keys())

        material_frame = ttk.LabelFrame(frame, text="Material")
        material_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)

        material_combo = LabeledCombobox(
            material_frame,
            text="Material",
            textvariable=self.fdm_material_var,
            values=materials,
            tooltip="Selecciona el material para usar sus densidades y costos",
        )
        material_combo.pack(anchor="w", pady=4)
        material_combo.combobox.bind("<<ComboboxSelected>>", lambda _: self.on_fdm_material_change())
        self.fdm_material_combo = material_combo

        LabeledEntry(
            material_frame,
            text="Densidad (g/cm³)",
            textvariable=self.fdm_density_var,
            validate="float",
        ).pack(anchor="w", pady=4)
        LabeledEntry(
            material_frame,
            text="Precio (MXN/kg)",
            textvariable=self.fdm_price_var,
            validate="float",
        ).pack(anchor="w", pady=4)

        ttk.Button(material_frame, text="Guardar material", command=self.save_fdm_material).pack(anchor="e", pady=(6, 0))

        params_frame = ttk.LabelFrame(frame, text="Parámetros de impresión")
        params_frame.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)

        for widget in [
            LabeledEntry(params_frame, "Infill (%)", self.fdm_infill_var, validate="float"),
            LabeledEntry(params_frame, "Capa (mm)", self.fdm_layer_height_var, validate="float"),
            LabeledEntry(params_frame, "Perímetros", self.fdm_perimeters_var, validate="int"),
            LabeledEntry(params_frame, "Boquilla (mm)", self.fdm_nozzle_var, validate="float"),
            LabeledEntry(params_frame, "Ancho línea (mm)", self.fdm_line_width_var, validate="float"),
            LabeledEntry(params_frame, "Factor casco", self.fdm_shell_factor_var, validate="float"),
            LabeledEntry(params_frame, "Factor tapas", self.fdm_top_bottom_factor_var, validate="float"),
            LabeledEntry(params_frame, "Overhead capa (s)", self.fdm_overhead_var, validate="float"),
        ]:
            widget.pack(anchor="w", pady=3)

        speeds_frame = ttk.LabelFrame(frame, text="Velocidades (mm/s) - Bambu Lab A1")
        speeds_frame.grid(row=1, column=0, columnspan=2, sticky="nsew", padx=10, pady=10)

        for widget in [
            LabeledEntry(speeds_frame, "Perímetros", self.fdm_speed_perimeter_var, validate="float"),
            LabeledEntry(speeds_frame, "Infill", self.fdm_speed_infill_var, validate="float"),
            LabeledEntry(speeds_frame, "Tapas/Pisos", self.fdm_speed_top_var, validate="float"),
        ]:
            widget.pack(anchor="w", pady=3)

        preset_frame = ttk.LabelFrame(frame, text="Presets")
        preset_frame.grid(row=2, column=0, columnspan=2, sticky="nsew", padx=10, pady=10)

        ttk.Label(preset_frame, text="Preset disponible").grid(row=0, column=0, sticky="w")
        self.fdm_preset_combo = ttk.Combobox(preset_frame, textvariable=self.fdm_preset_var, state="readonly")
        self.fdm_preset_combo.grid(row=0, column=1, padx=5, pady=4, sticky="ew")
        ttk.Button(preset_frame, text="Cargar", command=self.load_fdm_preset).grid(row=0, column=2, padx=5)

        ttk.Label(preset_frame, text="Nombre nuevo").grid(row=1, column=0, sticky="w")
        self.fdm_preset_name = tk.StringVar()
        ttk.Entry(preset_frame, textvariable=self.fdm_preset_name).grid(row=1, column=1, padx=5, pady=4, sticky="ew")
        ttk.Button(preset_frame, text="Guardar preset", command=self.save_fdm_preset).grid(row=1, column=2, padx=5)

        ttk.Button(frame, text="Guardar como predeterminado", command=self.save_fdm_defaults).grid(
            row=3, column=1, sticky="e", padx=10, pady=(0, 10)
        )

        frame.columnconfigure(1, weight=1)
        preset_frame.columnconfigure(1, weight=1)
        self.refresh_preset_list("FDM")

    # ------------------------------------------------------------------
    def _build_resin_tab(self) -> None:
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="Resina")

        materials = list(self.config_manager.get("materials", "Resin", default={}).keys())

        material_frame = ttk.LabelFrame(frame, text="Material")
        material_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)

        material_combo = LabeledCombobox(
            material_frame,
            text="Material",
            textvariable=self.resin_material_var,
            values=materials,
            tooltip="Selecciona la resina utilizada",
        )
        material_combo.pack(anchor="w", pady=4)
        material_combo.combobox.bind("<<ComboboxSelected>>", lambda _: self.on_resin_material_change())
        self.resin_material_combo = material_combo

        LabeledEntry(material_frame, "Densidad (g/cm³)", self.resin_density_var, validate="float").pack(anchor="w", pady=3)
        LabeledEntry(material_frame, "Precio (MXN/L)", self.resin_price_l_var, validate="float").pack(anchor="w", pady=3)
        LabeledEntry(material_frame, "Precio (MXN/kg)", self.resin_price_kg_var, validate="float").pack(anchor="w", pady=3)
        ttk.Button(material_frame, text="Guardar material", command=self.save_resin_material).pack(anchor="e", pady=(6, 0))

        params_frame = ttk.LabelFrame(frame, text="Parámetros de impresión")
        params_frame.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)

        for widget in [
            LabeledEntry(params_frame, "Capa (mm)", self.resin_layer_height_var, validate="float"),
            LabeledEntry(params_frame, "Exposición (s)", self.resin_exposure_var, validate="float"),
            LabeledEntry(params_frame, "Elevación (s)", self.resin_lift_var, validate="float"),
            LabeledEntry(params_frame, "Capas base", self.resin_base_layers_var, validate="int"),
            LabeledEntry(params_frame, "Exposición base (s)", self.resin_base_exposure_var, validate="float"),
            LabeledEntry(params_frame, "Elevación base (s)", self.resin_base_lift_var, validate="float"),
            LabeledEntry(params_frame, "Hueco (%)", self.resin_hollow_var, validate="float"),
            LabeledEntry(params_frame, "Pared (mm)", self.resin_wall_var, validate="float"),
        ]:
            widget.pack(anchor="w", pady=3)

        preset_frame = ttk.LabelFrame(frame, text="Presets")
        preset_frame.grid(row=1, column=0, columnspan=2, sticky="nsew", padx=10, pady=10)

        ttk.Label(preset_frame, text="Preset disponible").grid(row=0, column=0, sticky="w")
        self.resin_preset_combo = ttk.Combobox(preset_frame, textvariable=self.resin_preset_var, state="readonly")
        self.resin_preset_combo.grid(row=0, column=1, padx=5, pady=4, sticky="ew")
        ttk.Button(preset_frame, text="Cargar", command=self.load_resin_preset).grid(row=0, column=2, padx=5)

        ttk.Label(preset_frame, text="Nombre nuevo").grid(row=1, column=0, sticky="w")
        self.resin_preset_name = tk.StringVar()
        ttk.Entry(preset_frame, textvariable=self.resin_preset_name).grid(row=1, column=1, padx=5, pady=4, sticky="ew")
        ttk.Button(preset_frame, text="Guardar preset", command=self.save_resin_preset).grid(row=1, column=2, padx=5)

        ttk.Button(frame, text="Guardar como predeterminado", command=self.save_resin_defaults).grid(
            row=2, column=1, sticky="e", padx=10, pady=(0, 10)
        )

        frame.columnconfigure(1, weight=1)
        preset_frame.columnconfigure(1, weight=1)
        self.refresh_preset_list("Resin")

    # ------------------------------------------------------------------
    def _build_cost_tab(self) -> None:
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="Costos & Finanzas")

        costs_frame = ttk.LabelFrame(frame, text="Costos operativos")
        costs_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)

        for widget in [
            LabeledEntry(costs_frame, "Electricidad (MXN/kWh)", self.cost_electricity_var, validate="float"),
            LabeledEntry(costs_frame, "Consumo impresora (W)", self.cost_power_var, validate="float"),
            LabeledEntry(costs_frame, "Costo impresora (MXN)", self.cost_printer_var, validate="float"),
            LabeledEntry(costs_frame, "Vida útil (h)", self.cost_life_var, validate="float"),
            LabeledEntry(costs_frame, "Mantenimiento (MXN/h)", self.cost_maintenance_var, validate="float"),
            LabeledEntry(costs_frame, "Mano de obra (MXN/h)", self.cost_labor_var, validate="float"),
            LabeledEntry(costs_frame, "Preparación (min)", self.cost_prep_var, validate="float"),
        ]:
            widget.pack(anchor="w", pady=3)

        finance_frame = ttk.LabelFrame(frame, text="Finanzas")
        finance_frame.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)

        LabeledEntry(finance_frame, "Margen (%)", self.finance_margin_var, validate="float").pack(anchor="w", pady=3)
        LabeledEntry(finance_frame, "IVA (%)", self.finance_tax_var, validate="float").pack(anchor="w", pady=3)

        ttk.Button(frame, text="Guardar configuración", command=self.save_costs).grid(
            row=1, column=1, sticky="e", padx=10, pady=(0, 10)
        )

        frame.columnconfigure(0, weight=1)
        frame.columnconfigure(1, weight=1)

    # ------------------------------------------------------------------
    def _build_summary_tab(self) -> None:
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="Resumen & Cotización")

        mode_frame = ttk.LabelFrame(frame, text="Modo")
        mode_frame.grid(row=0, column=0, sticky="w", padx=10, pady=10)
        ttk.Radiobutton(mode_frame, text="FDM", variable=self.mode_var, value="FDM").pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(mode_frame, text="Resina", variable=self.mode_var, value="Resina").pack(
            side=tk.LEFT, padx=5
        )

        client_frame = ttk.LabelFrame(frame, text="Cliente y notas")
        client_frame.grid(row=1, column=0, columnspan=2, sticky="ew", padx=10, pady=10)
        ttk.Label(client_frame, text="Cliente").grid(row=0, column=0, sticky="w")
        ttk.Entry(client_frame, textvariable=self.client_name_var).grid(row=0, column=1, sticky="ew", padx=6)
        ttk.Label(client_frame, text="Notas").grid(row=1, column=0, sticky="nw")
        self.notes_widget = scrolledtext.ScrolledText(client_frame, height=4)
        self.notes_widget.grid(row=1, column=1, sticky="ew", padx=6, pady=4)
        client_frame.columnconfigure(1, weight=1)

        summary_frame = ttk.LabelFrame(frame, text="Resumen")
        summary_frame.grid(row=2, column=0, columnspan=2, sticky="nsew", padx=10, pady=10)
        self.summary_text = scrolledtext.ScrolledText(summary_frame, height=16)
        self.summary_text.pack(fill=tk.BOTH, expand=True)
        self.summary_text.configure(state=tk.DISABLED)

        button_frame = ttk.Frame(frame)
        button_frame.grid(row=3, column=0, columnspan=2, sticky="e", padx=10, pady=10)
        ttk.Button(button_frame, text="Calcular cotización", command=self.calculate_quote).grid(row=0, column=0, padx=5)
        ttk.Button(button_frame, text="Exportar PDF", command=self.export_pdf).grid(row=0, column=1, padx=5)
        ttk.Button(button_frame, text="Exportar CSV", command=self.export_csv).grid(row=0, column=2, padx=5)
        ttk.Button(button_frame, text="Copiar resumen", command=self.copy_summary).grid(row=0, column=3, padx=5)

        frame.rowconfigure(2, weight=1)
        frame.columnconfigure(1, weight=1)

    # ------------------------------------------------------------------
    def load_stl(self) -> None:
        path = filedialog.askopenfilename(filetypes=[("Archivos STL", "*.stl"), ("Todos", "*.*")])
        if not path:
            return
        try:
            mesh = load_mesh(path)
        except Exception as exc:  # noqa: BLE001 - mostrar error al usuario
            messagebox.showerror("Error al cargar STL", str(exc))
            return

        self.mesh_info = mesh
        self.update_mesh_info(mesh)

        if not mesh.is_watertight:
            messagebox.showwarning(
                "Advertencia",
                "El STL no está cerrado; el volumen podría ser impreciso.",
            )

    def reload_stl(self) -> None:
        if not self.mesh_info:
            messagebox.showinfo("Información", "No hay archivo cargado aún.")
            return
        try:
            mesh = load_mesh(str(self.mesh_info.file_path))
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror("Error al recargar", str(exc))
            return
        self.mesh_info = mesh
        self.update_mesh_info(mesh)

    def update_mesh_info(self, mesh: MeshInfo) -> None:
        self.file_vars["name"].set(mesh.file_name)
        self.file_vars["volume_mm3"].set(f"{mesh.volume_mm3:,.0f}")
        self.file_vars["volume_cm3"].set(f"{mesh.volume_cm3:.2f}")
        bbox = mesh.bbox_dimensions_mm
        self.file_vars["bbox"].set(f"{bbox[0]:.1f} x {bbox[1]:.1f} x {bbox[2]:.1f}")
        self.file_vars["watertight"].set("Sí" if mesh.is_watertight else "No")

    # ------------------------------------------------------------------
    def on_fdm_material_change(self) -> None:
        material = self.fdm_material_var.get()
        data = self.config_manager.get("materials", "FDM", material, default={})
        if data:
            self.fdm_density_var.set(str(data.get("density", self.fdm_density_var.get())))
            self.fdm_price_var.set(str(data.get("price_per_kg", self.fdm_price_var.get())))

    def save_fdm_material(self) -> None:
        material = self.fdm_material_var.get().strip()
        if not material:
            messagebox.showerror("Error", "El nombre del material no puede estar vacío.")
            return
        density = safe_float(self.fdm_density_var.get(), 1.0)
        price = safe_float(self.fdm_price_var.get(), 0.0)
        materials = self.config_manager.get("materials", "FDM", default={})
        materials[material] = {"density": density, "price_per_kg": price}
        self.config_manager.set(materials, "materials", "FDM")
        self.config_manager.save()
        messagebox.showinfo("Guardado", "Material actualizado correctamente.")
        self.refresh_materials("FDM")

    def save_fdm_defaults(self) -> None:
        defaults = {
            "material": self.fdm_material_var.get(),
            "infill_percentage": safe_float(self.fdm_infill_var.get(), 20.0),
            "layer_height_mm": safe_float(self.fdm_layer_height_var.get(), 0.2),
            "perimeters": int(safe_float(self.fdm_perimeters_var.get(), 2)),
            "nozzle_diameter_mm": safe_float(self.fdm_nozzle_var.get(), 0.4),
            "line_width_mm": safe_float(self.fdm_line_width_var.get(), 0.42),
            "shell_factor": safe_float(self.fdm_shell_factor_var.get(), 0.18),
            "top_bottom_factor": safe_float(self.fdm_top_bottom_factor_var.get(), 0.05),
            "overhead_per_layer_s": safe_float(self.fdm_overhead_var.get(), 3.0),
        }
        speeds = {
            "profile": "Bambu Lab A1",
            "perimeter_mm_s": safe_float(self.fdm_speed_perimeter_var.get(), 150.0),
            "infill_mm_s": safe_float(self.fdm_speed_infill_var.get(), 200.0),
            "top_bottom_mm_s": safe_float(self.fdm_speed_top_var.get(), 150.0),
        }
        self.config_manager.set(defaults, "fdm", "defaults")
        self.config_manager.set(speeds, "fdm", "speeds")
        messagebox.showinfo("Guardado", "Parámetros FDM predeterminados actualizados.")

    def load_fdm_preset(self) -> None:
        name = self.fdm_preset_var.get()
        if not name:
            return
        try:
            data = self.config_manager.load_preset("FDM", name)
        except FileNotFoundError:
            messagebox.showerror("Error", "Preset no encontrado.")
            return
        self.apply_fdm_preset(data)

    def apply_fdm_preset(self, data: Dict[str, Any]) -> None:
        self.fdm_material_var.set(data.get("material", self.fdm_material_var.get()))
        self.fdm_density_var.set(str(data.get("density", self.fdm_density_var.get())))
        self.fdm_price_var.set(str(data.get("price_per_kg", self.fdm_price_var.get())))
        self.fdm_infill_var.set(str(data.get("infill_percentage", self.fdm_infill_var.get())))
        self.fdm_layer_height_var.set(str(data.get("layer_height_mm", self.fdm_layer_height_var.get())))
        self.fdm_perimeters_var.set(str(data.get("perimeters", self.fdm_perimeters_var.get())))
        self.fdm_nozzle_var.set(str(data.get("nozzle_diameter_mm", self.fdm_nozzle_var.get())))
        self.fdm_line_width_var.set(str(data.get("line_width_mm", self.fdm_line_width_var.get())))
        self.fdm_shell_factor_var.set(str(data.get("shell_factor", self.fdm_shell_factor_var.get())))
        self.fdm_top_bottom_factor_var.set(str(data.get("top_bottom_factor", self.fdm_top_bottom_factor_var.get())))
        self.fdm_overhead_var.set(str(data.get("overhead_per_layer_s", self.fdm_overhead_var.get())))
        self.fdm_speed_perimeter_var.set(str(data.get("perimeter_mm_s", self.fdm_speed_perimeter_var.get())))
        self.fdm_speed_infill_var.set(str(data.get("infill_mm_s", self.fdm_speed_infill_var.get())))
        self.fdm_speed_top_var.set(str(data.get("top_bottom_mm_s", self.fdm_speed_top_var.get())))

    def save_fdm_preset(self) -> None:
        name = self.fdm_preset_name.get().strip()
        if not name:
            messagebox.showerror("Error", "Especifica un nombre para el preset.")
            return
        data = {
            "material": self.fdm_material_var.get(),
            "density": safe_float(self.fdm_density_var.get(), 1.0),
            "price_per_kg": safe_float(self.fdm_price_var.get(), 0.0),
            "infill_percentage": safe_float(self.fdm_infill_var.get(), 20.0),
            "layer_height_mm": safe_float(self.fdm_layer_height_var.get(), 0.2),
            "perimeters": safe_float(self.fdm_perimeters_var.get(), 3),
            "nozzle_diameter_mm": safe_float(self.fdm_nozzle_var.get(), 0.4),
            "line_width_mm": safe_float(self.fdm_line_width_var.get(), 0.42),
            "shell_factor": safe_float(self.fdm_shell_factor_var.get(), 0.18),
            "top_bottom_factor": safe_float(self.fdm_top_bottom_factor_var.get(), 0.05),
            "overhead_per_layer_s": safe_float(self.fdm_overhead_var.get(), 3.0),
            "perimeter_mm_s": safe_float(self.fdm_speed_perimeter_var.get(), 150.0),
            "infill_mm_s": safe_float(self.fdm_speed_infill_var.get(), 200.0),
            "top_bottom_mm_s": safe_float(self.fdm_speed_top_var.get(), 150.0),
        }
        self.config_manager.save_preset("FDM", name, data)
        messagebox.showinfo("Guardado", "Preset FDM almacenado.")
        self.refresh_preset_list("FDM")

    # ------------------------------------------------------------------
    def on_resin_material_change(self) -> None:
        material = self.resin_material_var.get()
        data = self.config_manager.get("materials", "Resin", material, default={})
        if data:
            self.resin_density_var.set(str(data.get("density", self.resin_density_var.get())))
            self.resin_price_l_var.set(str(data.get("price_per_liter", self.resin_price_l_var.get())))
            if "price_per_kg" in data:
                self.resin_price_kg_var.set(str(data.get("price_per_kg", self.resin_price_kg_var.get())))

    def save_resin_material(self) -> None:
        material = self.resin_material_var.get().strip()
        if not material:
            messagebox.showerror("Error", "El nombre del material no puede estar vacío.")
            return
        density = safe_float(self.resin_density_var.get(), 1.1)
        price_l = safe_float(self.resin_price_l_var.get(), 0.0)
        price_kg = safe_float(self.resin_price_kg_var.get(), 0.0)
        materials = self.config_manager.get("materials", "Resin", default={})
        materials[material] = {
            "density": density,
            "price_per_liter": price_l,
            "price_per_kg": price_kg,
        }
        self.config_manager.set(materials, "materials", "Resin")
        self.config_manager.save()
        messagebox.showinfo("Guardado", "Material de resina actualizado.")
        self.refresh_materials("Resin")

    def save_resin_defaults(self) -> None:
        defaults = {
            "material": self.resin_material_var.get(),
            "layer_height_mm": safe_float(self.resin_layer_height_var.get(), 0.05),
            "exposure_time_s": safe_float(self.resin_exposure_var.get(), 2.5),
            "lift_time_s": safe_float(self.resin_lift_var.get(), 3.0),
            "base_layers": int(safe_float(self.resin_base_layers_var.get(), 6)),
            "base_exposure_time_s": safe_float(self.resin_base_exposure_var.get(), 30.0),
            "base_lift_time_s": safe_float(self.resin_base_lift_var.get(), 6.0),
            "hollow_percentage": safe_float(self.resin_hollow_var.get(), 0.0),
            "wall_thickness_mm": safe_float(self.resin_wall_var.get(), 2.0),
        }
        self.config_manager.set(defaults, "resin", "defaults")
        messagebox.showinfo("Guardado", "Parámetros de resina predeterminados actualizados.")

    def load_resin_preset(self) -> None:
        name = self.resin_preset_var.get()
        if not name:
            return
        try:
            data = self.config_manager.load_preset("Resin", name)
        except FileNotFoundError:
            messagebox.showerror("Error", "Preset no encontrado.")
            return
        self.apply_resin_preset(data)

    def apply_resin_preset(self, data: Dict[str, Any]) -> None:
        self.resin_material_var.set(data.get("material", self.resin_material_var.get()))
        self.resin_density_var.set(str(data.get("density", self.resin_density_var.get())))
        self.resin_price_l_var.set(str(data.get("price_per_liter", self.resin_price_l_var.get())))
        self.resin_price_kg_var.set(str(data.get("price_per_kg", self.resin_price_kg_var.get())))
        self.resin_layer_height_var.set(str(data.get("layer_height_mm", self.resin_layer_height_var.get())))
        self.resin_exposure_var.set(str(data.get("exposure_time_s", self.resin_exposure_var.get())))
        self.resin_lift_var.set(str(data.get("lift_time_s", self.resin_lift_var.get())))
        self.resin_base_layers_var.set(str(data.get("base_layers", self.resin_base_layers_var.get())))
        self.resin_base_exposure_var.set(str(data.get("base_exposure_time_s", self.resin_base_exposure_var.get())))
        self.resin_base_lift_var.set(str(data.get("base_lift_time_s", self.resin_base_lift_var.get())))
        self.resin_hollow_var.set(str(data.get("hollow_percentage", self.resin_hollow_var.get())))
        self.resin_wall_var.set(str(data.get("wall_thickness_mm", self.resin_wall_var.get())))

    def save_resin_preset(self) -> None:
        name = self.resin_preset_name.get().strip()
        if not name:
            messagebox.showerror("Error", "Especifica un nombre para el preset.")
            return
        data = {
            "material": self.resin_material_var.get(),
            "density": safe_float(self.resin_density_var.get(), 1.1),
            "price_per_liter": safe_float(self.resin_price_l_var.get(), 0.0),
            "price_per_kg": safe_float(self.resin_price_kg_var.get(), 0.0),
            "layer_height_mm": safe_float(self.resin_layer_height_var.get(), 0.05),
            "exposure_time_s": safe_float(self.resin_exposure_var.get(), 2.5),
            "lift_time_s": safe_float(self.resin_lift_var.get(), 3.0),
            "base_layers": safe_float(self.resin_base_layers_var.get(), 6),
            "base_exposure_time_s": safe_float(self.resin_base_exposure_var.get(), 30.0),
            "base_lift_time_s": safe_float(self.resin_base_lift_var.get(), 6.0),
            "hollow_percentage": safe_float(self.resin_hollow_var.get(), 0.0),
            "wall_thickness_mm": safe_float(self.resin_wall_var.get(), 2.0),
        }
        self.config_manager.save_preset("Resin", name, data)
        messagebox.showinfo("Guardado", "Preset de resina almacenado.")
        self.refresh_preset_list("Resin")

    # ------------------------------------------------------------------
    def refresh_materials(self, mode: str) -> None:
        if mode == "FDM":
            materials_dict = self.config_manager.get("materials", "FDM", default={})
            materials = list(materials_dict.keys())
            if materials:
                if self.fdm_material_var.get() not in materials:
                    self.fdm_material_var.set(materials[0])
                self.fdm_material_combo.set_values(materials)
                self.on_fdm_material_change()
        else:
            materials_dict = self.config_manager.get("materials", "Resin", default={})
            materials = list(materials_dict.keys())
            if materials:
                if self.resin_material_var.get() not in materials:
                    self.resin_material_var.set(materials[0])
                self.resin_material_combo.set_values(materials)
                self.on_resin_material_change()
        self.refresh_preset_list(mode)

    def refresh_preset_list(self, mode: str) -> None:
        presets = self.config_manager.list_presets(mode)
        if mode == "FDM":
            self.fdm_preset_combo.configure(values=presets)
        else:
            self.resin_preset_combo.configure(values=presets)

    # ------------------------------------------------------------------
    def save_costs(self) -> None:
        costs = {
            "electricity_mxn_per_kwh": safe_float(self.cost_electricity_var.get(), 2.8),
            "printer_power_w": safe_float(self.cost_power_var.get(), 200.0),
            "printer_cost_mxn": safe_float(self.cost_printer_var.get(), 10000.0),
            "printer_life_hours": safe_float(self.cost_life_var.get(), 4000.0),
            "maintenance_per_hour": safe_float(self.cost_maintenance_var.get(), 5.0),
            "labor_rate_mxn_per_hour": safe_float(self.cost_labor_var.get(), 100.0),
            "prep_time_minutes": safe_float(self.cost_prep_var.get(), 15.0),
        }
        finance = {
            "margin_percent": safe_float(self.finance_margin_var.get(), 0.25),
            "tax_percent": safe_float(self.finance_tax_var.get(), 0.16),
        }
        self.config_manager.set(costs, "costs")
        self.config_manager.set(finance, "finance")
        messagebox.showinfo("Guardado", "Costos y finanzas actualizados.")

    # ------------------------------------------------------------------
    def gather_cost_settings(self) -> CostSettings:
        return CostSettings(
            electricity_mxn_per_kwh=safe_float(self.cost_electricity_var.get(), 2.8),
            printer_power_w=safe_float(self.cost_power_var.get(), 220.0),
            printer_cost_mxn=safe_float(self.cost_printer_var.get(), 12000.0),
            printer_life_hours=safe_float(self.cost_life_var.get(), 5000.0),
            maintenance_per_hour=safe_float(self.cost_maintenance_var.get(), 5.0),
            labor_rate_mxn_per_hour=safe_float(self.cost_labor_var.get(), 120.0),
            prep_time_minutes=safe_float(self.cost_prep_var.get(), 20.0),
        )

    def gather_finance_settings(self) -> FinanceSettings:
        return FinanceSettings(
            margin_percent=safe_float(self.finance_margin_var.get(), 0.3),
            tax_percent=safe_float(self.finance_tax_var.get(), 0.16),
        )

    def gather_fdm_parameters(self) -> FDMParameters:
        return FDMParameters(
            material_name=self.fdm_material_var.get(),
            density_g_cm3=safe_float(self.fdm_density_var.get(), 1.24),
            price_per_kg=safe_float(self.fdm_price_var.get(), 450.0),
            infill_percentage=safe_float(self.fdm_infill_var.get(), 20.0),
            layer_height_mm=safe_float(self.fdm_layer_height_var.get(), 0.2),
            perimeters=int(safe_float(self.fdm_perimeters_var.get(), 2)),
            nozzle_diameter_mm=safe_float(self.fdm_nozzle_var.get(), 0.4),
            line_width_mm=safe_float(self.fdm_line_width_var.get(), 0.42),
            shell_factor=safe_float(self.fdm_shell_factor_var.get(), 0.18),
            top_bottom_factor=safe_float(self.fdm_top_bottom_factor_var.get(), 0.05),
            overhead_per_layer_s=safe_float(self.fdm_overhead_var.get(), 3.0),
            perimeter_speed_mm_s=safe_float(self.fdm_speed_perimeter_var.get(), 150.0),
            infill_speed_mm_s=safe_float(self.fdm_speed_infill_var.get(), 200.0),
            top_bottom_speed_mm_s=safe_float(self.fdm_speed_top_var.get(), 150.0),
        )

    def gather_resin_parameters(self) -> ResinParameters:
        return ResinParameters(
            material_name=self.resin_material_var.get(),
            density_g_cm3=safe_float(self.resin_density_var.get(), 1.1),
            price_per_liter=safe_float(self.resin_price_l_var.get(), 0.0),
            price_per_kg=safe_float(self.resin_price_kg_var.get(), 0.0),
            layer_height_mm=safe_float(self.resin_layer_height_var.get(), 0.05),
            exposure_time_s=safe_float(self.resin_exposure_var.get(), 2.5),
            lift_time_s=safe_float(self.resin_lift_var.get(), 3.0),
            base_layers=int(safe_float(self.resin_base_layers_var.get(), 6)),
            base_exposure_time_s=safe_float(self.resin_base_exposure_var.get(), 30.0),
            base_lift_time_s=safe_float(self.resin_base_lift_var.get(), 6.0),
            hollow_percentage=safe_float(self.resin_hollow_var.get(), 0.0),
            wall_thickness_mm=safe_float(self.resin_wall_var.get(), 2.0),
        )

    # ------------------------------------------------------------------
    def calculate_quote(self) -> None:
        if not self.mesh_info:
            messagebox.showerror("Error", "Carga un archivo STL antes de calcular.")
            return

        costs = self.gather_cost_settings()
        finance = self.gather_finance_settings()

        mode = self.mode_var.get()
        try:
            if mode == "FDM":
                params = self.gather_fdm_parameters()
                estimate = estimate_fdm_costs(self.mesh_info, params, costs, finance)
                self.display_fdm_summary(self.mesh_info, params, estimate)
            else:
                params = self.gather_resin_parameters()
                estimate = estimate_resin_costs(self.mesh_info, params, costs, finance)
                self.display_resin_summary(self.mesh_info, params, estimate)
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror("Error", f"No se pudo calcular la cotización: {exc}")
            return

    def display_fdm_summary(self, mesh: MeshInfo, params: FDMParameters, estimate: FDMEstimate) -> None:
        costs = estimate.cost_breakdown
        summary = [
            "=== Cotización FDM ===",
            f"Archivo: {mesh.file_name}",
            f"Volumen modelo: {mesh.volume_cm3:.2f} cm³",
            f"Dimensiones: X={mesh.bbox_dimensions_mm[0]:.1f} mm, Y={mesh.bbox_dimensions_mm[1]:.1f} mm, Z={mesh.bbox_dimensions_mm[2]:.1f} mm",
            f"Material: {params.material_name} (densidad {params.density_g_cm3:.2f} g/cm³)",
            f"Capa: {params.layer_height_mm:.2f} mm | Perímetros: {params.perimeters}",
            f"Infill: {params.infill_percentage:.1f} %",
            f"Factor casco: {params.shell_factor:.2f} - Factor tapas: {params.top_bottom_factor:.2f}",
            f"Volumen equivalente: {estimate.extruded_volume_cm3:.2f} cm³",
            f"Masa estimada: {estimate.mass_g:.1f} g",
            f"Tiempo estimado: {estimate.print_time_text}",
            f"Longitud de extrusión: {estimate.total_length_mm:.0f} mm",
            "--- Costos ---",
            f"Material: ${costs['material']:.2f}",
            f"Electricidad: ${costs['electricity']:.2f}",
            f"Depreciación/Mantenimiento: ${costs['depreciation']:.2f}",
            f"Mano de obra: ${costs['labor']:.2f}",
            f"Subtotal: ${costs['subtotal']:.2f}",
            f"Margen aplicado: ${costs['margin_amount']:.2f}",
            f"IVA: ${costs['tax_amount']:.2f}",
            f"Precio sugerido: ${costs['total']:.2f}",
        ]
        self.write_summary(summary)
        self.last_quote = self.build_quote_data("FDM", mesh, summary, costs, estimate.print_time_text, params)

    def display_resin_summary(self, mesh: MeshInfo, params: ResinParameters, estimate: ResinEstimate) -> None:
        costs = estimate.cost_breakdown
        summary = [
            "=== Cotización Resina ===",
            f"Archivo: {mesh.file_name}",
            f"Volumen modelo: {mesh.volume_cm3:.2f} cm³",
            f"Dimensiones: X={mesh.bbox_dimensions_mm[0]:.1f} mm, Y={mesh.bbox_dimensions_mm[1]:.1f} mm, Z={mesh.bbox_dimensions_mm[2]:.1f} mm",
            f"Material: {params.material_name} (densidad {params.density_g_cm3:.2f} g/cm³)",
            f"Capa: {params.layer_height_mm:.3f} mm | Exposición: {params.exposure_time_s:.1f} s",
            f"Capas calculadas: {estimate.layers}",
            f"Volumen usado: {estimate.volume_used_cm3:.2f} cm³",
            f"Masa estimada: {estimate.mass_g:.1f} g",
            f"Tiempo estimado: {estimate.print_time_text}",
            "--- Costos ---",
            f"Material: ${costs['material']:.2f}",
            f"Electricidad: ${costs['electricity']:.2f}",
            f"Depreciación/Mantenimiento: ${costs['depreciation']:.2f}",
            f"Mano de obra: ${costs['labor']:.2f}",
            f"Subtotal: ${costs['subtotal']:.2f}",
            f"Margen aplicado: ${costs['margin_amount']:.2f}",
            f"IVA: ${costs['tax_amount']:.2f}",
            f"Precio sugerido: ${costs['total']:.2f}",
        ]
        self.write_summary(summary)
        self.last_quote = self.build_quote_data("Resina", mesh, summary, costs, estimate.print_time_text, params)

    def write_summary(self, lines: list[str]) -> None:
        self.summary_text.configure(state=tk.NORMAL)
        self.summary_text.delete("1.0", tk.END)
        self.summary_text.insert(tk.END, "\n".join(lines))
        self.summary_text.configure(state=tk.DISABLED)

    def build_quote_data(
        self,
        mode: str,
        mesh: MeshInfo,
        summary_lines: list[str],
        costs: Dict[str, float],
        print_time_text: str,
        params: Any,
    ) -> Dict[str, Any]:
        return {
            "mode": mode,
            "client_name": self.client_name_var.get(),
            "notes": self.notes_widget.get("1.0", tk.END).strip(),
            "file": {
                "name": mesh.file_name,
                "volume_mm3": mesh.volume_mm3,
                "volume_cm3": mesh.volume_cm3,
                "bbox": mesh.bbox_dimensions_mm,
            },
            "parameters": self.parameters_to_dict(params),
            "costs": costs,
            "summary": summary_lines,
            "print_time": print_time_text,
        }

    def parameters_to_dict(self, params: Any) -> Dict[str, Any]:
        try:
            data = asdict(params)
        except TypeError:
            data = dict(params)
        return {k: f"{v}" for k, v in data.items()}

    # ------------------------------------------------------------------
    def export_pdf(self) -> None:
        if not self.last_quote:
            messagebox.showinfo("Información", "Genera primero una cotización.")
            return
        path = filedialog.asksaveasfilename(defaultextension=".pdf", filetypes=[("PDF", "*.pdf")])
        if not path:
            return
        export_quote_to_pdf(path, self.last_quote)
        messagebox.showinfo("Exportación", "PDF generado correctamente.")

    def export_csv(self) -> None:
        if not self.last_quote:
            messagebox.showinfo("Información", "Genera primero una cotización.")
            return
        path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV", "*.csv")])
        if not path:
            return
        export_quote_to_csv(path, self.last_quote)
        messagebox.showinfo("Exportación", "CSV generado correctamente.")

    def copy_summary(self) -> None:
        content = self.summary_text.get("1.0", tk.END).strip()
        if not content:
            messagebox.showinfo("Información", "No hay resumen para copiar.")
            return
        self.clipboard_clear()
        self.clipboard_append(content)
        messagebox.showinfo("Copiado", "Resumen enviado al portapapeles.")

    # ------------------------------------------------------------------
    def on_exit(self) -> None:
        self.config_manager.save()
        self.destroy()


if __name__ == "__main__":
    app = CotizadorApp()
    app.mainloop()
