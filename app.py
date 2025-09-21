"""Aplicación de escritorio para cotizar impresiones 3D."""

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk
from typing import Any, Dict, Optional

ROOT_DIR = Path(__file__).resolve().parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from config import ConfigStorage
from export.csv_export import export_quote_to_csv
from export.pdf_export import export_quote_to_pdf
from models.geometry import MeshInfo, load_mesh
from models.printers import Printer, PrinterManager
from pricing import (
    CostBreakdown,
    CostInputs,
    FinancialContext,
    MaterialInfo,
    PrinterContext,
    calculate_costs,
    grams_from_volume,
)
from ui.components.widgets import LabeledCombobox, LabeledEntry


def parse_float(value: str, default: float = 0.0) -> float:
    """Parse ``value`` as float returning ``default`` on failure."""

    try:
        return float(value)
    except (TypeError, ValueError):
        return default


class CotizadorApp(tk.Tk):
    """Ventana principal del cotizador."""

    def __init__(self) -> None:
        super().__init__()
        self.title("Cotizador 3D")
        self.geometry("1100x760")

        self.storage = ConfigStorage()
        self.printer_manager = PrinterManager(self.storage)
        self.mesh_info: Optional[MeshInfo] = None
        self.breakdown: Optional[CostBreakdown] = None
        self.last_export_payload: Optional[Dict[str, Any]] = None

        self._init_variables()
        self._build_ui()
        self.refresh_materials()
        self.refresh_printer_options()

    # ------------------------------------------------------------------
    def _init_variables(self) -> None:
        cfg = self.storage.data
        materiales = cfg.get("materiales", {})
        primera_material = next(iter(materiales)) if materiales else ""

        self.moneda = cfg.get("moneda", "MXN")

        # Proyecto
        self.project_name_var = tk.StringVar()
        self.tipo_var = tk.StringVar(value="filamento")
        self.printer_var = tk.StringVar()
        self.mass_var = tk.StringVar(value="0.0")
        self.time_hours_var = tk.StringVar(value="0.0")
        mano_cfg = cfg.get("mano_obra", {})
        self.prep_minutes_var = tk.StringVar(value=str(mano_cfg.get("post_min", 0.0)))
        self.supervision_hours_var = tk.StringVar(value=str(mano_cfg.get("supervision_h", 0.0)))
        self.costo_stl_var = tk.StringVar(value="0.0")
        self.extras_var = tk.StringVar(value="0.0")
        self.suggested_mass_var = tk.StringVar(value="0.0")

        # STL info variables
        self.stl_file_var = tk.StringVar(value="Sin archivo")
        self.stl_volume_var = tk.StringVar(value="0.0 cm³")
        self.stl_volume_mm_var = tk.StringVar(value="0 mm³")
        self.stl_bbox_var = tk.StringVar(value="0 x 0 x 0 mm")
        self.stl_watertight_var = tk.StringVar(value="-")

        # Materiales
        self.material_name_var = tk.StringVar(value=primera_material)
        self.material_edit_name_var = tk.StringVar(value=primera_material)
        material_info = materiales.get(primera_material, {})
        self.material_density_var = tk.StringVar(
            value=str(material_info.get("densidad_g_cm3", 0.0))
        )
        self.material_price_var = tk.StringVar(value=str(material_info.get("precio_kg", 0.0)))

        # Costos globales
        elec_cfg = cfg.get("electricidad", {})
        self.kwh_price_var = tk.StringVar(value=str(elec_cfg.get("kwh_precio", 0.0)))
        self.costo_hora_var = tk.StringVar(value=str(mano_cfg.get("costo_hora", 0.0)))
        self.post_min_config_var = tk.StringVar(value=str(mano_cfg.get("post_min", 0.0)))
        self.supervision_default_var = tk.StringVar(value=str(mano_cfg.get("supervision_h", 0.0)))

        porcentajes = cfg.get("porcentajes", {})
        self.merma_var = tk.StringVar(value=f"{porcentajes.get('merma', 0.0) * 100:.2f}")
        self.riesgo_var = tk.StringVar(value=f"{porcentajes.get('riesgo', 0.0) * 100:.2f}")
        self.ganancia_var = tk.StringVar(value=f"{porcentajes.get('ganancia', 0.0) * 100:.2f}")
        self.iva_var = tk.StringVar(value=f"{porcentajes.get('iva', 0.0) * 100:.2f}")

        # Cliente y notas
        self.client_name_var = tk.StringVar()
        self.client_email_var = tk.StringVar()
        self.client_phone_var = tk.StringVar()
        self.notes_text: Optional[scrolledtext.ScrolledText] = None

    # ------------------------------------------------------------------
    def _build_ui(self) -> None:
        notebook = ttk.Notebook(self)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        self.notebook = notebook

        self.project_tab = ttk.Frame(notebook)
        notebook.add(self.project_tab, text="Proyecto")
        self._build_project_tab(self.project_tab)

        self.material_tab = ttk.Frame(notebook)
        notebook.add(self.material_tab, text="Material")
        self._build_material_tab(self.material_tab)

        self.costs_tab = ttk.Frame(notebook)
        notebook.add(self.costs_tab, text="Costos & Porcentajes")
        self._build_costs_tab(self.costs_tab)

        self.printers_tab = ttk.Frame(notebook)
        notebook.add(self.printers_tab, text="Impresoras")
        self._build_printers_tab(self.printers_tab)

        self.client_tab = ttk.Frame(notebook)
        notebook.add(self.client_tab, text="Cliente & Exportar")
        self._build_client_tab(self.client_tab)

    # ------------------------------------------------------------------
    def _build_project_tab(self, frame: ttk.Frame) -> None:
        frame.columnconfigure(1, weight=1)

        header = ttk.Label(frame, text="Datos generales del proyecto", font=("TkDefaultFont", 12, "bold"))
        header.grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 10))

        ttk.Label(frame, text="Nombre del proyecto:").grid(row=1, column=0, sticky="w")
        ttk.Entry(frame, textvariable=self.project_name_var, width=40).grid(
            row=1, column=1, sticky="ew", padx=5, pady=2
        )

        type_combo = LabeledCombobox(
            frame,
            text="Tipo de impresión:",
            textvariable=self.tipo_var,
            values=["filamento", "resina"],
        )
        type_combo.grid(row=2, column=0, columnspan=2, sticky="w", pady=2)
        type_combo.combobox.bind("<<ComboboxSelected>>", lambda _: self.refresh_printer_options())

        self.printer_combo = LabeledCombobox(
            frame,
            text="Impresora:",
            textvariable=self.printer_var,
            values=[],
        )
        self.printer_combo.grid(row=3, column=0, columnspan=2, sticky="w", pady=2)

        ttk.Button(
            frame,
            text="Administrar impresoras",
            command=lambda: self.notebook.select(self.printers_tab),
        ).grid(row=3, column=2, sticky="e", padx=5)

        entries = ttk.Frame(frame)
        entries.grid(row=4, column=0, columnspan=3, sticky="ew", pady=10)
        entries.columnconfigure(1, weight=1)

        LabeledEntry(entries, "Masa utilizada (g):", self.mass_var, validate="float").grid(
            row=0, column=0, sticky="w", padx=2, pady=2
        )
        LabeledEntry(entries, "Horas de impresión:", self.time_hours_var, validate="float").grid(
            row=0, column=1, sticky="w", padx=2, pady=2
        )
        LabeledEntry(entries, "Min. mano de obra:", self.prep_minutes_var, validate="float").grid(
            row=1, column=0, sticky="w", padx=2, pady=2
        )
        LabeledEntry(entries, "Horas de supervisión:", self.supervision_hours_var, validate="float").grid(
            row=1, column=1, sticky="w", padx=2, pady=2
        )
        LabeledEntry(entries, "Costo STL:", self.costo_stl_var, validate="float").grid(
            row=2, column=0, sticky="w", padx=2, pady=2
        )
        LabeledEntry(entries, "Extras:", self.extras_var, validate="float").grid(
            row=2, column=1, sticky="w", padx=2, pady=2
        )

        ttk.Button(entries, text="Restablecer minutos", command=self._reset_prep_minutes).grid(
            row=1, column=2, sticky="w", padx=5
        )

        stl_frame = ttk.LabelFrame(frame, text="Archivo STL (opcional)")
        stl_frame.grid(row=5, column=0, columnspan=3, sticky="ew", pady=10)
        stl_frame.columnconfigure(1, weight=1)

        ttk.Button(stl_frame, text="Cargar STL", command=self.load_stl).grid(
            row=0, column=0, sticky="w", padx=5, pady=5
        )
        ttk.Button(stl_frame, text="Usar volumen para masa", command=self.estimate_mass_from_stl).grid(
            row=0, column=1, sticky="w", padx=5, pady=5
        )

        ttk.Label(stl_frame, textvariable=self.stl_file_var).grid(row=1, column=0, columnspan=2, sticky="w", padx=5)
        ttk.Label(stl_frame, textvariable=self.stl_volume_var).grid(row=2, column=0, sticky="w", padx=5)
        ttk.Label(stl_frame, textvariable=self.stl_volume_mm_var).grid(row=2, column=1, sticky="w", padx=5)
        ttk.Label(stl_frame, textvariable=self.stl_bbox_var).grid(row=3, column=0, columnspan=2, sticky="w", padx=5)
        ttk.Label(stl_frame, textvariable=self.stl_watertight_var).grid(row=4, column=0, columnspan=2, sticky="w", padx=5)

        ttk.Label(stl_frame, text="Masa sugerida desde STL (g):").grid(row=5, column=0, sticky="w", padx=5, pady=(5, 0))
        ttk.Label(stl_frame, textvariable=self.suggested_mass_var, font=("TkDefaultFont", 10, "bold")).grid(
            row=5, column=1, sticky="w", padx=5, pady=(5, 0)
        )

    # ------------------------------------------------------------------
    def _build_material_tab(self, frame: ttk.Frame) -> None:
        frame.columnconfigure(1, weight=1)

        ttk.Label(frame, text="Catálogo de materiales", font=("TkDefaultFont", 12, "bold")).grid(
            row=0, column=0, columnspan=2, sticky="w", pady=(0, 10)
        )

        self.material_combo = LabeledCombobox(
            frame,
            text="Selecciona material:",
            textvariable=self.material_name_var,
            values=[],
        )
        self.material_combo.grid(row=1, column=0, columnspan=2, sticky="w", pady=2)
        self.material_combo.combobox.bind("<<ComboboxSelected>>", lambda _: self._on_material_selected())

        ttk.Label(frame, text="Nombre para guardar:").grid(row=2, column=0, sticky="w")
        ttk.Entry(frame, textvariable=self.material_edit_name_var, width=30).grid(
            row=2, column=1, sticky="w", pady=2
        )

        LabeledEntry(frame, "Densidad (g/cm³):", self.material_density_var, validate="float").grid(
            row=3, column=0, columnspan=2, sticky="w", pady=2
        )
        LabeledEntry(frame, "Precio por kg:", self.material_price_var, validate="float").grid(
            row=4, column=0, columnspan=2, sticky="w", pady=2
        )

        buttons = ttk.Frame(frame)
        buttons.grid(row=5, column=0, columnspan=2, sticky="w", pady=10)
        ttk.Button(buttons, text="Guardar material", command=self.save_material).pack(side=tk.LEFT, padx=5)
        ttk.Button(buttons, text="Eliminar material", command=self.delete_material).pack(side=tk.LEFT, padx=5)

    # ------------------------------------------------------------------
    def _build_costs_tab(self, frame: ttk.Frame) -> None:
        frame.columnconfigure(1, weight=1)

        ttk.Label(frame, text="Parámetros globales", font=("TkDefaultFont", 12, "bold")).grid(
            row=0, column=0, columnspan=2, sticky="w", pady=(0, 10)
        )

        LabeledEntry(frame, "Precio kWh:", self.kwh_price_var, validate="float").grid(
            row=1, column=0, sticky="w", pady=2
        )
        LabeledEntry(frame, "Costo hora-hombre:", self.costo_hora_var, validate="float").grid(
            row=1, column=1, sticky="w", pady=2
        )
        LabeledEntry(frame, "Min. post-proceso default:", self.post_min_config_var, validate="float").grid(
            row=2, column=0, sticky="w", pady=2
        )
        LabeledEntry(frame, "Horas supervisión default:", self.supervision_default_var, validate="float").grid(
            row=2, column=1, sticky="w", pady=2
        )

        ttk.Label(frame, text="Porcentajes (%)", font=("TkDefaultFont", 11, "bold")).grid(
            row=3, column=0, columnspan=2, sticky="w", pady=(10, 5)
        )

        LabeledEntry(frame, "Merma:", self.merma_var, validate="float").grid(row=4, column=0, sticky="w", pady=2)
        LabeledEntry(frame, "Riesgo:", self.riesgo_var, validate="float").grid(row=4, column=1, sticky="w", pady=2)
        LabeledEntry(frame, "Ganancia:", self.ganancia_var, validate="float").grid(row=5, column=0, sticky="w", pady=2)
        LabeledEntry(frame, "IVA:", self.iva_var, validate="float").grid(row=5, column=1, sticky="w", pady=2)

        ttk.Button(frame, text="Guardar configuración", command=self.save_cost_settings).grid(
            row=6, column=0, columnspan=2, sticky="e", pady=10
        )

    # ------------------------------------------------------------------
    def _build_printers_tab(self, frame: ttk.Frame) -> None:
        frame.columnconfigure(0, weight=1)
        ttk.Label(frame, text="Impresoras registradas", font=("TkDefaultFont", 12, "bold")).pack(
            anchor="w", pady=(0, 10)
        )

        columns = ("tipo", "costo", "vida", "potencia")
        tree = ttk.Treeview(frame, columns=columns, show="headings", height=10)
        tree.heading("tipo", text="Tipo")
        tree.heading("costo", text="Costo (MXN)")
        tree.heading("vida", text="Vida útil (h)")
        tree.heading("potencia", text="Potencia (W)")
        tree.column("tipo", width=120)
        tree.column("costo", width=120)
        tree.column("vida", width=120)
        tree.column("potencia", width=120)
        tree.pack(fill=tk.BOTH, expand=True)
        self.printer_tree = tree

        buttons = ttk.Frame(frame)
        buttons.pack(fill=tk.X, pady=10)
        ttk.Button(buttons, text="Agregar", command=self.add_printer).pack(side=tk.LEFT, padx=5)
        ttk.Button(buttons, text="Editar", command=self.edit_printer).pack(side=tk.LEFT, padx=5)
        ttk.Button(buttons, text="Eliminar", command=self.delete_printer).pack(side=tk.LEFT, padx=5)

        self.refresh_printer_list()

    # ------------------------------------------------------------------
    def _build_client_tab(self, frame: ttk.Frame) -> None:
        frame.columnconfigure(1, weight=1)
        ttk.Label(frame, text="Datos del cliente", font=("TkDefaultFont", 12, "bold")).grid(
            row=0, column=0, columnspan=2, sticky="w", pady=(0, 10)
        )

        ttk.Label(frame, text="Nombre:").grid(row=1, column=0, sticky="w")
        ttk.Entry(frame, textvariable=self.client_name_var, width=40).grid(
            row=1, column=1, sticky="ew", pady=2
        )
        ttk.Label(frame, text="Correo:").grid(row=2, column=0, sticky="w")
        ttk.Entry(frame, textvariable=self.client_email_var, width=40).grid(
            row=2, column=1, sticky="ew", pady=2
        )
        ttk.Label(frame, text="Celular:").grid(row=3, column=0, sticky="w")
        ttk.Entry(frame, textvariable=self.client_phone_var, width=40).grid(
            row=3, column=1, sticky="ew", pady=2
        )

        ttk.Label(frame, text="Notas / Condiciones:").grid(row=4, column=0, sticky="nw", pady=(10, 2))
        notes = scrolledtext.ScrolledText(frame, width=60, height=6)
        notes.grid(row=4, column=1, sticky="ew", pady=(10, 2))
        self.notes_text = notes

        action_frame = ttk.Frame(frame)
        action_frame.grid(row=5, column=0, columnspan=2, sticky="ew", pady=10)
        ttk.Button(action_frame, text="Calcular cotización", command=self.calculate_quote).pack(
            side=tk.LEFT, padx=5
        )
        ttk.Button(action_frame, text="Exportar PDF", command=self.export_pdf).pack(side=tk.LEFT, padx=5)
        ttk.Button(action_frame, text="Exportar CSV", command=self.export_csv).pack(side=tk.LEFT, padx=5)

        summary_frame = ttk.LabelFrame(frame, text="Resumen de costos")
        summary_frame.grid(row=6, column=0, columnspan=2, sticky="nsew")
        frame.rowconfigure(6, weight=1)
        summary_frame.columnconfigure(0, weight=1)

        tree = ttk.Treeview(summary_frame, columns=("concepto", "valor"), show="headings", height=12)
        tree.heading("concepto", text="Concepto")
        tree.heading("valor", text="Monto")
        tree.column("concepto", width=220)
        tree.column("valor", width=160)
        tree.pack(fill=tk.BOTH, expand=True)
        self.summary_tree = tree

        self.total_label_var = tk.StringVar(value="Total: 0.00")
        ttk.Label(summary_frame, textvariable=self.total_label_var, font=("TkDefaultFont", 12, "bold")).pack(
            anchor="e", padx=10, pady=5
        )

    # ------------------------------------------------------------------
    def _reset_prep_minutes(self) -> None:
        self.prep_minutes_var.set(self.post_min_config_var.get())
        self.supervision_hours_var.set(self.supervision_default_var.get())

    # ------------------------------------------------------------------
    def refresh_materials(self) -> None:
        cfg = self.storage.data
        materials = cfg.get("materiales", {})
        values = list(materials.keys())
        self.material_combo.set_values(values)
        if not values:
            self.material_name_var.set("")
            self.material_edit_name_var.set("")
            self.material_density_var.set("0.0")
            self.material_price_var.set("0.0")
            return

        if self.material_name_var.get() not in values:
            self.material_name_var.set(values[0])
        if self.material_edit_name_var.get() == "":
            self.material_edit_name_var.set(self.material_name_var.get())
        self._on_material_selected()

    # ------------------------------------------------------------------
    def _on_material_selected(self) -> None:
        cfg = self.storage.data
        material_name = self.material_name_var.get()
        material_data = cfg.get("materiales", {}).get(material_name)
        if not material_data:
            return
        self.material_edit_name_var.set(material_name)
        self.material_density_var.set(str(material_data.get("densidad_g_cm3", 0.0)))
        self.material_price_var.set(str(material_data.get("precio_kg", 0.0)))
        self.update_suggested_mass()

    # ------------------------------------------------------------------
    def update_suggested_mass(self) -> None:
        if not self.mesh_info:
            self.suggested_mass_var.set("0.0")
            return
        density = parse_float(self.material_density_var.get(), 0.0)
        grams = grams_from_volume(self.mesh_info.volume_mm3, density)
        self.suggested_mass_var.set(f"{grams:.2f}")

    # ------------------------------------------------------------------
    def refresh_printer_options(self) -> None:
        tipo = self.tipo_var.get() or "filamento"
        printers = self.printer_manager.list_printers(tipo=tipo) if tipo else []
        names = [p.nombre for p in printers]
        self.printer_combo.set_values(names)
        if names:
            if self.printer_var.get() not in names:
                self.printer_var.set(names[0])
        else:
            self.printer_var.set("")
        self.refresh_printer_list()

    # ------------------------------------------------------------------
    def refresh_printer_list(self) -> None:
        if not hasattr(self, "printer_tree"):
            return
        self.printer_tree.delete(*self.printer_tree.get_children())
        for printer in self.printer_manager.list_printers():
            self.printer_tree.insert(
                "",
                tk.END,
                iid=printer.nombre,
                values=(
                    printer.tipo,
                    f"{printer.costo_equipo:.2f}",
                    f"{printer.vida_util_horas:.1f}",
                    f"{printer.potencia_w:.1f}",
                ),
            )

    # ------------------------------------------------------------------
    def load_stl(self) -> None:
        file_path = filedialog.askopenfilename(
            title="Seleccionar STL",
            filetypes=(("Archivos STL", "*.stl"), ("Todos", "*.*")),
        )
        if not file_path:
            return
        try:
            mesh = load_mesh(file_path)
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror("Error", f"No se pudo cargar el STL: {exc}")
            return
        self.mesh_info = mesh
        self.stl_file_var.set(f"Archivo: {mesh.file_name}")
        self.stl_volume_var.set(f"Volumen: {mesh.volume_cm3:.2f} cm³")
        self.stl_volume_mm_var.set(f"Volumen: {mesh.volume_mm3:.0f} mm³")
        bbox = mesh.bbox_dimensions_mm
        self.stl_bbox_var.set(f"Dimensiones: {bbox[0]:.1f} x {bbox[1]:.1f} x {bbox[2]:.1f} mm")
        watertight = "Malla cerrada" if mesh.is_watertight else "Advertencia: malla abierta"
        self.stl_watertight_var.set(watertight)
        if not mesh.is_watertight:
            messagebox.showwarning(
                "STL no manifold",
                "El STL no está cerrado; el volumen puede ser impreciso.",
            )
        self.update_suggested_mass()

    # ------------------------------------------------------------------
    def estimate_mass_from_stl(self) -> None:
        if not self.mesh_info:
            messagebox.showinfo("Sin STL", "Carga un STL para estimar la masa.")
            return
        density = parse_float(self.material_density_var.get(), 0.0)
        if density <= 0:
            messagebox.showwarning("Material inválido", "Define una densidad de material válida.")
            return
        grams = grams_from_volume(self.mesh_info.volume_mm3, density)
        self.mass_var.set(f"{grams:.2f}")
        self.suggested_mass_var.set(f"{grams:.2f}")

    # ------------------------------------------------------------------
    def save_material(self) -> None:
        name = self.material_edit_name_var.get().strip()
        if not name:
            messagebox.showwarning("Nombre requerido", "Indica un nombre para el material.")
            return
        density = parse_float(self.material_density_var.get(), 0.0)
        price = parse_float(self.material_price_var.get(), 0.0)
        if density <= 0 or price < 0:
            messagebox.showwarning(
                "Valores inválidos",
                "Revisa la densidad y el precio del material.",
            )
            return
        self.storage.upsert_material(
            name,
            {"densidad_g_cm3": density, "precio_kg": price},
        )
        self.material_name_var.set(name)
        self.refresh_materials()
        messagebox.showinfo("Material guardado", "El material se guardó correctamente.")

    # ------------------------------------------------------------------
    def delete_material(self) -> None:
        name = self.material_name_var.get().strip()
        if not name:
            return
        cfg = self.storage.data
        materials = cfg.get("materiales", {})
        if len(materials) <= 1:
            messagebox.showwarning(
                "No permitido",
                "Debe existir al menos un material en el catálogo.",
            )
            return
        if messagebox.askyesno("Confirmar", f"¿Eliminar el material '{name}'?"):
            self.storage.delete_material(name)
            self.material_name_var.set("")
            self.refresh_materials()

    # ------------------------------------------------------------------
    def save_cost_settings(self) -> None:
        kwh = parse_float(self.kwh_price_var.get(), 0.0)
        costo_hora = parse_float(self.costo_hora_var.get(), 0.0)
        post_min = parse_float(self.post_min_config_var.get(), 0.0)
        supervision_default = parse_float(self.supervision_default_var.get(), 0.0)

        merma = parse_float(self.merma_var.get(), 0.0) / 100.0
        riesgo = parse_float(self.riesgo_var.get(), 0.0) / 100.0
        ganancia = parse_float(self.ganancia_var.get(), 0.0) / 100.0
        iva = parse_float(self.iva_var.get(), 0.0) / 100.0

        self.storage.update_section("electricidad", {"kwh_precio": kwh})
        self.storage.update_section(
            "mano_obra",
            {
                "costo_hora": costo_hora,
                "post_min": post_min,
                "supervision_h": supervision_default,
            },
        )
        self.storage.update_section(
            "porcentajes",
            {
                "merma": merma,
                "riesgo": riesgo,
                "ganancia": ganancia,
                "iva": iva,
            },
        )

        self.prep_minutes_var.set(f"{post_min:.2f}")
        self.supervision_hours_var.set(f"{supervision_default:.2f}")
        messagebox.showinfo("Configuración", "Parámetros guardados correctamente.")

    # ------------------------------------------------------------------
    def _collect_material_info(self) -> Optional[MaterialInfo]:
        material_name = self.material_name_var.get()
        cfg = self.storage.data
        data = cfg.get("materiales", {}).get(material_name)
        if not data:
            messagebox.showerror("Material inválido", "Selecciona un material válido.")
            return None
        return MaterialInfo(
            nombre=material_name,
            densidad_g_cm3=float(data.get("densidad_g_cm3", 0.0)),
            precio_kg=float(data.get("precio_kg", 0.0)),
        )

    # ------------------------------------------------------------------
    def _collect_printer(self) -> Optional[Printer]:
        printer_name = self.printer_var.get()
        if not printer_name:
            messagebox.showerror("Impresora requerida", "Agrega y selecciona una impresora del tipo indicado.")
            return None
        printer = self.printer_manager.get(printer_name)
        if not printer:
            messagebox.showerror("Impresora inválida", "La impresora seleccionada no existe.")
            return None
        return printer

    # ------------------------------------------------------------------
    def _build_financial_context(self) -> FinancialContext:
        return FinancialContext(
            precio_kwh=parse_float(self.kwh_price_var.get(), 0.0),
            costo_hora_hombre=parse_float(self.costo_hora_var.get(), 0.0),
            merma=parse_float(self.merma_var.get(), 0.0) / 100.0,
            riesgo=parse_float(self.riesgo_var.get(), 0.0) / 100.0,
            ganancia=parse_float(self.ganancia_var.get(), 0.0) / 100.0,
            iva=parse_float(self.iva_var.get(), 0.0) / 100.0,
        )

    # ------------------------------------------------------------------
    def calculate_quote(self) -> None:
        material = self._collect_material_info()
        if not material:
            return
        printer = self._collect_printer()
        if not printer:
            return

        mass_g = parse_float(self.mass_var.get(), 0.0)
        horas = parse_float(self.time_hours_var.get(), 0.0)
        minutos_mano = parse_float(self.prep_minutes_var.get(), 0.0)
        horas_supervision = parse_float(self.supervision_hours_var.get(), 0.0)
        costo_stl = parse_float(self.costo_stl_var.get(), 0.0)
        extras = parse_float(self.extras_var.get(), 0.0)

        financial = self._build_financial_context()
        inputs = CostInputs(
            masa_g=mass_g,
            horas_impresion=horas,
            minutos_mano_obra=minutos_mano,
            horas_supervision=horas_supervision,
            costo_stl=costo_stl,
            extras=extras,
        )
        breakdown = calculate_costs(
            material,
            PrinterContext(
                nombre=printer.nombre,
                tipo=printer.tipo,
                costo_equipo=printer.costo_equipo,
                vida_util_horas=printer.vida_util_horas,
                potencia_w=printer.potencia_w,
            ),
            financial,
            inputs,
        )
        self.breakdown = breakdown

        self._update_summary(breakdown)
        self.last_export_payload = self._build_export_payload(material, printer, breakdown, financial, inputs)
        messagebox.showinfo("Cotización", "Cálculo completado.")

    # ------------------------------------------------------------------
    def _update_summary(self, breakdown: CostBreakdown) -> None:
        for item in self.summary_tree.get_children():
            self.summary_tree.delete(item)
        currency = self.moneda
        fmt = lambda value: f"{currency} ${value:,.2f}"
        rows = [
            ("Material", breakdown.material),
            ("Energía eléctrica", breakdown.energia),
            ("Depreciación", breakdown.depreciacion),
            ("Mano de obra", breakdown.mano_obra),
            ("Costo STL", breakdown.costo_stl),
            ("Extras", breakdown.extras),
            ("Subtotal base", breakdown.subtotal_base),
            ("Merma", breakdown.merma),
            ("Subtotal tras merma", breakdown.subtotal_post_merma),
            ("Riesgo", breakdown.riesgo),
            ("Subtotal tras riesgo", breakdown.subtotal_post_riesgo),
            ("Ganancia", breakdown.ganancia),
            ("Total sin IVA", breakdown.total_sin_iva),
            ("IVA", breakdown.iva),
        ]
        for concept, value in rows:
            self.summary_tree.insert("", tk.END, values=(concept, fmt(value)))
        self.total_label_var.set(f"Total: {fmt(breakdown.total)}")

    # ------------------------------------------------------------------
    def _build_export_payload(
        self,
        material: MaterialInfo,
        printer: Printer,
        breakdown: CostBreakdown,
        financial: FinancialContext,
        inputs: CostInputs,
    ) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "fecha": datetime.now(),
            "moneda": self.moneda,
            "cliente": {
                "nombre": self.client_name_var.get().strip(),
                "correo": self.client_email_var.get().strip(),
                "celular": self.client_phone_var.get().strip(),
            },
            "proyecto": {
                "nombre": self.project_name_var.get().strip(),
                "tipo": self.tipo_var.get(),
                "impresora": printer.nombre,
                "material": material.nombre,
                "masa_g": inputs.masa_g,
                "horas_impresion": inputs.horas_impresion,
                "minutos_mano_obra": inputs.minutos_mano_obra,
                "horas_supervision": inputs.horas_supervision,
                "costo_stl": inputs.costo_stl,
                "extras": inputs.extras,
            },
            "costos": breakdown.to_dict(),
            "porcentajes": {
                "merma": financial.merma,
                "riesgo": financial.riesgo,
                "ganancia": financial.ganancia,
                "iva": financial.iva,
            },
            "impresora": {
                "costo_equipo": printer.costo_equipo,
                "vida_util_horas": printer.vida_util_horas,
                "potencia_w": printer.potencia_w,
            },
            "notas": self.notes_text.get("1.0", tk.END).strip() if self.notes_text else "",
        }
        if self.mesh_info:
            payload["stl"] = {
                "archivo": self.mesh_info.file_name,
                "volumen_mm3": self.mesh_info.volume_mm3,
                "volumen_cm3": self.mesh_info.volume_cm3,
                "bbox": self.mesh_info.bbox_dimensions_mm,
                "watertight": self.mesh_info.is_watertight,
            }
        return payload

    # ------------------------------------------------------------------
    def export_pdf(self) -> None:
        if not self.last_export_payload:
            messagebox.showinfo("Sin datos", "Calcula la cotización antes de exportar.")
            return
        client_name = self.last_export_payload["cliente"].get("nombre") or "Cliente"
        default_name = f"Cotizacion_{client_name.replace(' ', '_')}_{datetime.now():%Y%m%d}.pdf"
        file_path = filedialog.asksaveasfilename(
            title="Guardar PDF",
            defaultextension=".pdf",
            initialfile=default_name,
            filetypes=(("PDF", "*.pdf"),),
        )
        if not file_path:
            return
        export_quote_to_pdf(file_path, self.last_export_payload)
        messagebox.showinfo("Exportación", f"PDF generado en {file_path}")

    # ------------------------------------------------------------------
    def export_csv(self) -> None:
        if not self.last_export_payload:
            messagebox.showinfo("Sin datos", "Calcula la cotización antes de exportar.")
            return
        client_name = self.last_export_payload["cliente"].get("nombre") or "Cliente"
        default_name = f"Cotizacion_{client_name.replace(' ', '_')}_{datetime.now():%Y%m%d}.csv"
        file_path = filedialog.asksaveasfilename(
            title="Guardar CSV",
            defaultextension=".csv",
            initialfile=default_name,
            filetypes=(("CSV", "*.csv"),),
        )
        if not file_path:
            return
        export_quote_to_csv(file_path, self.last_export_payload)
        messagebox.showinfo("Exportación", f"CSV generado en {file_path}")

    # ------------------------------------------------------------------
    def add_printer(self) -> None:
        dialog = PrinterDialog(self, title="Agregar impresora")
        self.wait_window(dialog)
        if not dialog.result:
            return
        self.printer_manager.save_printer(dialog.result)
        self.refresh_printer_options()
        messagebox.showinfo("Impresoras", "Impresora guardada correctamente.")

    # ------------------------------------------------------------------
    def edit_printer(self) -> None:
        selection = self.printer_tree.selection()
        if not selection:
            messagebox.showinfo("Editar", "Selecciona una impresora para editar.")
            return
        nombre = selection[0]
        printer = self.printer_manager.get(nombre)
        if not printer:
            return
        dialog = PrinterDialog(self, title="Editar impresora", printer=printer)
        self.wait_window(dialog)
        if not dialog.result:
            return
        if dialog.result.nombre != nombre:
            self.printer_manager.delete_printer(nombre)
        self.printer_manager.save_printer(dialog.result)
        self.refresh_printer_options()
        messagebox.showinfo("Impresoras", "Impresora actualizada.")

    # ------------------------------------------------------------------
    def delete_printer(self) -> None:
        selection = self.printer_tree.selection()
        if not selection:
            messagebox.showinfo("Eliminar", "Selecciona una impresora.")
            return
        nombre = selection[0]
        if messagebox.askyesno("Confirmar", f"¿Eliminar la impresora '{nombre}'?"):
            self.printer_manager.delete_printer(nombre)
            self.refresh_printer_options()


