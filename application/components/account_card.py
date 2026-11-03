import flet as ft

from MySpaceShared.components import AccentIcon, ElevatedCard, StatusBadge
from MySpaceShared.core.tokens import SPACING


class AccountCard(ft.Container):
    """Карточка счёта: иконка валюты, название и баланс."""

    def __init__(
        self,
        name: str,
        balance: str,
        currency_icon: str = "●",
        on_edit=None,
        on_delete=None,
        *,
        highlighted: bool = False,
        savings: bool = False,
    ):
        super().__init__()
        self.name = name
        self.balance = balance
        self.highlighted = highlighted
        self.savings = savings

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

        name_controls: list[ft.Control] = [self._name_text]
        if savings:
            name_controls.append(StatusBadge("Накопительный"))
        name_row = ft.Row(
            name_controls,
            spacing=6,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )
        info = ft.Column(
            [name_row, self._balance_text],
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
        if highlighted:
            self.border = ft.Border.all(2, ft.Colors.PRIMARY)
            self.tooltip = "Открыт по ссылке"

    def update_balance(self, balance: str):
        self.balance = balance
        self._balance_text.value = balance
        self.update()
