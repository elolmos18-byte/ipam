# pantalla_lista_compras.py (version IPAM / web)
import flet as ft
import sqlite3
from typing import Dict, Optional
from db_web import agregar_producto_lista, obtener_lista_compras, eliminar_producto_lista, limpiar_lista

NAVY = "#0a1628"
NAVY_LIGHT = "#142238"
GOLD = "#c9a84c"
GOLD_DIM = "#a08636"
CREAM = "#f5f0e8"
TEXT_LIGHT = "#6b6b6b"
GREEN = "#2d6a4f"


class PantallaListaCompras:
    def __init__(self, datos_dashboard: Optional[Dict], con_web: sqlite3.Connection, usuario_id: int):
        self.datos_dashboard = datos_dashboard
        self.con_web = con_web
        self.usuario_id = usuario_id
        self.tiendas = datos_dashboard.get("tiendas", {}) if datos_dashboard else {}
        self.lista_items = []
        self.tienda_seleccionada: Optional[str] = None
        self.chips_tienda: Dict[str, ft.Container] = {}

    def build(self) -> ft.Column:
        self._cargar_lista()

        self.input_producto = ft.TextField(
            label="Producto", hint_text="Ej: Harina", width=250,
            border_color="#cbb98a", focused_border_color=GOLD,
            label_style=ft.TextStyle(color=NAVY),
        )
        self.selector_tienda = self._construir_selector_tienda()
        boton_agregar = ft.Button("Agregar", on_click=self._agregar_producto, color=NAVY, bgcolor=GOLD)

        self.lista_view = ft.Column()
        self._actualizar_vista_lista()

        self.area_totales = ft.Column()
        self._actualizar_totales()

        boton_limpiar = ft.Button(
            "Limpiar Lista", on_click=self._limpiar_lista_click,
            color="#b85450", bgcolor="#ffffff",
        )

        return ft.Column([
            ft.Text("Mi Lista de Compras", size=20, weight="bold", color=NAVY, font_family="Cinzel"),
            ft.Row([self.input_producto, boton_agregar]),
            ft.Text("Tienda:", size=12, color=NAVY),
            self.selector_tienda,
            ft.Divider(color="#e8e0d0"),
            ft.Text("Productos", size=13, weight="bold", color=NAVY),
            ft.Container(content=self.lista_view, expand=True, bgcolor="#ffffff",
                         border=ft.Border.all(1, "#e8e0d0"), border_radius=8, padding=10),
            ft.Divider(color="#e8e0d0"),
            ft.Text("Totales por Tienda", size=13, weight="bold", color=NAVY),
            ft.Container(content=self.area_totales, bgcolor=NAVY_LIGHT,
                         border=ft.Border.all(1, "#1e3250"), border_radius=8, padding=12),
            boton_limpiar
        ], scroll=ft.ScrollMode.AUTO, expand=True, spacing=10)

    def _cargar_lista(self):
        self.lista_items = obtener_lista_compras(self.con_web, self.usuario_id)

    def _construir_selector_tienda(self) -> ft.Row:
        chips = []
        for tienda_id, nombre in self.tiendas.items():
            chip = ft.Container(
                content=ft.Text(nombre, size=12, color=NAVY),
                padding=ft.Padding(left=14, top=7, right=14, bottom=7),
                bgcolor="#ffffff",
                border=ft.Border.all(1, "#cbb98a"),
                border_radius=16,
                on_click=lambda e, tid=tienda_id: self._seleccionar_tienda(tid, e),
            )
            self.chips_tienda[tienda_id] = chip
            chips.append(chip)
        return ft.Row(chips, spacing=8, wrap=True)

    def _seleccionar_tienda(self, tienda_id: str, e):
        self.tienda_seleccionada = tienda_id
        for tid, chip in self.chips_tienda.items():
            seleccionado = tid == tienda_id
            chip.bgcolor = GOLD if seleccionado else "#ffffff"
            chip.border = ft.Border.all(1, GOLD if seleccionado else "#cbb98a")
            chip.content.weight = "bold" if seleccionado else "normal"
        e.page.update()

    def refrescar(self, page: ft.Page):
        """Se llama desde afuera (ej: Comparador) cuando se agrega un
        producto a la lista para que esta pantalla vuelva a leer la DB
        y se repinte."""
        self._cargar_lista()
        self._actualizar_vista_lista()
        self._actualizar_totales()
        page.update()

    def _actualizar_vista_lista(self):
        self.lista_view.controls.clear()
        if not self.lista_items:
            self.lista_view.controls.append(ft.Text("Lista vacía", color=TEXT_LIGHT))
            return

        for item in self.lista_items:
            tienda_nombre = self.tiendas.get(item.get("tienda_id"), "Unknown")

            fila = ft.Row([
                ft.Text(
                    f"{item['producto_nombre']} ({item['marca']}) - {tienda_nombre}: ${item['precio']:,.0f}",
                    expand=True, color=NAVY,
                ),
                ft.IconButton(
                    ft.Icons.DELETE, icon_size=18, icon_color="#b85450",
                    on_click=lambda _, iid=item["id"]: self._eliminar_producto(iid),
                )
            ])
            self.lista_view.controls.append(fila)

    def _actualizar_totales(self):
        totales = {}
        for item in self.lista_items:
            tienda_id = item.get("tienda_id")
            if tienda_id not in totales:
                totales[tienda_id] = 0
            totales[tienda_id] += item.get("precio", 0)

        self.area_totales.controls.clear()
        for tienda_id in sorted(self.tiendas.keys()):
            tienda_nombre = self.tiendas[tienda_id]
            total = totales.get(tienda_id, 0)
            self.area_totales.controls.append(
                ft.Row([
                    ft.Text(f"{tienda_nombre}:", width=150, weight="bold", color="#e8e0d0"),
                    ft.Text(f"${total:,.0f}", size=14, weight="bold", color=CREAM)
                ])
            )

        self.area_totales.controls.append(ft.Divider(color="#1e3250"))
        total_general = sum(totales.values())
        self.area_totales.controls.append(
            ft.Row([
                ft.Text("TOTAL GENERAL:", width=150, weight="bold", color="#e8e0d0"),
                ft.Text(f"${total_general:,.0f}", size=16, weight="bold", color=GOLD)
            ])
        )

    def _agregar_producto(self, e):
        nombre = self.input_producto.value
        tienda_id = self.tienda_seleccionada

        if not nombre:
            return

        if not tienda_id:
            e.page.show_dialog(ft.SnackBar(
                content=ft.Text("Elegí una tienda antes de agregar", color=CREAM),
                bgcolor="#b85450",
            ))
            return

        precio = 0
        for categoria, productos in self.datos_dashboard.get("productos_por_categoria", {}).items():
            for p in productos:
                if p.get("nombre").lower() == nombre.lower():
                    historico = p.get("historico", [])
                    if historico:
                        precio_data = historico[-1].get("precios", {}).get(tienda_id)
                        precio = precio_data.get("precio", 0) if isinstance(precio_data, dict) else precio_data
                    break

        agregar_producto_lista(self.con_web, self.usuario_id, nombre, "", tienda_id, precio)
        self._cargar_lista()
        self._actualizar_vista_lista()
        self._actualizar_totales()

        self.input_producto.value = ""
        e.page.update()

    def _eliminar_producto(self, item_id: int):
        eliminar_producto_lista(self.con_web, self.usuario_id, item_id)
        self._cargar_lista()
        self._actualizar_vista_lista()
        self._actualizar_totales()

    def _limpiar_lista_click(self, e):
        def cancelar(e):
            e.page.pop_dialog()

        def confirmar_vaciado(e):
            limpiar_lista(self.con_web, self.usuario_id)
            self._cargar_lista()
            self._actualizar_vista_lista()
            self._actualizar_totales()
            e.page.pop_dialog()
            e.page.update()

        dlg = ft.AlertDialog(
            title=ft.Text("Confirmar", color=NAVY),
            content=ft.Text("¿Vaciar lista de compras?"),
            actions=[
                ft.TextButton("Cancelar", on_click=cancelar, style=ft.ButtonStyle(color=NAVY)),
                ft.TextButton("Sí, vaciar", on_click=confirmar_vaciado, style=ft.ButtonStyle(color="#b85450")),
            ]
        )
        e.page.show_dialog(dlg)
