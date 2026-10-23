"""Pruebas del buscador de precios. Ejecutar desde la raíz del repo:  python -m unittest -v"""

import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from src.fuentes import ErrorFuente, FuenteJSON, obtener_fuente
from src.modelo import ConsultaPrecio, ErrorConsulta, convertir_fecha, normalizar_texto
from src.pipeline import (ErrorValidacion, buscar_estaciones, cargar_y_limpiar, convertir_precio,
                          ejecutar, normalizar_precios, resolver_duplicados, validar_esquema)

DATA = Path(__file__).resolve().parent.parent / "data"
MUESTRA_CSV = DATA / "muestra_precios.csv"
MUESTRA_JSON = DATA / "muestra_precios.json"
SUPER = "Nafta (súper) entre 92 y 95 Ron"


def fila(id_="1", nombre="EST", precio="1000", fecha="2026-09-20 10:00:00",
         producto=SUPER, localidad="PUEBLO", horario="Diurno"):
    return {"idempresa": id_, "empresa": nombre, "direccion": "X", "localidad": localidad,
            "provincia": "SANTA FE", "producto": producto, "tipohorario": horario,
            "precio": precio, "fecha_vigencia": fecha, "empresabandera": "B"}


def consulta(fecha="2026-10-01", **kw):
    return ConsultaPrecio("Pueblo", "super", fecha=fecha, **kw)


def buscar(filas, c):
    registros, _ = normalizar_precios(filas, "test")
    registros, _ = resolver_duplicados(registros)
    return buscar_estaciones(registros, c)


class TestCasoNormal(unittest.TestCase):
    def test_estacion_con_dos_actualizaciones_devuelve_la_mas_reciente(self):
        """Consigna: una estación con dos actualizaciones debe devolver la correcta."""
        filas = [fila(precio="1000", fecha="01/09/2026 10:00"),
                 fila(precio="1100", fecha="2026-09-20 10:00:00")]
        resultado, _ = buscar(filas, consulta())
        self.assertEqual(len(resultado), 1)
        self.assertEqual(resultado[0]["precio"], 1100)

    def test_ordena_por_precio_y_desempata_por_nombre(self):
        filas = [fila("1", "NORTE", "1100"), fila("2", "SUR", "1050"), fila("3", "ESTE", "1100")]
        resultado, _ = buscar(filas, consulta())
        self.assertEqual([f["empresa"] for f in resultado], ["SUR", "ESTE", "NORTE"])

    def test_muestra_completa(self):
        resultado, desactualizadas, rechazos = ejecutar(
            [MUESTRA_CSV], ConsultaPrecio("pueblo ejemplo", "super", fecha="2026-10-01"))
        self.assertEqual([(f["empresa"], f["precio"]) for f in resultado],
                         [("ESTACION SUR", 1050), ("ESTACION ESTE", 1100),
                          ("ESTACION NORTE", 1100)])
        self.assertEqual(len(desactualizadas), 2)
        self.assertEqual(len(rechazos), 11)  # 8 filas con errores + 1 duplicado + 2 contradictorios


class TestFechasYRegex(unittest.TestCase):
    def test_formatos_aceptados(self):
        esperado = datetime(2026, 9, 24, 11, 13)
        self.assertEqual(convertir_fecha("2026-09-24 11:13:00"), esperado)
        self.assertEqual(convertir_fecha("2026-09-24 11:13"), esperado)
        self.assertEqual(convertir_fecha("24/09/2026 11:13"), esperado)

    def test_formato_invalido(self):
        for texto in ["2026/09/24", "24-09-2026", "", "ayer", "2026-9-24"]:
            self.assertIsNone(convertir_fecha(texto), texto)

    def test_fecha_que_no_existe_en_el_calendario(self):
        """La regex acepta el formato, pero el 31/02 no existe."""
        self.assertIsNone(convertir_fecha("31/02/2026 10:00"))
        self.assertIsNone(convertir_fecha("2026-02-29"))  # 2026 no es bisiesto

    def test_localidad_sin_tildes_ni_mayusculas(self):
        self.assertEqual(normalizar_texto("  Villa  Constitución "), "VILLA CONSTITUCION")


