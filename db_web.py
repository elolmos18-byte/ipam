# db_web.py
"""
Funciones de "Mi Lista" para la version web de IPAM -- equivalentes a
db/sqlite_local.py de la app de escritorio, pero con una diferencia
central: ahi cada PC tenia su propio local.db (una sola lista, sin
dueño). Aca, como el mismo servidor atiende a varias personas a la
vez, TODAS las funciones piden un usuario_id y solo tocan/devuelven
las filas de ESE usuario -- para que la lista de una persona nunca se
mezcle con la de otra.
"""

import sqlite3
from typing import Dict, List


def agregar_producto_lista(
    con: sqlite3.Connection, usuario_id: int, nombre: str, marca: str, tienda_id: str, precio: float
) -> None:
    con.execute(
        "INSERT INTO lista_compras (usuario_id, producto_nombre, marca, tienda_id, precio) VALUES (?, ?, ?, ?, ?)",
        (usuario_id, nombre, marca, tienda_id, precio),
    )
    con.commit()


def obtener_lista_compras(con: sqlite3.Connection, usuario_id: int) -> List[Dict]:
    filas = con.execute(
        "SELECT id, producto_nombre, marca, tienda_id, precio FROM lista_compras WHERE usuario_id = ? ORDER BY id",
        (usuario_id,),
    ).fetchall()
    return [dict(f) for f in filas]


def eliminar_producto_lista(con: sqlite3.Connection, usuario_id: int, item_id: int) -> None:
    # El "AND usuario_id = ?" es la parte importante -- sin esto,
    # alguien podria borrar un item ajeno adivinando el id.
    con.execute(
        "DELETE FROM lista_compras WHERE id = ? AND usuario_id = ?",
        (item_id, usuario_id),
    )
    con.commit()


def limpiar_lista(con: sqlite3.Connection, usuario_id: int) -> None:
    con.execute("DELETE FROM lista_compras WHERE usuario_id = ?", (usuario_id,))
    con.commit()
