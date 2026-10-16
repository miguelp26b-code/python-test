"""Lógica de negocio y persistencia (SQLite) para la gestión de finanzas personales."""

from __future__ import annotations

import csv
import sqlite3
from dataclasses import dataclass
from datetime import date
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from pathlib import Path

TIPOS = ("ingreso", "gasto")

ESQUEMA = """
CREATE TABLE IF NOT EXISTS movimientos (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    fecha       TEXT    NOT NULL,
    tipo        TEXT    NOT NULL CHECK (tipo IN ('ingreso', 'gasto')),
    categoria   TEXT    NOT NULL,
    centimos    INTEGER NOT NULL CHECK (centimos > 0),
    descripcion TEXT    NOT NULL DEFAULT ''
);
CREATE INDEX IF NOT EXISTS idx_movimientos_fecha ON movimientos (fecha);

CREATE TABLE IF NOT EXISTS presupuestos (
    categoria TEXT    PRIMARY KEY,
    centimos  INTEGER NOT NULL CHECK (centimos > 0)
);
"""


class ErrorFinanzas(ValueError):
    """Error de validación de datos introducidos por el usuario."""


@dataclass(frozen=True)
class Movimiento:
    id: int
    fecha: date
    tipo: str
    categoria: str
    importe: Decimal
    descripcion: str


@dataclass(frozen=True)
class EstadoPresupuesto:
    categoria: str
    limite: Decimal
    gastado: Decimal

    @property
    def restante(self) -> Decimal:
        return self.limite - self.gastado

    @property
    def porcentaje(self) -> float:
        return float(self.gastado / self.limite * 100)

    @property
    def excedido(self) -> bool:
        return self.gastado > self.limite


@dataclass(frozen=True)
class Resumen:
    ingresos: Decimal
    gastos: Decimal
    gastos_por_categoria: dict[str, Decimal]
    ingresos_por_categoria: dict[str, Decimal]

    @property
    def balance(self) -> Decimal:
        return self.ingresos - self.gastos

    @property
    def tasa_ahorro(self) -> float | None:
        if not self.ingresos:
            return None
        return float(self.balance / self.ingresos * 100)


