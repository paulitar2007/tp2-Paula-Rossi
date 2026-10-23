"""Genera la MUESTRA DE PRUEBA en data/ (CSV y JSON con el mismo contenido).

Son estaciones inventadas, con casos conocidos para comprobar que el programa
elige bien el precio vigente, y con errores puestos a propósito para probar la limpieza.

Uso:  python scripts/generar_muestra.py
"""

import csv
import json
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "data"
COLUMNAS = ["idempresa", "empresa", "direccion", "localidad", "provincia", "producto",
            "tipohorario", "precio", "fecha_vigencia", "empresabandera"]
SUPER = "Nafta (súper) entre 92 y 95 Ron"
LUGAR = ("PUEBLO EJEMPLO", "SANTA FE")


def fila(id_, nombre, producto, precio, fecha, horario="Diurno", lugar=LUGAR):
    return [id_, nombre, f"Calle {id_} 100", lugar[0], lugar[1], producto,
            horario, precio, fecha, "BANDERA PRUEBA"]


FILAS = [
    # Estación 1: tres actualizaciones de súper. Al 01/10/2026 vale la del 20/09.
    fila("1", "ESTACION NORTE", SUPER, "1000", "01/09/2026 10:00"),   # formato histórico
    fila("1", "ESTACION NORTE", SUPER, "1100", "2026-09-20 10:00:00"),  # formato vigentes
    fila("1", "ESTACION NORTE", SUPER, "1200", "2026-10-05 10:00:00"),  # posterior a la consulta
    fila("1", "ESTACION NORTE", "GNC", "500", "2026-09-10 08:00:00"),
    fila("1", "ESTACION NORTE", SUPER, "1100", "2026-09-20 10:00:00", horario="Nocturno"),
    # Estación 2: el mismo dato informado en los dos formatos (duplicado).
    fila("2", "ESTACION SUR", SUPER, "1050", "15/09/2026 09:30"),
    fila("2", "ESTACION SUR", SUPER, "1050", "2026-09-15 09:30:00"),
    # Estación 3: dos precios distintos para la misma fecha (contradictorios).
    # Se descartan los dos y queda el precio anterior, que tiene más de 30 días.
    fila("3", "ESTACION OESTE", SUPER, "980", "01/08/2026 07:00"),
    fila("3", "ESTACION OESTE", SUPER, "990", "18/09/2026 07:00"),
    fila("3", "ESTACION OESTE", SUPER, "995", "18/09/2026 07:00"),
    # Estación 4: mismo precio que la estación 1 (para probar el desempate por nombre).
    fila("4", "ESTACION ESTE", SUPER, "1100", "2026-09-25 12:00:00"),
    # Estación 5: precio muy viejo (desactualizado).
    fila("5", "ESTACION VIEJA", SUPER, "700", "01/01/2025 06:00"),
    # Estación 6: otra localidad.
    fila("6", "ESTACION LEJANA", SUPER, "900", "2026-09-20 10:00:00",
         lugar=("OTRO PUEBLO", "SANTA FE")),
    # --- filas con errores intencionales ---
    fila("abc", "ID INVALIDO", SUPER, "1000", "2026-09-20 10:00:00"),
    fila("7", "COMBUSTIBLE RARO", "Kerosene", "1000", "2026-09-20 10:00:00"),
    fila("7", "HORARIO RARO", SUPER, "1000", "2026-09-20 10:00:00", horario="Tarde"),
    fila("7", "FECHA IMPOSIBLE", SUPER, "1000", "31/02/2026 10:00"),
    fila("7", "FECHA MAL ESCRITA", SUPER, "1000", "2026/09/20"),
    fila("7", "FECHA ANTIGUA", SUPER, "1000", "01/01/1157 00:00"),
    fila("7", "PRECIO CERO", SUPER, "0", "2026-09-20 10:00:00"),
    fila("7", "PRECIO TEXTO", SUPER, "abc", "2026-09-20 10:00:00"),
]


def escribir():
    DATA.mkdir(exist_ok=True)
    registros = [dict(zip(COLUMNAS, f)) for f in FILAS]
    with open(DATA / "muestra_precios.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNAS)
        w.writeheader()
        w.writerows(registros)
    with open(DATA / "muestra_precios.json", "w", encoding="utf-8") as f:
        json.dump(registros, f, ensure_ascii=False, indent=2)
    print(f"muestra_precios: {len(registros)} registros (CSV y JSON)")


if __name__ == "__main__":
    escribir()
