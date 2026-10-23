"""Нативные файловые диалоги и короткие уведомления (слайсы 3.3a–3.3c)."""

from __future__ import annotations

import asyncio
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from datetime import date
from pathlib import Path

import flet as ft
from core.csv_export import csv_filename

CSV_EXTENSION = "csv"
CSV_BOM_ENCODING = "utf-8-sig"
PDF_EXTENSION = "pdf"


@contextmanager
def file_picker(page) -> Iterator[ft.FilePicker]:
    """Временный `FilePicker` в сервисах страницы — только на время нативного диалога."""
    picker = ft.FilePicker()
    page.services.append(picker)
    try:
        yield picker
    finally:
        if picker in page.services:
            page.services.remove(picker)


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
    """Спросить путь у пользователя и записать текстовый файл; None — отмена."""
    target = await _ask_path(page, file_name=file_name, dialog_title=dialog_title, extension=CSV_EXTENSION)
    if not target:
        return None
    await asyncio.to_thread(Path(target).write_text, content, encoding=CSV_BOM_ENCODING)
    return target


async def save_bytes_file(
    page,
    *,
    file_name: str,
    content: bytes,
    dialog_title: str = "Сохранить PDF",
) -> str | None:
    """Спросить путь у пользователя и записать бинарный файл; None — отмена."""
    target = await _ask_path(page, file_name=file_name, dialog_title=dialog_title, extension=PDF_EXTENSION)
    if not target:
        return None
    await asyncio.to_thread(Path(target).write_bytes, content)
    return target


async def _ask_path(page, *, file_name: str, dialog_title: str, extension: str) -> str | None:
    with file_picker(page) as picker:
        return await picker.save_file(
            dialog_title=dialog_title,
            file_name=file_name,
            allowed_extensions=[extension],
            file_type=ft.FilePickerFileType.CUSTOM,
        )


def show_toast(page, message: str) -> None:
    """Короткое сообщение внизу экрана."""
    page.show_dialog(ft.SnackBar(content=ft.Text(message)))


__all__ = ["export_csv", "file_picker", "save_bytes_file", "save_text_file", "show_toast"]
