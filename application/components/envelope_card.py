"""Карточка бюджета-конверта (слайс 3.2b)."""

from __future__ import annotations

import flet as ft
from application.components.card_actions import action_button
from application.components.formatting import format_money
from core.envelopes import EnvelopeProgress

from MySpaceShared.components.elevated_card import ElevatedCard

PROGRESS_HEIGHT = 6


class EnvelopeCard(ElevatedCard):
    """Лимит конверта: потрачено/лимит, прогресс, правка и удаление."""

    def __init__(self, envelope: EnvelopeProgress, *, on_edit=None, on_delete=None):
        spent = format_money(envelope.spent, envelope.currency)
        limit = format_money(envelope.limit_amount, envelope.currency)

        header = ft.Row(
            controls=[
                ft.Text(envelope.category, size=14, weight=ft.FontWeight.W_600, expand=True),
                ft.Text(f"{spent} из {limit}", size=13),
                action_button(ft.Icons.EDIT_OUTLINED, "Изменить конверт", on_edit),
                action_button(ft.Icons.DELETE_OUTLINE, "Удалить конверт", on_delete),
            ],
            spacing=4,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )
        controls: list[ft.Control] = [
            header,
            ft.ProgressBar(
                value=envelope.share,
                color=ft.Colors.ERROR if envelope.is_over else ft.Colors.PRIMARY,
                height=PROGRESS_HEIGHT,
            ),
        ]
        if envelope.is_over:
            controls.append(
                ft.Text(
                    f"Превышение на {format_money(envelope.overspent, envelope.currency)}",
                    size=12,
                    color=ft.Colors.ERROR,
                )
            )

        super().__init__(
            content=ft.Column(
                controls=controls,
                spacing=6,
                horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
            )
        )


__all__ = ["EnvelopeCard"]
