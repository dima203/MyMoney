import datetime

import flet as ft
from application.display import READ_ONLY_BADGE_LABEL
from MySpaceShared.components import StatusBadge


class TransactionCard(ft.Container):
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
        amount_color = ft.Colors.GREEN_700 if is_positive else ft.Colors.RED_700
        amount_prefix = "+" if is_positive else ""
        amount_str = f"{amount_prefix}{amount:,.2f}"
        if currency:
            amount_str = f"{amount_str} {currency}"

        time_str = ""
        if timestamp and (timestamp.hour, timestamp.minute, timestamp.second) != (0, 0, 0):
            time_str = timestamp.strftime("%H:%M")

        self._amount_text = ft.Text(amount_str, size=16, weight=ft.FontWeight.BOLD, color=amount_color)
        self._desc_text = ft.Text(
            description or "Без описания", size=14, expand=True, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS
        )

        category_controls = []
        if category:
            category_controls = [
                ft.Container(
                    content=ft.Text(category, size=11, color=ft.Colors.PRIMARY),
                    bgcolor=ft.Colors.PRIMARY_CONTAINER,
                    border_radius=4,
                    padding=ft.Padding.symmetric(horizontal=6, vertical=2),
                )
            ]

        badge_controls = []
        if read_only:
            badge_controls = [StatusBadge(READ_ONLY_BADGE_LABEL)]

        top_row = ft.Row(
            [
                self._amount_text,
                ft.Row(category_controls + badge_controls, spacing=4),
                ft.Text(time_str, size=12, color=ft.Colors.ON_SURFACE_VARIANT) if time_str else ft.Container(),
            ],
            alignment=ft.MainAxisAlignment.START,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=8,
        )

        bottom_controls = [
            ft.Icon(ft.Icons.ACCOUNT_BALANCE_WALLET, size=14, color=ft.Colors.ON_SURFACE_VARIANT),
            ft.Text(
                account_name,
                size=12,
                color=ft.Colors.ON_SURFACE_VARIANT,
                expand=True,
                max_lines=1,
                overflow=ft.TextOverflow.ELLIPSIS,
            ),
        ]
        if not read_only:
            bottom_controls.append(
                ft.PopupMenuButton(
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
            )

        bottom_row = ft.Row(
            bottom_controls,
            alignment=ft.MainAxisAlignment.START,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=4,
        )

        self.content = ft.Column([top_row, bottom_row], spacing=4)
        self.padding = ft.Padding.symmetric(horizontal=16, vertical=10)
        self.border_radius = 8
        self.bgcolor = ft.Colors.SURFACE_CONTAINER_LOW

    def update_amount(self, amount: float):
        is_positive = amount >= 0
        amount_color = ft.Colors.GREEN_700 if is_positive else ft.Colors.RED_700
        amount_prefix = "+" if is_positive else ""
        amount_str = f"{amount_prefix}{amount:,.2f}"
        if self._currency:
            amount_str = f"{amount_str} {self._currency}"
        self._amount_text.value = amount_str
        self._amount_text.color = amount_color
        self.update()
