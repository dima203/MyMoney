import flet as ft
from MySpaceShared.view.splash_view import SplashView as SharedSplashView


class SplashView(SharedSplashView):
    def __init__(self):
        super().__init__(
            app_title="MyMoney",
            app_icon=ft.Icons.ACCOUNT_BALANCE_WALLET,
        )


__all__ = ["SplashView"]
