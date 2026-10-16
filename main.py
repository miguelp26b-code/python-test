"""App Android (Kivy) del gestor de finanzas personales.

En escritorio: `python main.py`. Para Android se empaqueta con Buildozer (ver README).
"""

from __future__ import annotations

import os
from datetime import date

from kivy.app import App
from kivy.core.window import Window
from kivy.lang import Builder
from kivy.metrics import dp
from kivy.properties import ColorProperty, NumericProperty, StringProperty
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.screenmanager import Screen
from kivy.utils import get_color_from_hex as color, platform

from finanzas.core import ErrorFinanzas, Finanzas, dinero
from finanzas.recomendaciones import AVISO, BIEN, recomendar

MESES = [
    "enero", "febrero", "marzo", "abril", "mayo", "junio",
    "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
]
CATEGORIAS_BASE = {
    "gasto": ["comida", "transporte", "vivienda", "ocio", "salud", "suministros", "ropa"],
    "ingreso": ["sueldo", "extra", "regalo", "inversiones"],
}

KV = """
#:import dp kivy.metrics.dp

<Tarjeta>:
    orientation: "vertical"
    padding: dp(16)
    spacing: dp(6)
    size_hint_y: None
    height: self.minimum_height
    canvas.before:
        Color:
            rgba: self.bg
        RoundedRectangle:
            pos: self.pos
            size: self.size
            radius: [dp(16)]

<Boton>:
    color: self.fg
    bold: True
    font_size: "15sp"
    size_hint_y: None
    height: dp(48)
    canvas.before:
        Color:
            rgba: self.bg if self.state == "normal" else [c * 0.8 for c in self.bg[:3]] + [1]
        RoundedRectangle:
            pos: self.pos
            size: self.size
            radius: [dp(12)]

<Texto@Label>:
    color: app.c_texto
    font_size: "15sp"
    text_size: self.width, None
    size_hint_y: None
    height: self.texture_size[1]
    halign: "left"

<Secundario@Texto>:
    color: app.c_suave
    font_size: "13sp"

<Campo@TextInput>:
    multiline: False
    size_hint_y: None
    height: dp(48)
    font_size: "16sp"
    padding: [dp(12), dp(14)]
    background_normal: ""
    background_active: ""
    background_color: app.c_campo
    foreground_color: app.c_texto
    hint_text_color: app.c_suave
    cursor_color: app.c_acento
    write_tab: False

<Cifra@BoxLayout>:
    orientation: "vertical"
    titulo: ""
    valor: ""
    tono: app.c_texto
    size_hint_y: None
    height: dp(48)
    Secundario:
        text: root.titulo
    Texto:
        text: root.valor
        color: root.tono
        bold: True
        font_size: "16sp"

<SelectorMes@BoxLayout>:
    size_hint_y: None
    height: dp(48)
    spacing: dp(8)
    Boton:
        text: "<"
        size_hint_x: None
        width: dp(48)
        bg: app.c_tarjeta
        fg: app.c_texto
        on_release: app.cambiar_mes(-1)
    Label:
        text: app.nombre_mes
        color: app.c_texto
        bold: True
        font_size: "17sp"
    Boton:
        text: ">"
        size_hint_x: None
        width: dp(48)
        bg: app.c_tarjeta
        fg: app.c_texto
        on_release: app.cambiar_mes(1)

<FilaMovimiento>:
    size_hint_y: None
    height: dp(68)
    padding: dp(14), dp(8)
    spacing: dp(8)
    canvas.before:
        Color:
            rgba: app.c_tarjeta if self.state == "normal" else app.c_campo
        RoundedRectangle:
            pos: self.x, self.y + dp(3)
            size: self.width, self.height - dp(6)
            radius: [dp(12)]
    BoxLayout:
        orientation: "vertical"
        Label:
            text: root.titulo
            color: app.c_texto
            font_size: "15sp"
            bold: True
            text_size: self.size
            halign: "left"
            valign: "bottom"
            shorten: True
        Label:
            text: root.subtitulo
            color: app.c_suave
            font_size: "12sp"
            text_size: self.size
            halign: "left"
            valign: "top"
            shorten: True
    Label:
        text: root.importe
        color: root.tono
        bold: True
        font_size: "16sp"
        size_hint_x: None
        width: dp(120)
        text_size: self.size
        halign: "right"
        valign: "middle"

<FilaPresupuesto>:
    orientation: "vertical"
    size_hint_y: None
    height: dp(76)
    padding: dp(14), dp(10)
    canvas.before:
        Color:
            rgba: app.c_tarjeta if self.state == "normal" else app.c_campo
        RoundedRectangle:
            pos: self.x, self.y + dp(3)
            size: self.width, self.height - dp(6)
            radius: [dp(12)]
    BoxLayout:
        Label:
            text: root.categoria
            color: app.c_texto
            bold: True
            font_size: "15sp"
            text_size: self.size
            halign: "left"
            valign: "middle"
        Label:
            text: root.detalle
            color: root.tono
            font_size: "13sp"
            text_size: self.size
            halign: "right"
            valign: "middle"
    Widget:
        size_hint_y: None
        height: dp(10)
        canvas:
            Color:
                rgba: app.c_campo
            RoundedRectangle:
                pos: self.pos
                size: self.size
                radius: [dp(5)]
            Color:
                rgba: root.tono
            RoundedRectangle:
                pos: self.pos
                size: self.width * min(root.progreso, 1), self.height
                radius: [dp(5)]

<Consejo>:
    canvas.before:
        Color:
            rgba: self.tono
        RoundedRectangle:
            pos: self.pos
            size: dp(4), self.height
            radius: [dp(2)]
    Texto:
        text: root.texto

<PantallaInicio>:
    ScrollView:
        do_scroll_x: False
        BoxLayout:
            orientation: "vertical"
            padding: dp(16)
            spacing: dp(14)
            size_hint_y: None
            height: self.minimum_height
            Tarjeta:
                bg: app.c_acento
                Texto:
                    text: "Saldo total"
                    color: 1, 1, 1, .85
                Texto:
                    id: saldo
                    font_size: "34sp"
                    bold: True
                    color: 1, 1, 1, 1
            Tarjeta:
                bg: app.c_tarjeta
                Texto:
                    text: "Este mes"
                    bold: True
                GridLayout:
                    cols: 3
                    size_hint_y: None
                    height: dp(48)
                    Cifra:
                        id: ingresos
                        titulo: "Ingresos"
                        tono: app.c_ingreso
                    Cifra:
                        id: gastos
                        titulo: "Gastos"
                        tono: app.c_gasto
                    Cifra:
                        id: balance
                        titulo: "Balance"
            BoxLayout:
                size_hint_y: None
                height: dp(48)
                spacing: dp(12)
                Boton:
                    text: "+ Ingreso"
                    bg: app.c_ingreso
                    on_release: app.nuevo_movimiento("ingreso")
                Boton:
                    text: "- Gasto"
                    bg: app.c_gasto
                    on_release: app.nuevo_movimiento("gasto")
            Texto:
                text: "Recomendaciones"
                bold: True
                font_size: "18sp"
            BoxLayout:
                id: consejos
                orientation: "vertical"
                size_hint_y: None
                height: self.minimum_height
                spacing: dp(12)
            Secundario:
                text: "Consejos orientativos basados en tus propios datos. No son asesoramiento financiero."

<PantallaMovimientos>:
    BoxLayout:
        orientation: "vertical"
        padding: dp(16)
        spacing: dp(10)
        SelectorMes:
        Secundario:
            id: totales
            halign: "center"
        RecycleView:
            id: lista
            viewclass: "FilaMovimiento"
            RecycleBoxLayout:
                orientation: "vertical"
                default_size: None, dp(68)
                default_size_hint: 1, None
                size_hint_y: None
                height: self.minimum_height
        Secundario:
            text: "Toca un movimiento para eliminarlo."
            halign: "center"

<PantallaPresupuestos>:
    BoxLayout:
        orientation: "vertical"
        padding: dp(16)
        spacing: dp(10)
        SelectorMes:
        RecycleView:
            id: lista
            viewclass: "FilaPresupuesto"
            RecycleBoxLayout:
                orientation: "vertical"
                default_size: None, dp(76)
                default_size_hint: 1, None
                size_hint_y: None
                height: self.minimum_height
        Tarjeta:
            bg: app.c_tarjeta
            spacing: dp(10)
            Texto:
                text: "Límite mensual por categoría"
                bold: True
            BoxLayout:
                size_hint_y: None
                height: dp(48)
                spacing: dp(8)
                Campo:
                    id: categoria
                    hint_text: "Categoría"
                Campo:
                    id: limite
                    hint_text: "Límite €"
                    input_type: "number"
                    size_hint_x: .6
            Boton:
                text: "Guardar presupuesto"
                bg: app.c_acento
                on_release: root.guardar()

<PantallaNuevo>:
    ScrollView:
        do_scroll_x: False
        BoxLayout:
            orientation: "vertical"
            padding: dp(16)
            spacing: dp(12)
            size_hint_y: None
            height: self.minimum_height
            BoxLayout:
                size_hint_y: None
                height: dp(48)
                spacing: dp(8)
                Boton:
                    text: "Gasto"
                    bg: app.c_gasto if root.tipo == "gasto" else app.c_tarjeta
                    fg: (1, 1, 1, 1) if root.tipo == "gasto" else app.c_suave
                    on_release: root.tipo = "gasto"
                Boton:
                    text: "Ingreso"
                    bg: app.c_ingreso if root.tipo == "ingreso" else app.c_tarjeta
                    fg: (1, 1, 1, 1) if root.tipo == "ingreso" else app.c_suave
                    on_release: root.tipo = "ingreso"
            Secundario:
                text: "Importe (€)"
            Campo:
                id: importe
                hint_text: "0,00"
                input_type: "number"
                font_size: "22sp"
                height: dp(56)
            Secundario:
                text: "Categoría"
            Campo:
                id: categoria
                hint_text: "p. ej. comida"
            StackLayout:
                id: sugerencias
                size_hint_y: None
                height: self.minimum_height
                spacing: dp(6)
            Secundario:
                text: "Descripción (opcional)"
            Campo:
                id: descripcion
            Secundario:
                text: "Fecha (AAAA-MM-DD)"
            Campo:
                id: fecha
            Widget:
                size_hint_y: None
                height: dp(4)
            Boton:
                text: "Guardar"
                bg: app.c_acento
                on_release: root.guardar()
            Boton:
                text: "Cancelar"
                bg: app.c_tarjeta
                fg: app.c_texto
                on_release: app.ir("inicio")

<Pestana@Boton>:
    pantalla: ""
    bg: app.c_fondo
    fg: app.c_acento if app.pantalla == self.pantalla else app.c_suave
    font_size: "14sp"
    height: dp(56)
    on_release: app.ir(self.pantalla)

BoxLayout:
    orientation: "vertical"
    canvas.before:
        Color:
            rgba: app.c_fondo
        Rectangle:
            pos: self.pos
            size: self.size
    Label:
        text: app.titulo
        color: app.c_texto
        bold: True
        font_size: "20sp"
        size_hint_y: None
        height: dp(56)
        padding: dp(16), 0
        text_size: self.size
        halign: "left"
        valign: "middle"
    ScreenManager:
        id: pantallas
        PantallaInicio:
            name: "inicio"
        PantallaMovimientos:
            name: "movimientos"
        PantallaPresupuestos:
            name: "presupuestos"
        PantallaNuevo:
            name: "nuevo"
    BoxLayout:
        size_hint_y: None
        height: dp(56)
        canvas.before:
            Color:
                rgba: app.c_campo
            Rectangle:
                pos: self.x, self.top - dp(1)
                size: self.width, dp(1)
        Pestana:
            text: "Inicio"
            pantalla: "inicio"
        Pestana:
            text: "Movimientos"
            pantalla: "movimientos"
        Pestana:
            text: "Presupuestos"
            pantalla: "presupuestos"
"""


