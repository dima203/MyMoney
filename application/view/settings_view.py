import asyncio

from application.api import ApiError, BackendUnreachableError
from application.components.navigation_items import NAVIGATION_ITEMS
from core import APP_SETTINGS, AppSettings
from MySpaceShared.view.settings_view import BaseSettingsView


class SettingsView(BaseSettingsView):
    def __init__(
        self,
        route: str,
        api_client,
        on_logout=None,
        app_settings: AppSettings | None = None,
    ):
        super().__init__(
            route=route,
            api_client=api_client,
            on_logout=on_logout,
            app_settings=app_settings if app_settings is not None else APP_SETTINGS,
            navigation_items=NAVIGATION_ITEMS,
            selected_index=3,
        )

    def did_mount(self):
        super().did_mount()
        asyncio.create_task(self._async_load_profile())

    async def _async_load_profile(self):
        try:
            self._error_text.visible = False
            self._loading.visible = True
            self.update()

            profile = await asyncio.to_thread(self.api_client.me)
            if self._disposed:
                return

            self._loading.visible = False
            self._name_field.value = profile.get("username", "")
            self._email_text.value = profile.get("email", "")
            self._currency_dropdown.value = profile.get("base_currency", "USDT")
            self._backend_url_text.value = self.api_client.base_url

            avatar_url = profile.get("avatar_url")
            if avatar_url:
                self._avatar_image.src = avatar_url
                self._avatar_image.visible = True
                self._avatar_icon.visible = False
            else:
                self._avatar_image.visible = False
                self._avatar_icon.visible = True
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

    async def _on_profile_save(self, e):
        self._profile_status.value = ""
        self._profile_error.visible = False
        self._save_profile_button.disabled = True
        self._save_profile_button.text = "Сохранение..."
        self.page.update()

        try:
            data = await asyncio.to_thread(
                self.api_client.update_profile,
                username=self._name_field.value.strip() if self._name_field.value else "",
                base_currency=str(self._currency_dropdown.value or "USDT"),
            )
            self._save_profile_button.disabled = False
            self._save_profile_button.text = "Сохранить"
            self._name_field.value = data.get("username", "")
            self._profile_status.value = "Сохранено"
            self.page.update()
        except ApiError as exc:
            self._save_profile_button.disabled = False
            self._save_profile_button.text = "Сохранить"
            detail = getattr(exc, "detail", None)
            if isinstance(detail, dict):
                error_str = "; ".join(f"{k}: {v}" for k, v in detail.items())
            else:
                error_str = str(exc)
            self._profile_error.value = error_str
            self._profile_error.visible = True
            self.page.update()
        except BackendUnreachableError:
            self._save_profile_button.disabled = False
            self._save_profile_button.text = "Сохранить"
            self._profile_error.value = "Сервер недоступен"
            self._profile_error.visible = True
            self.page.update()
