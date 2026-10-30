"""Экран «Операции»: режимы, фильтры, итоги и кросс-планы (2.48b)."""

import asyncio
import tempfile
from pathlib import Path
from unittest.mock import MagicMock

import flet as ft
from application.api import RestClientError
from application.components.cross_app_budget_card import CrossAppBudgetCard
from application.components.planned_transaction_card import PlannedTransactionCard
from application.components.recurrence_fields import RecurrenceEditor
from application.fx_rates import FxRateStore
from application.view.operations_view import MODE_ACTUAL, MODE_PLANNED, OperationsView

from MySpaceShared.components.empty_state import EmptyState

ACCOUNTS = [
    {"id": 1, "name": "Основной", "resource": "BYN", "account_type": "main"},
    {"id": 2, "name": "Валютный", "resource": "EUR", "account_type": "main"},
    {"id": 4, "name": "Долларовый", "resource": "USD", "account_type": "main"},
]
PRICES = [
    {"symbol": "USDT", "price": 1.0},
    {"symbol": "BYN", "price": 0.33},
    {"symbol": "EUR", "price": 1.08},
]
LAPTOP = {
    "id": 1,
    "date": "2026-10-20T10:00:00",
    "description": "Ноутбук",
    "category": "Техника",
    "is_planned": False,
    "entries": [{"account": 1, "amount": -300.0, "unit_price": 1}],
}
SALARY = {
    "id": 2,
    "date": "2026-10-25T10:00:00",
    "description": "Зарплата",
    "category": "Доход",
    "is_planned": False,
    "entries": [{"account": 1, "amount": 1000.0, "unit_price": 1}],
}
RENT = {
    "id": 3,
    "date": "2026-11-01T09:00:00",
    "description": "Аренда",
    "category": "Жильё",
    "is_planned": True,
    "recurrence_rule": "monthly",
    "entries": [{"account": 1, "amount": -400.0, "unit_price": 1}],
}
TASK_BUDGET = {
    "source_app": "task",
    "source_id": 7,
    "title": "Сдать отчёт",
    "date": "2026-11-03",
    "amount": "0",
    "currency": "BYN",
}
CALENDAR_BUDGET = {
    "source_app": "calendar",
    "source_id": 9,
    "title": "День рождения",
    "date": "2026-11-05",
    "amount": "100",
    "currency": "BYN",
}


def _view(transactions=None, budgets=None, base_currency="BYN", prices=None, mode=MODE_ACTUAL, fx_rows=None):
    transaction_view = MagicMock()
    transaction_view.is_online = True
    transaction_view.get_all.return_value = list(transactions or [])
    account_view = MagicMock()
    account_view.is_online = True
    account_view.get_all.return_value = list(ACCOUNTS)
    api_client = MagicMock()
    api_client.list_budgets.return_value = list(budgets or [])
    api_client.me.return_value = {"base_currency": base_currency} if base_currency else {}
    api_client.get_prices.return_value = prices if prices is not None else list(PRICES)
    api_client.get_fx_rates.return_value = list(fx_rows or [])
    view = OperationsView(
        route="/operations",
        api_client=api_client,
        transaction_view=transaction_view,
        account_view=account_view,
        initial_mode=mode,
        fx_store=FxRateStore(Path(tempfile.mkdtemp()) / "fx.json"),
    )
    view.update = MagicMock()
    return view


def _filtered(view):
    return view._get_filtered_transactions()


class TestShell:
    def test_title_route_and_nav_index(self):
        view = _view()

        assert view.title == "Операции"
        assert view.route == "/operations"
        assert view.selected_index == 1

    def test_has_both_segments(self):
        view = _view()

        assert [segment.value for segment in view._segments.segments] == [MODE_ACTUAL, MODE_PLANNED]
        assert view._segments.selected == [MODE_ACTUAL]

    def test_initial_planned_mode_from_route(self):
        view = _view(mode=MODE_PLANNED)

        assert view._segments.selected == [MODE_PLANNED]


