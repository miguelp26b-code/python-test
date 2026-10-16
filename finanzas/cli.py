"""Interfaz de línea de comandos: `python -m finanzas <comando> ...`."""

from __future__ import annotations

import argparse
import os
import sys
from decimal import Decimal
from pathlib import Path

from .core import ErrorFinanzas, Finanzas, dinero

RUTA_POR_DEFECTO = Path.home() / ".finanzas.db"


def barra(porcentaje: float, ancho: int = 20) -> str:
    llenos = min(ancho, round(porcentaje / 100 * ancho))
    return "█" * llenos + "░" * (ancho - llenos)


def cmd_agregar(f: Finanzas, args: argparse.Namespace) -> None:
    nuevo_id = f.agregar(args.tipo, args.importe, args.categoria, args.descripcion, args.fecha)
    print(f"✔ {args.tipo.capitalize()} registrado (id {nuevo_id}). Saldo: {dinero(f.saldo())}")


def cmd_listar(f: Finanzas, args: argparse.Namespace) -> None:
    movimientos = f.listar(args.mes, args.tipo, args.categoria)
    if not movimientos:
        print("No hay movimientos.")
        return
    print(f"{'ID':>4}  {'Fecha':10}  {'Categoría':15}  {'Importe':>14}  Descripción")
    print("-" * 70)
    for m in movimientos:
        signo = "+" if m.tipo == "ingreso" else "-"
        print(
            f"{m.id:>4}  {m.fecha}  {m.categoria[:15]:15}  "
            f"{signo + dinero(m.importe):>14}  {m.descripcion}"
        )


def cmd_eliminar(f: Finanzas, args: argparse.Namespace) -> None:
    f.eliminar(args.id)
    print(f"✔ Movimiento {args.id} eliminado.")


def cmd_saldo(f: Finanzas, _args: argparse.Namespace) -> None:
    print(f"Saldo actual: {dinero(f.saldo())}")


def cmd_resumen(f: Finanzas, args: argparse.Namespace) -> None:
    r = f.resumen(args.mes)
    print(f"Resumen {args.mes or '(todo el historial)'}")
    print(f"  Ingresos: {dinero(r.ingresos):>14}")
    print(f"  Gastos:   {dinero(r.gastos):>14}")
    print(f"  Balance:  {dinero(r.balance):>14}")
    if r.tasa_ahorro is not None:
        print(f"  Tasa de ahorro: {r.tasa_ahorro:.1f} %")
    if r.gastos_por_categoria:
        print("\nGastos por categoría:")
        for categoria, total in r.gastos_por_categoria.items():
            pct = float(total / r.gastos * 100)
            print(f"  {categoria[:15]:15} {dinero(total):>14}  {barra(pct)} {pct:5.1f} %")


def cmd_presupuesto(f: Finanzas, args: argparse.Namespace) -> None:
    if args.accion == "fijar":
        f.fijar_presupuesto(args.categoria, args.limite)
        print(f"✔ Presupuesto mensual de '{args.categoria}': {dinero(Decimal(args.limite.replace(',', '.')))}")
    elif args.accion == "quitar":
        f.quitar_presupuesto(args.categoria)
        print(f"✔ Presupuesto de '{args.categoria}' eliminado.")
    else:
        estados = f.estado_presupuestos(args.mes)
        if not estados:
            print("No hay presupuestos definidos.")
            return
        for e in estados:
            aviso = "  ⚠ EXCEDIDO" if e.excedido else ""
            print(
                f"{e.categoria[:15]:15} {dinero(e.gastado):>12} / {dinero(e.limite):>12}  "
                f"{barra(e.porcentaje)} {e.porcentaje:5.1f} %{aviso}"
            )


def cmd_exportar(f: Finanzas, args: argparse.Namespace) -> None:
    print(f"✔ {f.exportar_csv(args.fichero)} movimientos exportados a {args.fichero}")


def cmd_importar(f: Finanzas, args: argparse.Namespace) -> None:
    print(f"✔ {f.importar_csv(args.fichero)} movimientos importados desde {args.fichero}")


def construir_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="finanzas", description="Gestor de finanzas personales"
    )
    parser.add_argument(
        "--db",
        default=os.environ.get("FINANZAS_DB", RUTA_POR_DEFECTO),
        help=f"fichero de base de datos (por defecto: $FINANZAS_DB o {RUTA_POR_DEFECTO})",
    )
    sub = parser.add_subparsers(dest="comando", required=True)

    for tipo in ("ingreso", "gasto"):
        p = sub.add_parser(tipo, help=f"registrar un {tipo}")
        p.add_argument("importe", help="cantidad, p. ej. 12.50")
        p.add_argument("categoria", help="p. ej. comida, sueldo, transporte")
        p.add_argument("-d", "--descripcion", default="")
        p.add_argument("-f", "--fecha", help="AAAA-MM-DD (por defecto: hoy)")
        p.set_defaults(func=cmd_agregar, tipo=tipo)

    p = sub.add_parser("listar", help="listar movimientos")
    p.add_argument("-m", "--mes", help="AAAA-MM")
    p.add_argument("-t", "--tipo", choices=("ingreso", "gasto"))
    p.add_argument("-c", "--categoria")
    p.set_defaults(func=cmd_listar)

    p = sub.add_parser("eliminar", help="eliminar un movimiento por id")
    p.add_argument("id", type=int)
    p.set_defaults(func=cmd_eliminar)

    sub.add_parser("saldo", help="mostrar el saldo total").set_defaults(func=cmd_saldo)

    p = sub.add_parser("resumen", help="ingresos, gastos y balance")
    p.add_argument("-m", "--mes", help="AAAA-MM (por defecto: todo)")
    p.set_defaults(func=cmd_resumen)

    p = sub.add_parser("presupuesto", help="gestionar presupuestos mensuales")
    acciones = p.add_subparsers(dest="accion", required=True)
    a = acciones.add_parser("fijar", help="fijar el límite mensual de una categoría")
    a.add_argument("categoria")
    a.add_argument("limite")
    a = acciones.add_parser("quitar", help="eliminar el presupuesto de una categoría")
    a.add_argument("categoria")
    a = acciones.add_parser("estado", help="ver gasto frente a presupuesto")
    a.add_argument("-m", "--mes", help="AAAA-MM (por defecto: mes actual)")
    p.set_defaults(func=cmd_presupuesto)

    p = sub.add_parser("exportar", help="exportar movimientos a CSV")
    p.add_argument("fichero")
    p.set_defaults(func=cmd_exportar)

    p = sub.add_parser("importar", help="importar movimientos desde CSV")
    p.add_argument("fichero")
    p.set_defaults(func=cmd_importar)

    return parser


def main(argv: list[str] | None = None) -> int:
    args = construir_parser().parse_args(argv)
    try:
        with Finanzas(args.db) as f:
            args.func(f, args)
    except (ErrorFinanzas, OSError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1
    return 0
