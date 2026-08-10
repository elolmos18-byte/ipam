# graficos.py
# Graficos con LineChart real (flet-charts), eje X = dias, eje Y = precio.
import flet as ft
import flet_charts as fc
from typing import Optional, List, Dict

# Paleta LCV, un color por tienda (se asignan en orden de aparicion)
PALETA_TIENDAS = ["#c9a84c", "#2d6a4f", "#7ecac4", "#b85450", "#5b7fb5", "#a0522d"]
NAVY = "#0a1628"
TEXT_LIGHT = "#6b6b6b"


def _fecha_corta(fecha: str) -> str:
    """'2026-08-01' -> '01/08'"""
    try:
        partes = fecha.split("-")
        return f"{partes[2]}/{partes[1]}"
    except Exception:
        return fecha


def _etiquetas_eje_x(fechas: List[str], maximo_etiquetas: int = 6) -> List[fc.ChartAxisLabel]:
    """Muestra como mucho `maximo_etiquetas` fechas en el eje X (siempre
    la primera y la ultima), para que no se amontonen si hay 15 dias."""
    n = len(fechas)
    if n == 0:
        return []
    if n <= maximo_etiquetas:
        indices = list(range(n))
    else:
        paso = max(1, (n - 1) // (maximo_etiquetas - 1))
        indices = list(range(0, n, paso))
        if indices[-1] != n - 1:
            indices.append(n - 1)

    return [
        fc.ChartAxisLabel(value=i, label=_fecha_corta(fechas[i]))
        for i in indices
    ]


def _rango_y(valores: List[float]):
    """Calcula min_y/max_y con margen. Sin esto, cuando hay muy pocos
    puntos (o todos el mismo precio) el rango del eje colapsa a 0 y el
    grafico queda en blanco -- pasaba justo con productos que recien
    hoy tienen su primer registro en catalogo_reciente.json."""
    if not valores:
        return 0, 100
    minimo = min(valores)
    maximo = max(valores)
    if minimo == maximo:
        margen = max(minimo * 0.1, 50)
        return max(0, minimo - margen), maximo + margen
    margen = (maximo - minimo) * 0.15
    return max(0, minimo - margen), maximo + margen


def _rango_x(cantidad_puntos: int):
    """Igual que _rango_y pero para el eje X -- con un solo punto
    (producto que recien hoy tiene su primer precio), min_x=max_x=0
    hace que el chart no tenga ancho para dibujar nada. El margen
    derecho es de 0.6 (no 0.3) para dejar lugar al punto duplicado
    que arma _asegurar_dos_puntos en x+0.4."""
    return -0.3, max(cantidad_puntos - 1, 0) + 0.6


def _asegurar_dos_puntos(puntos: List["fc.LineChartDataPoint"]) -> List["fc.LineChartDataPoint"]:
    """fl_chart (la libreria debajo de flet-charts) puede no dibujar
    nada -- ni siquiera un punto suelto -- cuando una serie tiene un
    solo dato, sin importar el rango de ejes. Si pasa eso, duplicamos
    el punto con un pequeno desplazamiento para forzar una linea de
    2 puntos de verdad (un segmento cortito) en vez de un punto solo."""
    if len(puntos) == 1:
        p = puntos[0]
        return [p, fc.LineChartDataPoint(x=p.x + 0.4, y=p.y)]
    return puntos


def crear_linechart_indice(historico: List[Dict]) -> ft.Control:
    """Grafico del Indice: una sola linea (precio promedio de la
    canasta) a lo largo del tiempo. historico: [{"fecha", "precio"}]"""

    if not historico:
        return ft.Container(content=ft.Text("Sin datos", color=TEXT_LIGHT), padding=10)

    fechas = [h["fecha"] for h in historico]
    puntos = [
        fc.LineChartDataPoint(x=i, y=h["precio"])
        for i, h in enumerate(historico)
    ]
    puntos = _asegurar_dos_puntos(puntos)

    serie = fc.LineChartData(
        points=puntos,
        color=PALETA_TIENDAS[0],
        curved=True,
        stroke_width=3,
        point=True,
        below_line_bgcolor=ft.Colors.with_opacity(0.15, PALETA_TIENDAS[0]),
    )

    min_x, max_x = _rango_x(len(historico))
    min_y, max_y = _rango_y([h["precio"] for h in historico])

    grafico = fc.LineChart(
        data_series=[serie],
        expand=True,
        interactive=False,
        min_x=min_x, max_x=max_x,
        min_y=min_y, max_y=max_y,
        bgcolor="#ffffff",
        border=ft.Border.all(1, "#e8e0d0"),
        bottom_axis=fc.ChartAxis(labels=_etiquetas_eje_x(fechas), label_size=24),
        left_axis=fc.ChartAxis(label_size=44),
        horizontal_grid_lines=fc.ChartGridLines(interval=1, color="#f0ebe0", width=1),
        vertical_grid_lines=fc.ChartGridLines(interval=1, color="#f0ebe0", width=1),
    )

    return ft.Container(content=grafico, height=260, padding=10, bgcolor="#ffffff", border_radius=8)


def crear_linechart_comparador(producto: Dict, tiendas: Optional[Dict[str, str]] = None) -> ft.Control:
    """Grafico del Comparador: una linea por tienda, mostrando el
    precio del producto a lo largo de los ultimos dias.
    historico: [{"fecha", "precios": {tienda_id: {"precio": N}}}]"""

    historico = producto.get("historico", [])
    if not historico:
        return ft.Container(content=ft.Text("Sin datos", color=TEXT_LIGHT), padding=10)

    tiendas = tiendas or {}
    fechas = [h.get("fecha", "") for h in historico]

    # Detectar que tiendas aparecen en el historico, en orden de aparicion
    tiendas_presentes: List[str] = []
    for h in historico:
        for tienda_id in h.get("precios", {}).keys():
            if tienda_id not in tiendas_presentes:
                tiendas_presentes.append(tienda_id)

    series = []
    leyenda_items = []
    valores_totales: List[float] = []
    for idx, tienda_id in enumerate(tiendas_presentes):
        color = PALETA_TIENDAS[idx % len(PALETA_TIENDAS)]
        puntos = []
        for i, h in enumerate(historico):
            precio_data = h.get("precios", {}).get(tienda_id)
            if precio_data is None:
                continue
            precio = precio_data.get("precio") if isinstance(precio_data, dict) else precio_data
            if precio:
                puntos.append(fc.LineChartDataPoint(x=i, y=precio))
                valores_totales.append(precio)

        if not puntos:
            continue

        puntos = _asegurar_dos_puntos(puntos)

        series.append(
            fc.LineChartData(
                points=puntos, color=color, curved=True, stroke_width=3, point=True,
                below_line_bgcolor=ft.Colors.with_opacity(0.12, color),
            )
        )

        nombre_tienda = tiendas.get(tienda_id, f"Tienda {tienda_id}")
        leyenda_items.append(
            ft.Row(
                [
                    ft.Container(width=10, height=10, bgcolor=color, border_radius=5),
                    ft.Text(nombre_tienda, size=11, color=NAVY),
                ],
                spacing=4,
            )
        )

    if not series:
        return ft.Container(content=ft.Text("Sin precios en el historico reciente", color=TEXT_LIGHT), padding=10)

    min_x, max_x = _rango_x(len(historico))
    min_y, max_y = _rango_y(valores_totales)

    grafico = fc.LineChart(
        data_series=series,
        expand=True,
        interactive=False,
        min_x=min_x, max_x=max_x,
        min_y=min_y, max_y=max_y,
        bgcolor="#ffffff",
        border=ft.Border.all(1, "#e8e0d0"),
        bottom_axis=fc.ChartAxis(labels=_etiquetas_eje_x(fechas), label_size=24),
        left_axis=fc.ChartAxis(label_size=44),
        horizontal_grid_lines=fc.ChartGridLines(interval=1, color="#f0ebe0", width=1),
        vertical_grid_lines=fc.ChartGridLines(interval=1, color="#f0ebe0", width=1),
    )

    return ft.Column(
        [
            ft.Row(leyenda_items, spacing=14, wrap=True),
            ft.Container(content=grafico, height=260, padding=10, bgcolor="#ffffff", border_radius=8),
        ],
        spacing=6,
    )


def crear_linechart_simple(datos: List[float], titulo: str = "Gráfico") -> ft.Control:
    """Grafico simple de una sola serie a partir de una lista de
    valores (sin fechas asociadas, eje X = indice 0,1,2...)."""

    if not datos:
        return ft.Container(content=ft.Text("Sin datos", color=TEXT_LIGHT), padding=10)

    puntos = [fc.LineChartDataPoint(x=i, y=v) for i, v in enumerate(datos)]
    serie = fc.LineChartData(points=puntos, color=PALETA_TIENDAS[0], curved=True, stroke_width=3, point=True)

    grafico = fc.LineChart(
        data_series=[serie],
        expand=True,
        min_y=0,
        left_axis=fc.ChartAxis(label_size=44),
        horizontal_grid_lines=fc.ChartGridLines(interval=1, color="#e8e0d0", width=1),
        vertical_grid_lines=fc.ChartGridLines(interval=1, color="#e8e0d0", width=1),
    )

    return ft.Column(
        [
            ft.Text(titulo, size=13, weight="bold", color=NAVY),
            ft.Container(content=grafico, height=260, padding=10),
        ],
        spacing=6,
    )
