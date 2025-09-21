# Cotizador 3D

Aplicación de escritorio escrita en Python 3.11+ (Tkinter) para replicar el flujo de cotización del archivo de Excel utilizado en Axis3D. Permite registrar impresoras FDM y de resina, gestionar materiales y calcular una propuesta económica con merma, riesgo, ganancia e IVA opcional.

## Características principales

- Carga opcional de archivos `.stl` mediante `trimesh` con cálculo de volumen, dimensiones y advertencia si la malla no está cerrada.
- Catálogo persistente de impresoras (filamento/resina) con costo del equipo, vida útil y potencia eléctrica para incluir depreciación y consumo energético reales.
- Control de materiales con densidad y precio por kilogramo para estimar el costo directo del insumo **sin margen adicional**.
- Fórmulas alineadas con la hoja de cálculo original: subtotal base (material, energía, depreciación, mano de obra, STL, extras) seguido de merma %, riesgo %, ganancia % e IVA %.
- Configuración global editable (precio kWh, costo hora-hombre, tiempos de postproceso por defecto y porcentajes) almacenada en `config.json`.
- Exportación de la cotización a PDF y CSV incluyendo nombre, correo y celular del cliente, así como notas y condiciones.

## Requisitos

- Python **3.11** o superior.
- Dependencias listadas en `requirements.txt`:
  - `trimesh`
  - `numpy`
  - `scipy`
  - `reportlab`

## Instalación

1. Clona o descarga este repositorio.
2. (Opcional) Crea y activa un entorno virtual:

   ```bash
   python -m venv .venv
   source .venv/bin/activate  # En Windows: .venv\Scripts\activate
   ```

3. Instala las dependencias:

   ```bash
   pip install -r requirements.txt
   ```

4. Ejecuta la aplicación:

   ```bash
   python app.py
   ```

## Uso de la interfaz

La ventana principal se organiza en cinco pestañas:

1. **Proyecto**: selecciona el tipo de impresión (filamento o resina) y la impresora correspondiente. Ingresa masa en gramos, horas de impresión, minutos de mano de obra, horas de supervisión, costo del STL y extras. Desde aquí puedes cargar un STL para obtener volumen y dimensiones, y estimar la masa según el material activo.
2. **Material**: administra el catálogo de materiales (densidad g/cm³ y precio MXN/kg). Los cambios se guardan de forma persistente en `config.json`.
3. **Costos & Porcentajes**: establece el precio del kWh, costo hora-hombre, tiempos por defecto y porcentajes de merma, riesgo, ganancia e IVA (los campos aceptan valores en %). Estos valores alimentan directamente las fórmulas del cálculo.
4. **Impresoras**: registra, edita o elimina impresoras diferenciando entre filamento y resina. Los datos alimentan automáticamente la depreciación y el consumo eléctrico.
5. **Cliente & Exportar**: captura nombre, correo y celular del cliente, añade notas y genera el desglose completo. Desde esta pestaña puedes exportar a PDF o CSV.

## Flujo de cálculo

El motor en `pricing/calc.py` aplica las siguientes fórmulas:

```
subtotal_base = material + energia + depreciacion + mano_obra + costo_stl + extras
subtotal_merma = subtotal_base * (1 + merma)
subtotal_riesgo = subtotal_merma * (1 + riesgo)
total_sin_iva = subtotal_riesgo * (1 + ganancia)
total_con_iva = total_sin_iva * (1 + iva)
```

La utilidad se controla mediante el porcentaje de **ganancia** y la mano de obra; el costo del material nunca incorpora margen adicional.

## Configuración

`config.json` contiene moneda, costos globales, porcentajes, materiales e impresoras. Puede editarse manualmente o mediante la interfaz. Un ejemplo del contenido generado por defecto es:

```json
{
  "moneda": "MXN",
  "electricidad": {"kwh_precio": 3.0},
  "mano_obra": {"costo_hora": 120.0, "post_min": 20.0, "supervision_h": 0.0},
  "porcentajes": {"merma": 0.02, "riesgo": 0.05, "ganancia": 0.3, "iva": 0.16},
  "materiales": {
    "PLA": {"densidad_g_cm3": 1.24, "precio_kg": 360.0},
    "PETG": {"densidad_g_cm3": 1.27, "precio_kg": 420.0}
  },
  "impresoras": [
    {"nombre": "Bambu Lab A1", "tipo": "filamento", "costo_equipo": 16000.0, "vida_util_horas": 5000.0, "potencia_w": 220.0},
    {"nombre": "Elegoo Mars 3", "tipo": "resina", "costo_equipo": 9000.0, "vida_util_horas": 4000.0, "potencia_w": 120.0}
  ]
}
```

## Estructura del proyecto

```
app.py                 # Ventana principal y lógica de la GUI
config/storage.py      # Lectura/escritura de config.json
models/geometry.py     # Carga y métricas de archivos STL
models/printers.py     # CRUD de impresoras persistentes
pricing/calc.py        # Fórmulas de costos y utilidades
export/                # Exportación a PDF y CSV
ui/components/         # Widgets reutilizables (entries etiquetados, tooltips)
requirements.txt       # Dependencias
```

## Pruebas

Ejecuta los tests unitarios del módulo de costos con:

```bash
python -m unittest
```

## Limitaciones

- Los cálculos siguen una aproximación similar a la hoja de Excel; no sustituyen el slicing real ni contemplan soportes complejos.
- Se asume que los STL están en milímetros y que la densidad declarada corresponde al material efectivamente usado (infill + cascarón).
- Si la malla no está cerrada, el volumen reportado puede ser impreciso; la aplicación muestra una advertencia pero permite continuar.

¡Felices impresiones!