class TestModeFiltering:
    def test_actual_mode_hides_plans(self):
        view = _view([LAPTOP, RENT])

        asyncio.run(view._load_data())

        assert [tx["id"] for tx in _filtered(view)] == [1]

    def test_planned_mode_shows_only_plans(self):
        view = _view([LAPTOP, RENT], mode=MODE_PLANNED)

        asyncio.run(view._load_data())

        assert [tx["id"] for tx in _filtered(view)] == [3]
        assert view._totals.value == "Планов: 1"

    def test_set_mode_records_selection(self):
        view = _view([LAPTOP, RENT])

        asyncio.run(view._load_data())
        view.set_mode(MODE_PLANNED)

        assert view._segments.selected == [MODE_PLANNED]
        assert [tx["id"] for tx in _filtered(view)] == [3]

    def test_snapshots_switch_only_in_actual_mode(self):
        view = _view([])

        assert view._show_snapshots.visible is True
        view.set_mode(MODE_PLANNED)
        assert view._show_snapshots.visible is False
        view.set_mode(MODE_ACTUAL)
        assert view._show_snapshots.visible is True

    def test_csv_actions_only_in_actual_mode(self):
        view = _view([])

        assert view._filter_bar.visible is True
        view.set_mode(MODE_PLANNED)
        assert view._filter_bar.visible is False
        view.set_mode(MODE_ACTUAL)
        assert view._filter_bar.visible is True

    def test_set_mode_ignores_unknown_value(self):
        view = _view()

        view.set_mode("archive")

        assert view._mode == MODE_ACTUAL

    def test_filters_apply_in_both_modes(self):
        view = _view([LAPTOP, SALARY, RENT])
        asyncio.run(view._load_data())

        view._filter_type.value = "income"
        assert [tx["id"] for tx in _filtered(view)] == [2]

        view._filter_type.value = "all"
        view._filter_period.value = "month"
        assert [tx["id"] for tx in _filtered(view)] == [2, 1]

        view.set_mode(MODE_PLANNED)
        view._filter_period.value = "all"
        view._filter_category.value = "Жильё"
        assert [tx["id"] for tx in _filtered(view)] == [3]


class TestPlanList:
    def test_plan_cards_and_cross_plans(self):
        view = _view([RENT], budgets=[TASK_BUDGET, CALENDAR_BUDGET], mode=MODE_PLANNED)

        asyncio.run(view._load_data())
        controls = view._tx_list.controls

        cards = [item for item in controls if isinstance(item, PlannedTransactionCard)]
        cross = [item for item in controls if isinstance(item, CrossAppBudgetCard)]
        assert len(cards) == 1
        assert len(cross) == 2

    def test_cross_plan_goes_before_operations(self):
        view = _view([RENT], budgets=[TASK_BUDGET], mode=MODE_PLANNED)

        asyncio.run(view._load_data())
        kinds = [type(item) for item in view._tx_list.controls]

        assert kinds.index(CrossAppBudgetCard) < kinds.index(PlannedTransactionCard)

    def test_empty_plan_mode_has_empty_state(self):
        view = _view([], mode=MODE_PLANNED)

        asyncio.run(view._load_data())
        empties = [item for item in view._tx_list.controls if isinstance(item, EmptyState)]

        assert empties
        texts = [control.value for control in empties[0].content.controls if isinstance(control, ft.Text)]
        assert "Нет планов" in texts

    def test_budget_hint_when_offline(self):
        view = _view([RENT], budgets=[TASK_BUDGET], mode=MODE_PLANNED)
        view._transaction_view.is_online = False

        asyncio.run(view._load_data())

        assert "Нет подключения" in view._budget_hint

    def test_budget_failure_keeps_screen(self):
        view = _view([RENT], mode=MODE_PLANNED)
        view.api_client.list_budgets.side_effect = RestClientError("boom")

        asyncio.run(view._load_data())

        assert "Не удалось загрузить" in view._budget_hint


