# main.py (IPAM -- version web de Indice LCV)
"""
A diferencia de la app de escritorio (que descarga los JSON por
internet), IPAM corre en la MISMA VPS donde el pipeline de indice-lcv
ya genera los archivos -- asi que los lee directo del disco, sin
descargar nada.

El catalogo (compartido, igual para todo el mundo) se carga UNA sola
vez cuando arranca el servidor, no en cada visita -- varias personas
entrando a la vez no disparan descargas ni calculos redundantes.

Mi Lista si es por persona -- cada quien ve solo la suya, filtrada
por su usuario_id (ver auth_email.py / db_web.py / pantalla_login.py).
"""

import json
import flet as ft

from utils.matching import unificar_catalogo
from utils.categorias import agrupar_por_grupo_unificado
import auth_email as ae
from pantalla_login import PantallaLogin, extraer_token_de_ruta
from pantalla_indice import PantallaIndice
from pantalla_comparador import PantallaComparador
from pantalla_lista_compras import PantallaListaCompras

# Rutas a los archivos que ya genera indice-lcv en esta misma VPS
RUTA_CATALOGO_RECIENTE = "/home/lcv/indice-lcv/catalogo_reciente.json"
RUTA_PRECIOS_ULTIMO = "/home/lcv/indice-lcv/precios_ultimo.json"

NAVY = "#0a1628"
GOLD = "#c9a84c"
GOLD_DIM = "#a08636"
CREAM = "#f5f0e8"

# Datos compartidos, cargados UNA vez al arrancar el servidor (no por
# cada visita) -- ver cargar_catalogo_compartido() mas abajo.
datos_dashboard = None
precios_ultimo = None
con_web = None


def cargar_catalogo_compartido():
    """Se llama una sola vez, al arrancar el proceso (no por cada
    sesion). Lee los JSON del disco y corre la unificacion entre
    supers -- todas las personas que entren despues comparten este
    mismo resultado ya calculado."""
    global datos_dashboard, precios_ultimo

    print("[INFO] Leyendo catalogo_reciente.json...")
    with open(RUTA_CATALOGO_RECIENTE, encoding="utf-8") as f:
        datos_dashboard = json.load(f)

    print("[INFO] Leyendo precios_ultimo.json...")
    with open(RUTA_PRECIOS_ULTIMO, encoding="utf-8") as f:
        precios_ultimo = json.load(f)

    print("[INFO] Unificando categorías parecidas entre súpers...")
    productos_agrupados = agrupar_por_grupo_unificado(datos_dashboard["productos_por_categoria"])

    print("[INFO] Unificando catálogo entre súpers (rapidfuzz)...")
    datos_dashboard["productos_por_categoria"] = unificar_catalogo(productos_agrupados)
    print("[INFO] Catálogo unificado y listo para todas las visitas")


def main(page: ft.Page):
    page.title = "IPAM - Índice de Precios App Madryn"
    page.bgcolor = CREAM

    page.fonts = {
        "Cinzel": "fonts/Cinzel_wght_.ttf",
        "Lato": "fonts/Lato-Regular.ttf",
    }
    page.theme = ft.Theme(font_family="Lato")

    header = ft.Container(
        content=ft.Column(
            [
                ft.Text("🌬️ ÍNDICE LCV", size=20, weight="bold", color=GOLD, font_family="Cinzel"),
                ft.Text("Canasta básica comparada — Puerto Madryn", size=11, color="#e8e0d0"),
            ],
            spacing=2,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        padding=ft.Padding(left=15, top=15, right=15, bottom=12),
        bgcolor=NAVY,
        border=ft.Border(bottom=ft.BorderSide(3, GOLD)),
        alignment=ft.Alignment(0, 0),
    )

    def mostrar_app(usuario: dict):
        """Se llama una vez que sabemos quien es la persona (por
        token en la URL, o porque acaba de confirmar el codigo de
        email). Arma las 3 tabs, igual que la version de escritorio,
        pero pasandole el usuario_id a Mi Lista y al Comparador."""
        usuario_id = usuario["id"]

        pantalla_lista = PantallaListaCompras(datos_dashboard, con_web, usuario_id)
        vista_lista = pantalla_lista.build()

        vista_indice = PantallaIndice(precios_ultimo).build(page)
        vista_comparador = PantallaComparador(
            datos_dashboard, con_web, usuario_id,
            on_agregado_a_lista=pantalla_lista.refrescar,
        ).build(page)

        tabs = ft.Tabs(
            selected_index=0,
            expand=True,
            length=3,
            content=ft.Column(
                expand=True,
                spacing=0,
                controls=[
                    ft.TabBar(
                        tabs=[
                            ft.Tab(label="Índice"),
                            ft.Tab(label="Comparador"),
                            ft.Tab(label="Mi Lista"),
                        ],
                        label_color=GOLD_DIM,
                        unselected_label_color="#9aa5b8",
                        indicator_color=GOLD,
                        divider_color="#e8e0d0",
                    ),
                    ft.TabBarView(expand=True, controls=[vista_indice, vista_comparador, vista_lista]),
                ],
            ),
        )

        page.controls.clear()
        page.add(header, tabs)
        page.update()

    # --- Login (solo en web; el .exe de escritorio nunca llega a
    # este archivo, usa su propio main.py sin login) ---
    pantalla_login = PantallaLogin(con_web, on_login_exitoso=mostrar_app)
    resultado_login = pantalla_login.build(page)

    if getattr(resultado_login, "data", None) == "__login_automatico__":
        # Vino con un token valido en la URL -- pasar directo, sin
        # mostrar el formulario de login.
        token = extraer_token_de_ruta(page.route or "")
        usuario = ae.obtener_usuario_por_token(con_web, token)
        mostrar_app(usuario)
    else:
        page.add(resultado_login)


if __name__ == "__main__":
    con_web = ae.inicializar_db("web_app.db")
    cargar_catalogo_compartido()
    ft.run(main, view=ft.AppView.WEB_BROWSER, port=8550)