class Tarjeta(BoxLayout):
    bg = ColorProperty("#FFFFFF")


class Boton(ButtonBehavior, Label):
    bg = ColorProperty("#3A6FF7")
    fg = ColorProperty("#FFFFFF")


class FilaMovimiento(ButtonBehavior, BoxLayout):
    mov_id = NumericProperty(0)
    titulo = StringProperty("")
    subtitulo = StringProperty("")
    importe = StringProperty("")
    tono = ColorProperty("#000000")

    def on_release(self):
        app = App.get_running_app()
        app.confirmar(
            f"¿Eliminar «{self.titulo}» ({self.importe})?",
            lambda: app.eliminar_movimiento(self.mov_id),
        )


class FilaPresupuesto(ButtonBehavior, BoxLayout):
    categoria = StringProperty("")
    detalle = StringProperty("")
    progreso = NumericProperty(0)
    tono = ColorProperty("#000000")

    def on_release(self):
        app = App.get_running_app()
        app.confirmar(
            f"¿Quitar el presupuesto de {self.categoria}?",
            lambda: app.quitar_presupuesto(self.categoria),
        )


class Consejo(BoxLayout):
    texto = StringProperty("")
    tono = ColorProperty("#000000")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.size_hint_y = None
        self.padding = (dp(14), 0, 0, 0)
        self.bind(minimum_height=self.setter("height"))


