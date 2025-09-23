"""Proyecto tab with multi-piece capture."""

from __future__ import annotations

import tkinter as tk
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import List, Optional

from models.cliente import Cliente, ClienteInfo
from models.cotizacion import Cotizacion
from models.impresora import Impresora, PrinterType
from models.material import Material
from models.pieza import (
    Pieza,
    combine_hours_minutes,
    format_hours_minutes,
    split_hours_minutes,
)
from models.geometry import load_mesh
from pricing import (
    FDMHeuristicSettings,
    ResinHeuristicSettings,
    estimate_fdm_mass_time,
    estimate_resin_mass_time,
    grams_from_volume,
)
from storage.config_store import ConfigStore
from storage.clients_store import ClientsStore

from ui.components.widgets import LabeledCombobox, LabeledEntry


@dataclass
class QuoteContext:
    folio: Optional[str]
    proyecto: str
    fecha: str
    tipo: PrinterType
    impresora: Impresora
    material: Material
    precio_material: float
    piezas: List[Pieza]
    cliente: ClienteInfo
    notas: str


class ClientSearchDialog(tk.Toplevel):
    """Modal dialog to search and select a client from the catalog."""

    def __init__(self, master: tk.Widget, clients_store: ClientsStore, initial_query: str = "") -> None:
        super().__init__(master)
        self.title("Buscar cliente")
        self.geometry("700x500")
        self.resizable(False, False)
        self.transient(master)
        self.grab_set()

        self.clients_store = clients_store
        self.result: Optional[Cliente] = None
        self._items: dict[str, Cliente] = {}
        self.query_var = tk.StringVar(value=initial_query)

        container = ttk.Frame(self)
        container.pack(fill=tk.BOTH, expand=True, padx=12, pady=12)
        container.columnconfigure(0, weight=1)
        container.rowconfigure(1, weight=1)

        search_frame = ttk.Frame(container)
        search_frame.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        search_frame.columnconfigure(1, weight=1)
        ttk.Label(search_frame, text="Buscar:").grid(row=0, column=0, padx=(0, 6), sticky="w")
        entry = ttk.Entry(search_frame, textvariable=self.query_var)
        entry.grid(row=0, column=1, sticky="ew")
        entry.bind("<KeyRelease>", lambda _: self._refresh())
        entry.bind("<Return>", self._on_enter)

        columns = ("nombre", "correo", "celular")
        self.tree = ttk.Treeview(container, columns=columns, show="headings")
        self.tree.heading("nombre", text="Nombre")
        self.tree.heading("correo", text="Correo")
        self.tree.heading("celular", text="Celular")
        self.tree.column("nombre", width=240, anchor="w")
        self.tree.column("correo", width=200, anchor="w")
        self.tree.column("celular", width=120, anchor="center")
        self.tree.grid(row=1, column=0, sticky="nsew")
        scrollbar = ttk.Scrollbar(container, orient=tk.VERTICAL, command=self.tree.yview)
        scrollbar.grid(row=1, column=1, sticky="ns")
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.bind("<Double-1>", lambda _: self._accept())

        button_frame = ttk.Frame(container)
        button_frame.grid(row=2, column=0, columnspan=2, pady=(12, 0), sticky="e")
        ttk.Button(button_frame, text="Seleccionar", command=self._accept).pack(side=tk.RIGHT, padx=4)
        ttk.Button(button_frame, text="Cancelar", command=self._cancel).pack(side=tk.RIGHT, padx=4)

        self._refresh()
        entry.focus_set()

    def _refresh(self) -> None:
        query = self.query_var.get()
        matches = self.clients_store.search(query)
        self._items.clear()
        self.tree.delete(*self.tree.get_children())
        for cliente in matches:
            item = self.tree.insert(
                "",
                tk.END,
                values=(cliente.nombre, cliente.correo, cliente.celular),
            )
            self._items[item] = cliente

    def _selected_client(self) -> Optional[Cliente]:
        selection = self.tree.selection()
        if not selection:
            return None
        return self._items.get(selection[0])

    def _accept(self) -> None:
        cliente = self._selected_client()
        if not cliente:
            return
        self.result = cliente
        self.destroy()

    def _cancel(self) -> None:
        self.result = None
        self.destroy()

    def _on_enter(self, _: tk.Event) -> None:
        items = self.tree.get_children()
        if not items:
            return
        if len(items) == 1 or not self.tree.selection():
            self.tree.selection_set(items[0])
        self._accept()

    def show(self) -> Optional[Cliente]:
        self.wait_window(self)
        return self.result


