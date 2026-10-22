# Buscador de precios vigentes de combustibles

Paula Rossi – Programación Orientada a Datos, Licenciatura en Ciencia de Datos, UCA Rosario (2026).

## Problema

Las estaciones de servicio están obligadas a informar a la Secretaría de Energía cada vez que cambian un precio. Esos datos son públicos, pero no se pueden usar tal cual para comparar. Cada estación aparece muchas veces, una por cada actualización, y hay varios combustibles mezclados. Además, los dos archivos que se publican usan formatos de fecha distintos.

Si alguien compara los registros sin elegir cuál está vigente, puede quedarse con un precio viejo. Y una estación que dejó de informar hace un año aparece como "la más barata", aunque ese precio ya no existe.

## Usuario

Cualquier persona que quiera saber dónde conviene cargar combustible en su ciudad, o comparar cómo estaban los precios en una fecha pasada. También le puede servir a alguien que siga la evolución de precios por zona.

## Solución propuesta

Hice un programa en Python que se usa desde la terminal. Le indicás una localidad, un tipo de combustible y una fecha, y te devuelve las estaciones de esa localidad con el precio que estaba vigente en ese momento, ordenadas de la más barata a la más cara.

Para eso el programa:

- lee uno o más archivos de precios, en CSV o JSON;
- convierte las fechas y los precios, y descarta lo que no se puede usar, guardando el motivo;
- junta los registros repetidos y descarta los contradictorios;
- para cada estación elige el precio más reciente que no sea posterior a la fecha consultada;
- deja afuera los precios que tienen más de 30 días sin actualizarse (el límite se puede cambiar);
- guarda el resultado en un archivo CSV dentro de la carpeta outputs, con la fecha de consulta y desde cuándo rige cada precio.

En esta primera versión se consulta un combustible y una localidad por vez. No calcula distancias ni muestra mapas, aunque los datos traen coordenadas.

## Instalación

Hace falta Python 3.10 o más nuevo. No usa librerías externas, solo la biblioteca estándar.

```
git clone https://github.com/paulitar2007/tp2-Paula-Rossi.git
cd tp2-Paula-Rossi
```

Los datos de Rosario ya están incluidos en la carpeta data, así que no hace falta descargar nada para probarlo.

## Cómo se usa

Los comandos se ejecutan desde la carpeta principal del proyecto.

```
python -m src.main --localidad Rosario --combustible super --fecha 2026-10-15
```

Otros ejemplos:

```
python -m src.main --localidad Rosario --combustible gnc --fecha 2025-06-01 --top 5
python -m src.main --localidad Rosario --combustible gasoil --max-dias 60
python -m src.main --precios data/muestra_precios.json --localidad "Pueblo Ejemplo" --combustible super --fecha 2026-10-01
```

Lo que se le puede indicar al programa:

- La localidad, que es obligatoria. No importan las mayúsculas ni las tildes.
- El combustible, también obligatorio: super, premium, gasoil, gasoil-premium o gnc.
- La fecha de consulta, en formato año-mes-día. Si no se indica, se usa la fecha de hoy.
- Opcionalmente: cuántos días de antigüedad se aceptan (30 por defecto), el horario (diurno o nocturno), la provincia y cuántas estaciones mostrar.
- También se pueden usar otros archivos de precios en lugar de los de Rosario.

## Pruebas

```
python -m unittest -v
```

Las pruebas revisan que una estación con dos actualizaciones devuelva la correcta, que una actualización posterior a la fecha de consulta quede afuera y que una localidad sin estaciones devuelva una lista vacía sin romperse. También prueban las entradas con errores (fechas imposibles como el 31/02, precios en cero, combustibles desconocidos, JSON mal armado) y algunas propiedades del resultado: que el CSV y el JSON den lo mismo, que no se pierdan registros, que no se mezclen combustibles y que cada estación aparezca una sola vez.

## Organización del código

El código está dividido en cuatro archivos dentro de la carpeta src:

- **fuentes.py** se encarga de leer los archivos. Tiene una clase base, FuenteDatos, y dos versiones de esa clase: una para leer CSV y otra para leer JSON. Las dos devuelven los datos de la misma forma, así el resto del programa no depende del formato.
- **modelo.py** tiene la clase ConsultaPrecio, que guarda y revisa lo que pide el usuario (localidad, combustible, fecha, etc.), y la función que convierte las fechas.
- **pipeline.py** tiene los pasos del procesamiento: normalizar los precios, resolver duplicados, elegir el precio vigente de cada estación, buscar y ordenar, verificar el resultado y guardarlo.
- **main.py** es el punto de entrada: lee lo que se escribe en la terminal y ejecuta todo.

Además, la carpeta tests tiene las pruebas, la carpeta scripts tiene el programa que genera la muestra de prueba y la carpeta data tiene los datos.

El recorrido es: leer los archivos, revisar que tengan las columnas necesarias, normalizar fechas y precios, resolver duplicados, elegir el precio vigente de cada estación, filtrar, ordenar, verificar y guardar.

