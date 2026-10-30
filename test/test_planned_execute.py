import asyncio
from datetime import date
from unittest.mock import MagicMock

from application.view.planned_view import PlannedView
from core.recurrence import next_planned_date


def _view():
    transaction_view = MagicMock()
    transaction_view.is_online = True
    transaction_view.get_all.return_value = []
    account_view = MagicMock()
    account_view.is_online = True
    account_view.get_all.return_value = []
    api_client = MagicMock()
    api_client.list_budgets.return_value = []
    view = PlannedView(
        route="/planned",
        api_client=api_client,
        transaction_view=transaction_view,
        account_view=account_view,
    )
    view.update = MagicMock()

    async def noop():
        return None

    view._load_data = noop
    return view, transaction_view


def _tx(**overrides):
    tx = {
        "id": 5,
        "date": "2026-01-01T09:30:00",
        "description": "Аренда",
        "category": "Жильё",
        "recurrence_rule": "monthly",
        "entries": [{"account": 1, "amount": -100.0}],
    }
    tx.update(overrides)
    return tx


def test_recurring_plan_shifts_date_instead_of_staying_overdue():
    view, transaction_view = _view()

    asyncio.run(view._execute_transaction(_tx()))

    transaction_view.add.assert_called_once()
    transaction_view.delete.assert_not_called()
    tx_id, payload = transaction_view.update.call_args.args
    expected = next_planned_date(date(2026, 1, 1), "monthly")
    assert tx_id == 5
    assert payload["date"] == f"{expected.isoformat()}T09:30:00"
    assert expected > date.today()


def test_single_plan_is_deleted_after_execution():
    view, transaction_view = _view()

    asyncio.run(view._execute_transaction(_tx(recurrence_rule="")))

    transaction_view.add.assert_called_once()
    transaction_view.delete.assert_called_once_with(5)
    transaction_view.update.assert_not_called()


def test_finished_series_is_deleted(monkeypatch):
    view, transaction_view = _view()
    monkeypatch.setattr("application.planned_actions.next_planned_date", lambda *_args: None)

    asyncio.run(view._execute_transaction(_tx(recurrence_rule="daily until 2026-01-02")))

    transaction_view.delete.assert_called_once_with(5)
    transaction_view.update.assert_not_called()


def test_api_client_fallback_without_offline_view():
    transaction_view = MagicMock()
    transaction_view.is_online = True
    transaction_view.get_all.return_value = []
    account_view = MagicMock()
    account_view.is_online = True
    account_view.get_all.return_value = []
    api_client = MagicMock()
    api_client.list_budgets.return_value = []
    view = PlannedView(route="/planned", api_client=api_client, transaction_view=None, account_view=account_view)
    view.update = MagicMock()

    async def noop():
        return None

    view._load_data = noop

    asyncio.run(view._execute_transaction(_tx()))

    api_client.create_transaction.assert_called_once()
    api_client.update_transaction.assert_called_once()
    api_client.delete_transaction.assert_not_called()


def test_bad_date_falls_back_to_today_time():
    view, transaction_view = _view()

    asyncio.run(view._execute_transaction(_tx(date="мусор")))

    _, payload = transaction_view.update.call_args.args
    assert "T09:00:00" in payload["date"]
