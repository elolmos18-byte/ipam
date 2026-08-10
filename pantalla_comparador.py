# pantalla_comparador.py
import flet as ft
import sqlite3
from typing import Callable, Dict, List, Optional
from utils.graficos import crear_linechart_comparador
from db_web import agregar_producto_lista

NAVY = "#0a1628"
NAVY_LIGHT = "#142238"
GOLD = "#c9a84c"
GOLD_DIM = "#a08636"
CREAM = "#f5f0e8"
TEXT_LIGHT = "#6b6b6b"
GREEN = "#2d6a4f"

MAX_RESULTADOS = 30
MAX_POR_GRUPO = 40  # los grupos grandes (ej. Limpieza, ~3600 productos) se
                     # muestran de a tandas, con un filtro para acotar


class PantallaComparador:
    def __init__(
        self,
        datos_dashboard: Optional[Dict],
        con_web: sqlite3.Connection,
        usuario_id: int,
        on_agregado_a_lista: Optional[Callable[[ft.Page], None]] = None,
    ):
        self.datos_dashboard = datos_dashboard
        self.con_web = con_web
        self.usuario_id = usuario_id
        self.productos_por_categoria = datos_dashboard.get("productos_por_categoria", {}) if datos_dashboard else {}
        self.tiendas = datos_dashboard.get("tiendas", {}) if datos_dashboard else {}
        # productos_por_categoria ya viene agrupado en las 13 categorias
        # unificadas Y con el matching entre supers aplicado desde
        # main.py -- no hace falta volver a procesarlo aca.
        self.grupos_unificados = self.productos_por_categoria
        # Callback para avisarle a la tab "Mi Lista" que hay un producto
        # nuevo, ya que esa tab no se reconstruye sola al cambiar de tab.
        self.on_agregado_a_lista = on_agregado_a_lista
        self.page: Optional[ft.Page] = None

    def build(self, page: ft.Page) -> ft.Column:
        self.page = page

        if not self.datos_dashboard:
            return ft.Column([ft.Text("Error: No hay datos", color="red")])

        self.input_busqueda = ft.TextField(
            label="Buscar producto",
            hint_text="Ej: Harina",
            expand=True,
            border_color="#cbb98a",
            focused_border_color=GOLD,
            label_style=ft.TextStyle(color=NAVY),
            cursor_color=GOLD_DIM,
            on_submit=self._buscar_producto,
        )
        boton_buscar = ft.Button("Buscar", on_click=self._buscar_producto, color=NAVY, bgcolor=GOLD)
        boton_categorias = ft.Button(
            "📂 Categorías", on_click=self._mostrar_categorias, color=NAVY, bgcolor="#ffffff",
            style=ft.ButtonStyle(side=ft.BorderSide(1, "#cbb98a")),
        )

        self.area_resultado = ft.Container(
            content=ft.Text(
                "Ingresá el nombre de un producto, o tocá \"Categorías\" para explorar.",
                color=TEXT_LIGHT,
            ),
            padding=16,
            bgcolor="#ffffff",
            border_radius=8,
            expand=True,
        )

        return ft.Column(
            [
                ft.Text("Comparador de Precios", size=20, weight="bold", color=NAVY, font_family="Cinzel"),
                ft.Row([self.input_busqueda, boton_buscar, boton_categorias]),
                ft.Divider(color="#e8e0d0"),
                self.area_resultado,
            ],
            scroll=ft.ScrollMode.AUTO,
            expand=True,
            spacing=10,
        )

    # ------------------------------------------------------------
    # Búsqueda por nombre: junta TODAS las coincidencias
    # ------------------------------------------------------------

    def _buscar_producto(self, e):
        nombre = self.input_busqueda.value.lower().strip() if self.input_busqueda.value else ""
        if not nombre:
            self.area_resultado.content = ft.Text("Ingresá un nombre", color=TEXT_LIGHT)
            self.area_resultado.update()
            return

        # Todas las coincidencias, SIN el tope de MAX_RESULTADOS -- el
        # resumen "mas barato por super" tiene que mirar todo, no solo
        # los primeros 30 que despues se listan.
        todas_las_coincidencias: List[Dict] = []
        for categoria, productos in self.productos_por_categoria.items():
            for producto in productos:
                if nombre in producto.get("nombre", "").lower():
                    todas_las_coincidencias.append(producto)

        if not todas_las_coincidencias:
            self.area_resultado.content = ft.Text(f"No se encontró: {nombre}", color="#b85450")
            self.area_resultado.update()
            return

        coincidencias = todas_las_coincidencias[:MAX_RESULTADOS]

        resumen = self._calcular_mas_barato_por_tienda(todas_las_coincidencias)
        tarjetas_resumen = self._construir_tarjetas_mas_barato(resumen, nombre) if resumen else None

        self._mostrar_lista_productos(
            coincidencias,
            titulo=f'{len(coincidencias)} resultado(s) para "{nombre}"'
            + (f" (mostrando los primeros {MAX_RESULTADOS})" if len(coincidencias) >= MAX_RESULTADOS else ""),
            volver_a=self._volver_a_input,
            extra_arriba=tarjetas_resumen,
        )

    def _calcular_mas_barato_por_tienda(self, productos: List[Dict]) -> Dict[str, tuple]:
        """De TODOS los productos que matchearon la busqueda, encuentra
        el precio normalizado ($/L, $/kg o $/u) mas bajo QUE CADA
        TIENDA tiene para ofrecer -- sin importar si es "el mismo"
        producto exacto en las 4, ni el tamaño del envase. Es la
        pregunta "¿cuál es la Coca-Cola mas barata por litro que
        vende cada super?", no "¿cuál super tiene el mismo producto
        mas barato?"."""

        # Primero, cual es la unidad normalizada mas comun entre los
        # resultados (para no comparar $/L contra $/kg si la busqueda
        # trajo productos de tipos distintos por error).
        conteo_unidades: Dict[str, int] = {}
        for producto in productos:
            historico = producto.get("historico", [])
            if not historico:
                continue
            for info in historico[-1].get("precios", {}).values():
                if isinstance(info, dict) and info.get("unidad_normalizada"):
                    u = info["unidad_normalizada"]
                    conteo_unidades[u] = conteo_unidades.get(u, 0) + 1

        if not conteo_unidades:
            return {}
        unidad_elegida = max(conteo_unidades, key=conteo_unidades.get)

        mejor_por_tienda: Dict[str, tuple] = {}  # tienda_id -> (precio_norm, nombre_producto, url)
        for producto in productos:
            historico = producto.get("historico", [])
            if not historico:
                continue
            nombre_producto = producto.get("nombre", "")
            for tienda_id, info in historico[-1].get("precios", {}).items():
                if not isinstance(info, dict):
                    continue
                if info.get("unidad_normalizada") != unidad_elegida:
                    continue
                precio_norm = info.get("precio_normalizado")
                if not precio_norm:
                    continue
                actual = mejor_por_tienda.get(tienda_id)
                if actual is None or precio_norm < actual[0]:
                    mejor_por_tienda[tienda_id] = (precio_norm, nombre_producto, info.get("url"))

        return {"unidad": unidad_elegida, "por_tienda": mejor_por_tienda}

    def _construir_tarjetas_mas_barato(self, resumen: Dict, busqueda: str) -> Optional[ft.Control]:
        por_tienda = resumen.get("por_tienda", {})
        unidad = resumen.get("unidad", "u")
        if not por_tienda:
            return None

        ganador_global = min(por_tienda, key=lambda t: por_tienda[t][0])

        tarjetas = []
        for tienda_id, tienda_nombre in self.tiendas.items():
            if tienda_id not in por_tienda:
                continue
            precio_norm, nombre_producto, url = por_tienda[tienda_id]
            es_ganador = tienda_id == ganador_global

            contenido_tarjeta = [
                ft.Text(tienda_nombre.upper(), size=10, color="#e8e0d0", weight="bold"),
                ft.Text(f"${precio_norm:,.0f}/{unidad}", size=18, weight="bold",
                         color=GOLD if es_ganador else CREAM),
                ft.Text(nombre_producto, size=9, color="#c8bda0", max_lines=2),
            ]
            if url:
                contenido_tarjeta.append(
                    ft.TextButton("Ver producto →", url=url, style=ft.ButtonStyle(color=GOLD_DIM))
                )

            tarjetas.append(
                ft.Container(
                    content=ft.Column(contenido_tarjeta, spacing=2),
                    bgcolor=NAVY_LIGHT,
                    padding=12,
                    border_radius=8,
                    border=ft.Border.all(1, GOLD if es_ganador else "#1e3250"),
                    width=170,
                )
            )

        return ft.Container(
            content=ft.Column(
                [
                    ft.Text(f'Más barata por {unidad}, buscando "{busqueda}":', size=12, color="#e8e0d0"),
                    ft.Row(tarjetas, spacing=8, wrap=True),
                ],
                spacing=8,
            ),
            bgcolor=NAVY,
            padding=14,
            border_radius=8,
        )

    # ------------------------------------------------------------
    # Navegación por categoría
    # ------------------------------------------------------------

    def _mostrar_categorias(self, e=None):
        filas = [ft.Text("Elegí una categoría:", size=13, weight="bold", color=NAVY)]

        for grupo, productos in self.grupos_unificados.items():
            filas.append(
                ft.Container(
                    content=ft.Row(
                        [
                            ft.Text(grupo, size=13, color=NAVY, expand=True),
                            ft.Text(f"{len(productos)} productos", size=11, color=TEXT_LIGHT),
                            ft.Text("→", size=13, color=GOLD_DIM),
                        ],
                    ),
                    padding=ft.Padding(left=12, top=10, right=12, bottom=10),
                    border=ft.Border(bottom=ft.BorderSide(1, "#e8e0d0")),
                    on_click=lambda e, g=grupo: self._mostrar_productos_de_grupo(g),
                )
            )

        self.area_resultado.content = ft.Column(filas, spacing=0, scroll=ft.ScrollMode.AUTO)
        self.area_resultado.update()

    def _mostrar_productos_de_grupo(self, grupo: str, filtro: str = ""):
        todos = self.grupos_unificados.get(grupo, [])

        if filtro:
            filtrados = [p for p in todos if filtro.lower() in p.get("nombre", "").lower()]
        else:
            filtrados = todos

        mostrados = filtrados[:MAX_POR_GRUPO]

        boton_volver = ft.TextButton(
            "← Volver a categorías",
            on_click=lambda e: self._mostrar_categorias(),
            style=ft.ButtonStyle(color=GOLD_DIM),
        )

        campo_filtro = ft.TextField(
            label=f"Filtrar dentro de {grupo}",
            value=filtro,
            dense=True,
            border_color="#cbb98a",
            focused_border_color=GOLD,
            on_change=lambda e, g=grupo: self._mostrar_productos_de_grupo(g, e.control.value),
        )

        info = ft.Text(
            f"{len(filtrados)} producto(s)"
            + (f" — mostrando los primeros {MAX_POR_GRUPO}" if len(filtrados) > MAX_POR_GRUPO else ""),
            size=11, color=TEXT_LIGHT,
        )

        filas: List[ft.Control] = [boton_volver, campo_filtro, info]

        if not mostrados:
            filas.append(ft.Text("Sin resultados con ese filtro.", color=TEXT_LIGHT))
        else:
            for producto in mostrados:
                filas.append(
                    ft.Container(
                        content=ft.Row(
                            [
                                ft.Text(producto.get("nombre", ""), size=13, color=NAVY, expand=True),
                                ft.Text("Ver precios →", size=12, color=GOLD_DIM),
                            ],
                        ),
                        padding=ft.Padding(left=12, top=8, right=12, bottom=8),
                        border=ft.Border(bottom=ft.BorderSide(1, "#e8e0d0")),
                        on_click=lambda e, p=producto: self._mostrar_producto(
                            p, volver_a=lambda: self._mostrar_productos_de_grupo(grupo, filtro)
                        ),
                    )
                )

        self.area_resultado.content = ft.Column(filas, spacing=6, scroll=ft.ScrollMode.AUTO)
        self.area_resultado.update()

    # ------------------------------------------------------------
    # Lista de resultados genérica (usada por la búsqueda por nombre)
    # ------------------------------------------------------------

    def _mostrar_lista_productos(self, productos: List[Dict], titulo: str, volver_a: Optional[Callable] = None,
                                   extra_arriba: Optional[ft.Control] = None):
        filas: List[ft.Control] = []
        if extra_arriba:
            filas.append(extra_arriba)
        filas.append(ft.Text(titulo, size=12, color=TEXT_LIGHT))

        for producto in productos:
            filas.append(
                ft.Container(
                    content=ft.Row(
                        [
                            ft.Column(
                                [
                                    ft.Text(producto.get("nombre", ""), size=13, weight="bold", color=NAVY),
                                    ft.Text(f"Marca: {producto.get('marca') or 'N/A'}", size=11, color=TEXT_LIGHT),
                                ],
                                spacing=2,
                                expand=True,
                            ),
                            ft.Text("Ver precios →", size=12, color=GOLD_DIM),
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    ),
                    padding=ft.Padding(left=12, top=10, right=12, bottom=10),
                    border=ft.Border(bottom=ft.BorderSide(1, "#e8e0d0")),
                    on_click=lambda e, p=producto: self._mostrar_producto(p, volver_a=volver_a),
                )
            )

        self.area_resultado.content = ft.Column(filas, spacing=0, scroll=ft.ScrollMode.AUTO)
        self.area_resultado.update()

    # ------------------------------------------------------------
    # Detalle de un producto elegido: historico + agregar a Mi Lista
    # ------------------------------------------------------------

    def _mostrar_producto(self, producto: Dict, volver_a: Optional[Callable] = None):
        grafico = crear_linechart_comparador(producto, self.tiendas)

        boton_volver = ft.TextButton(
            "← Volver",
            on_click=lambda e: (volver_a or self._volver_a_input)(),
            style=ft.ButtonStyle(color=GOLD_DIM),
        )

        encabezado = ft.Container(
            content=ft.Column(
                [
                    ft.Text(producto.get("nombre", ""), size=16, weight="bold", color=GOLD, font_family="Cinzel"),
                    ft.Text(f"Marca: {producto.get('marca') or 'N/A'}", size=12, color="#e8e0d0"),
                ],
                spacing=4,
            ),
            bgcolor=NAVY_LIGHT,
            padding=14,
            border_radius=8,
            border=ft.Border.all(1, "#1e3250"),
        )

        agregar_col = ft.Column(
            [ft.Text("Agregar a Mi Lista:", size=12, weight="bold", color=NAVY)],
            spacing=6,
        )

        historico = producto.get("historico", [])
        precios_ultimo_dia = historico[-1].get("precios", {}) if historico else {}

        # Encontrar quien tiene el precio normalizado ($/L, $/kg, $/u)
        # mas bajo -- el "mas barato de verdad", no solo el numero en
        # pesos mas chico (que puede engañar si los envases son de
        # tamaño distinto entre supers).
        normalizados_validos = {
            tid: info.get("precio_normalizado")
            for tid, info in precios_ultimo_dia.items()
            if isinstance(info, dict) and info.get("precio_normalizado")
        }
        tienda_mas_barata = min(normalizados_validos, key=normalizados_validos.get) if normalizados_validos else None

        if tienda_mas_barata:
            unidad_ganadora = precios_ultimo_dia[tienda_mas_barata].get("unidad_normalizada", "u")
            agregar_col.controls.append(
                ft.Text(
                    f"🏆 Más barato de verdad: {self.tiendas.get(tienda_mas_barata, tienda_mas_barata)} "
                    f"(${normalizados_validos[tienda_mas_barata]:,.0f}/{unidad_ganadora})",
                    size=11, color=GREEN, weight="bold",
                )
            )

        for tienda_id, tienda_nombre in self.tiendas.items():
            precio_data = precios_ultimo_dia.get(tienda_id)
            precio = precio_data.get("precio", 0) if isinstance(precio_data, dict) else precio_data
            if not precio:
                continue

            precio_normalizado = precio_data.get("precio_normalizado") if isinstance(precio_data, dict) else None
            unidad_normalizada = precio_data.get("unidad_normalizada") if isinstance(precio_data, dict) else None
            url = precio_data.get("url") if isinstance(precio_data, dict) else None
            es_mas_barata = tienda_id == tienda_mas_barata

            columna_precio = [ft.Text(f"${precio:,.0f}", size=12, weight="bold", color=NAVY)]
            if precio_normalizado:
                columna_precio.append(
                    ft.Text(f"${precio_normalizado:,.0f}/{unidad_normalizada}", size=10,
                            color=GREEN if es_mas_barata else TEXT_LIGHT)
                )

            botones_fila = []
            if url:
                botones_fila.append(
                    ft.IconButton(
                        ft.Icons.OPEN_IN_NEW,
                        icon_size=18,
                        icon_color=GOLD_DIM,
                        tooltip="Ver producto en la web del súper",
                        url=url,
                    )
                )
            botones_fila.append(
                ft.IconButton(
                    ft.Icons.ADD_CIRCLE,
                    icon_size=20,
                    icon_color=GOLD_DIM,
                    tooltip="Agregar a Mi Lista",
                    on_click=lambda e, p=producto, tid=tienda_id, tn=tienda_nombre, pr=precio:
                        self._agregar_a_lista(e, p, tid, tn, pr),
                )
            )

            agregar_col.controls.append(
                ft.Container(
                    content=ft.Row(
                        [
                            ft.Text(
                                ("🏆 " if es_mas_barata else "") + tienda_nombre,
                                size=12, color=GREEN if es_mas_barata else NAVY,
                                weight="bold" if es_mas_barata else "normal", expand=True,
                            ),
                            ft.Column(columna_precio, spacing=0, horizontal_alignment=ft.CrossAxisAlignment.END),
                            ft.Row(botones_fila, spacing=0),
                        ],
                    ),
                    bgcolor="#e8f3ec" if es_mas_barata else CREAM,
                    padding=ft.Padding(left=10, top=4, right=10, bottom=4),
                    border_radius=6,
                )
            )

        if len(agregar_col.controls) == 1:  # solo el título, sin tiendas con precio
            agregar_col.controls.append(ft.Text("Sin precios disponibles hoy.", size=12, color=TEXT_LIGHT))

        info_col = ft.Column(
            [
                boton_volver,
                encabezado,
                agregar_col,
                ft.Text("Últimos registros", size=13, weight="bold", color=NAVY),
                ft.Container(content=grafico, expand=True, border=ft.Border.all(1, "#e8e0d0"), border_radius=8),
            ],
            spacing=10,
            scroll=ft.ScrollMode.AUTO,
        )

        self.area_resultado.content = info_col
        self.area_resultado.update()

    def _agregar_a_lista(self, e, producto: Dict, tienda_id: str, tienda_nombre: str, precio: float):
        agregar_producto_lista(
            self.con_web,
            self.usuario_id,
            producto.get("nombre", ""),
            producto.get("marca", ""),
            tienda_id,
            precio,
        )

        # Avisarle a la tab "Mi Lista" que hay un producto nuevo
        if self.on_agregado_a_lista:
            self.on_agregado_a_lista(e.page)

        confirmacion = ft.SnackBar(
            content=ft.Text(f"Agregado: {producto.get('nombre', '')} — {tienda_nombre}", color=CREAM),
            bgcolor=NAVY,
        )
        e.page.show_dialog(confirmacion)

    def _volver_a_input(self):
        self.area_resultado.content = ft.Text(
            "Ingresá el nombre de un producto, o tocá \"Categorías\" para explorar.",
            color=TEXT_LIGHT,
        )
        self.area_resultado.update()