## Expresiones regulares

Los dos archivos oficiales escriben las fechas de forma distinta. En el de precios vigentes aparecen como 2026-09-24 11:13:00 (año, mes, día y hora) y en el histórico como 24/09/2026 11:13 (día, mes, año y hora).

Para reconocerlas uso dos expresiones regulares, que están en el archivo modelo.py:

- La primera reconoce las fechas que empiezan con el año: cuatro números, un guion, dos números para el mes, otro guion y dos números para el día. La hora es opcional.
- La segunda reconoce las fechas que empiezan con el día: dos números, una barra, dos números para el mes, otra barra, cuatro números para el año y después la hora.

Las expresiones regulares solo revisan que la fecha esté bien escrita. No saben si la fecha existe: por ejemplo, un 31 de febrero tiene el formato correcto pero no existe. Eso lo controlo después, cuando convierto el texto en una fecha de Python. También reviso que la fecha no sea anterior a 2016, cuando empezó este registro, ni posterior a hoy.

## Decisiones de limpieza

- Si el identificador de la estación no es un número positivo, descarto el registro.
- Solo acepto los cinco combustibles que usa el registro oficial. Cada uno tiene su unidad: los líquidos se venden por litro y el GNC por m³. Como cada consulta es de un solo combustible, nunca se mezclan unidades.
- Si la fecha tiene un formato que no reconozco, no existe o está fuera de rango, descarto el registro.
- Si el precio no es un número o es cero, lo descarto. Un precio en cero no significa que el combustible sea gratis, es un error de carga.
- Si una estación informó el mismo precio, para el mismo combustible y horario, en la misma fecha más de una vez, lo cuento una sola vez. Esto pasa mucho porque el archivo de vigentes repite el último dato del histórico.
- Si para la misma estación, combustible, horario y fecha hay dos precios distintos, no puedo saber cuál es el bueno, así que descarto los dos. En ese caso, se usa el precio anterior de esa estación.
- Un precio con más de 30 días sin actualizarse no lo muestro como vigente. Lo cuento aparte y el programa avisa cuántas estaciones quedaron afuera.

Todo lo descartado queda guardado en un archivo de rechazos dentro de la carpeta outputs, con el archivo de origen, el número de registro y el motivo.

Si dos estaciones tienen el mismo precio, se ordenan por nombre.

## Ejemplo de resultado

```
python -m src.main --localidad Rosario --combustible super --fecha 2026-10-15 --top 5

  #     Precio  Desde       Estación
  1    2159.00  2026-10-09  MADEGAS SA (GULF) - AV. PTE PERON 6575
  2    2169.00  2026-10-01  CIRCUNVALACION SERVICIOS S.A. (DAPSA S.A.) - BAIGORRIA 2630
  3    2212.00  2026-09-22  BRIBAL AGRO SRL (PUMA) - PUEYRREDON 1089
  4    2212.00  2026-09-23  ENERGÍA & SERVICIOS SA (PUMA) - AV CÓRDOBA Y CIRCUNVALACIÓN
  5    2212.00  2026-09-29  MARIANI ENZO ROMULO (PUMA) - AV. CARLOS COLOMBRES 1552

Precios en $/litro.
Se excluyeron 72 estaciones con precios de más de 30 días.
Registros rechazados: 764
```

## Interpretación y limitaciones

Al 15/10/2026, la nafta súper más barata de Rosario, entre las estaciones con datos recientes, estaba a $2159 por litro. La diferencia con las siguientes es chica, de unos pocos pesos.

El dato más llamativo es otro: de las 87 estaciones de Rosario que alguna vez informaron precios de súper, solo 15 lo hicieron en los últimos 30 días. Si no aplicara ese filtro, la primera de la lista sería una estación con un precio de $94,70 del año 2021, que obviamente ya no rige. Por eso el límite de antigüedad es la decisión más importante del programa.

Limitaciones:

- Los precios los declaran las propias estaciones. Si una estación no informa un cambio, el programa no tiene forma de saberlo.
- En 2026 muchas estaciones de Rosario dejaron de actualizar sus datos, así que la comparación actual se hace con pocas estaciones.
- El límite de 30 días es una elección mía. Con otro valor cambia cuántas estaciones aparecen.
- El histórico incluido empieza en 2024, así que las consultas a fechas anteriores no son confiables.
- Algunas estaciones aparecen con dos identificadores distintos en la misma dirección, probablemente por un cambio de dueño. El programa las trata como estaciones distintas.

## Datos

Uso el dataset "Precios en surtidor – Resolución 314/2016" de la Secretaría de Energía, publicado en http://datos.energia.gob.ar/dataset/precios-en-surtidor con licencia Creative Commons Attribution 4.0. Lo consulté el 21/10/2026.

Cada fila es una actualización de precio: una estación, un combustible, un horario (diurno o nocturno), un precio y la fecha desde la que rige. Los archivos completos son de todo el país y pesan mucho, así que incluí solo las estaciones de Rosario. El detalle está en el README de la carpeta data.
