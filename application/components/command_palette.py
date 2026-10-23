"""Палитра команд MyMoney: Ctrl+K — поиск по счетам и транзакциям (слайс 1.6)."""

from __future__ import annotations

import flet as ft
from core.search import (
    DEFAULT_LIMIT,
    KIND_ACCOUNT,
    KIND_PLANNED,
    KIND_TRANSACTION,
    SearchHit,
    search_hits,
)

PALETTE_WIDTH = 460
RESULTS_HEIGHT = 320
PLACEHOLDER = "Счёт, категория или описание"
EMPTY_HINT = "Начните вводить название счёта, категорию или описание"
NO_MATCHES = "Ничего не найдено"
TITLE = "Поиск"
HOTKEY_KEY = "k"
HOTKEY_HINT = "Ctrl+K"
KIND_ICONS = {
    KIND_ACCOUNT: ft.Icons.ACCOUNT_BALANCE_WALLET_OUTLINED,
    KIND_TRANSACTION: ft.Icons.RECEIPT_LONG_OUTLINED,
    KIND_PLANNED: ft.Icons.EVENT_NOTE_OUTLINED,
}


def as_rows(value) -> list[dict]:
    """Строки, которые принимает палитра: список или словарь pk → строка; мусор отбрасывается."""
    rows = value.values() if isinstance(value, dict) else value or []
    return [row for row in rows if isinstance(row, dict)]


class CommandPalette:
    """Диалог поиска: строки подгружаются один раз при открытии, фильтр — на вводе."""

    def __init__(self, *, load_rows, on_navigate, limit: int = DEFAULT_LIMIT, on_close=None):
        self._load_rows = load_rows
        self._on_navigate = on_navigate
        self._on_close = on_close
        self._limit = limit
        self._page = None
        self._transactions: list[dict] = []
        self._accounts: list[dict] = []

        self._field = ft.TextField(hint_text=PLACEHOLDER, autofocus=True, on_change=self._on_change)
        self._results = ft.Column(spacing=0, scroll=ft.ScrollMode.AUTO, height=RESULTS_HEIGHT)
        self.dialog = ft.AlertDialog(
            title=ft.Row(
                controls=[ft.Icon(ft.Icons.SEARCH, size=20), ft.Text(TITLE)],
                spacing=8,
            ),
            content=ft.Column(
                controls=[self._field, self._results],
                spacing=8,
                width=PALETTE_WIDTH,
                horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
            ),
            actions=[ft.TextButton("Закрыть", on_click=lambda _: self._close())],
        )

    def show(self, page) -> None:
        self._page = page
        transactions, accounts = self._load_rows()
        self._transactions = as_rows(transactions)
        self._accounts = as_rows(accounts)
        self._field.value = ""
        self._render("")
        page.show_dialog(self.dialog)

    def _on_change(self, event) -> None:
        self._render(getattr(event.control, "value", "") or "")
        if self._page is not None:
            self._page.update()

    def _render(self, query: str) -> None:
        hits = search_hits(query, self._transactions, self._accounts, limit=self._limit)
        if hits:
            self._results.controls = [self._tile(hit) for hit in hits]
        else:
            hint = NO_MATCHES if str(query or "").strip() else EMPTY_HINT
            self._results.controls = [self._hint(hint)]

    def _tile(self, hit: SearchHit) -> ft.ListTile:
        return ft.ListTile(
            leading=ft.Icon(KIND_ICONS.get(hit.kind, ft.Icons.SEARCH), size=20),
            title=ft.Text(hit.title, size=14),
            subtitle=ft.Text(hit.subtitle, size=12),
            on_click=lambda _event, hit=hit: self._choose(hit),
        )

    @staticmethod
    def _hint(text: str) -> ft.Control:
        return ft.Container(
            padding=ft.Padding.symmetric(horizontal=12, vertical=16),
            content=ft.Text(text, size=12, color=ft.Colors.ON_SURFACE_VARIANT),
        )

    def _choose(self, hit: SearchHit) -> None:
        self._close()
        self._on_navigate(hit.route)

    def _close(self) -> None:
        if self._page is not None:
            self._page.pop_dialog()
            self._page = None
        if self._on_close is not None:
            self._on_close()


__all__ = ["HOTKEY_HINT", "HOTKEY_KEY", "CommandPalette", "as_rows"]