class PantallaInicio(Screen):
    def refrescar(self, app):
        hoy = date.today().strftime("%Y-%m")
        r = app.finanzas.resumen(hoy)
        self.ids.saldo.text = dinero(app.finanzas.saldo())
        self.ids.ingresos.valor = dinero(r.ingresos)
        self.ids.gastos.valor = dinero(r.gastos)
        self.ids.balance.valor = dinero(r.balance)
        self.ids.balance.tono = app.c_ingreso if r.balance >= 0 else app.c_gasto
        tonos = {AVISO: app.c_gasto, BIEN: app.c_ingreso}
        caja = self.ids.consejos
        caja.clear_widgets()
        for consejo in recomendar(app.finanzas):
            caja.add_widget(Consejo(texto=consejo.texto, tono=tonos.get(consejo.nivel, app.c_acento)))


class PantallaMovimientos(Screen):
    def refrescar(self, app):
        movimientos = app.finanzas.listar(mes=app.mes)
        r = app.finanzas.resumen(app.mes)
        self.ids.totales.text = (
            f"Ingresos {dinero(r.ingresos)}  ·  Gastos {dinero(r.gastos)}"
            if movimientos else "No hay movimientos este mes."
        )
        self.ids.lista.data = [
            {
                "mov_id": m.id,
                "titulo": m.descripcion or m.categoria.capitalize(),
                "subtitulo": f"{m.fecha.strftime('%d/%m/%Y')} · {m.categoria}",
                "importe": ("+" if m.tipo == "ingreso" else "-") + dinero(m.importe),
                "tono": app.c_ingreso if m.tipo == "ingreso" else app.c_gasto,
            }
            for m in reversed(movimientos)
        ]


