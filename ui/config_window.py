"""Configuration management window."""

from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Optional

from models.impresora import Impresora
from models.material import Material
from storage.config_store import ConfigStore

from PIL import Image, ImageTk


class ConfigWindow(tk.Toplevel):
    def __init__(self, master: tk.Widget, config_store: ConfigStore, focus_section: str | None = None) -> None:
        super().__init__(master)
        self.title("Configuraciones")
        self.geometry("720x520")
        self.transient(master)
        self.grab_set()

        self.config_store = config_store

        notebook = ttk.Notebook(self)
        notebook.pack(fill=tk.BOTH, expand=True)

        self.material_tab = ttk.Frame(notebook)
        self.printer_tab = ttk.Frame(notebook)
        self.costs_tab = ttk.Frame(notebook)
        self.identity_tab = ttk.Frame(notebook)
        self.integrations_tab = ttk.Frame(notebook)

        notebook.add(self.material_tab, text="Materiales")
        notebook.add(self.printer_tab, text="Impresoras")
        notebook.add(self.costs_tab, text="Costos & Porcentajes")
        notebook.add(self.identity_tab, text="Identidad")
        notebook.add(self.integrations_tab, text="Integraciones")

        self._build_material_tab()
        self._build_printer_tab()
        self._build_costs_tab()
        self._build_identity_tab()
        self._build_integrations_tab()

        if focus_section:
            mapping = {
                "materiales": 0,
                "impresoras": 1,
                "costos": 2,
                "identidad": 3,
                "integraciones": 4,
            }
            index = mapping.get(focus_section)
            if index is not None:
                notebook.select(index)

    # ------------------------------------------------------------------
    def _build_material_tab(self) -> None:
        frame = self.material_tab
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(0, weight=1)

        columns = ("nombre", "densidad", "precio")
        self.material_tree = ttk.Treeview(frame, columns=columns, show="headings")
        self.material_tree.heading("nombre", text="Nombre")
        self.material_tree.heading("densidad", text="Densidad g/cm³")
        self.material_tree.heading("precio", text="Precio kg")
        self.material_tree.column("nombre", width=180, anchor="w")
        self.material_tree.column("densidad", width=140, anchor="center")
        self.material_tree.column("precio", width=140, anchor="center")
        self.material_tree.grid(row=0, column=0, sticky="nsew")

        scrollbar = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=self.material_tree.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.material_tree.configure(yscrollcommand=scrollbar.set)

        btn_frame = ttk.Frame(frame)
        btn_frame.grid(row=1, column=0, columnspan=2, pady=6)
        ttk.Button(btn_frame, text="Agregar", command=self.add_material).pack(side=tk.LEFT, padx=4)
        ttk.Button(btn_frame, text="Editar", command=self.edit_material).pack(side=tk.LEFT, padx=4)
        ttk.Button(btn_frame, text="Eliminar", command=self.delete_material).pack(side=tk.LEFT, padx=4)

        self.refresh_materials()

    def refresh_materials(self) -> None:
        for item in self.material_tree.get_children():
            self.material_tree.delete(item)
        for material in self.config_store.get_materials():
            self.material_tree.insert(
                "",
                tk.END,
                values=(
                    material.nombre,
                    f"{material.densidad_g_cm3:.2f}",
                    f"{material.precio_kg:.2f}",
                ),
            )

    def _material_dialog(self, material: Optional[Material] = None) -> Optional[Material]:
        dialog = tk.Toplevel(self)
        dialog.title("Material")
        dialog.transient(self)
        dialog.grab_set()
        ttk.Label(dialog, text="Nombre:").grid(row=0, column=0, sticky="w", padx=6, pady=4)
        nombre_var = tk.StringVar(value=material.nombre if material else "")
        ttk.Entry(dialog, textvariable=nombre_var).grid(row=0, column=1, padx=6, pady=4)
        ttk.Label(dialog, text="Densidad g/cm³:").grid(row=1, column=0, sticky="w", padx=6, pady=4)
        densidad_var = tk.StringVar(value=f"{material.densidad_g_cm3:.3f}" if material else "1.240")
        ttk.Entry(dialog, textvariable=densidad_var).grid(row=1, column=1, padx=6, pady=4)
        ttk.Label(dialog, text="Precio kg:").grid(row=2, column=0, sticky="w", padx=6, pady=4)
        precio_var = tk.StringVar(value=f"{material.precio_kg:.2f}" if material else "350.0")
        ttk.Entry(dialog, textvariable=precio_var).grid(row=2, column=1, padx=6, pady=4)

        result: Optional[Material] = None

        def on_accept() -> None:
            nombre = nombre_var.get().strip()
            if not nombre:
                messagebox.showerror("Dato faltante", "Ingresa el nombre del material.", parent=dialog)
                return
            try:
                densidad = float(densidad_var.get())
                precio = float(precio_var.get())
            except ValueError:
                messagebox.showerror("Dato inválido", "Verifica la densidad y el precio.", parent=dialog)
                return
            if densidad <= 0 or precio <= 0:
                messagebox.showerror(
                    "Dato inválido",
                    "La densidad y el precio deben ser mayores que cero.",
                    parent=dialog,
                )
                return
            nonlocal result
            result = Material(nombre=nombre, densidad_g_cm3=densidad, precio_kg=precio)
            dialog.destroy()

        ttk.Button(dialog, text="Aceptar", command=on_accept).grid(row=3, column=0, padx=6, pady=8)
        ttk.Button(dialog, text="Cancelar", command=dialog.destroy).grid(row=3, column=1, padx=6, pady=8)
        dialog.wait_window(dialog)
        return result

    def add_material(self) -> None:
        material = self._material_dialog()
        if material:
            if self.config_store.material_exists(material.nombre):
                messagebox.showerror(
                    "Duplicado",
                    "Ya existe un material con ese nombre.",
                    parent=self,
                )
                return
            self.config_store.upsert_material(material)
            self.refresh_materials()

    def edit_material(self) -> None:
        selection = self.material_tree.selection()
        if not selection:
            return
        nombre = self.material_tree.item(selection[0], "values")[0]
        current = next((m for m in self.config_store.get_materials() if m.nombre == nombre), None)
        if not current:
            return
        material = self._material_dialog(current)
        if material:
            if material.nombre != current.nombre and self.config_store.material_exists(material.nombre):
                messagebox.showerror(
                    "Duplicado",
                    "Ya existe un material con ese nombre.",
                    parent=self,
                )
                return
            self.config_store.upsert_material(material, previous_name=current.nombre)
            self.refresh_materials()

    def delete_material(self) -> None:
        selection = self.material_tree.selection()
        if not selection:
            return
        nombre = self.material_tree.item(selection[0], "values")[0]
        if messagebox.askyesno("Eliminar", f"¿Eliminar el material {nombre}?", parent=self):
            self.config_store.delete_material(nombre)
            self.refresh_materials()

    # ------------------------------------------------------------------
    def _build_printer_tab(self) -> None:
        frame = self.printer_tab
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(0, weight=1)

        columns = ("tipo", "costo", "vida", "potencia")
        self.printer_tree = ttk.Treeview(frame, columns=columns, show="headings")
        self.printer_tree.heading("tipo", text="Tipo")
        self.printer_tree.heading("costo", text="Costo")
        self.printer_tree.heading("vida", text="Vida útil h")
        self.printer_tree.heading("potencia", text="Potencia W")
        for col in columns:
            self.printer_tree.column(col, width=140, anchor="center")
        self.printer_tree.grid(row=0, column=0, sticky="nsew")

        scrollbar = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=self.printer_tree.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.printer_tree.configure(yscrollcommand=scrollbar.set)

        btn_frame = ttk.Frame(frame)
        btn_frame.grid(row=1, column=0, columnspan=2, pady=6)
        ttk.Button(btn_frame, text="Agregar", command=self.add_printer).pack(side=tk.LEFT, padx=4)
        ttk.Button(btn_frame, text="Editar", command=self.edit_printer).pack(side=tk.LEFT, padx=4)
        ttk.Button(btn_frame, text="Eliminar", command=self.delete_printer).pack(side=tk.LEFT, padx=4)

        self.refresh_printers()

    def refresh_printers(self) -> None:
        for item in self.printer_tree.get_children():
            self.printer_tree.delete(item)
        for printer in self.config_store.get_printers():
            self.printer_tree.insert(
                "",
                tk.END,
                values=(
                    printer.tipo,
                    f"{printer.costo_equipo:.2f}",
                    f"{printer.vida_util_horas:.1f}",
                    f"{printer.potencia_w:.1f}",
                ),
                text=printer.nombre,
            )

    def _printer_dialog(self, printer: Optional[Impresora] = None) -> Optional[Impresora]:
        dialog = tk.Toplevel(self)
        dialog.title("Impresora")
        dialog.transient(self)
        dialog.grab_set()

        ttk.Label(dialog, text="Nombre:").grid(row=0, column=0, sticky="w", padx=6, pady=4)
        nombre_var = tk.StringVar(value=printer.nombre if printer else "")
        ttk.Entry(dialog, textvariable=nombre_var).grid(row=0, column=1, padx=6, pady=4)

        ttk.Label(dialog, text="Tipo:").grid(row=1, column=0, sticky="w", padx=6, pady=4)
        tipo_var = tk.StringVar(value=printer.tipo if printer else "filamento")
        ttk.Combobox(dialog, textvariable=tipo_var, values=["filamento", "resina"], state="readonly").grid(
            row=1, column=1, padx=6, pady=4
        )

        ttk.Label(dialog, text="Costo equipo:").grid(row=2, column=0, sticky="w", padx=6, pady=4)
        costo_var = tk.StringVar(value=f"{printer.costo_equipo:.2f}" if printer else "15000")
        ttk.Entry(dialog, textvariable=costo_var).grid(row=2, column=1, padx=6, pady=4)

        ttk.Label(dialog, text="Vida útil (h):").grid(row=3, column=0, sticky="w", padx=6, pady=4)
        vida_var = tk.StringVar(value=f"{printer.vida_util_horas:.1f}" if printer else "6000")
        ttk.Entry(dialog, textvariable=vida_var).grid(row=3, column=1, padx=6, pady=4)

        ttk.Label(dialog, text="Potencia (W):").grid(row=4, column=0, sticky="w", padx=6, pady=4)
        potencia_var = tk.StringVar(value=f"{printer.potencia_w:.1f}" if printer else "350")
        ttk.Entry(dialog, textvariable=potencia_var).grid(row=4, column=1, padx=6, pady=4)

        result: Optional[Impresora] = None

        def on_accept() -> None:
            nombre = nombre_var.get().strip()
            if not nombre:
                messagebox.showerror("Dato faltante", "Ingresa el nombre de la impresora.", parent=dialog)
                return
            try:
                costo = float(costo_var.get())
                vida = float(vida_var.get())
                potencia = float(potencia_var.get())
            except ValueError:
                messagebox.showerror("Dato inválido", "Verifica costo, vida útil y potencia.", parent=dialog)
                return
            nonlocal result
            result = Impresora(
                nombre=nombre,
                tipo=tipo_var.get() or "filamento",
                costo_equipo=costo,
                vida_util_horas=vida,
                potencia_w=potencia,
            )
            dialog.destroy()

        ttk.Button(dialog, text="Aceptar", command=on_accept).grid(row=5, column=0, padx=6, pady=8)
        ttk.Button(dialog, text="Cancelar", command=dialog.destroy).grid(row=5, column=1, padx=6, pady=8)
        dialog.wait_window(dialog)
        return result

    def add_printer(self) -> None:
        printer = self._printer_dialog()
        if printer:
            if any(p.nombre == printer.nombre for p in self.config_store.get_printers()):
                messagebox.showerror("Duplicado", "Ya existe una impresora con ese nombre.", parent=self)
                return
            self.config_store.upsert_printer(printer)
            self.refresh_printers()

    def edit_printer(self) -> None:
        selection = self.printer_tree.selection()
        if not selection:
            return
        nombre = self.printer_tree.item(selection[0], "text")
        current = next((p for p in self.config_store.get_printers() if p.nombre == nombre), None)
        if not current:
            return
        printer = self._printer_dialog(current)
        if printer:
            self.config_store.upsert_printer(printer)
            self.refresh_printers()

    def delete_printer(self) -> None:
        selection = self.printer_tree.selection()
        if not selection:
            return
        nombre = self.printer_tree.item(selection[0], "text")
        if messagebox.askyesno("Eliminar", f"¿Eliminar la impresora {nombre}?", parent=self):
            self.config_store.delete_printer(nombre)
            self.refresh_printers()

    # ------------------------------------------------------------------
    def _build_costs_tab(self) -> None:
        frame = self.costs_tab
        frame.columnconfigure(1, weight=1)

        financials = self.config_store.get_financials()
        labels = [
            ("Precio kWh", "precio_kwh"),
            ("Costo hora mano de obra", "costo_hora"),
            ("Post-proceso (min)", "post_min"),
            ("Supervisión (h)", "supervision_h"),
            ("Merma %", "merma"),
            ("Riesgo %", "riesgo"),
            ("Ganancia %", "ganancia"),
            ("IVA %", "iva"),
        ]
        self.cost_vars = {}
        for idx, (label, key) in enumerate(labels):
            ttk.Label(frame, text=label).grid(row=idx, column=0, sticky="w", padx=8, pady=4)
            value = financials.get(key, 0.0)
            if key in {"merma", "riesgo", "ganancia", "iva"}:
                value *= 100
            var = tk.StringVar(value=f"{value:.2f}")
            entry = ttk.Entry(frame, textvariable=var)
            entry.grid(row=idx, column=1, sticky="ew", padx=8, pady=4)
            self.cost_vars[key] = var

        ttk.Button(frame, text="Guardar", command=self.save_costs).grid(row=len(labels), column=1, sticky="e", padx=8, pady=12)

    def save_costs(self) -> None:
        payload = {}
        for key, var in self.cost_vars.items():
            try:
                value = float(var.get())
                if key in {"merma", "riesgo", "ganancia", "iva"}:
                    value /= 100.0
                payload[key] = value
            except ValueError:
                messagebox.showerror("Dato inválido", f"Revisa el campo {key}", parent=self)
                return
        self.config_store.update_financials(payload)
        messagebox.showinfo("Guardado", "Configuración económica actualizada.", parent=self)

    # ------------------------------------------------------------------
    def _build_identity_tab(self) -> None:
        frame = self.identity_tab
        frame.columnconfigure(1, weight=1)

        identity = self.config_store.get_identity()
        fields = [
            ("Nombre comercial", "nombre_comercial"),
            ("RFC", "rfc"),
            ("Dirección", "direccion"),
            ("Teléfono", "telefono"),
            ("Logo", "logo_path"),
        ]
        self.identity_vars = {}
        for idx, (label, key) in enumerate(fields):
            ttk.Label(frame, text=label).grid(row=idx, column=0, sticky="w", padx=8, pady=4)
            var = tk.StringVar(value=str(identity.get(key, "")))
            entry = ttk.Entry(frame, textvariable=var)
            entry.grid(row=idx, column=1, sticky="ew", padx=8, pady=4)
            if key == "logo_path":
                ttk.Button(frame, text="Buscar", command=lambda v=var: self._select_logo(v)).grid(row=idx, column=2, padx=4)
                ttk.Button(frame, text="Probar logo", command=lambda v=var: self._preview_logo(v)).grid(row=idx, column=3, padx=4)
            self.identity_vars[key] = var

        ttk.Label(frame, text="Políticas:").grid(row=len(fields), column=0, sticky="nw", padx=8, pady=4)
        self.politicas_text = tk.Text(frame, height=6)
        self.politicas_text.grid(row=len(fields), column=1, columnspan=2, sticky="nsew", padx=8, pady=4)
        frame.rowconfigure(len(fields), weight=1)
        self.politicas_text.insert(tk.END, identity.get("politicas", ""))

        ttk.Button(frame, text="Guardar", command=self.save_identity).grid(row=len(fields) + 1, column=1, sticky="e", padx=8, pady=12)

    def _select_logo(self, var: tk.StringVar) -> None:
        path = filedialog.askopenfilename(parent=self, filetypes=[("Imágenes", "*.png;*.jpg;*.jpeg")])
        if path:
            var.set(Path(path).expanduser().as_posix())

    def _preview_logo(self, var: tk.StringVar) -> None:
        path_str = var.get().strip()
        if not path_str:
            messagebox.showwarning("Logo", "Primero selecciona una ruta de logo.", parent=self)
            return
        logo_path = self.config_store.resolve_path(path_str)
        if not logo_path.exists():
            messagebox.showerror("Logo", f"No se encontró el archivo en {logo_path}", parent=self)
            return
        try:
            image = Image.open(logo_path)
        except Exception as exc:
            messagebox.showerror("Logo", f"No se pudo abrir el logo: {exc}", parent=self)
            return
        image.thumbnail((240, 240))
        preview = tk.Toplevel(self)
        preview.title("Vista previa del logo")
        preview.transient(self)
        preview.grab_set()
        photo = ImageTk.PhotoImage(image)
        label = ttk.Label(preview, image=photo)
        label.image = photo  # type: ignore[attr-defined]
        label.pack(padx=12, pady=12)
        ttk.Button(preview, text="Cerrar", command=preview.destroy).pack(pady=(0, 12))

    def save_identity(self) -> None:
        payload = {key: var.get() for key, var in self.identity_vars.items()}
        payload["politicas"] = self.politicas_text.get("1.0", tk.END).strip()
        self.config_store.update_identity(payload)
        messagebox.showinfo("Guardado", "Identidad actualizada.", parent=self)

    # ------------------------------------------------------------------
    def _build_integrations_tab(self) -> None:
        frame = self.integrations_tab
        frame.columnconfigure(1, weight=1)

        integrations = self.config_store.get_integrations()
        email_cfg = integrations.get("email", {})
        whatsapp_cfg = integrations.get("whatsapp", {})

        ttk.Label(frame, text="Email (SMTP)", font=("TkDefaultFont", 10, "bold")).grid(row=0, column=0, sticky="w", padx=8, pady=4)
        email_fields = [
            ("Host", "host"),
            ("Puerto", "puerto"),
            ("Usuario", "usuario"),
            ("Password", "password"),
            ("Remitente", "remitente"),
            ("Usar TLS (True/False)", "usar_tls"),
            ("Mensaje", "mensaje"),
        ]
        self.email_vars = {}
        for idx, (label, key) in enumerate(email_fields, start=1):
            ttk.Label(frame, text=label).grid(row=idx, column=0, sticky="w", padx=8, pady=4)
            var = tk.StringVar(value=str(email_cfg.get(key, "")))
            ttk.Entry(frame, textvariable=var).grid(row=idx, column=1, sticky="ew", padx=8, pady=4)
            self.email_vars[key] = var

        separator_row = len(email_fields) + 1
        ttk.Label(frame, text="WhatsApp", font=("TkDefaultFont", 10, "bold")).grid(row=separator_row, column=0, sticky="w", padx=8, pady=(12, 4))
        whatsapp_fields = [
            ("Endpoint", "endpoint"),
            ("Token", "token"),
            ("Número negocio", "numero"),
            ("Mensaje base", "mensaje_base"),
        ]
        self.whatsapp_vars = {}
        for idx, (label, key) in enumerate(whatsapp_fields, start=separator_row + 1):
            ttk.Label(frame, text=label).grid(row=idx, column=0, sticky="w", padx=8, pady=4)
            var = tk.StringVar(value=str(whatsapp_cfg.get(key, "")))
            ttk.Entry(frame, textvariable=var).grid(row=idx, column=1, sticky="ew", padx=8, pady=4)
            self.whatsapp_vars[key] = var

        ttk.Button(frame, text="Guardar", command=self.save_integrations).grid(row=separator_row + len(whatsapp_fields) + 1, column=1, sticky="e", padx=8, pady=12)

    def save_integrations(self) -> None:
        email_cfg = {key: var.get() for key, var in self.email_vars.items()}
        try:
            email_cfg["puerto"] = int(email_cfg.get("puerto", 587))
        except ValueError:
            messagebox.showerror("Dato inválido", "El puerto SMTP debe ser numérico.", parent=self)
            return
        email_cfg["usar_tls"] = email_cfg.get("usar_tls", "True").lower() in {"1", "true", "si", "sí"}
        whatsapp_cfg = {key: var.get() for key, var in self.whatsapp_vars.items()}
        integrations = {"email": email_cfg, "whatsapp": whatsapp_cfg}
        self.config_store.update_integrations(integrations)
        messagebox.showinfo("Guardado", "Integraciones actualizadas.", parent=self)


__all__ = ["ConfigWindow"]
