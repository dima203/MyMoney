"""Массовое назначение категорий OKX-операциям (2.57b)."""

import datetime
from unittest.mock import MagicMock

import flet as ft
import pytest
from application.view.operations_view import OperationsView
from application.view.transactions_view import TransactionsView
from core.okx_categories import (
    apply_category,
    is_okx_operation,
    is_service_category,
    unlabeled_operations,
)
from core.transaction_filters import ALL_VALUE

from MySpaceShared.components.confirm_dialog import ConfirmDialog  # ruff: ignore[unused-import]

TODAY = datetime.date(2026, 11, 4)


def _tx(
    tx_id,
    *,
    source="okx",
    kind="operation",
    category="OKX: ввод",
    date="2026-11-01T10:00:00",
    amount=100.0,
    planned=False,
):
    return {
        "id": tx_id,
        "date": date,
        "category": category,
        "source": source,
        "kind": kind,
        "is_planned": planned,
        "description": f"Операция {tx_id}",
        "entries": [{"account": 1, "amount": amount, "unit_price": 1}],
    }


class TestServiceCategory:
    @pytest.mark.parametrize(
        "category",
        ["OKX: ввод", "OKX: вывод", "OKX: перевод", "OKX: сделка", "OKX", "", None, "  OKX: ввод "],
    )
    def test_service_values(self, category):
        assert is_service_category(category) is True

    @pytest.mark.parametrize("category", ["Продукты", "Зарплата", "okx: ввод", "OKX ввод"])
    def test_user_values(self, category):
        assert is_service_category(category) is False


class TestOkxOperation:
    def test_operation_is_target(self):
        assert is_okx_operation(_tx(1)) is True

    @pytest.mark.parametrize("kind", ["snapshot", "opening", "transfer"])
    def test_read_only_kinds_are_skipped(self, kind):
        assert is_okx_operation(_tx(1, kind=kind)) is False

    def test_foreign_source_and_plans_are_skipped(self):
        assert is_okx_operation(_tx(1, source="manual")) is False
        assert is_okx_operation(_tx(1, planned=True)) is False
        assert is_okx_operation("мусор") is False

    def test_missing_kind_is_operation(self):
        row = _tx(1)
        row.pop("kind")

        assert is_okx_operation(row) is True


class TestUnlabeledOperations:
    def test_filters_and_sorts_newest_first(self):
        rows = [
            _tx(1, date="2026-10-01T10:00:00"),
            _tx(2, date="2026-11-02T10:00:00"),
            _tx(3, date="2026-11-03T10:00:00", category="Продукты"),
            _tx(4, kind="snapshot"),
            _tx(5, source="manual", category="OKX: ввод"),
        ]

        result = unlabeled_operations(rows, today=TODAY)

        assert [tx["id"] for tx in result] == [2, 1]

    def test_period_filter(self):
        rows = [
            _tx(1, date="2026-10-01T10:00:00"),
            _tx(2, date="2026-11-02T10:00:00"),
        ]

        assert [tx["id"] for tx in unlabeled_operations(rows, period="7d", today=TODAY)] == [2]
        assert [tx["id"] for tx in unlabeled_operations(rows, period=ALL_VALUE, today=TODAY)] == [2, 1]

    def test_custom_category_is_not_listed(self):
        rows = [_tx(1, category="Такси")]

        assert unlabeled_operations(rows, today=TODAY) == []


class TestApplyCategory:
    def test_applies_each_row(self):
        patch = MagicMock()
        rows = [_tx(1), _tx(2)]

        updated, failed = apply_category(rows, "Продукты", patch)

        assert (updated, failed) == (2, [])
        assert patch.call_args_list == [
            ((1, {"category": "Продукты"}),),
            ((2, {"category": "Продукты"}),),
        ]

    def test_partial_failure_returns_retry_rows(self):
        def patch(tx_id, payload):
            if tx_id == 2:
                raise RuntimeError("boom")

        updated, failed = apply_category([_tx(1), _tx(2)], "Продукты", patch)

        assert updated == 1
        assert failed == [{"id": 2, "error": "boom"}]

    def test_retry_with_failed_rows_does_not_duplicate(self):
        calls = []

        def patch(tx_id, payload):
            calls.append(tx_id)

        apply_category([_tx(2)], "Продукты", patch)

        assert calls == [2]

    def test_empty_category_is_rejected(self):
        with pytest.raises(ValueError):
            apply_category([_tx(1)], "   ", MagicMock())


# ------------------------------------------------------------------ вьюха


