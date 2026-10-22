"""Lógica de la aplicación: normalizar, limpiar, elegir precios vigentes y buscar.

Las funciones reciben datos YA CARGADOS (listas de diccionarios), así que no
dependen de si el archivo original era CSV o JSON.
"""

import csv
import json
from datetime import datetime
from pathlib import Path

from .fuentes import obtener_fuente
from .modelo import COMBUSTIBLES, HORARIOS, convertir_fecha, normalizar_texto

COLUMNAS_REQUERIDAS = {"idempresa", "empresa", "direccion", "localidad", "provincia",
                       "producto", "tipohorario", "precio", "fecha_vigencia"}

# Nombre oficial del producto -> unidad en que se vende.
UNIDADES = {nombre: unidad for nombre, unidad in COMBUSTIBLES.values()}

# El registro de precios empezó con la Resolución 314/2016: antes de 2016 no puede haber datos.
FECHA_MINIMA = datetime(2016, 1, 1)


class ErrorValidacion(ValueError):
    """Los datos no cumplen las condiciones mínimas para el análisis."""


# ---------------------------------------------------------------- validación

def validar_esquema(filas, nombre):
    """Comprueba que el archivo tenga filas y todas las columnas necesarias."""
    if not filas:
        raise ErrorValidacion(f"'{nombre}' no tiene filas.")
    faltantes = COLUMNAS_REQUERIDAS - set(filas[0].keys())
    if faltantes:
        raise ErrorValidacion(f"A '{nombre}' le faltan columnas: {sorted(faltantes)}")


def convertir_precio(texto):
    """Convierte el precio a float. Acepta '1514', '1514.5' o '1514,5'. None si no es válido."""
    try:
        precio = float((texto or "").strip().replace(",", "."))
    except ValueError:
        return None
    return precio if precio > 0 else None


def _rechazo(archivo, fila, motivo, contenido):
    return {"archivo": archivo, "fila": fila, "motivo": motivo,
            "contenido": json.dumps(contenido, ensure_ascii=False)}


# ---------------------------------------------------------------- limpieza

def normalizar_precios(filas, archivo):
    """Convierte cada fila en un registro limpio. Devuelve (registros, rechazos).

    Reglas:
      - idempresa (la estación) debe ser un entero positivo.
      - el producto debe ser uno de los cinco combustibles conocidos.
      - el horario debe ser Diurno o Nocturno.
      - la fecha debe tener un formato válido, existir en el calendario,
        ser posterior a 2016 y no estar en el futuro.
      - el precio debe ser un número mayor que cero.
    """
    registros, rechazos = [], []
    ahora = datetime.now()
    for i, fila in enumerate(filas, start=1):  # número de registro, sin contar el encabezado
        try:
            estacion = int(fila["idempresa"])
        except ValueError:
            estacion = 0
        if estacion <= 0:
            rechazos.append(_rechazo(archivo, i, "estación inválida", fila))
            continue
        producto = fila["producto"].strip()
        if producto not in UNIDADES:
            rechazos.append(_rechazo(archivo, i, "combustible desconocido", fila))
            continue
        horario = fila["tipohorario"].strip().capitalize()
        if horario not in HORARIOS.values():
            rechazos.append(_rechazo(archivo, i, "horario inválido", fila))
            continue
        fecha = convertir_fecha(fila["fecha_vigencia"])
        if fecha is None:
            rechazos.append(_rechazo(archivo, i, "fecha con formato inválido", fila))
            continue
        if not FECHA_MINIMA <= fecha <= ahora:
            rechazos.append(_rechazo(archivo, i, "fecha fuera de rango", fila))
            continue
        precio = convertir_precio(fila["precio"])
        if precio is None:
            rechazos.append(_rechazo(archivo, i, "precio inválido o cero", fila))
            continue
        registros.append({
            "estacion": estacion,
            "empresa": fila["empresa"].strip(),
            "bandera": fila.get("empresabandera", "").strip(),
            "direccion": fila["direccion"].strip(),
            "localidad": normalizar_texto(fila["localidad"]),
            "provincia": normalizar_texto(fila["provincia"]),
            "producto": producto,
            "unidad": UNIDADES[producto],
            "horario": horario,
            "precio": precio,
            "fecha": fecha,
            "archivo": archivo,
            "fila": i,
        })
    return registros, rechazos


def resolver_duplicados(registros):
    """Junta registros repetidos entre archivos y descarta los contradictorios.

    Clave: misma estación, combustible, horario y fecha de vigencia.
      - mismo precio  -> es el mismo dato informado dos veces: se conserva uno.
      - precio distinto -> no se puede saber cuál es el correcto: se descartan todos.
    Devuelve (registros_unicos, rechazos).
    """
    grupos = {}
    for r in registros:
        clave = (r["estacion"], r["producto"], r["horario"], r["fecha"])
        grupos.setdefault(clave, []).append(r)

    unicos, rechazos = [], []
    for grupo in grupos.values():
        precios = {r["precio"] for r in grupo}
        if len(precios) == 1:
            unicos.append(grupo[0])
            for r in grupo[1:]:
                rechazos.append(_rechazo(r["archivo"], r["fila"], "duplicado", _resumen(r)))
        else:
            for r in grupo:
                rechazos.append(_rechazo(r["archivo"], r["fila"], "precios contradictorios",
                                         _resumen(r)))
    return unicos, rechazos


