"""Punto de entrada. Ejemplo:

    python -m src.main --localidad Rosario --combustible super --fecha 2026-10-01
"""

import argparse
import sys

from .fuentes import ErrorFuente
from .modelo import COMBUSTIBLES, ConsultaPrecio, ErrorConsulta
from .pipeline import ErrorValidacion, ejecutar, exportar_consulta, guardar_csv

ARCHIVOS_POR_DEFECTO = ["data/rosario_historicos.csv", "data/rosario_vigentes.csv"]
COLUMNAS_RECHAZOS = ["archivo", "fila", "motivo", "contenido"]


def leer_argumentos(argv=None):
    p = argparse.ArgumentParser(description="Buscador de precios vigentes de combustibles.")
    p.add_argument("--precios", nargs="+", default=ARCHIVOS_POR_DEFECTO,
                   help="uno o más archivos de precios (.csv o .json)")
    p.add_argument("--localidad", required=True, help="localidad, p. ej. Rosario")
    p.add_argument("--combustible", required=True, choices=list(COMBUSTIBLES),
                   help="tipo de combustible")
    p.add_argument("--fecha", help="fecha de referencia AAAA-MM-DD (por defecto, hoy)")
    p.add_argument("--provincia", help="provincia, para distinguir localidades con el mismo nombre")
    p.add_argument("--horario", default="diurno", choices=["diurno", "nocturno"])
    p.add_argument("--max-dias", type=int, default=30,
                   help="días máximos desde la última actualización (por defecto 30)")
    p.add_argument("--top", type=int, help="cantidad de estaciones a mostrar")
    p.add_argument("--salida", default="outputs/consulta.csv", help="CSV del resultado")
    p.add_argument("--rechazos", default="outputs/rechazos.csv", help="CSV de registros rechazados")
    return p.parse_args(argv)


def mostrar(resultado, consulta):
    print(f"{consulta.producto} en {consulta.localidad}, vigente al {consulta.fecha:%d/%m/%Y %H:%M}\n")
    if not resultado:
        print("No hay estaciones con precio informado para esa consulta.")
        return
    print(f"{'#':>3}  {'Precio':>9}  {'Desde':10}  Estación")
    for i, f in enumerate(resultado, start=1):
        print(f"{i:>3}  {f['precio']:>9.2f}  {f['vigente_desde'][:10]}  "
              f"{f['empresa']} ({f['bandera']}) - {f['direccion']}")
    print(f"\nPrecios en {resultado[0]['unidad']}.")


def main(argv=None):
    args = leer_argumentos(argv)
    try:
        consulta = ConsultaPrecio(args.localidad, args.combustible, fecha=args.fecha,
                                  provincia=args.provincia, horario=args.horario,
                                  max_dias=args.max_dias, top=args.top)
        resultado, desactualizadas, rechazos = ejecutar(args.precios, consulta)
    except (ErrorFuente, ErrorValidacion, ErrorConsulta) as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    mostrar(resultado, consulta)
    if desactualizadas:
        print(f"Se excluyeron {len(desactualizadas)} estaciones con precios de más de "
              f"{consulta.max_dias} días.")
    exportar_consulta(resultado, args.salida, consulta)
    guardar_csv(rechazos, args.rechazos, COLUMNAS_RECHAZOS)
    print(f"Resultado guardado en {args.salida}")
    print(f"Registros rechazados: {len(rechazos)} (detalle en {args.rechazos})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
