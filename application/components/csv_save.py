"""Сохранение CSV через нативный диалог и короткие уведомления (слайс 3.3a)."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from datetime import date
from pathlib import Path

import flet as ft
from core.csv_export import csv_filename

CSV_EXTENSION = "csv"
CSV_BOM_ENCODING = "utf-8-sig"


async def export_csv(page, *, kind: str, content: str, on_error: Callable[[str], None]) -> None:
    """Сохранить готовый CSV-текст: спросить путь, записать, сообщить об итоге.

    Текст ошибки отдаётся в `on_error` — экран сам решает, где его показать.
    """
    try:
        target = await save_text_file(page, file_name=csv_filename(kind, date.today()), content=content)
    except (OSError, RuntimeError, ValueError) as exc:
        on_error(f"Ошибка экспорта: {exc}")
        return
    if target:
        show_toast(page, f"Сохранено: {target}")


async def save_text_file(
    page,
    *,
    file_name: str,
    content: str,
    dialog_title: str = "Сохранить CSV",
) -> str | None:
    """Спросить путь у пользователя и записать файл; None — отмена диалога."""
    picker = ft.FilePicker()
    page.services.append(picker)
    try:
        target = await picker.save_file(
            dialog_title=dialog_title,
            file_name=file_name,
            allowed_extensions=[CSV_EXTENSION],
            file_type=ft.FilePickerFileType.CUSTOM,
        )
    finally:
        if picker in page.services:
            page.services.remove(picker)
    if not target:
        return None
    await asyncio.to_thread(Path(target).write_text, content, encoding=CSV_BOM_ENCODING)
    return target


def show_toast(page, message: str) -> None:
    """Короткое сообщение внизу экрана."""
    page.show_dialog(ft.SnackBar(content=ft.Text(message)))


__all__ = ["export_csv", "save_text_file", "show_toast"]
