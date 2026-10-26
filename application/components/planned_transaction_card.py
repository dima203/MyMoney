import datetime

import flet as ft
from MySpaceShared.core.formatting import format_money
from core.recurrence import RecurrenceRule

from MySpaceShared.components import ElevatedCard
from MySpaceShared.core.tokens import PILL_RADIUS, RADIUS, SPACING


class PlannedTransactionCard(ft.Container):
    """Карточка запланированной операции: сумма, дата, повтор и действия."""

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
        amount_color = ft.Colors.GREEN if is_positive else ft.Colors.RED
        amount_prefix = "+" if is_positive else ""
        amount_str = f"{amount_prefix}{format_money(amount)}"

        date_str = ""
        if planned_date:
            today = datetime.date.today()
            days_until = (planned_date - today).days
            if days_until < 0:
                date_str = f"Просрочено ({abs(days_until)} дн.)"
                date_color = ft.Colors.RED
            elif days_until == 0:
                date_str = "Сегодня"
                date_color = ft.Colors.ORANGE
            elif days_until == 1:
                date_str = "Завтра"
                date_color = ft.Colors.ORANGE
            else:
                date_str = planned_date.strftime("%d %b")
                date_color = ft.Colors.ON_SURFACE_VARIANT
        else:
            date_color = ft.Colors.ON_SURFACE_VARIANT

        chips: list[ft.Control] = []
        if category:
            chips.append(
                ft.Container(
                    content=ft.Text(category, size=11, weight=ft.FontWeight.W_600, color=ft.Colors.TERTIARY),
                    bgcolor=ft.Colors.with_opacity(0.16, ft.Colors.TERTIARY),
                    border_radius=PILL_RADIUS,
                    padding=ft.Padding.symmetric(horizontal=8, vertical=2),
                )
            )

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

                chips.append(
                    ft.Container(
                        content=ft.Row(
                            [
                                ft.Icon(ft.Icons.REPEAT, size=13, color=ft.Colors.PRIMARY),
                                ft.Text(label, size=11, weight=ft.FontWeight.W_600, color=ft.Colors.PRIMARY),
                            ],
                            spacing=2,
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                        bgcolor=ft.Colors.with_opacity(0.16, ft.Colors.PRIMARY),
                        border_radius=PILL_RADIUS,
                        padding=ft.Padding.symmetric(horizontal=8, vertical=2),
                    )
                )

        desc_text = ft.Text(
            description,
            size=14,
            weight=ft.FontWeight.W_500,
            max_lines=1,
            overflow=ft.TextOverflow.ELLIPSIS,
            visible=bool(description),
        )
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
            [desc_text, account_row],
            spacing=2,
            expand=True,
            alignment=ft.MainAxisAlignment.CENTER,
        )

        amount_text = ft.Text(amount_str, size=18, weight=ft.FontWeight.BOLD, color=amount_color)
        right = ft.Column(
            [
                amount_text,
                ft.Row(chips, spacing=SPACING["xs"], alignment=ft.MainAxisAlignment.END),
                ft.Text(date_str, size=12, color=date_color),
            ],
            spacing=SPACING["xs"],
            horizontal_alignment=ft.CrossAxisAlignment.END,
        )

        execute_btn = ft.IconButton(
            icon=ft.Icons.PLAY_ARROW,
            icon_size=20,
            icon_color=ft.Colors.GREEN,
            tooltip="Выполнить",
            on_click=lambda _: self._on_execute and self._on_execute(),
        )
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
        trailing = ft.Row(
            [execute_btn, menu_button],
            spacing=0,
            alignment=ft.MainAxisAlignment.END,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )

        body = ft.Row(
            [left, right],
            spacing=SPACING["md"],
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            expand=True,
        )
        self.content = ElevatedCard(
            body,
            trailing=trailing,
            radius=RADIUS["lg"],
            padding=ft.Padding.symmetric(horizontal=16, vertical=12),
        )
