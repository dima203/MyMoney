"""Экран входа через Google OAuth."""

import logging

import flet as ft

logger = logging.getLogger(__name__)


class LoginView(ft.View):
    def __init__(self, backend_url: str, on_success):
        super().__init__("/login")
        self.backend_url = backend_url
        self.on_success = on_success

        self.error_text = ft.Text(
            "",
            color=ft.Colors.RED,
            visible=False,
            size=14,
        )
        self.login_button = ft.Button(
            "Войти через Google",
            icon=ft.Icons.LOGIN,
            on_click=self._submit,
            width=280,
            height=48,
        )
        self.progress = ft.ProgressRing(
            visible=False,
            width=24,
            height=24,
        )

        self.controls = [
            ft.Container(
                content=ft.Column(
                    [
                        ft.Icon(
                            ft.Icons.LOCK,
                            size=64,
                            color=ft.Colors.BLUE,
                        ),
                        ft.Text("MyMoney", size=32, weight=ft.FontWeight.BOLD),
                        ft.Text("Вход в приложение", size=16),
                        ft.Container(height=24),
                        self.login_button,
                        self.progress,
                        self.error_text,
                    ],
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=10,
                ),
                alignment=ft.Alignment.CENTER,
                expand=True,
            )
        ]

    def _set_error(self, message: str) -> None:
        logger.error("Login error: %s", message)
        self.error_text.value = message
        self.error_text.visible = True
        self._safe_update(self.error_text)

    def _clear_error(self) -> None:
        self.error_text.visible = False
        self.error_text.value = ""
        self._safe_update(self.error_text)

    @staticmethod
    def _safe_update(control) -> None:
        try:
            control.update()
        except RuntimeError:
            pass

    def authenticate(self) -> tuple[bool, str]:
        from auth.google_auth import GoogleOAuthFlow, OAuthCallbackError
        from application.api.token_store import TokenData, TokenStore

        logger.info("Starting authentication flow, backend_url=%s", self.backend_url)
        try:
            flow = GoogleOAuthFlow(backend_url=self.backend_url)
            tokens = flow.start()
            logger.info("OAuth flow completed, saving tokens to store")

            store = TokenStore()
            store.save(TokenData(
                access=tokens.get("access", ""),
                refresh=tokens.get("refresh", ""),
            ))

            return True, ""
        except OAuthCallbackError as exc:
            logger.error("OAuth callback error: %s", exc)
            return False, str(exc)
        except Exception as exc:
            logger.exception("Unexpected error during authentication")
            return False, f"Не удалось подключиться к серверу: {exc}"

    async def _submit(self, e) -> None:
        logger.info("Login button clicked")
        self.login_button.disabled = True
        self.progress.visible = True
        self._clear_error()
        self._safe_update(self.login_button)
        self._safe_update(self.progress)

        import asyncio

        ok, message = await asyncio.to_thread(self.authenticate)
        logger.info("authenticate returned: ok=%s", ok)

        self.login_button.disabled = False
        self.progress.visible = False
        self._safe_update(self.login_button)
        self._safe_update(self.progress)

        if not ok:
            self._set_error(message)
            return

        logger.info("Calling on_success callback")
        self.on_success(self)
        logger.info("on_success callback completed")


__all__ = ["LoginView"]
