# Cotizador 3D

Aplicación de escritorio y web escrita en **Python 3.11+** con **Flet** que replica las fórmulas de la hoja de Excel original para cotizar impresiones 3D. Permite capturar proyectos completos con múltiples piezas, gestionar catálogos de materiales e impresoras, guardar cotizaciones, convertirlas en pedidos y generar reportes contables.

## Características principales

- **Captura integral en una sola pestaña**: datos del proyecto, cliente, tipo de impresión (filamento/resina), impresora filtrada por tecnología y lista de piezas con masa, tiempo, STL opcional, costos STL y extras particulares.
- **Cálculo financiero alineado al Excel**: subtotal base (material, energía, depreciación, mano de obra, STL y extras) seguido por merma %, riesgo %, ganancia % e IVA %. El material nunca incorpora margen adicional.
- **Configuración persistente** (`config.json`): moneda, precio kWh, costos de mano de obra, tiempos por defecto, porcentajes, materiales con densidad/precio e impresoras con costo, vida útil y potencia. Incluye identidad del negocio, logo, políticas y parámetros de integraciones (SMTP y WhatsApp).
- **Gestión de múltiples piezas**: cada cotización puede incluir varias piezas con cantidades, permitiendo distribuir automáticamente merma, riesgo, ganancia e IVA de manera proporcional.
- **Modal de cotización**: muestra el desglose formal y permite exportar a PDF/CSV, guardar la cotización, enviarla por correo electrónico o generar un archivo listo para integrarse con una API de WhatsApp.
- **Repositorio de cotizaciones**: listado de cotizaciones guardadas (`cotizaciones_guardadas/*.json`) con opciones para ver, editar (recargar en la pestaña Proyecto), eliminar o convertir en pedidos.
- **Gestión de pedidos**: creación de pedidos aceptados (`pedidos_guardados/*.json`) con estatus, fecha estimada, banderas de anticipo/liquidado y filtros por estado, tecnología y fechas.
- **Contabilidad mensual**: resumen por periodo (ingresos, costos, gastos, ganancia e IVA) con exportación a PDF y Excel (`reportes/`).
- **CRM básico** (`clientes.json`): auto-completa datos por correo/celular, cuenta pedidos, totales facturados y ganancia acumulada.

## Requisitos

- Python **3.11** o superior.
- Dependencias listadas en `requirements.txt`:
  - `trimesh`
  - `numpy`
  - `scipy`
  - `reportlab`
  - `openpyxl`
  - `Pillow`
  - `tkcalendar`
  - `flet`

## Instalación

1. Clona o descarga el repositorio.
2. (Opcional) Crea un entorno virtual:
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

- **Proyecto**: captura nombre, fecha, tipo (filamento/resina), impresora filtrada por tipo, material y precio por kg. Administra piezas (Agregar/Editar/Eliminar) con STL opcional y estimaciones automáticas de masa/tiempo usando heurísticas FDM/resina. Incluye datos del cliente (nombre, correo, celular) y notas.
- **Cotizaciones**: lista todas las cotizaciones guardadas (folio, fecha, proyecto, cliente). Permite ver el detalle (abre el modal), editar recargando la pestaña Proyecto, eliminar o convertir en pedido aceptado.
- **Pedidos**: administra pedidos aceptados con filtros por estado, tipo y fechas. Ofrece acciones para cambiar estatus, ajustar fecha estimada, marcar anticipo/liquidado y eliminar pedidos.
- **Contabilidad**: consolida pedidos realizados por mes. Muestra ingresos, costos, gastos (merma+riesgo), ganancia e IVA. Exporta reportes a PDF y Excel.

El botón **Configuraciones** (y los accesos rápidos “Administrar materiales/impresoras”) abre una ventana con pestañas para:

- **Materiales** y **Impresoras**: CRUD persistente sobre `config.json`.
- **Costos & Porcentajes**: precio kWh, costo hora, tiempos por defecto y porcentajes expresados en %.
- **Identidad**: nombre comercial, RFC, dirección, teléfono, logo (configurable mediante `identidad.logo_path`) y políticas utilizadas en el PDF.
  - El repositorio no incluye un logo por defecto; coloca tu archivo (por ejemplo,
    `logo_negocio.png`) dentro de la carpeta `assets/` y ajusta la ruta en `config.json`.
- **Integraciones**: credenciales SMTP y parámetros para la futura integración de WhatsApp. El envío por WhatsApp genera un archivo `.whatsapp.txt` con la información lista para conectarse a una API.

## Fórmulas empleadas

Para cada pieza se calcula el subtotal base (material + energía + depreciación + mano de obra + STL + extras). Los porcentajes globales se aplican sobre el total acumulado de todas las piezas:

```
subtotal_base = Σ(material + energia + depreciacion + mano_obra + costo_stl + extras)
subtotal_post_merma = subtotal_base * (1 + merma)
subtotal_post_riesgo = subtotal_post_merma * (1 + riesgo)
total_sin_iva = subtotal_post_riesgo * (1 + ganancia)
total = total_sin_iva * (1 + iva)
```

La merma, el riesgo, la ganancia y el IVA se distribuyen proporcionalmente entre las piezas para obtener precios unitarios y totales consistentes con el subtotal global.

## Estructura del proyecto

```
app.py                        # Ventana principal y orquestación de tabs/modal
models/                       # Dataclasses para materiales, impresoras, piezas, cotizaciones y pedidos
pricing/                      # Motor de costos y heurísticas FDM/resina
storage/                      # Persistencia en JSON (config, clientes, cotizaciones, pedidos)
ui/                           # Pestañas de Tkinter, modal de cotización y ventanas de configuración
export/                       # Exportadores a PDF/CSV y reportes contables PDF/Excel
utils/                        # Envío por email/WhatsApp (placeholder)
config.json                   # Configuración inicial con identidad e integraciones
clientes.json                 # CRM básico
cotizaciones_guardadas/       # Cotizaciones en formato JSON
pedidos_guardados/            # Pedidos aceptados
```

## Pruebas

Ejecuta las pruebas unitarias del motor de costos con:

```bash
python -m unittest
```

## Limitaciones

- Los cálculos son estimaciones basadas en parámetros medios; no sustituyen un *slicer* real ni contemplan soportes complejos.
- Se asume que los STL están en milímetros y que la densidad declarada corresponde al material realmente utilizado (infill + casco).
- Las integraciones de correo/WhatsApp requieren completar credenciales válidas; la función de WhatsApp es un *placeholder* que genera un archivo con la información lista para integrarse con un proveedor externo.

¡Felices impresiones!
