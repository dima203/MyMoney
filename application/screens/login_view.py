import flet as ft
from MySpaceShared.screens.login_view import LoginView as SharedLoginView
from MySpaceShared.screens.login_view import default_authenticate


class LoginView(SharedLoginView):
    def __init__(self, backend_url: str, on_success):
        super().__init__(
            backend_url=backend_url,
            on_success=on_success,
            app_title="MyMoney",
            app_icon=ft.Icons.ACCOUNT_BALANCE_WALLET,
            on_authenticate=lambda url: default_authenticate(url, "mymoney"),
        )


__all__ = ["LoginView"]
