# utils/matching.py
"""
Matching de productos entre supermercados usando rapidfuzz, corriendo
LOCAL en la app (no requiere backend ni IA).

El problema que resuelve: catalogo_reciente.json trae cada producto
separado por tienda (porque cada super usa su propio codigo interno),
asi que "Coca Cola 1.5L" de La Anonima y "Coca Cola 1.75L" de
Carrefour aparecen como productos sueltos, sin relacion entre si -- el
Comparador no puede compararlos.

Idea central (la cantidad no debe pesar en el matching, solo en el
precio): en vez de comparar "Coca Cola 1.5L" contra "Coca Cola 1.75L"
tal cual (el tamano distinto baja el score de similitud), se le saca
la cantidad al nombre ANTES de comparar -- "coca cola" vs "coca cola",
usando utils/unidades.py (misma logica que ya usa el backend para la
canasta basica). El tamano y el precio normalizado ($/kg, $/L, $/u)
se calculan aparte y se guardan junto a cada precio, para poder
comparar de verdad aunque el packaging no coincida.

Dos salvaguardas mas, encontradas probando con datos reales:

1. Veto por palabra diferenciadora asimetrica -- "Coca Cola" vs "Coca
   Cola ZERO" da un score de similitud muy alto (son casi el mismo
   texto) pero son productos DISTINTOS. Si una palabra de la lista
   DIFERENCIADORES aparece en uno de los dos nombres y no en el otro,
   se descarta el match sin importar el score.

2. Nunca mas de 1 producto por tienda en un grupo fusionado -- con
   nombres cortos y genericos, el encadenamiento transitivo (A se
   parece a B, B a C, pero A y C nunca se compararon directo) puede
   armar grupos gigantes e invalidos. Si un grupo termina con 2+
   productos de la misma tienda, es señal de que paso eso -- se
   descarta la fusion de ese grupo entero.
"""

from typing import Dict, List, Optional

from rapidfuzz import fuzz, process

from utils.unidades import (
    calcular_precio_normalizado_generico,
    normalizar,
    quitar_cantidad,
)

UMBRAL_MATCH = 85  # score de 0 a 100 (token_set_ratio, sobre nombres
                    # normalizados y SIN cantidad). Mas alto = mas
                    # estricto, menos falsos positivos pero tambien
                    # menos matches encontrados.

DIFERENCIADORES = [
    "zero", "light", "diet", "sin azucar", "descremada", "descremado",
    "entera", "entero", "sin tacc", "integral", "sin sal", "sin gluten",
    "reducido", "reducida", "libre de", "sin lactosa",
]


def _hay_diferenciador_asimetrico(a: str, b: str) -> bool:
    """True si una palabra "importante" (zero, light, etc) aparece en
    uno de los dos nombres y no en el otro -- señal de que son
    productos distintos aunque el texto se parezca mucho."""
    for palabra in DIFERENCIADORES:
        if (palabra in a) != (palabra in b):
            return True
    return False


def _tienda_de(producto: dict) -> Optional[str]:
    """De que tienda es este producto, mirando el ultimo registro de
    su historico (cada producto de catalogo_reciente.json hoy
    pertenece a UNA sola tienda, por construccion)."""
    historico = producto.get("historico", [])
    if not historico:
        return None
    precios = historico[-1].get("precios", {})
    return next(iter(precios), None)


def _enriquecer_con_precio_normalizado(producto: dict) -> dict:
    """Le agrega 'precio_normalizado' y 'unidad_normalizada' a cada
    entrada de precio en el historico del producto, calculado a
    partir del nombre. No modifica el producto original, devuelve una
    copia con las claves agregadas. Si no se pudo detectar el tamano,
    esas claves quedan en None (no rompe nada, simplemente no se
    puede comparar por unidad para ese producto puntual)."""
    nombre_norm = normalizar(producto.get("nombre", ""))
    nuevo_historico = []
    for registro in producto.get("historico", []):
        nuevos_precios = {}
        for tienda_id, info in registro.get("precios", {}).items():
            es_dict = isinstance(info, dict)
            precio = info.get("precio") if es_dict else info
            url = info.get("url") if es_dict else None
            precio_norm, unidad_norm = (
                calcular_precio_normalizado_generico(precio, nombre_norm)
                if precio else (None, None)
            )
            nuevos_precios[tienda_id] = {
                "precio": precio,
                "url": url,
                "precio_normalizado": precio_norm,
                "unidad_normalizada": unidad_norm,
            }
        nuevo_historico.append({"fecha": registro.get("fecha"), "precios": nuevos_precios})

    return {**producto, "historico": nuevo_historico}


