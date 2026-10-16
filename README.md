# Finanzas personales

Gestor de finanzas personales en la línea de comandos, escrito en Python sin dependencias externas (solo la biblioteca estándar). Los datos se guardan en un fichero SQLite.

## Funciones

- Registrar **ingresos** y **gastos** por categoría, con descripción y fecha
- Listar movimientos filtrando por mes, tipo o categoría, y eliminarlos
- Consultar el **saldo** total
- **Resumen** mensual: ingresos, gastos, balance, tasa de ahorro y reparto de gastos por categoría
- **Presupuestos** mensuales por categoría, con aviso al superarlos
- **Exportar e importar** movimientos en CSV

Los importes se guardan como céntimos enteros, así que no hay errores de redondeo.

## Uso

Requiere Python 3.10 o superior.

```bash
python -m finanzas ingreso 2000 sueldo -d "Nómina"
python -m finanzas gasto 87,40 comida -d "Supermercado" -f 2026-10-15
python -m finanzas listar -m 2026-10
python -m finanzas saldo
python -m finanzas resumen -m 2026-10
python -m finanzas presupuesto fijar comida 300
python -m finanzas presupuesto estado
python -m finanzas eliminar 3
python -m finanzas exportar movimientos.csv
python -m finanzas importar movimientos.csv
```

Usa `python -m finanzas --help` (o `<comando> --help`) para ver todas las opciones.

Los datos se guardan en `~/.finanzas.db`. Puedes elegir otro fichero con `--db ruta.db` o la variable de entorno `FINANZAS_DB`.

El CSV de importación necesita las columnas `fecha,tipo,categoria,importe` (y, si quieres, `descripcion`). Si una línea no es válida no se importa ninguna.

## Tests

```bash
python -m unittest -v
```
