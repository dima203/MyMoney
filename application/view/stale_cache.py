"""Мгновенный рендер из кэша, фоновое обновление и баннер устаревших данных (2.184)."""

from __future__ import annotations

import flet as ft

STALE_BANNER_TEXT = "Не удалось обновить — данные могли устареть"
RETRY_LABEL = "Повторить"


def build_stale_banner(on_retry) -> ft.Container:
    """Баннер «данные могли устареть» с кнопкой повтора (виден при ошибке с кэшем)."""
    return ft.Container(
        content=ft.Row(
            [
                ft.Icon(ft.Icons.CLOUD_OFF, size=16, color=ft.Colors.ON_SURFACE_VARIANT),
                ft.Text(
                    STALE_BANNER_TEXT,
                    size=12,
                    color=ft.Colors.ON_SURFACE_VARIANT,
                    expand=True,
                ),
                ft.TextButton(RETRY_LABEL, on_click=lambda _event: on_retry()),
            ],
            spacing=8,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        bgcolor=ft.Colors.with_opacity(0.08, ft.Colors.ERROR),
        border_radius=8,
        padding=ft.Padding.symmetric(horizontal=12, vertical=6),
        visible=False,
    )


def payload_changed(previous, current) -> bool:
    """Сравнение снимков: неизменившиеся данные не перерисовываем (без мигания)."""
    return previous != current


__all__ = ["RETRY_LABEL", "STALE_BANNER_TEXT", "build_stale_banner", "payload_changed"]
