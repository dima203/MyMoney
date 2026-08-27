"""Экран входа через Google OAuth.

Показывает кнопку «Войти через Google», запускает OAuth flow
(локальный HTTP-сервер + браузер), при успехе переходит в приложение.
"""

import flet as ft


class AuthorizationScreen(ft.View):
    """Экран входа: Google OAuth через бэкенд."""

    def __init__(self, route: str, backend_url: str, success_callback: callable, *args, **kwargs):
        super().__init__(route, *args, **kwargs)
        self.backend_url = backend_url
        self.success_callback = success_callback

        self.error_text = ft.Text(
            "",
            color=ft.Colors.RED_200,
            visible=False,
            size=14,
        )
        self.login_button = ft.ElevatedButton(
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
                            color=ft.Colors.TEAL,
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
                alignment=ft.alignment.center,
                expand=True,
            )
        ]

    def _set_error(self, message: str) -> None:
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
        """Запускает Google OAuth flow. Возвращает (успех, сообщение об ошибке)."""
        from auth.google_auth import GoogleOAuthFlow, OAuthCallbackError

        try:
            flow = GoogleOAuthFlow(backend_url=self.backend_url)
            tokens = flow.start()
        except OAuthCallbackError as exc:
            return False, str(exc)
        except Exception as exc:
            return False, "Не удалось подключиться к серверу"

        self.success_callback(tokens["access"], tokens.get("refresh", ""))
        return True, ""

    async def _submit(self, e) -> None:
        import asyncio

        self.login_button.disabled = True
        self.progress.visible = True
        self._clear_error()
        self._safe_update(self.login_button)
        self._safe_update(self.progress)

        ok, message = await asyncio.to_thread(self.authenticate)

        self.login_button.disabled = False
        self.progress.visible = False
        self._safe_update(self.login_button)
        self._safe_update(self.progress)

        if not ok:
            self._set_error(message)
