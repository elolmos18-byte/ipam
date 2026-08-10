# utils/unidades.py
"""
Funciones puras para normalizar precios a una unidad metrica estandar
($/kg, $/L, $/unidad) a partir del nombre de un producto tal como
aparece en el catalogo de cada super.

Copia (casi) textual de precios_normalizar_unidades.py del backend de
Indice LCV (la misma logica que ya usa precios_ultimo.json para la
canasta basica), reusada aca para el matching entre supers en la app.
Si el backend corrige algun caso raro nuevo, conviene traer el cambio
para aca tambien.

Diferencia con el original: ahi calcular_precio_normalizado() recibe
un "rubro" (de la canasta basica curada, con su unidad ya definida:
kg/L/unidad/m/panos). Ac get no tenemos esa clasificacion previa para
el catalogo general (12000+ productos sueltos) -- por eso se suma
calcular_precio_normalizado_generico(), que prueba peso, despues
volumen, despues unidades, en ese orden, sin necesitar saber de
antemano cual aplica.
"""

import re
import unicodedata
from typing import Optional, Tuple

# --- Normalizacion de texto --------------------------------------------

def normalizar(texto: str) -> str:
    """Quita acentos, pasa a minusculas. Para comparar nombres."""
    sin_acentos = "".join(
        c for c in unicodedata.normalize("NFD", texto)
        if unicodedata.category(c) != "Mn"
    )
    return sin_acentos.lower()


# --- Extraccion de tamano ----------------------------------------------

PESO_MAXIMO_GRAMOS = 50_000
VOLUMEN_MAXIMO_ML = 50_000


def extraer_gramos(nombre_norm: str) -> Optional[float]:
    """Extrae el peso en gramos de un nombre normalizado."""
    m = re.search(r"(\d+(?:[.,]\s?\d+)?)\s*(?:kg|kilo)", nombre_norm)
    if m:
        valor = m.group(1).replace(" ", "").replace(",", ".")
        gramos = float(valor) * 1000
        if gramos > PESO_MAXIMO_GRAMOS:
            return None
        return gramos

    m = re.search(r"(\d+(?:[.,]\s?\d+)?)\s*(?:grs|gr|g)\b", nombre_norm)
    if m:
        valor = m.group(1).replace(" ", "").replace(",", ".")
        gramos = float(valor)
        if gramos > PESO_MAXIMO_GRAMOS:
            return None
        return gramos

    if re.search(r"\bkg\b|\bkilo\b", nombre_norm):
        return 1000.0

    return None


def extraer_mililitros(nombre_norm: str) -> Optional[float]:
    """Extrae el volumen en mililitros de un nombre normalizado."""
    m = re.search(r"(\d+(?:[.,]\s?\d+)?)\s*(?:litros?|lts|lt|l)\b", nombre_norm)
    if m:
        valor = m.group(1).replace(" ", "").replace(",", ".")
        ml = float(valor) * 1000
        if ml > VOLUMEN_MAXIMO_ML:
            return None
        return ml

    m = re.search(r"(\d+(?:[.,]\s?\d+)?)\s*(?:ml|cc)\b", nombre_norm)
    if m:
        valor = m.group(1).replace(" ", "").replace(",", ".")
        ml = float(valor)
        if ml > VOLUMEN_MAXIMO_ML:
            return None
        return ml

    return None


def extraer_unidades(nombre_norm: str) -> Optional[int]:
    """Extrae la cantidad de unidades (huevos x6, saquitos x25, etc.)."""
    m = re.search(r"(\d+)\s*(?:unidades?|uni|un|u|saquitos?|sobres?)\b", nombre_norm)
    if m:
        return int(m.group(1))

    m = re.search(r"x\s*(\d+)\b(?!\s*(?:grs|gr|g|kg|kilo|ml|cc|lt|lts|l)\b)", nombre_norm)
    if m:
        return int(m.group(1))

    return None


def calcular_precio_normalizado_generico(precio: float, nombre_norm: str) -> Tuple[Optional[float], Optional[str]]:
    """Version generica de calcular_precio_normalizado(), para cuando
    NO se sabe de antemano si el producto se mide en kg, L o unidades
    (a diferencia de la canasta basica curada, el catalogo general no
    tiene esa clasificacion previa por rubro).

    Prueba peso primero, despues volumen, despues unidades. Devuelve
    (precio_normalizado, unidad_estandar) o (None, None) si no pudo
    detectar ningun tamano en el nombre."""
    gramos = extraer_gramos(nombre_norm)
    if gramos and gramos > 0:
        return precio / gramos * 1000, "kg"

    ml = extraer_mililitros(nombre_norm)
    if ml and ml > 0:
        return precio / ml * 1000, "L"

    unidades = extraer_unidades(nombre_norm)
    if unidades and unidades > 0:
        return precio / unidades, "unidad"

    return None, None


def quitar_cantidad(nombre_norm: str) -> str:
    """Saca del nombre cualquier mencion de cantidad/tamano (pesos,
    volumenes, cantidad de unidades, multiplicadores "x N"), dejando
    solo las palabras que describen el producto en si. Para poder
    comparar "Coca Cola 1.5L" contra "Coca Cola 1.75L" como el MISMO
    producto (ignorando que el tamano no coincide), en vez de que el
    tamano distinto baje el score de similitud."""
    n = nombre_norm
    n = re.sub(r"(\d+(?:[.,]\s?\d+)?)\s*(?:kg|kilo)\b", " ", n)
    n = re.sub(r"(\d+(?:[.,]\s?\d+)?)\s*(?:grs|gr|g)\b", " ", n)
    n = re.sub(r"(\d+(?:[.,]\s?\d+)?)\s*(?:litros?|lts|lt|l)\b", " ", n)
    n = re.sub(r"(\d+(?:[.,]\s?\d+)?)\s*(?:ml|cc)\b", " ", n)
    n = re.sub(r"(\d+)\s*(?:unidades?|uni|un|u|saquitos?|sobres?)\b", " ", n)
    n = re.sub(r"x\s*\d+\b", " ", n)
    n = re.sub(r"\bx\b", " ", n)  # 'x' suelta que quedo de marcador (ej. 'pet x' tras sacar '1,5 lt')
    n = re.sub(r"[^a-z0-9 ]", " ", n)
    n = re.sub(r"\s+", " ", n).strip()
    return n
