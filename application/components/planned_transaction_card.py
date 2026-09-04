import datetime

import flet as ft
from core.recurrence import RecurrenceRule


class PlannedTransactionCard(ft.Container):
    def __init__(
        self,
        description: str,
        amount: float,
        account_name: str,
        category: str = "",
        planned_date: datetime.date | None = None,
        recurrence_rule: str = "",
        on_execute=None,
        on_edit=None,
        on_delete=None,
    ):
        super().__init__()
        self._on_execute = on_execute
        self._on_edit = on_edit
        self._on_delete = on_delete

        is_positive = amount >= 0
        amount_color = ft.Colors.GREEN_700 if is_positive else ft.Colors.RED_700
        amount_prefix = "+" if is_positive else ""
        amount_str = f"{amount_prefix}{amount:,.2f}"

        date_str = ""
        if planned_date:
            today = datetime.date.today()
            days_until = (planned_date - today).days
            if days_until < 0:
                date_str = f"Просрочено ({abs(days_until)} дн.)"
                date_color = ft.Colors.RED_700
            elif days_until == 0:
                date_str = "Сегодня"
                date_color = ft.Colors.ORANGE_700
            elif days_until == 1:
                date_str = "Завтра"
                date_color = ft.Colors.ORANGE_700
            else:
                date_str = planned_date.strftime("%d %b")
                date_color = ft.Colors.ON_SURFACE_VARIANT
        else:
            date_color = ft.Colors.ON_SURFACE_VARIANT

        recurrence_controls = []
        if recurrence_rule:
            rule = RecurrenceRule.parse(recurrence_rule)
            if rule:
                freq_labels = {
                    "daily": "Каждый день",
                    "weekly": "Каждую неделю",
                    "monthly": "Каждый месяц",
                    "yearly": "Каждый год",
                }
                label = freq_labels.get(rule.frequency.value, rule.frequency.value)
                if rule.interval > 1:
                    label = f"Каждые {rule.interval} "
                    period_map = {"daily": "дня", "weekly": "недели", "monthly": "месяца", "yearly": "года"}
                    label += period_map.get(rule.frequency.value, rule.frequency.value)

                recurrence_controls = [
                    ft.Container(
                        content=ft.Row(
                            [
                                ft.Icon(ft.Icons.REPEAT, size=14, color=ft.Colors.PRIMARY),
                                ft.Text(label, size=11, color=ft.Colors.PRIMARY),
                            ],
                            spacing=2,
                        ),
                        bgcolor=ft.Colors.PRIMARY_CONTAINER,
                        border_radius=4,
                        padding=ft.padding.symmetric(horizontal=6, vertical=2),
                    )
                ]

        category_controls = []
        if category:
            category_controls = [
                ft.Container(
                    content=ft.Text(category, size=11, color=ft.Colors.TERTIARY),
                    bgcolor=ft.Colors.TERTIARY_CONTAINER,
                    border_radius=4,
                    padding=ft.padding.symmetric(horizontal=6, vertical=2),
                )
            ]

        execute_btn = ft.IconButton(
            icon=ft.Icons.PLAY_ARROW,
            icon_size=20,
            icon_color=ft.Colors.GREEN,
            tooltip="Выполнить",
            on_click=lambda _: self._on_execute and self._on_execute(),
        )

        top_row = ft.Row(
            [
                ft.Text(amount_str, size=16, weight=ft.FontWeight.BOLD, color=amount_color),
                ft.Row(category_controls + recurrence_controls, spacing=4),
                ft.Text(date_str, size=12, color=date_color),
            ],
            alignment=ft.MainAxisAlignment.START,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=8,
        )

        bottom_row = ft.Row(
            [
                ft.Icon(ft.Icons.ACCOUNT_BALANCE_WALLET, size=14, color=ft.Colors.ON_SURFACE_VARIANT),
                ft.Text(account_name, size=12, color=ft.Colors.ON_SURFACE_VARIANT, expand=True),
                execute_btn,
                ft.PopupMenuButton(
                    icon=ft.Icons.MORE_VERT,
                    icon_size=18,
                    items=[
                        ft.PopupMenuItem(
                            text="Редактировать",
                            icon=ft.Icons.EDIT,
                            on_click=lambda _: self._on_edit and self._on_edit(),
                        ),
                        ft.PopupMenuItem(
                            text="Удалить",
                            icon=ft.Icons.DELETE,
                            on_click=lambda _: self._on_delete and self._on_delete(),
                        ),
                    ],
                ),
            ],
            alignment=ft.MainAxisAlignment.START,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=4,
        )

        self.content = ft.Column([top_row, bottom_row], spacing=4)
        self.padding = ft.padding.symmetric(horizontal=16, vertical=10)
        self.border_radius = 8
        self.bgcolor = ft.Colors.SURFACE_CONTAINER_LOW
