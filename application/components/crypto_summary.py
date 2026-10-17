import flet as ft
from core.app_settings import APP_SETTINGS

from MySpaceShared.components import AccentIcon, GradientSurface, HeroValue
from MySpaceShared.core.tokens import SPACING, accent_gradient

from .account_card import AccountCard


class CryptoSummary(ft.Container):
    """Сводка по криптосчетам с градиентной hero-шапкой."""

    def __init__(self, total_usd: str, accounts: list[dict], expanded: bool = False):
        super().__init__()
        self._expanded = expanded
        self._total_usd = total_usd
        self._accounts = accounts

        self._hero_value = HeroValue(total_usd, value_size=30)
        self._hero_value.value_text.color = ft.Colors.WHITE
        self._total_text = self._hero_value.value_text
        self._chevron = ft.Icon(ft.Icons.KEYBOARD_ARROW_DOWN, size=22, color=ft.Colors.WHITE)
        self._cards_column = ft.Column(
            controls=[self._build_card(acc) for acc in accounts],
            visible=expanded,
            spacing=SPACING["sm"],
        )

        header = ft.Row(
            [
                ft.Row(
                    [
                        AccentIcon(ft.Icons.CURRENCY_BITCOIN, size=40, color=ft.Colors.WHITE),
                        ft.Text("Крипто", size=15, weight=ft.FontWeight.W_600, color=ft.Colors.WHITE),
                    ],
                    spacing=SPACING["sm"],
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                ft.Row(
                    [self._hero_value, self._chevron],
                    spacing=SPACING["xs"],
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )

        hero = GradientSurface(
            header,
            gradient=accent_gradient(APP_SETTINGS.accent_color),
            padding=ft.Padding.symmetric(horizontal=16, vertical=14),
        )
        hero.on_click = self._toggle
        hero.ink = True

        self.content = ft.Column(controls=[hero, self._cards_column], spacing=SPACING["sm"])

    @staticmethod
    def _build_card(acc: dict) -> AccountCard:
        return AccountCard(
            name=acc["name"],
            balance=acc["balance"],
            currency_icon=acc.get("icon", "●"),
            on_edit=acc.get("on_edit"),
            on_delete=acc.get("on_delete"),
        )

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
            self._cards_column.controls = [self._build_card(acc) for acc in accounts]
        self.update()