class PieceDialog(tk.Toplevel):
    """Modal dialog to capture or edit a piece."""

    def __init__(
        self,
        master: tk.Widget,
        tipo: PrinterType,
        material: Material,
        prep_min_default: float,
        supervision_default: float,
    ) -> None:
        super().__init__(master)
        self.title("Detalle de pieza")
        self.geometry("900x650")
        self.resizable(False, False)
        self.transient(master)
        self.grab_set()

        self.tipo = tipo
        self.material = material
        self._result: Optional[Pieza] = None
        self.mesh_path: Optional[str] = None
        self.mesh_volume_mm3 = 0.0

        self.nombre_var = tk.StringVar()
        self.cantidad_var = tk.StringVar(value="1")
        self.horas_var = tk.StringVar(value="0")
        self.minutos_var = tk.StringVar(value="0")
        self.masa_var = tk.StringVar(value="0.000")
        self.costo_stl_var = tk.StringVar(value="0.0")
        self.extras_var = tk.StringVar(value="0.0")
        self.prep_var = tk.StringVar(value=f"{prep_min_default:.0f}")
        self.supervision_var = tk.StringVar(value=f"{supervision_default:.1f}")
        self.notas_var = tk.StringVar()

        self.volume_label = tk.StringVar(value="Volumen: 0 cm³")
        self.bbox_label = tk.StringVar(value="Dimensiones: -")
        self.mesh_status_var = tk.StringVar(value="STL no cargado")

        self._build_ui()
        self.protocol("WM_DELETE_WINDOW", self.on_cancel)

    def _build_ui(self) -> None:
        frame = ttk.Frame(self)
        frame.pack(fill=tk.BOTH, expand=True, padx=12, pady=12)

        ttk.Label(frame, text="Nombre de la pieza:").grid(row=0, column=0, sticky="w")
        ttk.Entry(frame, textvariable=self.nombre_var, width=32).grid(row=0, column=1, sticky="ew")

        LabeledEntry(frame, "Cantidad", self.cantidad_var, validate="int").grid(row=1, column=0, sticky="w")
        ttk.Button(frame, text="Cargar STL", command=self.on_load_stl).grid(row=1, column=1, sticky="w")

        time_row = ttk.Frame(frame)
        time_row.grid(row=2, column=0, columnspan=2, sticky="w", pady=(4, 0))
        self.horas_entry = LabeledEntry(time_row, "Horas", self.horas_var, validate="int", width=6)
        self.horas_entry.pack(side=tk.LEFT, padx=(0, 12))
        self.minutos_entry = LabeledEntry(time_row, "Minutos", self.minutos_var, validate="int", width=6)
        self.minutos_entry.pack(side=tk.LEFT, padx=(0, 12))
        self.masa_entry = LabeledEntry(time_row, "Masa (g)", self.masa_var, validate="float", width=10)
        self.masa_entry.pack(side=tk.LEFT, padx=(0, 12))
        self.masa_entry.entry.bind("<FocusOut>", self._format_mass)

        LabeledEntry(frame, "Costo STL", self.costo_stl_var, validate="float").grid(row=3, column=0, sticky="w")
        LabeledEntry(frame, "Extras", self.extras_var, validate="float").grid(row=3, column=1, sticky="w")

        LabeledEntry(frame, "Prep. (min)", self.prep_var, validate="float").grid(row=4, column=0, sticky="w")
        LabeledEntry(frame, "Supervisión (h)", self.supervision_var, validate="float").grid(row=4, column=1, sticky="w")

        ttk.Label(frame, textvariable=self.volume_label).grid(row=5, column=0, columnspan=2, sticky="w")
        ttk.Label(frame, textvariable=self.bbox_label).grid(row=6, column=0, columnspan=2, sticky="w")
        ttk.Label(frame, textvariable=self.mesh_status_var, foreground="gray").grid(row=7, column=0, columnspan=2, sticky="w")

        ttk.Label(frame, text="Notas:").grid(row=8, column=0, sticky="nw")
        ttk.Entry(frame, textvariable=self.notas_var, width=40).grid(row=8, column=1, sticky="ew")

        button_frame = ttk.Frame(frame)
        button_frame.grid(row=9, column=0, columnspan=2, pady=(12, 0))
        ttk.Button(button_frame, text="Aceptar", command=self.on_accept).pack(side=tk.LEFT, padx=4)
        ttk.Button(button_frame, text="Cancelar", command=self.on_cancel).pack(side=tk.LEFT, padx=4)

        self._set_time_fields(0.0)
        self._format_mass()

    def _set_mass(self, mass: float) -> None:
        mass = max(mass, 0.0)
        self.masa_var.set(f"{mass:.3f}")

    def _format_mass(self, *_: object) -> None:
        value = self.masa_var.get().strip()
        if not value:
            self.masa_var.set("0.000")
            return
        try:
            mass = float(value)
        except ValueError:
            return
        self.masa_var.set(f"{mass:.3f}")

    def _set_time_fields(self, total_hours: float) -> None:
        hours, minutes = split_hours_minutes(total_hours)
        self.horas_var.set(str(hours))
        self.minutos_var.set(f"{minutes:02d}")

    def on_load_stl(self) -> None:
        file_path = filedialog.askopenfilename(filetypes=[("Archivos STL", "*.stl")])
        if not file_path:
            return
        try:
            mesh = load_mesh(file_path)
        except Exception as exc:  # pragma: no cover - UI feedback
            messagebox.showerror("Error", str(exc), parent=self)
            return

        self.mesh_path = file_path
        self.mesh_volume_mm3 = mesh.volume_mm3
        masa = grams_from_volume(mesh.volume_mm3, self.material.densidad_g_cm3)
        self.volume_label.set(f"Volumen: {mesh.volume_cm3:.2f} cm³")
        bbox = mesh.bbox_dimensions_mm
        self.bbox_label.set(f"Dimensiones: {bbox[0]:.1f} x {bbox[1]:.1f} x {bbox[2]:.1f} mm")
        status = "STL cerrado" if mesh.is_watertight else "STL no cerrado; revisar volumen"
        self.mesh_status_var.set(status)
        self._set_mass(masa)

        if self.tipo == "filamento":
            heuristics = FDMHeuristicSettings()
            masa_estimada, horas = estimate_fdm_mass_time(mesh, self.material.densidad_g_cm3, heuristics)
            if masa_estimada > 0:
                self._set_mass(masa_estimada)
            self._set_time_fields(horas)
        else:
            heuristics = ResinHeuristicSettings()
            masa_estimada, horas = estimate_resin_mass_time(mesh, self.material.densidad_g_cm3, heuristics)
            if masa_estimada > 0:
                self._set_mass(masa_estimada)
            self._set_time_fields(horas)

    def on_accept(self) -> None:
        try:
            cantidad = int(float(self.cantidad_var.get() or 0))
            if cantidad <= 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("Dato inválido", "La cantidad debe ser un entero positivo.", parent=self)
            return
        try:
            horas = int(self.horas_var.get() or 0)
            minutos = int(self.minutos_var.get() or 0)
        except ValueError:
            messagebox.showerror("Dato inválido", "Horas y minutos deben ser enteros.", parent=self)
            return
        if horas < 0:
            messagebox.showerror("Dato inválido", "Las horas deben ser cero o mayores.", parent=self)
            return
        if minutos < 0:
            messagebox.showerror("Dato inválido", "Los minutos deben ser cero o mayores.", parent=self)
            return
        extra_hours, minutos = divmod(minutos, 60)
        horas += extra_hours
        tiempo_horas = combine_hours_minutes(horas, minutos)
        try:
            masa = float(self.masa_var.get() or 0.0)
            costo_stl = float(self.costo_stl_var.get() or 0.0)
            extras = float(self.extras_var.get() or 0.0)
            prep = float(self.prep_var.get() or 0.0)
            supervision = float(self.supervision_var.get() or 0.0)
        except ValueError:
            messagebox.showerror("Dato inválido", "Verifica los campos numéricos.", parent=self)
            return
        nombre = self.nombre_var.get().strip()
        if not nombre:
            messagebox.showerror("Dato faltante", "Ingresa el nombre de la pieza.", parent=self)
            return
        if masa < 0:
            messagebox.showerror("Dato inválido", "La masa debe ser mayor o igual a cero.", parent=self)
            return

        self._result = Pieza(
            nombre=nombre,
            cantidad=cantidad,
            masa_g=masa,
            horas=horas,
            minutos=minutos,
            tiempo_horas=tiempo_horas,
            costo_stl=costo_stl,
            extras=extras,
            prep_min=prep,
            supervision_h=supervision,
            stl_path=self.mesh_path,
            volumen_mm3=self.mesh_volume_mm3,
            notas=self.notas_var.get().strip() or None,
        )
        self.destroy()

    def on_cancel(self) -> None:
        self._result = None
        self.destroy()

    def edit_piece(self, pieza: Pieza) -> None:
        self.nombre_var.set(pieza.nombre)
        self.cantidad_var.set(str(pieza.cantidad))
        self._set_mass(pieza.masa_g)
        self._set_time_fields(pieza.tiempo_horas)
        self.costo_stl_var.set(f"{pieza.costo_stl:.2f}")
        self.extras_var.set(f"{pieza.extras:.2f}")
        self.prep_var.set(f"{pieza.prep_min:.2f}")
        self.supervision_var.set(f"{pieza.supervision_h:.2f}")
        self.mesh_path = pieza.stl_path
        self.mesh_volume_mm3 = pieza.volumen_mm3
        if pieza.notas:
            self.notas_var.set(pieza.notas)
        if pieza.volumen_mm3:
            cm3 = pieza.volumen_mm3 / 1000.0
            self.volume_label.set(f"Volumen: {cm3:.2f} cm³")
        if pieza.stl_path:
            self.mesh_status_var.set(Path(pieza.stl_path).name)

    def show(self) -> Optional[Pieza]:
        self.wait_window(self)
        return self._result


