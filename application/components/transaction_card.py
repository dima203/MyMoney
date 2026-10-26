import datetime

import flet as ft
from MySpaceShared.core.formatting import format_money
from application.display import READ_ONLY_BADGE_LABEL

from MySpaceShared.components import ElevatedCard, StatusBadge
from MySpaceShared.core.tokens import PILL_RADIUS, RADIUS, SPACING


class TransactionCard(ft.Container):
    """Карточка транзакции: сумма, категория, счёт и время."""

    def __init__(
        self,
        description: str,
        amount: float,
        account_name: str,
        currency: str = "",
        category: str = "",
        timestamp: datetime.datetime | None = None,
        on_edit=None,
        on_delete=None,
        read_only: bool = False,
    ):
        super().__init__()
        if read_only:
            on_edit = None
            on_delete = None
        self._on_edit = on_edit
        self._on_delete = on_delete
        self._read_only = read_only
        self._currency = currency

        is_positive = amount >= 0
        amount_color = ft.Colors.GREEN if is_positive else ft.Colors.RED
        amount_prefix = "+" if is_positive else ""
        amount_str = f"{amount_prefix}{format_money(amount)}"
        if currency:
            amount_str = f"{amount_str} {currency}"

        time_str = ""
        if timestamp and (timestamp.hour, timestamp.minute, timestamp.second) != (0, 0, 0):
            time_str = timestamp.strftime("%H:%M")

        self._amount_text = ft.Text(amount_str, size=18, weight=ft.FontWeight.BOLD, color=amount_color)
        self._desc_text = ft.Text(
            description,
            size=14,
            weight=ft.FontWeight.W_500,
            max_lines=1,
            overflow=ft.TextOverflow.ELLIPSIS,
            visible=bool(description),
        )

        chips: list[ft.Control] = []
        if category:
            chips.append(
                ft.Container(
                    content=ft.Text(category, size=11, weight=ft.FontWeight.W_600, color=ft.Colors.PRIMARY),
                    bgcolor=ft.Colors.with_opacity(0.16, ft.Colors.PRIMARY),
                    border_radius=PILL_RADIUS,
                    padding=ft.Padding.symmetric(horizontal=8, vertical=2),
                )
            )
        if read_only:
            chips.append(StatusBadge(READ_ONLY_BADGE_LABEL))
        if time_str:
            chips.append(ft.Text(time_str, size=12, color=ft.Colors.ON_SURFACE_VARIANT))

        account_row = ft.Row(
            [
                ft.Icon(ft.Icons.ACCOUNT_BALANCE_WALLET, size=14, color=ft.Colors.ON_SURFACE_VARIANT),
                ft.Text(
                    account_name,
                    size=12,
                    color=ft.Colors.ON_SURFACE_VARIANT,
                    expand=True,
                    max_lines=1,
                    overflow=ft.TextOverflow.ELLIPSIS,
                ),
            ],
            spacing=SPACING["xs"],
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )

        left = ft.Column(
            [self._desc_text, account_row],
            spacing=2,
            expand=True,
            alignment=ft.MainAxisAlignment.CENTER,
        )
        right = ft.Column(
            [self._amount_text, ft.Row(chips, spacing=SPACING["xs"], alignment=ft.MainAxisAlignment.END)],
            spacing=SPACING["xs"],
            horizontal_alignment=ft.CrossAxisAlignment.END,
        )
        body = ft.Row(
            [left, right],
            spacing=SPACING["md"],
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            expand=True,
        )

        menu_button = None
        if not read_only:
            menu_button = ft.PopupMenuButton(
                icon=ft.Icons.MORE_VERT,
                icon_size=18,
                items=[
                    ft.PopupMenuItem(
                        content="Редактировать",
                        icon=ft.Icons.EDIT,
                        on_click=lambda _: self._on_edit and self._on_edit(),
                    ),
                    ft.PopupMenuItem(
                        content="Удалить",
                        icon=ft.Icons.DELETE,
                        on_click=lambda _: self._on_delete and self._on_delete(),
                    ),
                ],
            )

        self.content = ElevatedCard(
            body,
            trailing=menu_button,
            radius=RADIUS["lg"],
            padding=ft.Padding.symmetric(horizontal=16, vertical=12),
        )

    def update_amount(self, amount: float):
        is_positive = amount >= 0
        amount_color = ft.Colors.GREEN if is_positive else ft.Colors.RED
        amount_prefix = "+" if is_positive else ""
        amount_str = f"{amount_prefix}{format_money(amount)}"
        if self._currency:
            amount_str = f"{amount_str} {self._currency}"
        self._amount_text.value = amount_str
        self._amount_text.color = amount_color
        self.update()
