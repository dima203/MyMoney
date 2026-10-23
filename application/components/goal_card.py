"""Карточка цели накоплений (слайс 3.2c)."""

from __future__ import annotations

import flet as ft
from application.components.card_actions import action_button
from application.components.formatting import format_money
from core.goals import GoalProgress

from MySpaceShared.components.elevated_card import ElevatedCard

PROGRESS_HEIGHT = 6
DEADLINE_FORMAT = "%d.%m.%Y"


class GoalCard(ElevatedCard):
    """Цель: накоплено/цель, прогресс, срок, пополнение, правка и удаление."""

    def __init__(self, goal: GoalProgress, *, today=None, on_contribute=None, on_edit=None, on_delete=None):
        saved = format_money(goal.saved_amount, goal.currency)
        target = format_money(goal.target_amount, goal.currency)

        header = ft.Row(
            controls=[
                ft.Text(goal.name, size=14, weight=ft.FontWeight.W_600, expand=True),
                ft.Text(f"{saved} из {target}", size=13),
                action_button(ft.Icons.ADD_CARD_OUTLINED, "Пополнить цель", on_contribute),
                action_button(ft.Icons.EDIT_OUTLINED, "Изменить цель", on_edit),
                action_button(ft.Icons.DELETE_OUTLINE, "Удалить цель", on_delete),
            ],
            spacing=4,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )
        controls: list[ft.Control] = [
            header,
            ft.ProgressBar(
                value=goal.share,
                color=ft.Colors.TERTIARY if goal.is_reached else ft.Colors.PRIMARY,
                height=PROGRESS_HEIGHT,
            ),
            self._caption_row(goal, today),
        ]

        super().__init__(
            content=ft.Column(
                controls=controls,
                spacing=6,
                horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
            )
        )

    @staticmethod
    def _caption_row(goal: GoalProgress, today) -> ft.Row:
        if goal.is_reached:
            summary = ft.Text("Цель достигнута", size=12, color=ft.Colors.TERTIARY)
        else:
            summary = ft.Text(f"Осталось {format_money(goal.remaining, goal.currency)}", size=12)
        controls: list[ft.Control] = [ft.Row([summary], expand=True)]
        deadline = GoalCard._deadline_text(goal, today)
        if deadline is not None:
            controls.append(deadline)
        return ft.Row(controls=controls, spacing=8, vertical_alignment=ft.CrossAxisAlignment.CENTER)

    @staticmethod
    def _deadline_text(goal: GoalProgress, today) -> ft.Text | None:
        if goal.deadline is None:
            return None
        caption = f"до {goal.deadline.strftime(DEADLINE_FORMAT)}"
        days = goal.days_left(today) if today is not None else None
        if days is None or goal.is_reached:
            return ft.Text(caption, size=12, color=ft.Colors.ON_SURFACE_VARIANT)
        if days < 0:
            return ft.Text(f"{caption} · срок истёк", size=12, color=ft.Colors.ERROR)
        return ft.Text(f"{caption} · {days} дн.", size=12, color=ft.Colors.ON_SURFACE_VARIANT)


__all__ = ["GoalCard"]