class PrinterDialog(tk.Toplevel):
    """Diálogo modal para capturar datos de impresora."""

    def __init__(
        self,
        master: tk.Tk,
        *,
        title: str,
        printer: Optional[Printer] = None,
    ) -> None:
        super().__init__(master)
        self.title(title)
        self.resizable(False, False)
        self.result: Optional[Printer] = None

        self.nombre_var = tk.StringVar(value=printer.nombre if printer else "")
        self.tipo_var = tk.StringVar(value=printer.tipo if printer else "filamento")
        self.costo_var = tk.StringVar(value=f"{printer.costo_equipo:.2f}" if printer else "0.0")
        self.vida_var = tk.StringVar(value=f"{printer.vida_util_horas:.1f}" if printer else "0.0")
        self.potencia_var = tk.StringVar(value=f"{printer.potencia_w:.1f}" if printer else "0.0")

        ttk.Label(self, text="Nombre:").grid(row=0, column=0, sticky="w", padx=8, pady=5)
        ttk.Entry(self, textvariable=self.nombre_var, width=30).grid(row=0, column=1, padx=8, pady=5)

        ttk.Label(self, text="Tipo:").grid(row=1, column=0, sticky="w", padx=8, pady=5)
        tipo_combo = ttk.Combobox(
            self,
            textvariable=self.tipo_var,
            values=["filamento", "resina"],
            state="readonly",
        )
        tipo_combo.grid(row=1, column=1, padx=8, pady=5)

        ttk.Label(self, text="Costo equipo (MXN):").grid(row=2, column=0, sticky="w", padx=8, pady=5)
        ttk.Entry(self, textvariable=self.costo_var).grid(row=2, column=1, padx=8, pady=5)

        ttk.Label(self, text="Vida útil (horas):").grid(row=3, column=0, sticky="w", padx=8, pady=5)
        ttk.Entry(self, textvariable=self.vida_var).grid(row=3, column=1, padx=8, pady=5)

        ttk.Label(self, text="Potencia (W):").grid(row=4, column=0, sticky="w", padx=8, pady=5)
        ttk.Entry(self, textvariable=self.potencia_var).grid(row=4, column=1, padx=8, pady=5)

        button_frame = ttk.Frame(self)
        button_frame.grid(row=5, column=0, columnspan=2, pady=10)
        ttk.Button(button_frame, text="Cancelar", command=self.destroy).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Guardar", command=self._on_accept).pack(side=tk.LEFT, padx=5)

        self.transient(master)
        self.grab_set()
        self.protocol("WM_DELETE_WINDOW", self.destroy)

    # ------------------------------------------------------------------
    def _on_accept(self) -> None:
        nombre = self.nombre_var.get().strip()
        if not nombre:
            messagebox.showwarning("Nombre requerido", "Ingresa un nombre para la impresora.", parent=self)
            return
        try:
            costo = float(self.costo_var.get())
            vida = float(self.vida_var.get())
            potencia = float(self.potencia_var.get())
        except ValueError:
            messagebox.showwarning("Valores inválidos", "Revisa los campos numéricos.", parent=self)
            return
        if vida <= 0:
            messagebox.showwarning(
                "Vida útil inválida",
                "La vida útil debe ser mayor a cero.",
                parent=self,
            )
            return
        self.result = Printer(
            nombre=nombre,
            tipo=self.tipo_var.get(),
            costo_equipo=costo,
            vida_util_horas=vida,
            potencia_w=potencia,
        )
        self.destroy()


if __name__ == "__main__":
    app = CotizadorApp()
    app.mainloop()
