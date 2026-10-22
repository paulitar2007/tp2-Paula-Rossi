"""Modelo del dominio: la consulta de precios que hace quien usa el programa."""

import re
import unicodedata
from datetime import datetime

# Nombres oficiales de los combustibles en los datos de la Secretaría de Energía,
# con el alias corto que se usa en la terminal y la unidad en que se vende cada uno.
COMBUSTIBLES = {
    "super": ("Nafta (súper) entre 92 y 95 Ron", "litro"),
    "premium": ("Nafta (premium) de más de 95 Ron", "litro"),
    "gasoil": ("Gas Oil Grado 2", "litro"),
    "gasoil-premium": ("Gas Oil Grado 3", "litro"),
    "gnc": ("GNC", "m3"),
}
HORARIOS = {"diurno": "Diurno", "nocturno": "Nocturno"}

# Fechas que aceptan los archivos:
#   - 2026-09-24 11:13:00  o  2026-09-24 11:13   (archivo de precios vigentes)
#   - 24/09/2026 11:13                           (archivo de precios históricos)
#   - 2026-09-24                                 (fecha de consulta escrita por el usuario)
# Cada \d{n} pide exactamente n dígitos; (?: ... )? marca una parte opcional.
# La regex solo controla el FORMATO. Si la fecha existe en el calendario
# (por ejemplo, que no sea 31/02) lo controla datetime() en convertir_fecha.
PATRON_FECHA_ISO = re.compile(r"^(\d{4})-(\d{2})-(\d{2})(?:[ T](\d{2}):(\d{2})(?::(\d{2}))?)?$")
PATRON_FECHA_AR = re.compile(r"^(\d{2})/(\d{2})/(\d{4}) (\d{2}):(\d{2})$")


class ErrorConsulta(ValueError):
    """Parámetros de consulta inválidos."""


def convertir_fecha(texto):
    """Convierte un texto en datetime. Devuelve None si el formato o la fecha no son válidos."""
    texto = (texto or "").strip()
    m = PATRON_FECHA_ISO.match(texto)
    if m:
        anio, mes, dia, hora, minuto, seg = m.groups()
    else:
        m = PATRON_FECHA_AR.match(texto)
        if not m:
            return None
        dia, mes, anio, hora, minuto = m.groups()
        seg = None
    try:
        return datetime(int(anio), int(mes), int(dia),
                        int(hora or 0), int(minuto or 0), int(seg or 0))
    except ValueError:  # fecha imposible, por ejemplo 31/02 o 25:00
        return None


def normalizar_texto(texto):
    """Pasa a mayúsculas y saca tildes y espacios extra, para comparar localidades."""
    texto = unicodedata.normalize("NFKD", (texto or "").strip().upper())
    sin_tildes = "".join(c for c in texto if not unicodedata.combining(c))
    return " ".join(sin_tildes.split())


class ConsultaPrecio:
    """Representa y valida una consulta: qué combustible, dónde y a qué fecha.

    Atributos:
        localidad: localidad normalizada (sin tildes, en mayúsculas).
        provincia: provincia normalizada, o None para no filtrar.
        alias: alias del combustible ("super", "gnc", ...).
        producto: nombre oficial del combustible.
        unidad: "litro" o "m3".
        fecha: datetime de referencia; cuenta el precio vigente a ese momento.
        horario: "Diurno" o "Nocturno".
        max_dias: antigüedad máxima (en días) para considerar válido un precio.
        top: cantidad máxima de estaciones a mostrar, o None para todas.
    """

    def __init__(self, localidad, combustible, fecha=None, provincia=None,
                 horario="diurno", max_dias=30, top=None):
        self.localidad = normalizar_texto(localidad)
        if not self.localidad:
            raise ErrorConsulta("Hay que indicar una localidad.")
        self.provincia = normalizar_texto(provincia) or None

        self.alias = (combustible or "").strip().lower()
        if self.alias not in COMBUSTIBLES:
            raise ErrorConsulta(f"Combustible desconocido: '{combustible}'. "
                                f"Opciones: {', '.join(COMBUSTIBLES)}")
        self.producto, self.unidad = COMBUSTIBLES[self.alias]

        if fecha is None:
            self.fecha = datetime.now()
        else:
            self.fecha = convertir_fecha(fecha)
            if self.fecha is None:
                raise ErrorConsulta(f"Fecha inválida: '{fecha}'. Usar AAAA-MM-DD.")
            m = PATRON_FECHA_ISO.match(fecha.strip())
            if m and m.group(4) is None:
                # Si solo se indica el día, cuentan los precios hasta el final de ese día.
                self.fecha = self.fecha.replace(hour=23, minute=59, second=59)

        if (horario or "").lower() not in HORARIOS:
            raise ErrorConsulta("El horario debe ser 'diurno' o 'nocturno'.")
        self.horario = HORARIOS[horario.lower()]

        if not isinstance(max_dias, int) or max_dias < 0:
            raise ErrorConsulta("'max_dias' debe ser un entero >= 0.")
        self.max_dias = max_dias

        if top is not None and (not isinstance(top, int) or top < 1):
            raise ErrorConsulta("'top' debe ser un entero >= 1.")
        self.top = top

    def coincide(self, registro):
        """True si el registro es del combustible, horario y lugar pedidos."""
        return (registro["producto"] == self.producto
                and registro["horario"] == self.horario
                and registro["localidad"] == self.localidad
                and (self.provincia is None or registro["provincia"] == self.provincia))

    def __repr__(self):
        return (f"ConsultaPrecio(localidad={self.localidad!r}, provincia={self.provincia!r}, "
                f"combustible={self.alias!r}, fecha={self.fecha:%Y-%m-%d %H:%M}, "
                f"horario={self.horario!r}, max_dias={self.max_dias})")
