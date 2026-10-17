import flet as ft

from MySpaceShared.components import AccentIcon, ElevatedCard
from MySpaceShared.core.tokens import SPACING


class AccountCard(ft.Container):
    """Карточка счёта: иконка валюты, название и баланс."""

    def __init__(self, name: str, balance: str, currency_icon: str = "●", on_edit=None, on_delete=None):
        super().__init__()
        self.name = name
        self.balance = balance

        self._name_text = ft.Text(name, size=15, weight=ft.FontWeight.W_600)
        self._balance_text = ft.Text(balance, size=17, weight=ft.FontWeight.BOLD)

        menu_button = ft.PopupMenuButton(
            icon=ft.Icons.MORE_VERT,
            icon_size=20,
            items=[
                ft.PopupMenuItem(content="Редактировать", icon=ft.Icons.EDIT, on_click=lambda _: on_edit and on_edit()),
                ft.PopupMenuItem(content="Удалить", icon=ft.Icons.DELETE, on_click=lambda _: on_delete and on_delete()),
            ],
        )

        info = ft.Column(
            [self._name_text, self._balance_text],
            spacing=2,
            expand=True,
            alignment=ft.MainAxisAlignment.CENTER,
        )
        row = ft.Row(
            [AccentIcon(currency_icon, size=42), info],
            spacing=SPACING["md"],
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            expand=True,
        )
        self.content = ElevatedCard(row, trailing=menu_button, padding=ft.Padding.symmetric(horizontal=16, vertical=12))

    def update_balance(self, balance: str):
        self.balance = balance
        self._balance_text.value = balance
        self.update()
