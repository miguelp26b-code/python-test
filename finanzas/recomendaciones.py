"""Consejos basados en los propios movimientos del usuario (no es asesoramiento financiero)."""

from __future__ import annotations

import calendar
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from .core import Finanzas, dinero

# Peso de cada consejo para ordenarlos: primero los avisos.
AVISO, CONSEJO, BIEN = "aviso", "consejo", "bien"


@dataclass(frozen=True)
class Recomendacion:
    nivel: str
    texto: str


def _mes_anterior(mes: str, atras: int) -> str:
    anio, num = (int(p) for p in mes.split("-"))
    total = anio * 12 + (num - 1) - atras
    return f"{total // 12:04d}-{total % 12 + 1:02d}"


def recomendar(f: Finanzas, hoy: date | None = None) -> list[Recomendacion]:
    hoy = hoy or date.today()
    mes = hoy.strftime("%Y-%m")
    actual = f.resumen(mes)
    consejos: list[Recomendacion] = []

    # 1. Presupuestos: excedidos o en camino de excederse al ritmo actual.
    dias_mes = calendar.monthrange(hoy.year, hoy.month)[1]
    for e in f.estado_presupuestos(mes):
        if e.excedido:
            consejos.append(Recomendacion(
                AVISO, f"Has superado el presupuesto de {e.categoria} en {dinero(-e.restante)}."
            ))
        elif e.gastado and hoy.day < dias_mes:
            proyeccion = e.gastado / hoy.day * dias_mes
            if proyeccion > e.limite:
                consejos.append(Recomendacion(
                    AVISO,
                    f"Al ritmo actual gastarás unos {dinero(proyeccion)} en {e.categoria}, "
                    f"por encima de tu límite de {dinero(e.limite)}.",
                ))

    # 2. Categorías que se disparan respecto a la media de los 3 meses anteriores.
    previos = [f.resumen(_mes_anterior(mes, i)).gastos_por_categoria for i in (1, 2, 3)]
    for categoria, gastado in actual.gastos_por_categoria.items():
        historico = [p[categoria] for p in previos if categoria in p]
        if not historico:
            continue
        media = sum(historico, Decimal(0)) / len(historico)
        if gastado > media * Decimal("1.3") and gastado - media >= 20:
            subida = (gastado / media - 1) * 100
            consejos.append(Recomendacion(
                CONSEJO,
                f"Este mes llevas {dinero(gastado)} en {categoria}, un {subida:.0f} % más "
                f"que tu media ({dinero(media)}).",
            ))

    # 3. Tasa de ahorro del mes.
    tasa = actual.tasa_ahorro
    if tasa is not None:
        if tasa < 0:
            consejos.append(Recomendacion(
                AVISO, f"Este mes gastas más de lo que ingresas ({dinero(-actual.balance)} de déficit)."
            ))
        elif tasa < 10:
            consejos.append(Recomendacion(
                CONSEJO,
                f"Ahorras un {tasa:.0f} % de tus ingresos. Intenta llegar al 20 % "
                "(regla 50/30/20).",
            ))
        elif tasa >= 20:
            consejos.append(Recomendacion(
                BIEN, f"¡Bien! Ahorras un {tasa:.0f} % de tus ingresos este mes."
            ))

    # 4. Fondo de emergencia: 3-6 meses de gastos medios.
    gastos_previos = [f.resumen(_mes_anterior(mes, i)).gastos for i in (1, 2, 3)]
    gastos_previos = [g for g in gastos_previos if g]
    saldo = f.saldo()
    if gastos_previos and saldo > 0:
        gasto_medio = sum(gastos_previos, Decimal(0)) / len(gastos_previos)
        meses = saldo / gasto_medio
        if meses < 3:
            consejos.append(Recomendacion(
                CONSEJO,
                f"Tu saldo cubre {str(round(meses, 1)).replace('.', ',')} meses de gastos. Lo recomendable es "
                f"un fondo de emergencia de 3 a 6 meses (~{dinero(gasto_medio * 3)}).",
            ))
        else:
            consejos.append(Recomendacion(
                BIEN, f"Tu saldo cubre {str(round(meses, 1)).replace('.', ',')} meses de gastos: buen fondo de emergencia."
            ))

    if not consejos:
        consejos.append(Recomendacion(
            CONSEJO,
            "Registra tus ingresos y gastos durante unas semanas y fija presupuestos "
            "para recibir recomendaciones.",
        ))
    orden = {AVISO: 0, CONSEJO: 1, BIEN: 2}
    return sorted(consejos, key=lambda r: orden[r.nivel])
