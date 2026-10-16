import unittest
from decimal import Decimal
from pathlib import Path
from tempfile import TemporaryDirectory

from finanzas import ErrorFinanzas, Finanzas
from finanzas.cli import main


class TestFinanzas(unittest.TestCase):
    def setUp(self):
        self.f = Finanzas()

    def tearDown(self):
        self.f.cerrar()

    def test_saldo_suma_ingresos_y_resta_gastos(self):
        self.f.agregar("ingreso", "1500", "sueldo", fecha="2026-10-01")
        self.f.agregar("gasto", "0.1", "comida", fecha="2026-10-02")
        self.f.agregar("gasto", "0,2", "comida", fecha="2026-10-03")
        self.assertEqual(self.f.saldo(), Decimal("1499.70"))

    def test_rechaza_datos_invalidos(self):
        for args in [
            ("otro", "10", "x"),
            ("gasto", "-5", "x"),
            ("gasto", "abc", "x"),
            ("gasto", "nan", "x"),
            ("gasto", "5", "  "),
        ]:
            with self.subTest(args=args), self.assertRaises(ErrorFinanzas):
                self.f.agregar(*args)
        with self.assertRaises(ErrorFinanzas):
            self.f.agregar("gasto", "5", "x", fecha="16/10/2026")

    def test_listar_filtra_por_mes_tipo_y_categoria(self):
        self.f.agregar("gasto", "10", "Comida", fecha="2026-09-30")
        self.f.agregar("gasto", "20", "comida", fecha="2026-10-01")
        self.f.agregar("gasto", "30", "ocio", fecha="2026-10-31")
        self.f.agregar("ingreso", "100", "sueldo", fecha="2026-10-15")
        self.assertEqual(len(self.f.listar(mes="2026-10")), 3)
        self.assertEqual(len(self.f.listar(tipo="gasto")), 3)
        self.assertEqual(len(self.f.listar(categoria="COMIDA")), 2)
        self.assertEqual(len(self.f.listar(mes="2026-10", categoria="comida")), 1)

    def test_mes_de_diciembre(self):
        self.f.agregar("gasto", "10", "x", fecha="2026-12-31")
        self.f.agregar("gasto", "10", "x", fecha="2027-01-01")
        self.assertEqual(len(self.f.listar(mes="2026-12")), 1)

    def test_eliminar(self):
        nuevo = self.f.agregar("gasto", "10", "x")
        self.f.eliminar(nuevo)
        self.assertEqual(self.f.listar(), [])
        with self.assertRaises(ErrorFinanzas):
            self.f.eliminar(nuevo)

    def test_resumen(self):
        self.f.agregar("ingreso", "2000", "sueldo", fecha="2026-10-01")
        self.f.agregar("gasto", "600", "alquiler", fecha="2026-10-02")
        self.f.agregar("gasto", "150.50", "comida", fecha="2026-10-03")
        self.f.agregar("gasto", "49.50", "comida", fecha="2026-10-04")
        r = self.f.resumen("2026-10")
        self.assertEqual(r.ingresos, Decimal("2000.00"))
        self.assertEqual(r.gastos, Decimal("800.00"))
        self.assertEqual(r.balance, Decimal("1200.00"))
        self.assertAlmostEqual(r.tasa_ahorro, 60.0)
        self.assertEqual(r.gastos_por_categoria["comida"], Decimal("200.00"))
        self.assertIsNone(self.f.resumen("2026-11").tasa_ahorro)

    def test_presupuestos(self):
        self.f.fijar_presupuesto("comida", "300")
        self.f.fijar_presupuesto("ocio", "50")
        self.f.fijar_presupuesto("ocio", "100")  # actualiza
        self.f.agregar("gasto", "320", "comida", fecha="2026-10-05")
        self.f.agregar("gasto", "40", "ocio", fecha="2026-10-06")
        self.f.agregar("gasto", "999", "ocio", fecha="2026-09-06")
        comida, ocio = self.f.estado_presupuestos("2026-10")
        self.assertTrue(comida.excedido)
        self.assertEqual(comida.restante, Decimal("-20.00"))
        self.assertEqual(ocio.limite, Decimal("100.00"))
        self.assertFalse(ocio.excedido)
        self.f.quitar_presupuesto("ocio")
        self.assertEqual(len(self.f.estado_presupuestos("2026-10")), 1)

    def test_categorias_por_frecuencia(self):
        self.f.agregar("gasto", "1", "ocio")
        self.f.agregar("gasto", "1", "comida")
        self.f.agregar("gasto", "1", "comida")
        self.f.agregar("ingreso", "1", "sueldo")
        self.assertEqual(self.f.categorias("gasto"), ["comida", "ocio"])

    def test_csv_ida_y_vuelta(self):
        self.f.agregar("ingreso", "1000", "sueldo", "octubre", fecha="2026-10-01")
        self.f.agregar("gasto", "12.34", "comida", "súper, pan", fecha="2026-10-02")
        with TemporaryDirectory() as tmp:
            ruta = Path(tmp) / "mov.csv"
            self.assertEqual(self.f.exportar_csv(ruta), 2)
            with Finanzas() as otra:
                self.assertEqual(otra.importar_csv(ruta), 2)
                self.assertEqual(otra.listar()[1].descripcion, "súper, pan")
                self.assertEqual(otra.saldo(), self.f.saldo())

    def test_importacion_invalida_no_inserta_nada(self):
        with TemporaryDirectory() as tmp:
            ruta = Path(tmp) / "mal.csv"
            ruta.write_text(
                "fecha,tipo,categoria,importe\n"
                "2026-10-01,gasto,comida,10\n"
                "2026-10-02,gasto,comida,-3\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ErrorFinanzas, "Línea 3"):
                self.f.importar_csv(ruta)
        self.assertEqual(self.f.listar(), [])


class TestCli(unittest.TestCase):
    def test_flujo_completo(self):
        with TemporaryDirectory() as tmp:
            db = str(Path(tmp) / "f.db")
            self.assertEqual(main(["--db", db, "ingreso", "1000", "sueldo"]), 0)
            self.assertEqual(main(["--db", db, "gasto", "25,5", "comida", "-d", "cena"]), 0)
            self.assertEqual(main(["--db", db, "presupuesto", "fijar", "comida", "200"]), 0)
            for comando in (["listar"], ["saldo"], ["resumen"], ["presupuesto", "estado"]):
                self.assertEqual(main(["--db", db, *comando]), 0)
            self.assertEqual(main(["--db", db, "eliminar", "99"]), 1)
            with Finanzas(db) as f:
                self.assertEqual(f.saldo(), Decimal("974.50"))


if __name__ == "__main__":
    unittest.main()