class PantallaPresupuestos(Screen):
    def refrescar(self, app):
        self.ids.lista.data = [
            {
                "categoria": e.categoria.capitalize(),
                "detalle": f"{dinero(e.gastado)} de {dinero(e.limite)}",
                "progreso": e.porcentaje / 100,
                "tono": app.c_gasto if e.excedido
                else app.c_aviso if e.porcentaje >= 80 else app.c_ingreso,
            }
            for e in app.finanzas.estado_presupuestos(app.mes)
        ]

    def guardar(self):
        app = App.get_running_app()
        try:
            app.finanzas.fijar_presupuesto(self.ids.categoria.text, self.ids.limite.text)
        except ErrorFinanzas as error:
            app.aviso(str(error))
            return
        self.ids.categoria.text = self.ids.limite.text = ""
        app.refrescar()


class PantallaNuevo(Screen):
    tipo = StringProperty("gasto")

    def preparar(self, tipo):
        self.tipo = tipo
        for campo in ("importe", "categoria", "descripcion"):
            self.ids[campo].text = ""
        self.ids.fecha.text = date.today().isoformat()

    def on_tipo(self, *_):
        app = App.get_running_app()
        usadas = app.finanzas.categorias(self.tipo)
        opciones = usadas + [c for c in CATEGORIAS_BASE[self.tipo] if c not in usadas]
        caja = self.ids.sugerencias
        caja.clear_widgets()
        for categoria in opciones[:8]:
            boton = Boton(
                text=categoria, bg=app.c_tarjeta, fg=app.c_texto, bold=False,
                font_size="14sp", size_hint=(None, None), height=dp(36),
            )
            boton.width = boton.texture_size[0] + dp(28)
            boton.bind(
                texture_size=lambda b, t: setattr(b, "width", t[0] + dp(28)),
                on_release=lambda b: setattr(self.ids.categoria, "text", b.text),
            )
            caja.add_widget(boton)

    def guardar(self):
        app = App.get_running_app()
        try:
            app.finanzas.agregar(
                self.tipo,
                self.ids.importe.text,
                self.ids.categoria.text,
                self.ids.descripcion.text,
                self.ids.fecha.text.strip() or None,
            )
        except ErrorFinanzas as error:
            app.aviso(str(error))
            return
        app.refrescar()
        app.ir("inicio")


