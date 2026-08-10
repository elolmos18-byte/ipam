# pantalla_indice.py
# Replica el contenido de precios.html: totales por super, tabla agrupada
# por rubro con ranking (medallas) y detalle expandible por producto.
#
# Fuente de datos: precios_ultimo.json (fecha, rubros, totales, mas_barato)
# en vez del catalogo completo — mismo formato que usa la web.

import flet as ft
from typing import Dict, List, Optional

TIENDAS = ["La Anonima", "Carrefour", "Changomas", "Vea"]
TIENDAS_DISPLAY = {
    "La Anonima": "La Anónima",
    "Carrefour": "Carrefour",
    "Changomas": "Changomas",
    "Vea": "Vea",
}
UNIDADES = {"kg": "/kg", "L": "/L", "unidad": "/u", "m": "/m", "panos": "/paño"}

GRUPOS_ORDEN = ["Almacen", "Carniceria", "Verduleria", "Limpieza"]
GRUPOS_DISPLAY = {
    "Almacen": "🛒 Almacén",
    "Carniceria": "🥩 Carnicería",
    "Verduleria": "🥬 Verdulería",
    "Limpieza": "🧼 Limpieza",
}

ICONOS_TENDENCIA = {"baja": "▼", "igual": "=", "sube": "▲"}
COLOR_TENDENCIA = {"baja": "#2d6a4f", "igual": "#2d6a4f", "sube": "#b85450"}
MEDALLAS = {1: "🥇", 2: "🥈", 3: "🥉"}

NAVY = "#0a1628"
NAVY_LIGHT = "#142238"
GOLD = "#c9a84c"
GOLD_DIM = "#a08636"
CREAM = "#f5f0e8"
GREEN = "#2d6a4f"
TEXT_LIGHT = "#6b6b6b"


