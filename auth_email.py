# auth_email.py
"""
Login por codigo de email para la version web de Indice LCV.

Flujo:
1. La persona pone su email -> generar_codigo() crea un codigo de 6
   digitos, valido 10 minutos, y enviar_codigo_por_email() lo manda.
2. La persona pone el codigo -> validar_codigo() lo confirma.
3. Si es valido, crear_sesion() genera un token largo y aleatorio,
   guardado sin vencimiento, asociado a ese email. Ese token va en la
   URL como "recordarme" (?token=XXXX) -- la proxima vez que entra por
   ese link, obtener_usuario_por_token() lo reconoce sin pedir el
   codigo de nuevo.

Las credenciales de Gmail NUNCA se hardcodean aca -- se leen de
variables de entorno (GMAIL_USER, GMAIL_APP_PASSWORD), configuradas
en el servidor, para que el codigo se pueda compartir o subir a un
repo sin exponer la contraseña.
"""

import os
import random
import secrets
import smtplib
import sqlite3
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from typing import Optional

DB_PATH = "web_app.db"

GMAIL_USER = os.environ.get("GMAIL_USER", "")
GMAIL_APP_PASSWORD = os.environ.get("GMAIL_APP_PASSWORD", "")

MINUTOS_VALIDEZ_CODIGO = 10


def inicializar_db(db_path: str = DB_PATH) -> sqlite3.Connection:
    con = sqlite3.connect(db_path, check_same_thread=False)
    con.row_factory = sqlite3.Row
    con.executescript(
        """
        CREATE TABLE IF NOT EXISTS usuarios_web (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS codigos_verificacion (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT NOT NULL,
            codigo TEXT NOT NULL,
            expira_en TIMESTAMP NOT NULL,
            usado INTEGER DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS sesiones_token (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id INTEGER NOT NULL REFERENCES usuarios_web(id),
            token TEXT UNIQUE NOT NULL,
            creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
    )
    con.commit()
    return con


def generar_codigo(con: sqlite3.Connection, email: str) -> str:
    """Genera un codigo de 6 digitos para ese email, valido 10
    minutos. No manda el mail -- eso lo hace enviar_codigo_por_email()
    aparte, para poder testear la generacion sin mandar mails reales."""
    codigo = f"{random.randint(0, 999999):06d}"
    expira_en = datetime.now() + timedelta(minutes=MINUTOS_VALIDEZ_CODIGO)
    con.execute(
        "INSERT INTO codigos_verificacion (email, codigo, expira_en) VALUES (?, ?, ?)",
        (email.strip().lower(), codigo, expira_en.isoformat()),
    )
    con.commit()
    return codigo


def enviar_codigo_por_email(email: str, codigo: str) -> bool:
    """Manda el codigo por SMTP de Gmail. Devuelve True/False segun
    si pudo mandarlo -- nunca tira excepcion hacia afuera, para que un
    problema de red no rompa la pantalla de login."""
    if not GMAIL_USER or not GMAIL_APP_PASSWORD:
        print("[ERROR] Faltan las variables de entorno GMAIL_USER / GMAIL_APP_PASSWORD")
        return False

    cuerpo = (
        f"Tu código de acceso a Índice LCV es: {codigo}\n\n"
        f"Vence en {MINUTOS_VALIDEZ_CODIGO} minutos. Si no lo pediste vos, ignorá este mail."
    )
    mensaje = MIMEText(cuerpo)
    mensaje["Subject"] = f"Tu código de acceso: {codigo}"
    mensaje["From"] = GMAIL_USER
    mensaje["To"] = email

    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as servidor:
            servidor.starttls()
            servidor.login(GMAIL_USER, GMAIL_APP_PASSWORD)
            servidor.sendmail(GMAIL_USER, [email], mensaje.as_string())
        return True
    except Exception as e:
        print(f"[ERROR] No se pudo enviar el email: {e}")
        return False


def validar_codigo(con: sqlite3.Connection, email: str, codigo: str) -> bool:
    """Confirma que el codigo sea el correcto, no haya vencido, y no
    se haya usado antes. Si es valido, lo marca como usado (no se
    puede reusar)."""
    email = email.strip().lower()
    fila = con.execute(
        """
        SELECT id, expira_en FROM codigos_verificacion
        WHERE email = ? AND codigo = ? AND usado = 0
        ORDER BY id DESC LIMIT 1
        """,
        (email, codigo),
    ).fetchone()

    if not fila:
        return False

    if datetime.fromisoformat(fila["expira_en"]) < datetime.now():
        return False

    con.execute("UPDATE codigos_verificacion SET usado = 1 WHERE id = ?", (fila["id"],))
    con.commit()
    return True


def obtener_o_crear_usuario(con: sqlite3.Connection, email: str) -> int:
    email = email.strip().lower()
    fila = con.execute("SELECT id FROM usuarios_web WHERE email = ?", (email,)).fetchone()
    if fila:
        return fila["id"]

    cursor = con.execute("INSERT INTO usuarios_web (email) VALUES (?)", (email,))
    con.commit()
    return cursor.lastrowid


def crear_sesion(con: sqlite3.Connection, email: str) -> str:
    """Crea un token de sesion largo para el 'recordarme' -- no
    vence, queda asociado a este email hasta que se borre a mano."""
    usuario_id = obtener_o_crear_usuario(con, email)
    token = secrets.token_urlsafe(24)
    con.execute(
        "INSERT INTO sesiones_token (usuario_id, token) VALUES (?, ?)",
        (usuario_id, token),
    )
    con.commit()
    return token


def obtener_usuario_por_token(con: sqlite3.Connection, token: str) -> Optional[dict]:
    """Devuelve {'id': ..., 'email': ...} si el token es valido, o
    None si no existe (link viejo, invalido, o manipulado)."""
    fila = con.execute(
        """
        SELECT u.id, u.email FROM sesiones_token s
        JOIN usuarios_web u ON u.id = s.usuario_id
        WHERE s.token = ?
        """,
        (token,),
    ).fetchone()
    return dict(fila) if fila else None