def a_centimos(importe: str | int | float | Decimal) -> int:
    try:
        valor = Decimal(str(importe).replace(",", "."))
    except InvalidOperation:
        raise ErrorFinanzas(f"Importe no válido: {importe!r}") from None
    if not valor.is_finite() or valor <= 0:
        raise ErrorFinanzas("El importe debe ser un número positivo")
    return int((valor * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def de_centimos(centimos: int) -> Decimal:
    return (Decimal(centimos) / 100).quantize(Decimal("0.01"))


def dinero(valor: Decimal) -> str:
    """Formato español: 1.234,56 €."""
    return f"{valor:,.2f} €".replace(",", "X").replace(".", ",").replace("X", ".")


def parsear_fecha(texto: str | date | None) -> date:
    if texto is None:
        return date.today()
    if isinstance(texto, date):
        return texto
    try:
        return date.fromisoformat(texto)
    except ValueError:
        raise ErrorFinanzas(f"Fecha no válida (usa AAAA-MM-DD): {texto!r}") from None


def rango_mes(mes: str) -> tuple[str, str]:
    """Convierte 'AAAA-MM' en el rango [inicio, fin) de fechas ISO."""
    try:
        anio, num = (int(p) for p in mes.split("-"))
        inicio = date(anio, num, 1)
    except ValueError:
        raise ErrorFinanzas(f"Mes no válido (usa AAAA-MM): {mes!r}") from None
    fin = date(anio + 1, 1, 1) if num == 12 else date(anio, num + 1, 1)
    return inicio.isoformat(), fin.isoformat()


def _normalizar_categoria(categoria: str) -> str:
    categoria = categoria.strip().lower()
    if not categoria:
        raise ErrorFinanzas("La categoría no puede estar vacía")
    return categoria


class Finanzas:
    """Gestor de ingresos, gastos y presupuestos mensuales."""

    def __init__(self, ruta: str | Path = ":memory:"):
        self.conexion = sqlite3.connect(str(ruta))
        self.conexion.row_factory = sqlite3.Row
        self.conexion.executescript(ESQUEMA)

    def cerrar(self) -> None:
        self.conexion.close()

    def __enter__(self) -> Finanzas:
        return self

    def __exit__(self, *_exc) -> None:
        self.cerrar()

    # --- Movimientos -----------------------------------------------------

    def agregar(
        self,
        tipo: str,
        importe: str | int | float | Decimal,
        categoria: str,
        descripcion: str = "",
        fecha: str | date | None = None,
    ) -> int:
        if tipo not in TIPOS:
            raise ErrorFinanzas(f"Tipo no válido: {tipo!r} (usa 'ingreso' o 'gasto')")
        with self.conexion:
            cursor = self.conexion.execute(
                "INSERT INTO movimientos (fecha, tipo, categoria, centimos, descripcion)"
                " VALUES (?, ?, ?, ?, ?)",
                (
                    parsear_fecha(fecha).isoformat(),
                    tipo,
                    _normalizar_categoria(categoria),
                    a_centimos(importe),
                    descripcion.strip(),
                ),
            )
        return cursor.lastrowid

    def eliminar(self, movimiento_id: int) -> None:
        with self.conexion:
            cursor = self.conexion.execute(
                "DELETE FROM movimientos WHERE id = ?", (movimiento_id,)
            )
        if cursor.rowcount == 0:
            raise ErrorFinanzas(f"No existe el movimiento con id {movimiento_id}")

    def listar(
        self,
        mes: str | None = None,
        tipo: str | None = None,
        categoria: str | None = None,
    ) -> list[Movimiento]:
        condiciones, parametros = self._filtros(mes, tipo, categoria)
        filas = self.conexion.execute(
            f"SELECT * FROM movimientos {condiciones} ORDER BY fecha, id", parametros
        ).fetchall()
        return [
            Movimiento(
                id=f["id"],
                fecha=date.fromisoformat(f["fecha"]),
                tipo=f["tipo"],
                categoria=f["categoria"],
                importe=de_centimos(f["centimos"]),
                descripcion=f["descripcion"],
            )
            for f in filas
        ]

    def categorias(self, tipo: str) -> list[str]:
        """Categorías usadas para un tipo, de la más a la menos frecuente."""
        filas = self.conexion.execute(
            "SELECT categoria FROM movimientos WHERE tipo = ?"
            " GROUP BY categoria ORDER BY COUNT(*) DESC, categoria",
            (tipo,),
        ).fetchall()
        return [f["categoria"] for f in filas]

    def saldo(self) -> Decimal:
        (total,) = self.conexion.execute(
            "SELECT COALESCE(SUM(CASE tipo WHEN 'ingreso' THEN centimos"
            " ELSE -centimos END), 0) FROM movimientos"
        ).fetchone()
        return de_centimos(total)

    def resumen(self, mes: str | None = None) -> Resumen:
        condiciones, parametros = self._filtros(mes)
        filas = self.conexion.execute(
            f"SELECT tipo, categoria, SUM(centimos) AS total FROM movimientos"
            f" {condiciones} GROUP BY tipo, categoria ORDER BY total DESC",
            parametros,
        ).fetchall()
        por_tipo: dict[str, dict[str, Decimal]] = {t: {} for t in TIPOS}
        for f in filas:
            por_tipo[f["tipo"]][f["categoria"]] = de_centimos(f["total"])
        return Resumen(
            ingresos=sum(por_tipo["ingreso"].values(), Decimal("0.00")),
            gastos=sum(por_tipo["gasto"].values(), Decimal("0.00")),
            gastos_por_categoria=por_tipo["gasto"],
            ingresos_por_categoria=por_tipo["ingreso"],
        )

    def _filtros(
        self, mes: str | None, tipo: str | None = None, categoria: str | None = None
    ) -> tuple[str, list]:
        condiciones, parametros = [], []
        if mes:
            inicio, fin = rango_mes(mes)
            condiciones.append("fecha >= ? AND fecha < ?")
            parametros += [inicio, fin]
        if tipo:
            if tipo not in TIPOS:
                raise ErrorFinanzas(f"Tipo no válido: {tipo!r}")
            condiciones.append("tipo = ?")
            parametros.append(tipo)
        if categoria:
            condiciones.append("categoria = ?")
            parametros.append(_normalizar_categoria(categoria))
        sql = "WHERE " + " AND ".join(condiciones) if condiciones else ""
        return sql, parametros

    # --- Presupuestos ----------------------------------------------------

    def fijar_presupuesto(self, categoria: str, limite: str | int | float | Decimal) -> None:
        with self.conexion:
            self.conexion.execute(
                "INSERT INTO presupuestos (categoria, centimos) VALUES (?, ?)"
                " ON CONFLICT (categoria) DO UPDATE SET centimos = excluded.centimos",
                (_normalizar_categoria(categoria), a_centimos(limite)),
            )

    def quitar_presupuesto(self, categoria: str) -> None:
        with self.conexion:
            cursor = self.conexion.execute(
                "DELETE FROM presupuestos WHERE categoria = ?",
                (_normalizar_categoria(categoria),),
            )
        if cursor.rowcount == 0:
            raise ErrorFinanzas(f"No hay presupuesto para la categoría {categoria!r}")

    def estado_presupuestos(self, mes: str | None = None) -> list[EstadoPresupuesto]:
        """Compara cada presupuesto mensual con lo gastado en el mes (por defecto, el actual)."""
        gastos = self.resumen(mes or date.today().strftime("%Y-%m")).gastos_por_categoria
        filas = self.conexion.execute(
            "SELECT categoria, centimos FROM presupuestos ORDER BY categoria"
        ).fetchall()
        return [
            EstadoPresupuesto(
                categoria=f["categoria"],
                limite=de_centimos(f["centimos"]),
                gastado=gastos.get(f["categoria"], Decimal("0.00")),
            )
            for f in filas
        ]

    # --- Importar / exportar ---------------------------------------------

    def exportar_csv(self, ruta: str | Path) -> int:
        movimientos = self.listar()
        with open(ruta, "w", newline="", encoding="utf-8") as fichero:
            escritor = csv.writer(fichero)
            escritor.writerow(["fecha", "tipo", "categoria", "importe", "descripcion"])
            for m in movimientos:
                escritor.writerow(
                    [m.fecha.isoformat(), m.tipo, m.categoria, m.importe, m.descripcion]
                )
        return len(movimientos)

    def importar_csv(self, ruta: str | Path) -> int:
        with open(ruta, newline="", encoding="utf-8") as fichero:
            filas = list(csv.DictReader(fichero))
        # Validar todo antes de insertar para que la importación sea atómica.
        registros = []
        for numero, fila in enumerate(filas, start=2):
            try:
                tipo = fila["tipo"].strip().lower()
                if tipo not in TIPOS:
                    raise ErrorFinanzas(f"tipo no válido: {fila['tipo']!r}")
                registros.append(
                    (
                        parsear_fecha(fila["fecha"].strip()).isoformat(),
                        tipo,
                        _normalizar_categoria(fila["categoria"]),
                        a_centimos(fila["importe"]),
                        (fila.get("descripcion") or "").strip(),
                    )
                )
            except (ErrorFinanzas, KeyError, AttributeError) as error:
                raise ErrorFinanzas(f"Línea {numero} del CSV: {error}") from None
        with self.conexion:
            self.conexion.executemany(
                "INSERT INTO movimientos (fecha, tipo, categoria, centimos, descripcion)"
                " VALUES (?, ?, ?, ?, ?)",
                registros,
            )
        return len(registros)