class PantallaIndice:
    def __init__(self, precios_ultimo: Optional[Dict]):
        self.datos = precios_ultimo
        self.expandido: Dict[str, bool] = {}
        self.contenedores_detalle: Dict[str, ft.Container] = {}
        self.page: Optional[ft.Page] = None

    def build(self, page: ft.Page) -> ft.Control:
        self.page = page

        if not self.datos:
            return ft.Container(
                content=ft.Text(
                    "No se pudieron cargar los precios de hoy. "
                    "Verificá que precios_ultimo.json esté disponible en el VPS.",
                    color="red",
                ),
                padding=20,
            )

        rubros = self.datos.get("rubros", [])

        return ft.Column(
            [
                ft.Text("¿Cuál es el súper más barato hoy?", size=20, weight="bold", color=NAVY,
                        font_family="Cinzel"),
                ft.Text(self._formatear_fecha(), size=13, color=GOLD_DIM),
                ft.Container(height=8),
                self._construir_totales(),
                ft.Container(height=8),
                ft.Text(f"{len(rubros)} productos comparados", size=14, weight="bold", color=NAVY,
                        font_family="Cinzel"),
                self._construir_tabla(),
            ],
            scroll=ft.ScrollMode.AUTO,
            expand=True,
            spacing=8,
        )

    # ------------------------------------------------------------
    # Helpers de formato (equivalentes a los del precios.html)
    # ------------------------------------------------------------

    def _formatear_fecha(self) -> str:
        fecha = self.datos.get("fecha", "")
        try:
            partes = fecha.split("-")
            meses = [
                "enero", "febrero", "marzo", "abril", "mayo", "junio",
                "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
            ]
            return f"Precios del {int(partes[2])} de {meses[int(partes[1]) - 1]} de {partes[0]}"
        except Exception:
            return f"Precios del {fecha}" if fecha else "Sin fecha"

    def _valor_comparable(self, info: dict):
        pn = info.get("precio_normalizado")
        return pn if pn is not None else info.get("precio_envase")

    def _rankear(self, precios: dict) -> Dict[str, int]:
        disponibles = [t for t in TIENDAS if precios.get(t)]
        ordenadas = sorted(disponibles, key=lambda t: self._valor_comparable(precios[t]))
        return {t: i + 1 for i, t in enumerate(ordenadas)}

    def _mas_barato(self, precios: dict) -> Optional[str]:
        ranking = self._rankear(precios)
        for t in TIENDAS:
            if ranking.get(t) == 1:
                return t
        return None

    def _formatear_precio(self, valor, unidad) -> str:
        if valor is None:
            return "—"
        sufijo = UNIDADES.get(unidad, "")
        return f"${round(valor):,}".replace(",", ".") + sufijo

    def _formatear_total(self, valor) -> str:
        return f"${round(valor):,}".replace(",", ".")

    # ------------------------------------------------------------
    # Tarjetas de totales
    # ------------------------------------------------------------

    def _construir_totales(self) -> ft.Control:
        rubros = self.datos.get("rubros", [])
        totales = self.datos.get("totales", {})
        mas_barato_global = self.datos.get("mas_barato")

        rubros_ganados = {t: 0 for t in TIENDAS}
        for rubro in rubros:
            ganador = self._mas_barato(rubro.get("precios", {}))
            if ganador:
                rubros_ganados[ganador] += 1

        cards = []
        for tienda in TIENDAS:
            total = totales.get(tienda)
            if total is None:
                continue

            es_ganador = tienda == mas_barato_global

            contenido = [
                ft.Text(TIENDAS_DISPLAY[tienda].upper(), size=11, color="#e8e0d0", weight="bold"),
                ft.Text(self._formatear_total(total), size=22, weight="bold",
                        color=GOLD if es_ganador else CREAM),
            ]
            if es_ganador:
                contenido.append(
                    ft.Container(
                        content=ft.Text("MÁS BARATO", size=9, weight="bold", color=NAVY),
                        bgcolor=GOLD,
                        padding=ft.Padding(left=8, top=2, right=8, bottom=2),
                        border_radius=3,
                    )
                )
            contenido.append(
                ft.Text(f"Gana en {rubros_ganados[tienda]} de {len(rubros)} productos",
                        size=10, color=TEXT_LIGHT)
            )

            cards.append(
                ft.Container(
                    content=ft.Column(contenido, spacing=4),
                    bgcolor=NAVY_LIGHT,
                    padding=14,
                    border_radius=8,
                    border=ft.Border.all(1, GOLD if es_ganador else "#1e3250"),
                    width=170,
                )
            )

        return ft.Container(
            content=ft.Row(cards, spacing=10, wrap=True),
            bgcolor=NAVY,
            padding=14,
            border_radius=8,
        )

    # ------------------------------------------------------------
    # Tabla agrupada por rubro
    # ------------------------------------------------------------

    def _construir_tabla(self) -> ft.Control:
        rubros = self.datos.get("rubros", [])
        por_grupo: Dict[str, List[dict]] = {}
        for rubro in rubros:
            grupo = rubro.get("grupo", "Almacen")
            por_grupo.setdefault(grupo, []).append(rubro)

        filas: List[ft.Control] = []

        encabezado = ft.Container(
            content=ft.Row(
                [ft.Container(ft.Text("Producto", size=11, weight="bold", color=GOLD), expand=2)]
                + [
                    ft.Container(
                        ft.Text(TIENDAS_DISPLAY[t], size=11, weight="bold", color=GOLD),
                        expand=1,
                        alignment=ft.Alignment(1, 0),
                    )
                    for t in TIENDAS
                ],
                spacing=4,
            ),
            bgcolor=NAVY,
            padding=ft.Padding(left=10, top=8, right=10, bottom=8),
        )
        filas.append(encabezado)

        for grupo in GRUPOS_ORDEN:
            rubros_grupo = por_grupo.get(grupo)
            if not rubros_grupo:
                continue

            filas.append(
                ft.Container(
                    content=ft.Text(GRUPOS_DISPLAY.get(grupo, grupo), size=12, weight="bold", color=GOLD),
                    bgcolor=NAVY,
                    padding=ft.Padding(left=10, top=6, right=10, bottom=6),
                )
            )

            for rubro in rubros_grupo:
                filas.append(self._fila_rubro(rubro))

        return ft.Container(
            content=ft.Column(filas, spacing=1),
            bgcolor="#ffffff",
            border_radius=6,
        )

    def _fila_rubro(self, rubro: dict) -> ft.Control:
        rubro_id = str(rubro.get("id"))
        precios = rubro.get("precios", {})
        ranking = self._rankear(precios)
        ganador = self._mas_barato(precios)

        celdas: List[ft.Control] = [
            ft.Container(ft.Text(rubro.get("nombre", ""), size=12, weight="bold", color=NAVY), expand=2)
        ]

        for tienda in TIENDAS:
            info = precios.get(tienda)
            if not info:
                celdas.append(
                    ft.Container(
                        ft.Text("—", size=12, color=TEXT_LIGHT, italic=True),
                        expand=1,
                        alignment=ft.Alignment(1, 0),
                    )
                )
                continue

            pn = info.get("precio_normalizado")
            precio_str = self._formatear_precio(
                pn if pn is not None else info.get("precio_envase"),
                rubro.get("unidad") if pn is not None else "",
            )
            posicion = ranking.get(tienda)
            medalla = MEDALLAS.get(posicion, "")
            es_barato = posicion == 1
            tendencia = info.get("tendencia")
            icono_tendencia = ICONOS_TENDENCIA.get(tendencia, "")
            color_tendencia = COLOR_TENDENCIA.get(tendencia, TEXT_LIGHT)

            texto = f"{medalla} {precio_str}".strip()
            contenido_celda = [
                ft.Text(texto, size=12, color=GREEN if es_barato else NAVY,
                        weight="bold" if es_barato else "normal")
            ]
            if icono_tendencia:
                contenido_celda.append(ft.Text(icono_tendencia, size=11, color=color_tendencia))

            celdas.append(
                ft.Container(
                    content=ft.Row(contenido_celda, spacing=2, alignment=ft.MainAxisAlignment.END),
                    expand=1,
                    bgcolor="#e8f3ec" if es_barato else None,
                    padding=ft.Padding(left=4, top=2, right=4, bottom=2),
                    border_radius=3,
                )
            )

        detalle = self._detalle_rubro(rubro, ganador)
        detalle.visible = self.expandido.get(rubro_id, False)
        self.contenedores_detalle[rubro_id] = detalle

        fila_principal = ft.Container(
            content=ft.Row(celdas, spacing=4),
            padding=ft.Padding(left=10, top=8, right=10, bottom=8),
            on_click=lambda e, rid=rubro_id: self._toggle_detalle(rid),
        )

        return ft.Column([fila_principal, detalle], spacing=0)

    def _detalle_rubro(self, rubro: dict, ganador: Optional[str]) -> ft.Container:
        precios = rubro.get("precios", {})
        filas_detalle: List[ft.Control] = []

        for tienda in TIENDAS:
            info = precios.get(tienda)
            if not info:
                continue

            es_barato = tienda == ganador
            pn = info.get("precio_normalizado")
            precio_str = self._formatear_precio(
                pn if pn is not None else info.get("precio_envase"),
                rubro.get("unidad") if pn is not None else "",
            )
            envase = info.get("precio_envase")
            envase_str = (
                f" · envase ${round(envase):,}".replace(",", ".") if envase is not None else ""
            )

            fila_controles: List[ft.Control] = [
                ft.Text(TIENDAS_DISPLAY[tienda], size=11, weight="bold",
                        color=GREEN if es_barato else NAVY, width=90),
                ft.Text(precio_str, size=11, color=NAVY),
                ft.Text(envase_str, size=10, color=TEXT_LIGHT),
                ft.Text(f"— {info.get('producto', '')}", size=11, color="#2c2c2c"),
            ]
            if info.get("url"):
                fila_controles.append(
                    ft.TextButton(
                        "Ver producto →",
                        url=info["url"],
                        style=ft.ButtonStyle(color=GOLD_DIM),
                    )
                )
            filas_detalle.append(ft.Row(fila_controles, spacing=6, wrap=True))

        return ft.Container(
            content=ft.Column(filas_detalle, spacing=6),
            bgcolor=CREAM,
            padding=ft.Padding(left=14, top=10, right=14, bottom=10),
            visible=False,
        )

    def _toggle_detalle(self, rubro_id: str):
        self.expandido[rubro_id] = not self.expandido.get(rubro_id, False)
        detalle = self.contenedores_detalle.get(rubro_id)
        if detalle:
            detalle.visible = self.expandido[rubro_id]
            if self.page:
                self.page.update()
