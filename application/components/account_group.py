import flet as ft

from .account_card import AccountCard


class AccountGroup(ft.ExpansionTile):
    def __init__(self, group_name: str, total_balance: str, accounts: list[dict]):
        super().__init__(title=group_name)
        self.group_name = group_name
        self._total_balance = total_balance

        self.title = ft.Row(
            [
                ft.Text(
                    group_name or "Без группы",
                    size=14,
                    weight=ft.FontWeight.W_600,
                    expand=True,
                ),
                ft.Text(total_balance, size=14, color=ft.Colors.ON_SURFACE_VARIANT),
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        )
        self.subtitle = ft.Text(f"{len(accounts)} счетов", size=12, color=ft.Colors.ON_SURFACE_VARIANT)
        self.leading = ft.Icon(ft.Icons.FOLDER, size=20, color=ft.Colors.ON_SURFACE_VARIANT)
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
        if self.title.controls and len(self.title.controls) > 1:
            self.title.controls[1].value = total_balance
            self.update()