class TestTotals:
    def test_totals_in_base_currency(self):
        view = _view([LAPTOP, SALARY])

        asyncio.run(view._load_data())

        assert "Доход +" in view._totals.value
        assert "1 000.00" in view._totals.value
        assert "Расход −300.00" in view._totals.value
        assert "BYN" in view._totals.value

    def test_totals_convert_foreign_account(self):
        foreign = {
            "id": 4,
            "date": "2026-10-26T10:00:00",
            "description": "Фриланс",
            "is_planned": False,
            "entries": [{"account": 2, "amount": 100.0, "unit_price": 1}],
        }
        view = _view([foreign])

        asyncio.run(view._load_data())

        expected = 100 * 1.08 / 0.33
        assert f"+{expected:,.2f}".replace(",", " ") in view._totals.value

    def test_transfers_do_not_inflate_totals(self):
        transfer = {
            "id": 6,
            "date": "2026-10-27T10:00:00",
            "description": "Между счетами",
            "is_planned": False,
            "entries": [
                {"account": 1, "amount": -500.0, "unit_price": 1},
                {"account": 2, "amount": 500.0, "unit_price": 1},
            ],
        }
        view = _view([SALARY, transfer])

        asyncio.run(view._load_data())

        assert "Доход +1 000.00" in view._totals.value
        assert "Расход −0.00" in view._totals.value

    def test_plan_mode_clears_sticky_day_groups(self):
        view = _view([LAPTOP], mode=MODE_ACTUAL)
        asyncio.run(view._load_data())
        assert view._day_groups

        view.set_mode(MODE_PLANNED)

        assert view._day_groups == []
        assert view._pinned_header.visible is False

    def test_totals_convert_fiat_via_fx(self):
        usd_income = {
            "id": 7,
            "date": "2026-10-27T10:00:00",
            "description": "Фриланс в USD",
            "is_planned": False,
            "entries": [{"account": 4, "amount": 100.0, "unit_price": 1}],
        }
        view = _view([usd_income], prices=[], fx_rows=[{"base": "USD", "quote": "BYN", "rate": "0.3125"}])

        asyncio.run(view._load_data())

        assert "Доход +320.00" in view._totals.value

    def test_totals_hidden_without_base_currency(self):
        view = _view([SALARY], base_currency=None)

        asyncio.run(view._load_data())

        assert view._totals.value == ""

    def test_totals_note_missing_rate(self):
        unknown = {
            "id": 5,
            "date": "2026-10-26T10:00:00",
            "description": "Списание",
            "is_planned": False,
            "entries": [{"account": 3, "amount": -5.0}],
        }
        view = _view([unknown])

        asyncio.run(view._load_data())

        assert "курс недоступен" in view._totals.value


class TestActions:
    def test_fab_creates_actual_operation(self):
        view = _view()
        calls = []
        view._open_transaction_dialog = lambda tx=None, planned=False: calls.append(planned)

        view._show_add_dialog(None)

        assert calls == [False]

    def test_fab_creates_plan_in_plan_mode(self):
        view = _view(mode=MODE_PLANNED)
        calls = []
        view._open_transaction_dialog = lambda tx=None, planned=False: calls.append((tx, planned))

        view._show_add_dialog(None)

        assert calls == [(None, True)]

    def test_execute_plan_returns_to_actual_mode(self, monkeypatch):
        view = _view([RENT], mode=MODE_PLANNED)
        executed = []

        async def fake_execute(transaction_view, api_client, tx):
            executed.append(tx["id"])
            return None

        monkeypatch.setattr("application.view.operations_view.execute_planned", fake_execute)

        asyncio.run(view._load_data())
        asyncio.run(view._execute_plan(RENT))

        assert executed == [3]
        assert view._mode == MODE_ACTUAL
        assert view._segments.selected == [MODE_ACTUAL]

    def test_execute_plan_error_keeps_mode(self, monkeypatch):
        view = _view([RENT], mode=MODE_PLANNED)

        async def failing(*_args):
            raise RuntimeError("сеть")

        monkeypatch.setattr("application.view.operations_view.execute_planned", failing)

        asyncio.run(view._load_data())
        asyncio.run(view._execute_plan(RENT))

        assert view._mode == MODE_PLANNED
        assert "Ошибка проведения" in view._error_text.value


class TestRecurrenceEditor:
    def test_off_by_default(self):
        editor = RecurrenceEditor()

        assert editor.switch.value is False
        assert editor._row.visible is False
        assert editor.value == ""

    def test_enabled_monthly_rule(self):
        editor = RecurrenceEditor()
        editor.switch.value = True

        assert editor.value == "monthly"

    def test_interval_is_part_of_rule(self):
        editor = RecurrenceEditor("monthly every 2")

        assert editor.switch.value is True
        assert editor.frequency.value == "monthly"
        assert editor.interval.value == "2"
        assert editor.value == "monthly every 2"

    def test_bad_interval_falls_back_to_one(self):
        editor = RecurrenceEditor()
        editor.switch.value = True
        editor.frequency.value = "weekly"
        editor.interval.value = "abc"

        assert editor.value == "weekly"

    def test_invalid_rule_keeps_editor_off(self):
        editor = RecurrenceEditor("FREQ=MONTHLY")

        assert editor.switch.value is False

    def test_toggle_shows_hidden_row(self):
        editor = RecurrenceEditor()
        editor.update = MagicMock()

        editor._on_toggle(type("Event", (), {"control": type("Control", (), {"value": True})()})())

        assert editor._row.visible is True
        assert isinstance(editor._row, ft.ResponsiveRow)