class FinanzasApp(App):
    title = "Mis Finanzas"
    pantalla = StringProperty("inicio")
    titulo = StringProperty("Mis Finanzas")
    mes = StringProperty(date.today().strftime("%Y-%m"))
    nombre_mes = StringProperty("")

    c_fondo = ColorProperty(color("#F4F6FA"))
    c_tarjeta = ColorProperty(color("#FFFFFF"))
    c_campo = ColorProperty(color("#E6EAF2"))
    c_texto = ColorProperty(color("#1B2030"))
    c_suave = ColorProperty(color("#6B7387"))
    c_acento = ColorProperty(color("#3A6FF7"))
    c_ingreso = ColorProperty(color("#1E9E6A"))
    c_gasto = ColorProperty(color("#E0475B"))
    c_aviso = ColorProperty(color("#E89B20"))

    TITULOS = {
        "inicio": "Mis Finanzas",
        "movimientos": "Movimientos",
        "presupuestos": "Presupuestos",
    }

    def build(self):
        ruta = os.environ.get("FINANZAS_DB") or os.path.join(self.user_data_dir, "finanzas.db")
        self.finanzas = Finanzas(ruta)
        Window.clearcolor = self.c_fondo
        Window.softinput_mode = "below_target"
        Window.bind(on_keyboard=self.tecla)
        self._actualizar_nombre_mes()
        raiz = Builder.load_string(KV)
        self.pantallas = raiz.ids.pantallas
        return raiz

    def on_start(self):
        self.refrescar()

    def on_stop(self):
        self.finanzas.cerrar()

    def tecla(self, _ventana, codigo, *_):
        # Botón "atrás" de Android: volver a Inicio en lugar de cerrar la app.
        if codigo == 27 and self.pantalla != "inicio":
            self.ir("inicio")
            return True
        return False

    def ir(self, pantalla):
        self.pantalla = pantalla
        self.titulo = self.TITULOS.get(pantalla, "Nuevo movimiento")
        self.pantallas.current = pantalla

    def nuevo_movimiento(self, tipo):
        pantalla = self.pantallas.get_screen("nuevo")
        pantalla.preparar(tipo)
        pantalla.on_tipo()
        self.ir("nuevo")
        self.titulo = f"Nuevo {tipo}"

    def cambiar_mes(self, delta):
        anio, num = (int(p) for p in self.mes.split("-"))
        total = anio * 12 + num - 1 + delta
        self.mes = f"{total // 12:04d}-{total % 12 + 1:02d}"
        self._actualizar_nombre_mes()
        self.refrescar()

    def _actualizar_nombre_mes(self):
        anio, num = self.mes.split("-")
        self.nombre_mes = f"{MESES[int(num) - 1].capitalize()} {anio}"

    def refrescar(self):
        for nombre in ("inicio", "movimientos", "presupuestos"):
            self.pantallas.get_screen(nombre).refrescar(self)

    def eliminar_movimiento(self, mov_id):
        self.finanzas.eliminar(mov_id)
        self.refrescar()

    def quitar_presupuesto(self, categoria):
        self.finanzas.quitar_presupuesto(categoria)
        self.refrescar()

    def _dialogo(self, titulo, mensaje, acciones):
        caja = BoxLayout(orientation="vertical", padding=dp(12), spacing=dp(12))
        texto = Label(text=mensaje, color=self.c_texto, font_size="15sp")
        texto.bind(width=lambda l, w: setattr(l, "text_size", (w, None)))
        caja.add_widget(texto)
        botones = BoxLayout(size_hint_y=None, height=dp(48), spacing=dp(8))
        caja.add_widget(botones)
        popup = Popup(
            title=titulo, content=caja, size_hint=(.9, None), height=dp(220),
            title_color=self.c_texto, separator_color=self.c_acento,
            background="", background_color=self.c_tarjeta, auto_dismiss=True,
        )
        for texto_boton, bg, fg, accion in acciones:
            boton = Boton(text=texto_boton, bg=bg, fg=fg)
            boton.bind(on_release=lambda _b, a=accion: (popup.dismiss(), a and a()))
            botones.add_widget(boton)
        popup.open()

    def aviso(self, mensaje):
        self._dialogo("Revisa los datos", mensaje, [("Entendido", self.c_acento, (1, 1, 1, 1), None)])

    def confirmar(self, mensaje, accion):
        self._dialogo("Confirmar", mensaje, [
            ("Cancelar", self.c_campo, self.c_texto, None),
            ("Eliminar", self.c_gasto, (1, 1, 1, 1), accion),
        ])


if __name__ == "__main__":
    if platform not in ("android", "ios"):
        Window.size = (400, 800)
    FinanzasApp().run()