def _resumen(r):
    return {"estacion": r["estacion"], "producto": r["producto"], "horario": r["horario"],
            "precio": r["precio"], "fecha": f"{r['fecha']:%Y-%m-%d %H:%M}"}


# ---------------------------------------------------------------- análisis

def seleccionar_vigentes(registros, consulta):
    """Para cada estación, se queda con el precio más reciente que NO supere la fecha de consulta.

    Solo considera los registros del combustible, horario y lugar de la consulta,
    así nunca se mezclan combustibles ni unidades distintas.
    """
    vigentes = {}
    for r in registros:
        if not consulta.coincide(r) or r["fecha"] > consulta.fecha:
            continue
        actual = vigentes.get(r["estacion"])
        if actual is None or r["fecha"] > actual["fecha"]:
            vigentes[r["estacion"]] = r
    return list(vigentes.values())


def buscar_estaciones(registros, consulta):
    """Devuelve (resultado, desactualizadas).

    resultado: estaciones con su precio vigente, de la más barata a la más cara
    (a igual precio, por nombre de la estación).
    desactualizadas: estaciones cuyo último precio tiene más de consulta.max_dias días.
    Se separan porque un precio viejo no es confiable y aparecería como "el más barato".
    """
    vigentes = seleccionar_vigentes(registros, consulta)
    resultado, desactualizadas = [], []
    for r in sorted(vigentes, key=lambda r: (r["precio"], r["empresa"])):
        if (consulta.fecha - r["fecha"]).days > consulta.max_dias:
            desactualizadas.append(r)
            continue
        resultado.append({
            "estacion": r["estacion"],
            "empresa": r["empresa"],
            "bandera": r["bandera"],
            "direccion": r["direccion"],
            "combustible": r["producto"],
            "precio": r["precio"],
            "unidad": f"$/{r['unidad']}",
            "vigente_desde": f"{r['fecha']:%Y-%m-%d %H:%M}",
            "dias_sin_actualizar": (consulta.fecha - r["fecha"]).days,
        })
    if consulta.top:
        resultado = resultado[: consulta.top]
    return resultado, desactualizadas


def verificar_resultado(resultado, consulta):
    """Controla propiedades que el resultado SIEMPRE debe cumplir."""
    estaciones = [f["estacion"] for f in resultado]
    if len(estaciones) != len(set(estaciones)):
        raise ErrorValidacion("Una estación aparece más de una vez en el resultado.")
    for f in resultado:
        if f["combustible"] != consulta.producto or f["unidad"] != f"$/{consulta.unidad}":
            raise ErrorValidacion("El resultado mezcla combustibles o unidades.")
        if f["precio"] <= 0:
            raise ErrorValidacion(f"Precio no válido en {f['empresa']}.")
        if f["vigente_desde"] > f"{consulta.fecha:%Y-%m-%d %H:%M}":
            raise ErrorValidacion(f"{f['empresa']} tiene un precio posterior a la consulta.")
        if not 0 <= f["dias_sin_actualizar"] <= consulta.max_dias:
            raise ErrorValidacion(f"{f['empresa']} tiene un precio desactualizado.")
    precios = [f["precio"] for f in resultado]
    if precios != sorted(precios):
        raise ErrorValidacion("El resultado no está ordenado por precio.")


# ---------------------------------------------------------------- salida

def guardar_csv(filas, ruta, columnas):
    """Guarda una lista de diccionarios como CSV (crea la carpeta si no existe)."""
    ruta = Path(ruta)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    with open(ruta, "w", encoding="utf-8", newline="") as f:
        escritor = csv.DictWriter(f, fieldnames=columnas)
        escritor.writeheader()
        escritor.writerows(filas)


def exportar_consulta(resultado, ruta, consulta):
    """Guarda el resultado con la fecha de consulta en cada fila."""
    fecha = f"{consulta.fecha:%Y-%m-%d %H:%M}"
    filas = [{"fecha_consulta": fecha, **f} for f in resultado]
    columnas = ["fecha_consulta", "estacion", "empresa", "bandera", "direccion", "combustible",
                "precio", "unidad", "vigente_desde", "dias_sin_actualizar"]
    guardar_csv(filas, ruta, columnas)


# ---------------------------------------------------------------- flujo completo

def cargar_y_limpiar(rutas):
    """leer -> validar esquema -> normalizar -> resolver duplicados. Devuelve (registros, rechazos)."""
    todos, rechazos = [], []
    for ruta in rutas:
        filas = obtener_fuente(ruta).cargar(ruta)
        nombre = Path(ruta).name
        validar_esquema(filas, nombre)
        registros, rech = normalizar_precios(filas, nombre)
        todos.extend(registros)
        rechazos.extend(rech)
    unicos, rech = resolver_duplicados(todos)
    return unicos, rechazos + rech


def ejecutar(rutas, consulta):
    """Flujo completo. Devuelve (resultado, desactualizadas, rechazos)."""
    registros, rechazos = cargar_y_limpiar(rutas)
    resultado, desactualizadas = buscar_estaciones(registros, consulta)
    verificar_resultado(resultado, consulta)
    return resultado, desactualizadas, rechazos
