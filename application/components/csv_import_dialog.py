"""Диалог импорта CSV-выписки MyMoney: маппинг колонок, предпросмотр (слайс 3.3b)."""

from __future__ import annotations

import flet as ft
from application.api import ApiError, BackendUnreachableError
from core.csv_import import FIELD_LABELS, FIELDS, Statement, build_transactions, guess_mapping

DIALOG_WIDTH = 620
DIALOG_MARGIN = 80
MIN_DIALOG_WIDTH = 320
PREVIEW_ROWS = 5
PREVIEW_HEIGHT = 140
NO_COLUMN = "—"
TITLE = "Импорт выписки"
IMPORT_TEXT = "Импортировать"
BUSY_TEXT = "Импорт..."
CANCEL_TEXT = "Отмена"
EMPTY_PREVIEW = "Нет корректных строк — проверьте колонки даты и суммы"
NO_ACCOUNT = "Выберите счёт"


class CsvImportDialog:
    """Предпросмотр выписки и запись операций; маппинг колонок — на пользователе."""

    def __init__(self, *, statement: Statement, accounts, on_import):
        self._statement = statement
        self._accounts = [row for row in accounts or [] if isinstance(row, dict) and row.get("id") is not None]
        self._on_import = on_import
        self._page = None

        mapping = guess_mapping(statement.headers)
        self._mapping_controls = {field: self._mapping_dropdown(field, mapping[field]) for field in FIELDS}
        self._account = ft.Dropdown(
            label="Счёт",
            options=[
                ft.dropdown.Option(key=str(row["id"]), text=str(row.get("name") or row["id"])) for row in self._accounts
            ],
            value=str(self._accounts[0]["id"]) if len(self._accounts) == 1 else None,
            width=DIALOG_WIDTH,
            on_select=self._on_change,
        )
        self._status = ft.Text("", size=12)
        self._preview = ft.Column(spacing=2, scroll=ft.ScrollMode.AUTO, height=PREVIEW_HEIGHT)
        self._import_button = ft.Button(IMPORT_TEXT, on_click=self._confirm)
        self._content = ft.Column(
            controls=[
                ft.Text("Проверьте колонки выписки", size=12, color=ft.Colors.ON_SURFACE_VARIANT),
                *self._mapping_controls.values(),
                self._account,
                self._status,
                self._preview,
            ],
            spacing=10,
            width=DIALOG_WIDTH,
            horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
        )
        self.dialog = ft.AlertDialog(
            title=ft.Text(TITLE),
            content=ft.Container(content=self._content),
            actions=[
                ft.TextButton(CANCEL_TEXT, on_click=lambda _event: self._close()),
                self._import_button,
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        self.refresh()

    def show(self, page) -> None:
        self._page = page
        self._apply_width(dialog_width(page))
        page.show_dialog(self.dialog)

    def refresh(self) -> tuple[list[dict], list[str]]:
        """Пересчитать предпросмотр; вернуть payload-ы и ошибки."""
        payloads, errors = self._payloads()
        self._import_button.disabled = not payloads
        if payloads:
            self._set_status(_status_text(len(payloads), len(errors)), error=False)
            self._preview.controls = [ft.Text(line, size=12) for line in _preview_lines(payloads)]
        else:
            self._set_status(errors[0] if errors else self._status.value, error=bool(errors))
            self._preview.controls = [ft.Text(EMPTY_PREVIEW, size=12, color=ft.Colors.ON_SURFACE_VARIANT)]
        return payloads, errors

    def _payloads(self) -> tuple[list[dict], list[str]]:
        account_id = self._account_id()
        if account_id is None:
            return [], [NO_ACCOUNT]
        mapping = {
            field: (control.value if control.value and control.value != NO_COLUMN else None)
            for field, control in self._mapping_controls.items()
        }
        try:
            return build_transactions(self._statement, mapping, account_id)
        except ValueError as exc:
            return [], [str(exc)]

    def _account_id(self) -> int | None:
        value = self._account.value
        if not value:
            return None
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    def _mapping_dropdown(self, field: str, selected: str | None) -> ft.Dropdown:
        options = [ft.dropdown.Option(NO_COLUMN)] + [
            ft.dropdown.Option(header) for header in self._statement.headers if header
        ]
        return ft.Dropdown(
            label=FIELD_LABELS[field],
            options=options,
            value=selected or NO_COLUMN,
            width=DIALOG_WIDTH,
            on_select=self._on_change,
        )

    def _apply_width(self, width: int) -> None:
        """Ширина полей и колонки под текущее окно."""
        self._content.width = width
        for control in (*self._mapping_controls.values(), self._account):
            control.width = width

    def _set_status(self, text: str, *, error: bool) -> None:
        self._status.value = text
        self._status.color = ft.Colors.ERROR if error else ft.Colors.ON_SURFACE_VARIANT

    def _set_busy(self, busy: bool) -> None:
        self._import_button.disabled = busy
        self._import_button.content = BUSY_TEXT if busy else IMPORT_TEXT

    def _update_page(self) -> None:
        if self._page is not None:
            self._page.update()

    def _on_change(self, _event=None) -> None:
        self.refresh()
        self._update_page()

    async def _confirm(self, _event=None) -> None:
        payloads, _errors = self.refresh()
        if not payloads:
            self._update_page()
            return
        self._set_busy(True)
        self._update_page()
        try:
            await self._on_import(payloads)
        except (ApiError, BackendUnreachableError, OSError) as exc:
            self._set_busy(False)
            self._set_status(f"Ошибка импорта: {exc}", error=True)
            self._update_page()
            return
        self._close()

    def _close(self) -> None:
        if self._page is not None:
            self._page.pop_dialog()


def dialog_width(page) -> int:
    """Ширина диалога: не шире окна (на узком экране 620 диалог 620 обрезался)."""
    available = getattr(page, "width", None) or DIALOG_WIDTH
    return max(MIN_DIALOG_WIDTH, min(DIALOG_WIDTH, int(available) - DIALOG_MARGIN))


def _status_text(count: int, error_count: int) -> str:
    text = f"К импорту: {count} операций"
    return f"{text} · ошибок: {error_count}" if error_count else text


def _preview_lines(payloads: list[dict]) -> list[str]:
    """Строки предпросмотра: дата · сумма · категория первых операций."""
    return [_preview_line(payload) for payload in payloads[:PREVIEW_ROWS]]


def _preview_line(payload: dict) -> str:
    entry = (payload.get("entries") or [{}])[0]
    parts = (payload.get("date"), _amount_text(entry.get("amount")), payload.get("category"))
    return " · ".join(str(part) for part in parts if part)


def _amount_text(amount) -> str:
    return f"{amount:+.2f}" if isinstance(amount, (int, float)) else ""


__all__ = ["CsvImportDialog", "dialog_width"]