class TestEntradasInvalidasYLimites(unittest.TestCase):
    def test_actualizacion_posterior_a_la_consulta_queda_excluida(self):
        """Consigna: una actualización posterior a la fecha de consulta no cuenta."""
        filas = [fila(precio="1000", fecha="2026-09-20 10:00:00"),
                 fila(precio="1500", fecha="2026-10-05 10:00:00")]
        resultado, _ = buscar(filas, consulta(fecha="2026-10-01"))
        self.assertEqual(resultado[0]["precio"], 1000)

    def test_localidad_sin_resultados(self):
        """Consigna: una localidad sin resultados devuelve una lista vacía, no un error."""
        resultado, desactualizadas = buscar([fila()], ConsultaPrecio("Inexistente", "super",
                                                                     fecha="2026-10-01"))
        self.assertEqual(resultado, [])
        self.assertEqual(desactualizadas, [])

    def test_precio_desactualizado_se_excluye(self):
        filas = [fila(precio="700", fecha="2025-01-01 06:00:00")]
        resultado, desactualizadas = buscar(filas, consulta())
        self.assertEqual(resultado, [])
        self.assertEqual(len(desactualizadas), 1)

    def test_precios_contradictorios_se_descartan(self):
        filas = [fila(precio="990", fecha="18/09/2026 07:00"),
                 fila(precio="995", fecha="18/09/2026 07:00")]
        registros, _ = normalizar_precios(filas, "test")
        unicos, rechazos = resolver_duplicados(registros)
        self.assertEqual(unicos, [])
        self.assertEqual([r["motivo"] for r in rechazos], ["precios contradictorios"] * 2)

    def test_duplicado_en_distinto_formato_se_cuenta_una_vez(self):
        filas = [fila(fecha="15/09/2026 09:30"), fila(fecha="2026-09-15 09:30:00")]
        registros, _ = normalizar_precios(filas, "test")
        unicos, rechazos = resolver_duplicados(registros)
        self.assertEqual(len(unicos), 1)
        self.assertEqual(rechazos[0]["motivo"], "duplicado")

    def test_no_mezcla_combustibles(self):
        filas = [fila(precio="1100"), fila(precio="500", producto="GNC")]
        resultado, _ = buscar(filas, consulta())
        self.assertEqual([f["combustible"] for f in resultado], [SUPER])

    def test_filas_invalidas(self):
        filas = [fila(id_="abc"), fila(producto="Kerosene"), fila(horario="Tarde"),
                 fila(fecha="31/02/2026 10:00"), fila(fecha="01/01/1157 00:00"),
                 fila(precio="0"), fila(precio="abc")]
        registros, rechazos = normalizar_precios(filas, "test")
        self.assertEqual(registros, [])
        self.assertEqual(len(rechazos), 7)

    def test_convertir_precio(self):
        self.assertEqual(convertir_precio("1514"), 1514.0)
        self.assertEqual(convertir_precio("1514,5"), 1514.5)
        self.assertIsNone(convertir_precio("0"))
        self.assertIsNone(convertir_precio("-3"))
        self.assertIsNone(convertir_precio(""))

    def test_consulta_invalida(self):
        with self.assertRaises(ErrorConsulta):
            ConsultaPrecio("Rosario", "kerosene")
        with self.assertRaises(ErrorConsulta):
            ConsultaPrecio("", "super")
        with self.assertRaises(ErrorConsulta):
            ConsultaPrecio("Rosario", "super", fecha="2026-02-30")
        with self.assertRaises(ErrorConsulta):
            ConsultaPrecio("Rosario", "super", max_dias=-1)

    def test_esquema_incompleto(self):
        with self.assertRaises(ErrorValidacion):
            validar_esquema([{"idempresa": "1"}], "precios")

    def test_archivo_inexistente(self):
        with self.assertRaises(ErrorFuente):
            obtener_fuente("no_existe.csv").cargar("no_existe.csv")

    def test_json_mal_formado(self):
        with tempfile.TemporaryDirectory() as d:
            ruta = Path(d) / "malo.json"
            ruta.write_text('{"no": "es una lista"}', encoding="utf-8")
            with self.assertRaises(ErrorFuente):
                FuenteJSON().cargar(ruta)


class TestPropiedadesDelResultado(unittest.TestCase):
    def test_csv_y_json_dan_el_mismo_resultado(self):
        c = ConsultaPrecio("pueblo ejemplo", "super", fecha="2026-10-01")
        r_csv = ejecutar([MUESTRA_CSV], c)
        r_json = ejecutar([MUESTRA_JSON], c)
        self.assertEqual(r_csv[0], r_json[0])
        self.assertEqual(len(r_csv[2]), len(r_json[2]))

    def test_no_se_pierden_registros(self):
        """Registros válidos + rechazados = registros leídos."""
        filas = obtener_fuente(MUESTRA_CSV).cargar(MUESTRA_CSV)
        unicos, rechazos = cargar_y_limpiar([MUESTRA_CSV])
        self.assertEqual(len(unicos) + len(rechazos), len(filas))

    def test_una_estacion_por_resultado_y_ninguna_fecha_posterior(self):
        c = ConsultaPrecio("pueblo ejemplo", "super", fecha="2026-10-01", max_dias=10000)
        resultado, _, _ = ejecutar([MUESTRA_CSV], c)
        ids = [f["estacion"] for f in resultado]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertTrue(all(f["vigente_desde"] <= "2026-10-01 23:59" for f in resultado))


if __name__ == "__main__":
    unittest.main()
