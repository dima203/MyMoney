"""Тесты диалога импорта CSV-выписки MyMoney (слайс 3.3b)."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import flet as ft
from application.api import ApiError
from application.components.csv_import_dialog import (
    EMPTY_PREVIEW,
    IMPORT_TEXT,
    NO_ACCOUNT,
    NO_COLUMN,
    TITLE,
    CsvImportDialog,
    dialog_width,
)
from core.csv_import import parse_csv

ACCOUNTS = [
    {"id": 1, "name": "Наличные", "resource": "BYN"},
    {"id": 2, "name": "Крипта", "resource": "USDT"},
]
CSV_TEXT = (
    "Дата;Сумма;Назначение;Категория\n"
    "05.10.2026;-12,50;Обед в кафе;Еда\n"
    "06.10.2026;1000;Зарплата;\n"
    "07.10.2026;abc;Битая сумма;Еда\n"
)


def _dialog(on_import=None, accounts=ACCOUNTS) -> tuple[CsvImportDialog, MagicMock]:
    page = MagicMock()
    dialog = CsvImportDialog(
        statement=parse_csv(CSV_TEXT),
        accounts=accounts,
        on_import=on_import or AsyncMock(),
    )
    dialog.show(page)
    return dialog, page


def _ready_dialog(on_import=None) -> tuple[CsvImportDialog, MagicMock]:
    """Диалог с выбранным счётом: строки разобраны, статус и предпросмотр пересчитаны."""
    dialog, page = _dialog(on_import=on_import)
    dialog._account.value = "1"
    dialog.refresh()
    return dialog, page


def _texts(control) -> list[str]:
    found: list[str] = []
    if isinstance(control, ft.Text):
        found.append(str(control.value))
    for child in getattr(control, "controls", None) or []:
        found.extend(_texts(child))
    content = getattr(control, "content", None)
    if content is not None and not isinstance(content, str):
        found.extend(_texts(content))
    return found


class TestInitialState:
    def test_mapping_is_guessed(self) -> None:
        dialog, _page = _dialog()

        assert dialog._mapping_controls["date"].value == "Дата"
        assert dialog._mapping_controls["amount"].value == "Сумма"
        assert dialog._mapping_controls["description"].value == "Назначение"
        assert dialog._mapping_controls["category"].value == "Категория"

    def test_title_and_no_default_account_with_two_options(self) -> None:
        dialog, page = _dialog()

        assert dialog.dialog.title.value == TITLE
        assert dialog._account.value is None
        assert [option.key for option in dialog._account.options] == ["1", "2"]
        page.show_dialog.assert_called_once_with(dialog.dialog)

    def test_single_account_is_preselected(self) -> None:
        dialog, _page = _dialog(accounts=[ACCOUNTS[0]])

        assert dialog._account.value == "1"
        assert dialog._import_button.disabled is False

    def test_without_account_import_is_disabled(self) -> None:
        dialog, _page = _dialog()

        assert dialog._import_button.disabled is True
        assert NO_ACCOUNT in _texts(dialog.dialog)


class TestPreview:
    def _ready(self) -> CsvImportDialog:
        return _ready_dialog()[0]

    def test_status_counts_rows_and_errors(self) -> None:
        dialog = self._ready()

        assert dialog._status.value == "К импорту: 2 операций · ошибок: 1"
        assert dialog._import_button.disabled is False

    def test_preview_lines(self) -> None:
        dialog = self._ready()

        texts = _texts(dialog._preview)
        assert texts[0].startswith("2026-10-05")
        assert "-12.50" in texts[0]
        assert len(texts) == 2

    def test_broken_mapping_shows_message_and_disables(self) -> None:
        dialog = self._ready()

        dialog._mapping_controls["date"].value = NO_COLUMN
        dialog.refresh()

        assert dialog._import_button.disabled is True
        assert "даты и суммы" in dialog._status.value
        assert EMPTY_PREVIEW in _texts(dialog._preview)

    def test_change_refreshes_and_updates_page(self) -> None:
        dialog, page = _dialog()
        dialog._account.value = "2"

        dialog._on_change(None)

        page.update.assert_called()
        assert "К импорту: 2" in dialog._status.value


class TestResponsiveWidth:
    def test_narrow_page_shrinks_dialog(self) -> None:
        assert dialog_width(SimpleNamespace(width=604)) == 524

    def test_wide_page_keeps_default(self) -> None:
        assert dialog_width(SimpleNamespace(width=1200)) == 620

    def test_tiny_page_has_minimum(self) -> None:
        assert dialog_width(SimpleNamespace(width=360)) == 320

    def test_show_applies_width_to_fields(self) -> None:
        page = MagicMock()
        page.width = 604
        dialog = CsvImportDialog(statement=parse_csv(CSV_TEXT), accounts=ACCOUNTS, on_import=AsyncMock())

        dialog.show(page)

        assert dialog._content.width == 524
        assert all(control.width == 524 for control in dialog._mapping_controls.values())
        assert dialog._account.width == 524


class TestImport:
    def test_confirm_calls_callback_and_closes(self) -> None:
        on_import = AsyncMock()
        dialog, page = _ready_dialog(on_import=on_import)

        asyncio.run(dialog._confirm(None))

        payloads = on_import.await_args.args[0]
        assert [payload["date"] for payload in payloads] == ["2026-10-05", "2026-10-06"]
        assert payloads[0]["entries"][0]["account"] == 1
        page.pop_dialog.assert_called_once()

    def test_confirm_without_rows_does_nothing(self) -> None:
        on_import = AsyncMock()
        dialog, page = _dialog(on_import=on_import)

        asyncio.run(dialog._confirm(None))

        on_import.assert_not_awaited()
        page.pop_dialog.assert_not_called()

    def test_api_error_keeps_dialog_open(self) -> None:
        on_import = AsyncMock(side_effect=ApiError("boom"))
        dialog, page = _ready_dialog(on_import=on_import)

        asyncio.run(dialog._confirm(None))

        page.pop_dialog.assert_not_called()
        assert dialog._import_button.disabled is False
        assert dialog._import_button.text == IMPORT_TEXT
        assert "Ошибка импорта:" in dialog._status.value
        assert "boom" in dialog._status.value
