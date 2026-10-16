import unittest
from datetime import date

from finanzas import Finanzas
from finanzas.recomendaciones import AVISO, BIEN, CONSEJO, recomendar

HOY = date(2026, 10, 10)


class TestRecomendaciones(unittest.TestCase):
    def setUp(self):
        self.f = Finanzas()

    def tearDown(self):
        self.f.cerrar()

    def textos(self, nivel=None):
        return [r.texto for r in recomendar(self.f, HOY) if nivel in (None, r.nivel)]

    def test_sin_datos_da_consejo_inicial(self):
        (texto,) = self.textos(CONSEJO)
        self.assertIn("Registra", texto)

    def test_presupuesto_excedido_y_proyectado(self):
        self.f.fijar_presupuesto("ocio", 100)
        self.f.fijar_presupuesto("comida", 300)
        self.f.agregar("gasto", 120, "ocio", fecha="2026-10-02")
        self.f.agregar("gasto", 150, "comida", fecha="2026-10-03")  # 150/10*31 = 465 > 300
        avisos = self.textos(AVISO)
        self.assertTrue(any("superado el presupuesto de ocio en 20,00 €" in a for a in avisos))
        self.assertTrue(any("comida" in a and "465,00 €" in a for a in avisos))

    def test_subida_respecto_a_la_media(self):
        for mes in ("07", "08", "09"):
            self.f.agregar("gasto", 50, "ocio", fecha=f"2026-{mes}-05")
        self.f.agregar("gasto", 100, "ocio", fecha="2026-10-05")
        self.assertTrue(any("100 % más" in t for t in self.textos(CONSEJO)))

    def test_deficit_y_ahorro(self):
        self.f.agregar("ingreso", 1000, "sueldo", fecha="2026-10-01")
        self.f.agregar("gasto", 1200, "vivienda", fecha="2026-10-02")
        self.assertTrue(any("déficit" in t for t in self.textos(AVISO)))
        self.f.agregar("ingreso", 2000, "extra", fecha="2026-10-03")
        self.assertTrue(any("Ahorras un 60 %" in t for t in self.textos(BIEN)))

    def test_fondo_de_emergencia(self):
        self.f.agregar("ingreso", 1500, "sueldo", fecha="2026-09-01")
        self.f.agregar("gasto", 1000, "vivienda", fecha="2026-09-02")
        self.assertTrue(any("0,5 meses" in t for t in self.textos(CONSEJO)))

    def test_avisos_primero(self):
        self.f.fijar_presupuesto("ocio", 10)
        self.f.agregar("ingreso", 3000, "sueldo", fecha="2026-10-01")
        self.f.agregar("gasto", 20, "ocio", fecha="2026-10-02")
        niveles = [r.nivel for r in recomendar(self.f, HOY)]
        self.assertEqual(niveles[0], AVISO)
        self.assertEqual(niveles, sorted(niveles, key=[AVISO, CONSEJO, BIEN].index))


if __name__ == "__main__":
    unittest.main()
