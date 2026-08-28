import flet as ft

from .account_card import AccountCard


class CryptoSummary(ft.Container):
    def __init__(self, total_usd: str, accounts: list[dict], expanded: bool = False):
        super().__init__()
        self._expanded = expanded
        self._total_usd = total_usd
        self._accounts = accounts

        self._total_text = ft.Text(total_usd, size=16, weight=ft.FontWeight.BOLD)
        self._chevron = ft.Icon(ft.Icons.KEYBOARD_ARROW_DOWN, size=20)
        self._cards_column = ft.Column(
            controls=[
                AccountCard(
                    name=acc["name"],
                    balance=acc["balance"],
                    currency_icon=acc.get("icon", "●"),
                    on_edit=acc.get("on_edit"),
                    on_delete=acc.get("on_delete"),
                )
                for acc in accounts
            ],
            visible=expanded,
            spacing=4,
        )

        header = ft.Container(
            content=ft.Row(
                [
                    ft.Row(
                        [
                            ft.Icon(ft.Icons.CURRENCY_BITCOIN, size=24, color=ft.Colors.AMBER),
                            ft.Text("Крипто", size=16, weight=ft.FontWeight.W_600),
                        ],
                        spacing=8,
                    ),
                    ft.Row(
                        [
                            self._total_text,
                            self._chevron,
                        ],
                        spacing=4,
                    ),
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            padding=ft.padding.symmetric(horizontal=16, vertical=12),
            on_click=self._toggle,
            ink=True,
            border_radius=8,
        )

        self.content = ft.Column(
            controls=[header, self._cards_column],
            spacing=0,
        )
        self.bgcolor = ft.Colors.SURFACE_CONTAINER_LOWEST
        self.border_radius = 12
        self.padding = ft.padding.all(8)

    def _toggle(self, e):
        self._expanded = not self._expanded
        self._cards_column.visible = self._expanded
        self._chevron.rotate = ft.Rotate(angle=180 if self._expanded else 0)
        self.update()

    def update_total(self, total_usd: str, accounts: list[dict] | None = None):
        self._total_usd = total_usd
        self._total_text.value = total_usd
        if accounts is not None:
            self._accounts = accounts
            self._cards_column.controls = [
                AccountCard(
                    name=acc["name"],
                    balance=acc["balance"],
                    currency_icon=acc.get("icon", "●"),
                    on_edit=acc.get("on_edit"),
                    on_delete=acc.get("on_delete"),
                )
                for acc in accounts
            ]
        self.update()