def unificar_productos_categoria(productos: List[dict]) -> List[dict]:
    """Recibe los productos de UNA categoria (separados por tienda) y
    devuelve una lista de "productos unificados": los que tienen
    nombre parecido en tiendas distintas (comparando SIN la cantidad,
    y sin chocar con la lista de diferenciadores) se funden en una
    sola entrada, con el historico de todas las tiendas juntas y el
    precio normalizado calculado en cada una."""

    n = len(productos)
    if n == 0:
        return productos

    # Enriquecer primero (cada producto, sea que termine fusionado o
    # no, sale con su precio_normalizado calculado)
    productos = [_enriquecer_con_precio_normalizado(p) for p in productos]

    if n == 1:
        return productos

    nombres_norm = [normalizar(p.get("nombre", "")) for p in productos]
    nombres_sin_cantidad = [quitar_cantidad(nn) for nn in nombres_norm]
    tiendas = [_tienda_de(p) for p in productos]

    # Matriz de similitud entre todos los nombres SIN CANTIDAD de la
    # categoria. rapidfuzz.process.cdist esta escrito en C con SIMD --
    # aunque sean miles de productos tarda segundos, no minutos.
    matriz = process.cdist(nombres_sin_cantidad, nombres_sin_cantidad, scorer=fuzz.token_set_ratio, workers=-1)

    padre = list(range(n))

    def encontrar(x: int) -> int:
        while padre[x] != x:
            padre[x] = padre[padre[x]]
            x = padre[x]
        return x

    def unir(x: int, y: int) -> None:
        rx, ry = encontrar(x), encontrar(y)
        if rx != ry:
            padre[rx] = ry

    for i in range(n):
        for j in range(i + 1, n):
            if tiendas[i] == tiendas[j]:
                continue  # nunca fusionar dentro de la misma tienda
            if matriz[i][j] < UMBRAL_MATCH:
                continue
            if _hay_diferenciador_asimetrico(nombres_sin_cantidad[i], nombres_sin_cantidad[j]):
                continue
            unir(i, j)

    grupos: Dict[int, List[int]] = {}
    for i in range(n):
        grupos.setdefault(encontrar(i), []).append(i)

    unificados: List[dict] = []
    for indices in grupos.values():
        if len(indices) == 1:
            unificados.append(productos[indices[0]])
            continue

        # Salvaguarda: nunca puede haber 2 productos de la MISMA
        # tienda en un grupo fusionado. Si pasa, es señal de
        # encadenamiento transitivo descontrolado -- mejor no
        # fusionar nada de ese grupo que fusionar mal.
        tiendas_del_grupo = [tiendas[i] for i in indices]
        if len(tiendas_del_grupo) != len(set(tiendas_del_grupo)):
            for i in indices:
                unificados.append(productos[i])
            continue

        productos_grupo = [productos[i] for i in indices]
        nombre_canonico = max((p.get("nombre", "") for p in productos_grupo), key=len)

        historico_por_fecha: Dict[str, Dict[str, dict]] = {}
        for p in productos_grupo:
            for registro in p.get("historico", []):
                fecha = registro.get("fecha")
                precios = registro.get("precios", {})
                historico_por_fecha.setdefault(fecha, {}).update(precios)

        historico_fusionado = [
            {"fecha": fecha, "precios": precios}
            for fecha, precios in sorted(historico_por_fecha.items())
        ]

        unificados.append({
            "id": quitar_cantidad(normalizar(nombre_canonico)),
            "nombre": nombre_canonico,
            "marca": "",
            "tiendas_unificadas": len(productos_grupo),
            "historico": historico_fusionado,
        })

    return unificados


def unificar_catalogo(productos_por_categoria: Dict[str, List[dict]]) -> Dict[str, List[dict]]:
    """Aplica el matching a cada categoria del catalogo completo."""
    return {
        categoria: unificar_productos_categoria(productos)
        for categoria, productos in productos_por_categoria.items()
    }
