import flet as ft
from MySpaceShared.components import AccentIcon

from .account_card import AccountCard


class AccountGroup(ft.ExpansionTile):
    """Группа счетов с итогом по группе в шапке."""

    def __init__(self, group_name: str, total_balance: str, accounts: list[dict]):
        super().__init__(title=group_name)
        self.group_name = group_name
        self._total_balance = total_balance

        self._total_text = ft.Text(total_balance, size=16, weight=ft.FontWeight.BOLD, color=ft.Colors.PRIMARY)
        self.title = ft.Row(
            [
                ft.Text(
                    group_name or "Без группы",
                    size=15,
                    weight=ft.FontWeight.W_600,
                    expand=True,
                ),
                self._total_text,
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )
        self.subtitle = ft.Text(f"{len(accounts)} счетов", size=12, color=ft.Colors.ON_SURFACE_VARIANT)
        self.leading = AccentIcon(ft.Icons.FOLDER, size=36)
        self.controls_padding = ft.Padding.only(left=12, right=12, top=4, bottom=12)
        self.controls = [
            AccountCard(
                name=acc["name"],
                balance=acc["balance"],
                currency_icon=acc.get("icon", "●"),
                on_edit=acc.get("on_edit"),
                on_delete=acc.get("on_delete"),
            )
            for acc in accounts
        ]

    def update_total(self, total_balance: str):
        self._total_balance = total_balance
        self._total_text.value = total_balance
        self.update()
