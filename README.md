# Finanzas personales

Gestor de finanzas personales escrito en Python, con **app para Android** (Kivy) y **línea de comandos**. Ambas comparten la misma lógica y guardan los datos en SQLite.

## Funciones

- Registrar **ingresos** y **gastos** por categoría, con descripción y fecha
- Listar movimientos filtrando por mes, tipo o categoría, y eliminarlos
- Consultar el **saldo** total
- **Resumen** mensual: ingresos, gastos, balance, tasa de ahorro y reparto de gastos por categoría
- **Presupuestos** mensuales por categoría, con aviso al superarlos
- **Exportar e importar** movimientos en CSV (línea de comandos)
- **Recomendaciones** a partir de tus datos: presupuestos que vas a superar al ritmo actual, categorías que se disparan respecto a tu media, tasa de ahorro (regla 50/30/20) y fondo de emergencia. Son orientativas, no asesoramiento financiero.

Los importes se guardan como céntimos enteros, así que no hay errores de redondeo.

## App Android

### Descargar el APK

GitHub Actions compila el APK en cada push (workflow `Android APK`):

1. En GitHub, ve a la pestaña **Actions** → **Android APK** → la ejecución más reciente.
2. Descarga el artefacto **mis-finanzas-apk** (un `.zip` con el `.apk` dentro).
3. Copia el `.apk` al móvil, ábrelo y permite "instalar apps de origen desconocido".

Es un APK de depuración (firmado con clave de debug): sirve para instalarlo en tu móvil, no para publicarlo en Google Play.

### Probar la app en el ordenador

```bash
pip install kivy
python main.py
```

### Compilar el APK en local (Linux)

```bash
pip install buildozer cython==0.29.37
buildozer android debug   # el APK queda en bin/
```

## Línea de comandos

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
