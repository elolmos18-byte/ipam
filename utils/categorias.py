# utils/categorias.py
"""
Unifica las ~70 categorias reales que vienen del scraping (limpieza,
galletitas-dulces, yogures-enteros, etc) en 13 grupos mas amplios y
faciles de navegar, para la pantalla de "explorar por categoria" del
Comparador.

Si el scraping suma categorias nuevas que no estan en el mapeo, caen
en "Otros" en vez de perderse silenciosamente -- conviene revisar
MAPEO_CATEGORIAS de vez en cuando contra las categorias reales de
catalogo_reciente.json.
"""

from typing import Dict, List

MAPEO_CATEGORIAS: Dict[str, str] = {
    # Limpieza y Perfumeria
    "limpieza": "🧼 Limpieza y Perfumería",
    "jabon-polvo": "🧼 Limpieza y Perfumería",
    "desodorante-ambientes": "🧼 Limpieza y Perfumería",
    "papel-higienico": "🧼 Limpieza y Perfumería",
    "rollos-de-cocina": "🧼 Limpieza y Perfumería",

    # Galletitas
    "galletitas-dulces": "🍪 Galletitas",
    "galletitas-saladas": "🍪 Galletitas",
    "galletitas-saladas-y-tostadas": "🍪 Galletitas",

    # Infusiones
    "infusiones": "☕ Infusiones",
    "yerba": "☕ Infusiones",
    "cafe": "☕ Infusiones",
    "te": "☕ Infusiones",

    # Lacteos y Huevos
    "yogures-enteros": "🥛 Lácteos y Huevos",
    "queso-untable": "🥛 Lácteos y Huevos",
    "yogures-descremados": "🥛 Lácteos y Huevos",
    "yogures": "🥛 Lácteos y Huevos",
    "leches-descremadas": "🥛 Lácteos y Huevos",
    "leches": "🥛 Lácteos y Huevos",
    "leches-enteras": "🥛 Lácteos y Huevos",
    "leche-descremada": "🥛 Lácteos y Huevos",
    "leche-entera": "🥛 Lácteos y Huevos",
    "manteca": "🥛 Lácteos y Huevos",
    "manteca-y-margarina": "🥛 Lácteos y Huevos",
    "huevos": "🥛 Lácteos y Huevos",

    # Frutas y Verduras
    "frutas-y-verduras": "🥕 Frutas y Verduras",
    "verduras": "🥕 Frutas y Verduras",
    "frutas": "🥕 Frutas y Verduras",

    # Pastas, Arroz y Harinas
    "fideos-cortos": "🍝 Pastas, Arroz y Harinas",
    "fideos-y-pastas": "🍝 Pastas, Arroz y Harinas",
    "fideos-largos": "🍝 Pastas, Arroz y Harinas",
    "arroz": "🍝 Pastas, Arroz y Harinas",
    "polenta": "🍝 Pastas, Arroz y Harinas",
    "harinas": "🍝 Pastas, Arroz y Harinas",
    "harinas-especiales": "🍝 Pastas, Arroz y Harinas",
    "harina-de-trigo": "🍝 Pastas, Arroz y Harinas",

    # Condimentos y Aderezos
    "aderezos": "🧂 Condimentos y Aderezos",
    "sal-y-especias": "🧂 Condimentos y Aderezos",
    "sal": "🧂 Condimentos y Aderezos",
    "vinagre": "🧂 Condimentos y Aderezos",
    "vinagre-y-limon": "🧂 Condimentos y Aderezos",
    "mayonesa": "🧂 Condimentos y Aderezos",
    "ketchup": "🧂 Condimentos y Aderezos",
    "mostaza": "🧂 Condimentos y Aderezos",

    # Bebidas
    "jugo-en-polvo": "🥤 Bebidas",
    "aguas-saborizadas-y-jugos": "🥤 Bebidas",
    "agua-sin-gas": "🥤 Bebidas",
    "aguas-sin-gas": "🥤 Bebidas",
    "gaseosa-cola": "🥤 Bebidas",
    "gaseosas": "🥤 Bebidas",

    # Conservas y Salsas
    "legumbres-en-lata": "🥫 Conservas y Salsas",
    "salsa-y-pure-de-tomate": "🥫 Conservas y Salsas",
    "tomates-y-salsas": "🥫 Conservas y Salsas",
    "atun": "🥫 Conservas y Salsas",
    "atun-y-pescado": "🥫 Conservas y Salsas",
    "salsa-de-tomate": "🥫 Conservas y Salsas",
    "pure-de-tomate": "🥫 Conservas y Salsas",
    "arvejas-en-lata": "🥫 Conservas y Salsas",

    # Dulces y Endulzantes
    "mermelada": "🍯 Dulces y Endulzantes",
    "dulces-y-mermeladas": "🍯 Dulces y Endulzantes",
    "dulce-de-leche": "🍯 Dulces y Endulzantes",
    "azucar-y-endulzantes": "🍯 Dulces y Endulzantes",
    "azucar": "🍯 Dulces y Endulzantes",

    # Carniceria
    "carniceria": "🥩 Carnicería",

    # Legumbres Secas
    "legumbres-secas": "🫘 Legumbres Secas",
    "legumbres": "🫘 Legumbres Secas",
    "lentejas": "🫘 Legumbres Secas",

    # Aceites
    "aceite": "🫒 Aceites",
    "aceites": "🫒 Aceites",
    "aceite-girasol": "🫒 Aceites",
    "aceite-mezcla": "🫒 Aceites",
}

GRUPO_OTROS = "🗂️ Otros"

ORDEN_GRUPOS: List[str] = [
    "🧼 Limpieza y Perfumería",
    "🍪 Galletitas",
    "☕ Infusiones",
    "🥛 Lácteos y Huevos",
    "🥕 Frutas y Verduras",
    "🍝 Pastas, Arroz y Harinas",
    "🧂 Condimentos y Aderezos",
    "🥤 Bebidas",
    "🥫 Conservas y Salsas",
    "🍯 Dulces y Endulzantes",
    "🥩 Carnicería",
    "🫘 Legumbres Secas",
    "🫒 Aceites",
    GRUPO_OTROS,
]


def agrupar_por_grupo_unificado(productos_por_categoria: Dict[str, List[dict]]) -> Dict[str, List[dict]]:
    """Junta las categorias reales del catalogo (~70) en los grupos
    unificados de arriba. Categorias no mapeadas caen en "Otros" en
    vez de perderse silenciosamente. Devuelve solo los grupos que
    tengan al menos un producto, en el orden de ORDEN_GRUPOS."""
    grupos: Dict[str, List[dict]] = {grupo: [] for grupo in ORDEN_GRUPOS}

    for categoria_original, productos in productos_por_categoria.items():
        grupo = MAPEO_CATEGORIAS.get(categoria_original, GRUPO_OTROS)
        grupos[grupo].extend(productos)

    return {grupo: productos for grupo, productos in grupos.items() if productos}
