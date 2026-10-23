"""Тесты экспорта CSV из экранов MyMoney (слайс 3.3a)."""

from __future__ import annotations

import asyncio
import csv
from io import StringIO
from unittest.mock import MagicMock

import flet as ft
import pytest
from application.view.accounts_view import AccountsView
from application.view.transactions_view import TransactionsView
from core.onboarding import OnboardingState

ACCOUNTS = [
    {"id": 1, "name": "Наличные", "resource": "BYN", "current_balance_qty": 430.5},
    {"id": 2, "name": "Крипта", "resource": "USDT", "resource_count": 12, "group": "investments"},
]
TRANSACTIONS = [
    {
        "id": 1,
        "date": "2026-10-05T10:00:00",
        "category": "Еда",
        "description": "Обед",
        "entries": [{"account": 1, "amount": -12}],
    },
    {
        "id": 2,
        "date": "2026-10-06T10:00:00",
        "category": "Транспорт",
        "description": "",
        "entries": [{"account": 1, "amount": -3}],
    },
]
DEFAULT_TARGET = "C:/exports/file.csv"


def _stub_view(rows: list[dict]) -> MagicMock:
    stub = MagicMock()
    stub.is_online = True
    stub.get_all.side_effect = lambda: list(rows)
    return stub


def _transactions_view() -> TransactionsView:
    view = TransactionsView(
        route="/transactions",
        api_client=MagicMock(),
        transaction_view=_stub_view(TRANSACTIONS),
        account_view=_stub_view(ACCOUNTS),
    )
    view.update = MagicMock()
    asyncio.run(view._load_data())
    return view


def _accounts_view(tmp_path) -> AccountsView:
    view = AccountsView(
        route="/accounts",
        api_client=MagicMock(),
        resource_view=_stub_view([]),
        account_view=_stub_view(ACCOUNTS),
        onboarding=OnboardingState(path=tmp_path / "onboarding.json"),
    )
    view.update = MagicMock()
    asyncio.run(view._load_data())
    return view


def _rows(text: str) -> list[list[str]]:
    return list(csv.reader(StringIO(text)))


def _patch_page(monkeypatch, view) -> MagicMock:
    fake_page = MagicMock()
    monkeypatch.setattr(type(view), "page", property(lambda self: fake_page))
    return fake_page


@pytest.fixture
def saved(monkeypatch) -> dict:
    state = {"target": DEFAULT_TARGET, "file_name": "", "content": ""}

    async def fake_save(page, *, file_name, content):
        state["file_name"] = file_name
        state["content"] = content
        return state["target"]

    monkeypatch.setattr("application.components.file_save.save_text_file", fake_save)
    return state


@pytest.fixture
def toast(monkeypatch) -> MagicMock:
    toast_mock = MagicMock()
    monkeypatch.setattr("application.components.file_save.show_toast", toast_mock)
    return toast_mock


class TestTransactionsExport:
    def test_export_button_in_filter_bar(self) -> None:
        view = _transactions_view()

        buttons = [control for control in view._filter_bar.controls if isinstance(control, ft.IconButton)]

        assert [button.tooltip for button in buttons] == ["Экспорт CSV", "Импорт CSV"]

    def test_export_writes_csv_and_toasts(self, monkeypatch, saved, toast) -> None:
        view = _transactions_view()
        _patch_page(monkeypatch, view)

        asyncio.run(view._export_csv())

        assert saved["file_name"].startswith("mymoney-transactions-")
        rows = _rows(saved["content"])
        assert rows[0][:3] == ["date", "category", "description"]
        assert [row[1] for row in rows[1:]] == ["Транспорт", "Еда"]
        toast.assert_called_once()
        assert "Сохранено" in toast.call_args.args[1]

    def test_export_respects_category_filter(self, monkeypatch, saved) -> None:
        view = _transactions_view()
        _patch_page(monkeypatch, view)
        view._filter_category.value = "Еда"

        asyncio.run(view._export_csv())

        rows = _rows(saved["content"])
        assert [row[1] for row in rows[1:]] == ["Еда"]

    def test_cancelled_dialog_has_no_toast(self, monkeypatch, saved, toast) -> None:
        view = _transactions_view()
        _patch_page(monkeypatch, view)
        saved["target"] = None

        asyncio.run(view._export_csv())

        toast.assert_not_called()

    def test_write_error_is_reported(self, monkeypatch, saved) -> None:
        view = _transactions_view()
        _patch_page(monkeypatch, view)

        async def failing_save(*args, **kwargs):
            raise OSError("disk full")

        monkeypatch.setattr("application.components.file_save.save_text_file", failing_save)

        asyncio.run(view._export_csv())

        assert view._error_text.visible is True
        assert "disk full" in view._error_text.value


class TestAccountsExport:
    def test_export_button_in_content(self, tmp_path) -> None:
        view = _accounts_view(tmp_path)

        row_controls = [control for control in view.content.controls if isinstance(control, ft.Row)]
        buttons = [child for row in row_controls for child in row.controls if isinstance(child, ft.IconButton)]

        assert [button.tooltip for button in buttons] == ["Экспорт CSV"]

    def test_export_writes_accounts(self, monkeypatch, tmp_path, saved, toast) -> None:
        view = _accounts_view(tmp_path)
        _patch_page(monkeypatch, view)

        asyncio.run(view._export_csv())

        assert saved["file_name"].startswith("mymoney-accounts-")
        rows = _rows(saved["content"])
        assert rows[0] == ["name", "currency", "balance", "group", "type"]
        assert rows[1] == ["Наличные", "BYN", "430.50", "", "main"]
        toast.assert_called_once()
