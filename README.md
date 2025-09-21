# Cotizador 3D

Aplicación de escritorio en Python (Tkinter) para generar cotizaciones rápidas de impresiones 3D en modos **FDM** y **Resina** a partir de archivos STL.

## Características

- Carga de archivos `.stl` mediante `trimesh` con cálculo de volumen, bounding box y verificación de malla cerrada.
- Pestañas dedicadas para configuración de **FDM** y **Resina** con parámetros editables y validación numérica.
- Estimaciones heurísticas de volumen usado, masa de material, tiempo de impresión y costos asociados (material, electricidad, depreciación, mano de obra).
- Gestión de materiales y perfiles con persistencia en `config.json` y carpeta `presets/`.
- Exportación de la cotización a **PDF** y **CSV**, además de copia rápida al portapapeles.
- Costos financieros (margen, IVA) totalmente configurables.
- Proyecto modular y documentado listo para ejecutar con `python app.py`.

## Requisitos

- Python **3.11** o superior.
- Dependencias listadas en `requirements.txt`:
  - `trimesh`
  - `numpy`
  - `scipy`
  - `reportlab`

## Instalación

1. Clona o descarga este repositorio.
2. (Opcional pero recomendado) Crea y activa un entorno virtual:

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

## Uso

1. En la pestaña **Archivo STL**, presiona **"Cargar STL"** y selecciona el modelo a cotizar. El programa mostrará volumen, dimensiones y advertencias si la malla no es cerrada.
2. Ajusta los parámetros en las pestañas **FDM** o **Resina** según el tipo de impresión. Puedes guardar materiales y presets personalizados.
3. Configura los costos generales (electricidad, depreciación, mano de obra) en la pestaña **Costos & Finanzas**. Estos valores se guardan en `config.json`.
4. En **Resumen & Cotización** selecciona el modo (FDM o Resina), ingresa datos del cliente y pulsa **"Calcular cotización"**. Se mostrará el desglose de tiempo y costos.
5. Exporta el resultado a PDF o CSV, o copia el resumen al portapapeles.

## Configuración y presets

- El archivo `config.json` contiene los valores por defecto, materiales y tarifas. Se actualiza automáticamente al guardar cambios desde la interfaz.
- La carpeta `presets/` almacena perfiles personalizados en formato JSON. Puedes crear varios para diferentes materiales o calidades (ej. `PLA Calidad`, `Resina 0.05 mm`).

## Limitaciones

- Los cálculos son heurísticos y aproximados; no sustituyen a un slicer profesional. Factores como aceleraciones, retracciones o soportes complejos no se modelan con precisión.
- Se asume que las unidades del STL están en milímetros.
- La velocidad real de impresión depende de la máquina, por lo que se recomienda ajustar los parámetros a valores medidos.

## Compatibilidad

- La aplicación utiliza Tkinter (incluido en Python) y funciona en Windows 10/11, macOS y Linux.
- No requiere acceso a internet ni dependencias nativas adicionales.

## Estructura del proyecto

```
app.py                 # Punto de entrada de la GUI
models/geometry.py     # Carga y métricas del STL
pricing/               # Lógica de estimación de costos (FDM, Resina, común)
storage/config.py      # Gestión de config.json y presets
export/                # Exportación a PDF y CSV
ui/components/         # Widgets reutilizables
config.json            # Valores por defecto (se puede editar manualmente)
requirements.txt       # Dependencias del proyecto
presets/               # Carpeta para perfiles guardados
```

## Contribuciones

Si deseas mejorar las heurísticas o añadir nuevos modos de impresión, envía un PR o ajusta el código siguiendo la estructura modular existente. ¡Felices impresiones!
