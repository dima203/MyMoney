import datetime

import flet as ft

from MySpaceShared.components import ElevatedCard, StatusBadge
from MySpaceShared.core.formatting import format_money
from MySpaceShared.core.tokens import RADIUS, SPACING

SOURCE_LABELS: dict[str, str] = {"task": "Задача", "calendar": "Событие"}
SOURCE_COLORS: dict[str, str] = {"task": ft.Colors.PRIMARY, "calendar": ft.Colors.TERTIARY}
SOURCE_ICONS: dict[str, str] = {"task": ft.Icons.CHECKLIST, "calendar": ft.Icons.EVENT}


def format_amount(amount, currency: str) -> str:
    if amount is None:
        value = "—"
    else:
        try:
            value = format_money(amount)
        except (TypeError, ValueError):
            value = str(amount)
    return f"{value} {currency}" if currency else value


def format_budget_date(value) -> str:
    if not value:
        return "Без даты"
    text = str(value)[:10]
    try:
        return datetime.date.fromisoformat(text).strftime("%d.%m.%Y")
    except ValueError:
        return str(value)


class CrossAppBudgetCard(ft.Container):
    """Read-only budget item created in another app (MyList/MyCalendar)."""

    def __init__(self, item: dict):
        super().__init__()
        source = str(item.get("source_app", ""))
        title = str(item.get("title") or "Без названия")
        color = SOURCE_COLORS.get(source, ft.Colors.PRIMARY)

        top_row = ft.Row(
            [
                ft.Icon(
                    SOURCE_ICONS.get(source, ft.Icons.INFO_OUTLINE),
                    size=18,
                    color=color,
                ),
                ft.Text(
                    title,
                    size=14,
                    weight=ft.FontWeight.W_500,
                    expand=True,
                    max_lines=1,
                    overflow=ft.TextOverflow.ELLIPSIS,
                ),
                StatusBadge(SOURCE_LABELS.get(source, source), color=color),
            ],
            spacing=SPACING["sm"],
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )

        bottom_row = ft.Row(
            [
                ft.Text(
                    format_amount(item.get("amount"), str(item.get("currency") or "")),
                    size=15,
                    weight=ft.FontWeight.BOLD,
                ),
                ft.Text(
                    format_budget_date(item.get("date")),
                    size=12,
                    color=ft.Colors.ON_SURFACE_VARIANT,
                ),
            ],
            spacing=SPACING["sm"],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )

        self.content = ElevatedCard(
            ft.Column([top_row, bottom_row], spacing=SPACING["xs"]),
            radius=RADIUS["lg"],
            padding=ft.Padding.symmetric(horizontal=16, vertical=12),
        )
        self.tooltip = "Создано в другом приложении — просмотр только для чтения"


__all__ = ["CrossAppBudgetCard", "format_amount", "format_budget_date"]
