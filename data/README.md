# Datos

En esta carpeta hay dos cosas: los precios reales de las estaciones de Rosario y una muestra chica inventada que armé para las pruebas.

## Datos reales: precios en surtidor

- Fuente: Secretaría de Energía de la Nación, Subsecretaría de Hidrocarburos.
- Dataset: "Precios en Surtidor – Resolución 314/2016", http://datos.energia.gob.ar/dataset/precios-en-surtidor
- Licencia: Creative Commons Attribution 4.0 (se puede usar citando la fuente).
- Fecha de consulta: 21/10/2026.

El dataset tiene dos archivos:

| Archivo oficial | Qué tiene | Tamaño completo |
|---|---|---|
| Precios vigentes en surtidor | El último precio informado por cada estación | unas 36.600 filas de todo el país |
| Precios históricos | Todas las actualizaciones anteriores | unas 3.380.000 filas (780 MB) |

Como el histórico es muy pesado para subirlo al repositorio, armé dos extractos:

- **rosario_vigentes.csv**: las 782 filas del archivo de vigentes que corresponden a Rosario, Santa Fe.
- **rosario_historicos.csv**: las 21.684 filas del histórico de Rosario desde el 1/1/2024, más 8 filas con fechas imposibles o fuera de rango (años 1157, 0022, 2011 y 2012) que dejé para mostrar que el programa las detecta. En total son 21.692 filas.

Para armarlos me quedé con las filas cuya localidad es ROSARIO y la provincia SANTA FE, y solo con las columnas que usa el programa (las que se explican más abajo). Saqué las coordenadas y otras columnas que no necesito. Los valores no los modifiqué.

Si se quieren usar los archivos completos, se descargan desde la página del dataset y se le indican al programa al ejecutarlo. Conviene guardarlos en una carpeta llamada completos dentro de data, que está configurada para que Git no la suba.

## Qué representa cada fila

Cada fila es una actualización de precio informada por una estación:

- **idempresa**: número que identifica a la estación.
- **empresa**, **direccion** y **empresabandera**: nombre, dirección y bandera de la estación (YPF, Shell, Axion, etc.).
- **localidad** y **provincia**: dónde está la estación.
- **producto**: Nafta súper, Nafta premium, Gas Oil Grado 2, Gas Oil Grado 3 o GNC.
- **tipohorario**: Diurno o Nocturno. Cada precio se informa para los dos horarios.
- **precio**: en pesos por litro (o por m³ en el caso del GNC).
- **fecha_vigencia**: desde cuándo rige ese precio. En el archivo de vigentes viene como 2026-09-24 11:13:00 y en el histórico como 24/09/2026 11:13.

## Muestra de prueba

Los archivos muestra_precios.csv y muestra_precios.json tienen el mismo contenido: 21 registros de estaciones inventadas en una localidad llamada "Pueblo Ejemplo". Se generan con el programa generar_muestra.py de la carpeta scripts.

Cada estación tiene un caso armado a propósito: una con tres actualizaciones (una posterior a la fecha de consulta), una con el mismo dato repetido en los dos formatos de fecha, una con precios contradictorios, una con un precio muy viejo y una de otra localidad. También tiene filas con errores: un id que no es número, un combustible que no existe, un horario inválido, un 31 de febrero, una fecha mal escrita, el año 1157, un precio en cero y un precio que no es número.

## Limitaciones

- Los precios los informan las propias estaciones. Si una no informa un cambio, el dato queda viejo.
- Durante 2026 muchas estaciones de Rosario dejaron de actualizar sus precios.
- El extracto del histórico empieza en 2024, así que las consultas a fechas anteriores no son confiables.
- Hay algunos errores de carga en los datos originales, como precios en cero o fechas imposibles. El programa los descarta.
