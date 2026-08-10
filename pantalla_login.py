# pantalla_login.py
"""
Pantalla de login por codigo de email -- SOLO para la version web de
la app (main.py la muestra unicamente si page.web es True; en el .exe
de escritorio nunca aparece).

Flujo:
1. Si la URL trae ?token=... y es valido, se salta el login directo.
2. Si no, pide el email, manda el codigo, pide el codigo, y al
   confirmar genera un link con el token nuevo para que la persona lo
   guarde como favorito ("recordarme" sin storage persistente del
   navegador, que esta version de Flet no tiene).
"""

import re
from urllib.parse import urlparse, parse_qs
from typing import Callable, Optional

import flet as ft

import auth_email as ae

NAVY = "#0a1628"
NAVY_LIGHT = "#142238"
GOLD = "#c9a84c"
GOLD_DIM = "#a08636"
CREAM = "#f5f0e8"
TEXT_LIGHT = "#6b6b6b"

REGEX_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def extraer_token_de_ruta(route: str) -> Optional[str]:
    """Saca el ?token=... de page.route, si esta presente."""
    try:
        query = parse_qs(urlparse(route).query)
        valores = query.get("token")
        return valores[0] if valores else None
    except Exception:
        return None


class PantallaLogin:
    def __init__(self, con, on_login_exitoso: Callable[[dict], None]):
        """con: conexion sqlite ya abierta (auth_email.inicializar_db()).
        on_login_exitoso: callback que recibe {'id':.., 'email':..}
        cuando el login termina bien (por token existente o por
        codigo confirmado)."""
        self.con = con
        self.on_login_exitoso = on_login_exitoso
        self.email_actual = ""
        self.page: Optional[ft.Page] = None

    def build(self, page: ft.Page) -> ft.Container:
        self.page = page

        # Si ya viene con un token valido en la URL, ni mostramos el
        # formulario -- pasamos directo.
        token = extraer_token_de_ruta(page.route or "")
        if token:
            usuario = ae.obtener_usuario_por_token(self.con, token)
            if usuario:
                return ft.Container(
                    content=ft.Text("Ingresando...", color=NAVY),
                    expand=True,
                    alignment=ft.Alignment(0, 0),
                    data="__login_automatico__",  # main.py revisa esto
                )

        return self._pantalla_pedir_email()

    # ------------------------------------------------------------
    # Paso 1: pedir email
    # ------------------------------------------------------------

    def _pantalla_pedir_email(self) -> ft.Container:
        self.input_email = ft.TextField(
            label="Tu email",
            hint_text="ejemplo@gmail.com",
            width=320,
            border_color="#cbb98a",
            focused_border_color=GOLD,
            color=CREAM,
            label_style=ft.TextStyle(color="#e8e0d0"),
            hint_style=ft.TextStyle(color="#6b7a99"),
            cursor_color=GOLD,
            on_submit=self._enviar_codigo,
        )
        self.texto_error = ft.Text("", color="#b85450", size=12)

        contenido = ft.Column(
            [
                ft.Text("🌬️ ÍNDICE LCV", size=24, weight="bold", color=GOLD, font_family="Cinzel"),
                ft.Text("Ingresá tu email para entrar", size=13, color="#e8e0d0"),
                ft.Container(height=16),
                self.input_email,
                self.texto_error,
                ft.Button("Enviar código", on_click=self._enviar_codigo, color=NAVY, bgcolor=GOLD),
            ],
            spacing=10,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        )

        return ft.Container(
            content=contenido,
            bgcolor=NAVY,
            expand=True,
            alignment=ft.Alignment(0, 0),
            padding=20,
        )

    def _enviar_codigo(self, e):
        email = (self.input_email.value or "").strip()
        if not REGEX_EMAIL.match(email):
            self.texto_error.value = "Ingresá un email válido"
            e.page.update()
            return

        self.texto_error.value = "Enviando código..."
        e.page.update()

        codigo = ae.generar_codigo(self.con, email)
        enviado = ae.enviar_codigo_por_email(email, codigo)

        if not enviado:
            self.texto_error.value = "No se pudo enviar el código. Probá de nuevo en un momento."
            e.page.update()
            return

        self.email_actual = email
        self._mostrar_pantalla_codigo(e.page)

    # ------------------------------------------------------------
    # Paso 2: pedir codigo
    # ------------------------------------------------------------

    def _mostrar_pantalla_codigo(self, page: ft.Page):
        self.input_codigo = ft.TextField(
            label="Código de 6 dígitos",
            width=200,
            max_length=6,
            text_align=ft.TextAlign.CENTER,
            border_color="#cbb98a",
            focused_border_color=GOLD,
            color=CREAM,
            label_style=ft.TextStyle(color="#e8e0d0"),
            cursor_color=GOLD,
            on_submit=self._confirmar_codigo,
        )
        self.texto_error_codigo = ft.Text("", color="#b85450", size=12)

        contenido = ft.Column(
            [
                ft.Text("🌬️ ÍNDICE LCV", size=24, weight="bold", color=GOLD, font_family="Cinzel"),
                ft.Text(f"Te mandamos un código a {self.email_actual}", size=13, color="#e8e0d0"),
                ft.Container(height=16),
                self.input_codigo,
                self.texto_error_codigo,
                ft.Button("Confirmar", on_click=self._confirmar_codigo, color=NAVY, bgcolor=GOLD),
                ft.TextButton("Usar otro email", on_click=lambda e: self._volver_a_email(e.page),
                               style=ft.ButtonStyle(color="#c8bda0")),
            ],
            spacing=10,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        )

        page.controls.clear()
        page.add(
            ft.Container(content=contenido, bgcolor=NAVY, expand=True, alignment=ft.Alignment(0, 0), padding=20)
        )
        page.update()

    def _confirmar_codigo(self, e):
        codigo = (self.input_codigo.value or "").strip()
        if not ae.validar_codigo(self.con, self.email_actual, codigo):
            self.texto_error_codigo.value = "Código incorrecto o vencido"
            e.page.update()
            return

        token = ae.crear_sesion(self.con, self.email_actual)
        usuario = ae.obtener_usuario_por_token(self.con, token)
        self._mostrar_pantalla_guardar_link(e.page, token, usuario)

    # ------------------------------------------------------------
    # Paso 3: mostrar el link para "recordarme"
    # ------------------------------------------------------------

    def _mostrar_pantalla_guardar_link(self, page: ft.Page, token: str, usuario: dict):
        base_url = page.route.split("?")[0] if page.route else "/"
        link_completo = f"{base_url}?token={token}"

        contenido = ft.Column(
            [
                ft.Text("✅ ¡Listo!", size=22, weight="bold", color=GOLD, font_family="Cinzel"),
                ft.Text("Guardá este link como favorito para no tener que\npedir el código de nuevo la próxima vez:",
                         size=13, color="#e8e0d0", text_align=ft.TextAlign.CENTER),
                ft.Container(height=12),
                ft.Container(
                    content=ft.Text(link_completo, size=12, color=GOLD, selectable=True),
                    bgcolor=NAVY_LIGHT, padding=12, border_radius=8, border=ft.Border.all(1, "#1e3250"),
                ),
                ft.Container(height=16),
                ft.Button("Continuar a la app", on_click=lambda e: self.on_login_exitoso(usuario),
                           color=NAVY, bgcolor=GOLD),
            ],
            spacing=8,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        )

        page.controls.clear()
        page.add(
            ft.Container(content=contenido, bgcolor=NAVY, expand=True, alignment=ft.Alignment(0, 0), padding=20)
        )
        page.update()

    def _volver_a_email(self, page: ft.Page):
        page.controls.clear()
        page.add(self._pantalla_pedir_email())
        page.update()