def _view(transactions, *, online=True, period="all", categories=None):
    transaction_view = MagicMock()
    transaction_view.is_online = online
    transaction_view.get_all.return_value = list(transactions)
    account_view = MagicMock()
    account_view.is_online = online
    account_view.get_all.return_value = [{"id": 1, "name": "Основной", "resource": "BYN"}]
    api_client = MagicMock()
    api_client.list_budgets.return_value = []
    api_client.me.return_value = {"base_currency": "BYN"}
    api_client.get_prices.return_value = []
    api_client.get_fx_rates.return_value = []
    api_client.list_categories.return_value = [
        {"id": 1, "name": "Продукты", "is_archived": False},
        {"id": 2, "name": "Такси", "is_archived": False},
        {"id": 3, "name": "Старое", "is_archived": True},
    ]
    view = OperationsView(
        route="/operations",
        api_client=api_client,
        transaction_view=transaction_view,
        account_view=account_view,
        fx_store=MagicMock(),
    )
    view.update = MagicMock()
    view._filter_period.value = period
    return view


def _walk(control):
    yield control
    for child in getattr(control, "controls", None) or []:
        yield from _walk(child)
    content = getattr(control, "content", None)
    if content is not None and not isinstance(content, str):
        yield from _walk(content)


def _dialog_texts(dialog) -> list[str]:
    found = []

    def walk(control):
        for attr in ("value", "label", "text"):
            value = getattr(control, attr, None)
            if isinstance(value, str) and value:
                found.append(value)
        for child in getattr(control, "controls", None) or []:
            walk(child)
        content = getattr(control, "content", None)
        if content is not None and not isinstance(content, str):
            walk(content)

    walk(dialog)
    return found


@pytest.fixture
def page(monkeypatch):
    """`page` у Flet-контрола только для чтения — подменяем свойством класса."""
    mock = MagicMock()
    monkeypatch.setattr(OperationsView, "page", property(lambda _self: mock))
    return mock


class TestOkxCategoriesDialog:
    def test_offline_shows_toast_and_skips_dialog(self, monkeypatch, page):
        toasts = []
        monkeypatch.setattr("application.view.operations_view.show_toast", lambda page, text: toasts.append(text))
        view = _view([_tx(1)], online=False)

        view._show_okx_categories_dialog(None)

        assert toasts == ["Нужен сервер"]
        page.show_dialog.assert_not_called()

    def test_dialog_lists_unlabeled_operations(self, page):
        import asyncio

        view = _view([_tx(1), _tx(2, category="Такси"), _tx(3, kind="snapshot")])
        asyncio.run(view._load_data())
        view._category_rows = view.api_client.list_categories()

        view._show_okx_categories_dialog(None)

        dialog = page.show_dialog.call_args[0][0]
        labels = [control.label for control in _walk(dialog) if isinstance(control, ft.Checkbox)]
        assert len(labels) == 2  # «Выбрать все» + одна неразмеченная операция
        assert any("Операция 1" in label for label in labels)

    def test_apply_button_disabled_until_selection_and_category(self, page):
        import asyncio

        view = _view([_tx(1)])
        asyncio.run(view._load_data())
        view._category_rows = view.api_client.list_categories()
        view._show_okx_categories_dialog(None)

        dialog = page.show_dialog.call_args[0][0]
        apply_button = dialog.actions[-1]
        assert apply_button.disabled is True

    def test_action_button_hidden_offline_state(self):
        view = _view([_tx(1)])

        assert view._okx_categories_button is not None
        assert view._okx_categories_button.tooltip == "Категории OKX"


class TestMassAssignFlow:
    def test_apply_marks_rows_and_reloads(self, page):
        import asyncio

        view = _view([_tx(1), _tx(2)])
        view._load_data = MagicMock(return_value=asyncio.sleep(0))
        toasts = []
        view._show_toast = lambda text: toasts.append(text)

        asyncio.run(view._apply_selected_categories([_tx(1), _tx(2)], "Продукты"))

        assert view.api_client.update_transaction.call_count == 2
        assert toasts == ["Обновлено 2 операций"]

    def test_partial_failure_reports_counts(self, page):
        import asyncio

        view = _view([_tx(1), _tx(2)])
        view._load_data = MagicMock(return_value=asyncio.sleep(0))
        view.api_client.update_transaction.side_effect = [None, RuntimeError("boom")]
        errors = []
        view._category_error = lambda text: errors.append(text)

        asyncio.run(view._apply_selected_categories([_tx(1), _tx(2)], "Продукты"))

        assert "Обновлено 1" in errors[0]
        assert "не удалось 1" in errors[0]


class TestBaseViewHasNoAction:
    def test_plain_transactions_have_no_okx_action(self):
        view = TransactionsView(
            route="/transactions",
            api_client=MagicMock(),
            transaction_view=MagicMock(),
            account_view=MagicMock(),
            connection_banner=MagicMock(),
        )

        assert not hasattr(view, "_okx_categories_button")
