"""Fuentes de datos: lectura de archivos CSV y JSON con una interfaz común.

Todas las fuentes devuelven la MISMA representación: una lista de
diccionarios, donde cada diccionario es una fila y todos los valores son
texto (str). Así, el resto del programa no depende del formato de origen.
"""

import csv
import json
from abc import ABC, abstractmethod
from pathlib import Path


class ErrorFuente(Exception):
    """Error al leer una fuente de datos (archivo inexistente, mal formado, etc.)."""


class FuenteDatos(ABC):
    """Contrato común para todas las fuentes de datos.

    Cualquier clase hija DEBE implementar cargar(ruta). Gracias a esto,
    el pipeline puede trabajar con cualquier fuente sin saber si es CSV o JSON.
    """

    def cargar(self, ruta):
        """Verifica que el archivo exista y delega la lectura en _leer()."""
        ruta = Path(ruta)
        if not ruta.is_file():
            raise ErrorFuente(f"No se encontró el archivo: {ruta}")
        filas = self._leer(ruta)
        # Normalizamos: todas las claves y valores pasan a texto sin espacios extra.
        return [
            {str(k).strip(): ("" if v is None else str(v).strip()) for k, v in fila.items()}
            for fila in filas
        ]

    @abstractmethod
    def _leer(self, ruta):
        """Lee el archivo y devuelve una lista de diccionarios."""


class FuenteCSV(FuenteDatos):
    """Lee un CSV con encabezado en la primera fila."""

    def _leer(self, ruta):
        try:
            with open(ruta, encoding="utf-8", newline="") as f:
                lector = csv.DictReader(f)
                if lector.fieldnames is None:
                    raise ErrorFuente(f"El CSV está vacío: {ruta}")
                return list(lector)
        except UnicodeDecodeError as e:
            raise ErrorFuente(f"El CSV no está en UTF-8: {ruta}") from e


class FuenteJSON(FuenteDatos):
    """Lee un JSON cuyo contenido es una LISTA de objetos (uno por fila)."""

    def _leer(self, ruta):
        try:
            with open(ruta, encoding="utf-8") as f:
                datos = json.load(f)
        except json.JSONDecodeError as e:
            raise ErrorFuente(f"JSON mal formado en {ruta}: {e}") from e
        if not isinstance(datos, list) or not all(isinstance(x, dict) for x in datos):
            raise ErrorFuente(f"El JSON debe ser una lista de objetos: {ruta}")
        return datos


def obtener_fuente(ruta):
    """Elige la fuente adecuada según la extensión del archivo."""
    extension = Path(ruta).suffix.lower()
    if extension == ".csv":
        return FuenteCSV()
    if extension == ".json":
        return FuenteJSON()
    raise ErrorFuente(f"Formato no soportado: '{extension}' (use .csv o .json)")