class ProjectTab(ttk.Frame):
    """Main capture tab for projects."""

    def __init__(
        self,
        master: ttk.Notebook,
        config_store: ConfigStore,
        clients_store: ClientsStore,
        open_config_callback,
        calculate_callback,
    ) -> None:
        super().__init__(master)
        self.config_store = config_store
        self.clients_store = clients_store
        self.open_config_callback = open_config_callback
        self.calculate_callback = calculate_callback

        self.fecha_actual = datetime.utcnow().date().isoformat()
        self.materiales: List[Material] = []
        self.impresoras: List[Impresora] = []
        self.piezas: List[Pieza] = []
        self.current_folio: Optional[str] = None
        self.current_cliente_id: Optional[str] = None

        self.project_name_var = tk.StringVar()
        self.fecha_var = tk.StringVar(value=self.fecha_actual)
        self.tipo_var = tk.StringVar(value="filamento")
        self.impresora_var = tk.StringVar()

        self.material_var = tk.StringVar()
        self.material_precio_var = tk.StringVar(value="0.0")

        self.client_nombre_var = tk.StringVar()
        self.client_correo_var = tk.StringVar()
        self.client_celular_var = tk.StringVar()
        self.client_rfc_var = tk.StringVar()
        self.notas_text = tk.Text(self, height=4)

        self.piezas_tree: ttk.Treeview

        self._build_ui()
        self.refresh_materials()
        self.refresh_printers()

    # ------------------------------------------------------------------
    def _build_ui(self) -> None:
        self.columnconfigure(0, weight=1)

        project_frame = ttk.LabelFrame(self, text="Proyecto")
        project_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=8)
        project_frame.columnconfigure(1, weight=1)
        project_frame.columnconfigure(2, weight=0)

        ttk.Label(project_frame, text="Nombre del proyecto:").grid(row=0, column=0, sticky="w")
        ttk.Entry(project_frame, textvariable=self.project_name_var, width=40).grid(row=0, column=1, sticky="ew", padx=4)

        ttk.Label(project_frame, text="Fecha:").grid(row=1, column=0, sticky="w")
        ttk.Label(project_frame, textvariable=self.fecha_var).grid(row=1, column=1, sticky="w")

        type_combo = LabeledCombobox(project_frame, "Tipo impresión", self.tipo_var, ["filamento", "resina"])
        type_combo.grid(row=2, column=0, sticky="ew", pady=2)
        type_combo.combobox.bind("<<ComboboxSelected>>", lambda _: self.refresh_printers())

        self.impresora_combo = LabeledCombobox(project_frame, "Impresora", self.impresora_var, [])
        self.impresora_combo.grid(row=2, column=1, sticky="ew", pady=2, padx=(0, 4))

        ttk.Button(
            project_frame,
            text="Administrar impresoras",
            command=lambda: self.open_config_callback("impresoras"),
        ).grid(row=2, column=2, sticky="ew", pady=2)

        material_frame = ttk.LabelFrame(self, text="Material")
        material_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=8)
        material_frame.columnconfigure(0, weight=1)
        material_frame.columnconfigure(1, weight=0)
        material_frame.columnconfigure(2, weight=0)

        self.material_combo = LabeledCombobox(material_frame, "Material", self.material_var, [])
        self.material_combo.grid(row=0, column=0, sticky="ew", padx=(0, 4))
        self.material_combo.combobox.bind("<<ComboboxSelected>>", lambda _: self.on_material_change())

        LabeledEntry(material_frame, "Precio kg", self.material_precio_var, validate="float").grid(row=0, column=1, sticky="w")
        ttk.Button(
            material_frame,
            text="Administrar materiales",
            command=lambda: self.open_config_callback("materiales"),
        ).grid(row=0, column=2, sticky="ew")

        client_frame = ttk.LabelFrame(self, text="Cliente")
        client_frame.grid(row=2, column=0, sticky="nsew", padx=10, pady=8)
        client_frame.columnconfigure(1, weight=1)
        client_frame.columnconfigure(2, weight=0)

        ttk.Label(client_frame, text="Nombre:").grid(row=0, column=0, sticky="w")
        self.client_nombre_entry = ttk.Entry(client_frame, textvariable=self.client_nombre_var)
        self.client_nombre_entry.grid(row=0, column=1, sticky="ew", padx=4)
        self.client_nombre_entry.bind("<Return>", self.on_client_name_enter)
        ttk.Button(client_frame, text="Buscar cliente", command=self.open_client_search).grid(row=0, column=2, sticky="ew", padx=(4, 0))

        ttk.Label(client_frame, text="Correo:").grid(row=1, column=0, sticky="w")
        correo_entry = ttk.Entry(client_frame, textvariable=self.client_correo_var)
        correo_entry.grid(row=1, column=1, sticky="ew", padx=4)
        correo_entry.bind("<FocusOut>", lambda _: self.autocomplete_cliente())
        ttk.Label(client_frame, text="Celular:").grid(row=2, column=0, sticky="w")
        celular_entry = ttk.Entry(client_frame, textvariable=self.client_celular_var)
        celular_entry.grid(row=2, column=1, sticky="ew", padx=4)
        celular_entry.bind("<FocusOut>", lambda _: self.autocomplete_cliente())

        ttk.Label(client_frame, text="RFC:").grid(row=3, column=0, sticky="w")
        ttk.Entry(client_frame, textvariable=self.client_rfc_var).grid(row=3, column=1, sticky="ew", padx=4)

        ttk.Label(client_frame, text="Notas:").grid(row=4, column=0, sticky="nw")
        notas_scroll = tk.Scrollbar(client_frame, orient=tk.VERTICAL)
        self.notas_text = tk.Text(client_frame, height=4, width=40, yscrollcommand=notas_scroll.set)
        self.notas_text.grid(row=4, column=1, sticky="ew", padx=4)
        notas_scroll.grid(row=4, column=2, sticky="ns")
        notas_scroll.config(command=self.notas_text.yview)

        piezas_frame = ttk.LabelFrame(self, text="Piezas")
        piezas_frame.grid(row=3, column=0, sticky="nsew", padx=10, pady=8)
        piezas_frame.columnconfigure(0, weight=1)
        piezas_frame.rowconfigure(0, weight=1)

        columns = ("pieza", "cantidad", "masa", "tiempo", "extras")
        self.piezas_tree = ttk.Treeview(piezas_frame, columns=columns, show="headings")
        self.piezas_tree.heading("pieza", text="Pieza")
        self.piezas_tree.heading("cantidad", text="Cantidad")
        self.piezas_tree.heading("masa", text="Masa (g)")
        self.piezas_tree.heading("tiempo", text="Tiempo (h:mm)")
        self.piezas_tree.heading("extras", text="Extras")
        self.piezas_tree.column("pieza", width=200, anchor="w")
        self.piezas_tree.column("cantidad", width=80, anchor="center")
        self.piezas_tree.column("masa", width=100, anchor="center")
        self.piezas_tree.column("tiempo", width=120, anchor="center")
        self.piezas_tree.column("extras", width=120, anchor="center")
        self.piezas_tree.grid(row=0, column=0, sticky="nsew")

        tree_scroll = ttk.Scrollbar(piezas_frame, orient=tk.VERTICAL, command=self.piezas_tree.yview)
        tree_scroll.grid(row=0, column=1, sticky="ns")
        self.piezas_tree.configure(yscrollcommand=tree_scroll.set)

        btn_frame = ttk.Frame(piezas_frame)
        btn_frame.grid(row=1, column=0, columnspan=2, pady=6)
        ttk.Button(btn_frame, text="Agregar", command=self.add_piece).pack(side=tk.LEFT, padx=4)
        ttk.Button(btn_frame, text="Editar", command=self.edit_selected_piece).pack(side=tk.LEFT, padx=4)
        ttk.Button(btn_frame, text="Eliminar", command=self.delete_selected_piece).pack(side=tk.LEFT, padx=4)

        action_frame = ttk.Frame(self)
        action_frame.grid(row=4, column=0, sticky="e", padx=10, pady=(0, 10))
        ttk.Button(action_frame, text="Calcular cotización", command=self.on_calculate).pack(side=tk.RIGHT)

    # ------------------------------------------------------------------
    def refresh_materials(self) -> None:
        materiales = self.config_store.get_materials()
        self.materiales = materiales
        nombres = [m.nombre for m in materiales]
        previous = self.material_var.get()
        self.material_combo.set_values(nombres)
        if previous in nombres:
            self.material_var.set(previous)
        elif nombres:
            self.material_var.set(nombres[0])
        if self.material_var.get():
            self.on_material_change()

    def on_material_change(self) -> None:
        material = self.get_material()
        if material:
            self.material_precio_var.set(f"{material.precio_kg:.2f}")

    def refresh_printers(self) -> None:
        tipo = self.tipo_var.get() or "filamento"
        self.impresoras = self.config_store.get_printers(tipo=tipo)  # type: ignore[arg-type]
        nombres = [p.nombre for p in self.impresoras]
        previous = self.impresora_var.get()
        self.impresora_combo.set_values(nombres)
        if previous in nombres:
            self.impresora_var.set(previous)
        elif nombres:
            self.impresora_var.set(nombres[0])

    def get_material(self) -> Optional[Material]:
        nombre = self.material_var.get()
        for material in self.materiales:
            if material.nombre == nombre:
                return material
        return None

    def get_impresora(self) -> Optional[Impresora]:
        nombre = self.impresora_var.get()
        for impresora in self.impresoras:
            if impresora.nombre == nombre:
                return impresora
        return None

    def autocomplete_cliente(self) -> None:
        correo = self.client_correo_var.get()
        celular = self.client_celular_var.get()
        cliente = self.clients_store.find(correo, celular)
        if cliente:
            self._apply_client(cliente)
        else:
            self.current_cliente_id = None
            self.client_rfc_var.set("")

    def _apply_client(self, cliente: Cliente) -> None:
        self.current_cliente_id = cliente.id
        self.client_nombre_var.set(cliente.nombre)
        if cliente.correo:
            self.client_correo_var.set(cliente.correo)
        if cliente.celular:
            self.client_celular_var.set(cliente.celular)
        self.client_rfc_var.set(cliente.rfc or "")

    def on_client_name_enter(self, _: tk.Event) -> None:
        query = self.client_nombre_var.get().strip()
        if not query:
            return
        matches = self.clients_store.search(query)
        if not matches:
            messagebox.showinfo("Clientes", "No se encontraron coincidencias.", parent=self)
            return
        if len(matches) == 1:
            self._apply_client(matches[0])
            return
        dialog = ClientSearchDialog(self, self.clients_store, initial_query=query)
        seleccionado = dialog.show()
        if seleccionado:
            self._apply_client(seleccionado)

    def open_client_search(self) -> None:
        dialog = ClientSearchDialog(self, self.clients_store, initial_query=self.client_nombre_var.get().strip())
        seleccionado = dialog.show()
        if seleccionado:
            self._apply_client(seleccionado)

    def add_piece(self) -> None:
        material = self.get_material()
        impresora = self.get_impresora()
        if not material or not impresora:
            messagebox.showerror("Configura primero", "Selecciona material e impresora antes de agregar piezas.", parent=self)
            return
        financials = self.config_store.get_financials()
        dialog = PieceDialog(
            self,
            self.tipo_var.get() or "filamento",
            material,
            financials.get("post_min", 0.0),
            financials.get("supervision_h", 0.0),
        )
        pieza = dialog.show()
        if pieza:
            self.piezas.append(pieza)
            self._insert_piece_in_tree(pieza)

    def edit_selected_piece(self) -> None:
        selection = self.piezas_tree.selection()
        if not selection:
            return
        index = self.piezas_tree.index(selection[0])
        pieza = self.piezas[index]
        material = self.get_material()
        if not material:
            return
        financials = self.config_store.get_financials()
        dialog = PieceDialog(
            self,
            self.tipo_var.get() or "filamento",
            material,
            financials.get("post_min", 0.0),
            financials.get("supervision_h", 0.0),
        )
        dialog.edit_piece(pieza)
        updated = dialog.show()
        if updated:
            self.piezas[index] = updated
            self.refresh_tree()

    def delete_selected_piece(self) -> None:
        selection = self.piezas_tree.selection()
        if not selection:
            return
        index = self.piezas_tree.index(selection[0])
        if messagebox.askyesno("Confirmar", "¿Eliminar la pieza seleccionada?", parent=self):
            del self.piezas[index]
            self.refresh_tree()

    def refresh_tree(self) -> None:
        for item in self.piezas_tree.get_children():
            self.piezas_tree.delete(item)
        for pieza in self.piezas:
            self._insert_piece_in_tree(pieza)

    def _insert_piece_in_tree(self, pieza: Pieza) -> None:
        self.piezas_tree.insert(
            "",
            tk.END,
            values=(
                pieza.nombre,
                pieza.cantidad,
                f"{pieza.masa_g:.2f}",
                format_hours_minutes(pieza.horas, pieza.minutos),
                f"{pieza.extras:.2f}",
            ),
        )

    def gather_context(self) -> Optional[QuoteContext]:
        nombre = self.project_name_var.get().strip()
        if not nombre:
            messagebox.showerror("Dato faltante", "Ingresa el nombre del proyecto.", parent=self)
            return None
        material = self.get_material()
        impresora = self.get_impresora()
        if not material or not impresora:
            messagebox.showerror("Dato faltante", "Selecciona una impresora y un material.", parent=self)
            return None
        if not self.piezas:
            messagebox.showerror("Dato faltante", "Agrega al menos una pieza para cotizar.", parent=self)
            return None
        cliente = ClienteInfo(
            id=self.current_cliente_id,
            nombre=self.client_nombre_var.get().strip(),
            correo=self.client_correo_var.get().strip(),
            celular=self.client_celular_var.get().strip(),
            rfc=self.client_rfc_var.get().strip(),
        )
        notas = self.notas_text.get("1.0", tk.END).strip()
        try:
            precio_material = float(self.material_precio_var.get() or material.precio_kg)
        except ValueError:
            messagebox.showerror("Dato inválido", "El precio del material debe ser numérico.", parent=self)
            return None
        return QuoteContext(
            folio=self.current_folio,
            proyecto=nombre,
            fecha=self.fecha_var.get(),
            tipo=self.tipo_var.get() or "filamento",
            impresora=impresora,
            material=material,
            precio_material=precio_material,
            piezas=list(self.piezas),
            cliente=cliente,
            notas=notas,
        )

    def on_calculate(self) -> None:
        context = self.gather_context()
        if not context:
            return
        self.calculate_callback(context)

    def load_quote(self, quote: Cotizacion) -> None:
        self.current_folio = quote.folio
        self.project_name_var.set(quote.proyecto)
        self.fecha_var.set(quote.fecha)
        self.tipo_var.set(quote.tipo)
        self.refresh_printers()
        self.impresora_var.set(quote.impresora)
        self.material_var.set(quote.material)
        self.material_precio_var.set(f"{quote.material_precio_kg:.2f}")
        self.current_cliente_id = quote.cliente.id
        self.client_nombre_var.set(quote.cliente.nombre)
        self.client_correo_var.set(quote.cliente.correo)
        self.client_celular_var.set(quote.cliente.celular)
        self.client_rfc_var.set(quote.cliente.rfc)
        self.notas_text.delete("1.0", tk.END)
        if quote.notas:
            self.notas_text.insert(tk.END, quote.notas)
        self.piezas = [p.pieza for p in quote.piezas]
        self.refresh_tree()

    def clear(self) -> None:
        self.project_name_var.set("")
        self.fecha_var.set(datetime.utcnow().date().isoformat())
        self.piezas.clear()
        self.refresh_tree()
        self.client_nombre_var.set("")
        self.client_correo_var.set("")
        self.client_celular_var.set("")
        self.client_rfc_var.set("")
        self.notas_text.delete("1.0", tk.END)
        self.current_folio = None
        self.current_cliente_id = None


__all__ = ["ProjectTab", "PieceDialog", "QuoteContext", "ClientSearchDialog"]
