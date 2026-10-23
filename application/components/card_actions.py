"""Компактные иконки-действия в карточках MyMoney."""

from __future__ import annotations

import flet as ft

ICON_SIZE = 18
ICON_PADDING = 4


def action_button(icon: str, tooltip: str, on_click) -> ft.IconButton:
    """Иконка-кнопка карточки: мелкая, без лишнего паддинга."""
    return ft.IconButton(icon, tooltip=tooltip, icon_size=ICON_SIZE, padding=ICON_PADDING, on_click=on_click)


__all__ = ["action_button"]
