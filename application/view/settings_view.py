import asyncio

import flet as ft

from application.api import ApiError, BackendUnreachableError
from application.components import BaseView


class SettingsView(BaseView):
    def __init__(self, route: str, api_client, on_logout=None):
        self.api_client = api_client
        self.on_logout = on_logout
        self._disposed = False

        self._error_text = ft.Text("", size=13, color=ft.Colors.ERROR, visible=False)
        self._loading = ft.ProgressRing(width=40, height=40, visible=True)

        self._name_text = ft.Text("", size=16)
        self._email_text = ft.Text("", size=14, color=ft.Colors.ON_SURFACE_VARIANT)

        self._backend_url_text = ft.Text("", size=13, color=ft.Colors.ON_SURFACE_VARIANT)

        logout_button = ft.ElevatedButton(
            "Выйти из аккаунта",
            icon=ft.Icons.LOGOUT,
            on_click=self._on_logout,
            width=280,
            color=ft.Colors.ERROR,
        )

        profile_card = ft.Container(
            content=ft.Column(
                [
                    ft.Row(
                        [
                            ft.Container(
                                content=ft.Icon(ft.Icons.PERSON, size=32, color=ft.Colors.PRIMARY),
                                width=56,
                                height=56,
                                border_radius=28,
                                bgcolor=ft.Colors.PRIMARY_CONTAINER,
                                alignment=ft.Alignment.CENTER,
                            ),
                            ft.Column(
                                [self._name_text, self._email_text],
                                spacing=2,
                            ),
                        ],
                        spacing=16,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                ],
                spacing=12,
            ),
            padding=20,
            border_radius=12,
            bgcolor=ft.Colors.SURFACE_CONTAINER_LOW,
        )

        info_card = ft.Container(
            content=ft.Column(
                [
                    ft.Text("Информация", size=14, weight=ft.FontWeight.W_600),
                    ft.Divider(height=1),
                    ft.Row(
                        [ft.Text("Сервер:", size=13), self._backend_url_text],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    ),
                ],
                spacing=8,
            ),
            padding=20,
            border_radius=12,
            bgcolor=ft.Colors.SURFACE_CONTAINER_LOW,
        )

        content = ft.Column(
            controls=[
                self._error_text,
                self._loading,
                ft.Container(
                    content=ft.Column(
                        [
                            ft.Text("Настройки", size=24, weight=ft.FontWeight.BOLD),
                            profile_card,
                            info_card,
                            ft.Container(height=20),
                            logout_button,
                        ],
                        spacing=16,
                    ),
                    padding=ft.Padding.symmetric(horizontal=24),
                    expand=True,
                ),
            ],
            expand=True,
            scroll=ft.ScrollMode.AUTO,
        )

        super().__init__(content=content, title="Настройки", route=route, selected_index=3)

    def did_mount(self):
        super().did_mount()
        asyncio.create_task(self._load_profile())

    def dispose(self):
        self._disposed = True

    async def _load_profile(self):
        try:
            self._error_text.visible = False
            self._loading.visible = True
            self.update()

            profile = await asyncio.to_thread(self.api_client.me)
            if self._disposed:
                return

            self._loading.visible = False
            self._name_text.value = profile.get("name", profile.get("username", "Пользователь"))
            self._email_text.value = profile.get("email", "")
            self._backend_url_text.value = self.api_client.base_url
            self.update()
        except BackendUnreachableError:
            if not self._disposed:
                self._loading.visible = False
                self._error_text.value = "Сервер недоступен"
                self._error_text.visible = True
                self.update()
        except ApiError as exc:
            if not self._disposed:
                self._loading.visible = False
                self._error_text.value = f"Ошибка загрузки профиля: {exc}"
                self._error_text.visible = True
                self.update()

    def _on_logout(self, e):
        if self.on_logout:
            self.on_logout()
