"""Регрессия бага 14.10.2026: диалог редактирования транзакции.

Карточка показывает итог `sum(entries.amount)` — диалог обязан загружать ровно
те же значения (сумма, тип, счёт) и сохранять их без правок (round-trip).
"""

import asyncio
import datetime
from unittest.mock import MagicMock

import flet as ft
from application.transaction_form import form_state, is_transfer
from application.view.planned_view import PlannedView
from application.view.transactions_view import TransactionsView

MAIN_ACCOUNT = {
    "id": 1,
    "name": "Основной",
    "resource": "USDT",
    "account_type": "main",
    "current_balance_qty": 100.0,
}
TRADE_ACCOUNT = {
    "id": 2,
    "name": "Торговый",
    "resource": "USDT",
    "account_type": "trading",
    "current_balance_qty": 50.0,
}
ACCOUNTS = [MAIN_ACCOUNT, TRADE_ACCOUNT]


def _entry(account: int, amount: float) -> dict:
    return {"id": 7, "account": account, "quantity": amount, "amount": amount, "unit_price": 1}


def _tx(entries: list[dict], **overrides) -> dict:
    tx = {
        "id": 42,
        "date": "2026-10-09T07:09:00",
        "description": "Покупка",
        "category": "Еда",
        "is_planned": False,
        "entries": entries,
    }
    tx.update(overrides)
    return tx


def _make_transactions_view(transactions=None) -> TransactionsView:
    transaction_view = MagicMock()
    transaction_view.is_online = True
    transaction_view.get_all.side_effect = lambda: list(transactions or [])
    account_view = MagicMock()
    account_view.is_online = True
    account_view.get_all.side_effect = lambda: list(ACCOUNTS)
    view = TransactionsView(
        route="/transactions",
        api_client=MagicMock(),
        transaction_view=transaction_view,
        account_view=account_view,
    )
    view.update = MagicMock()
    return view


def _make_planned_view(transactions=None) -> PlannedView:
    transaction_view = MagicMock()
    transaction_view.is_online = True
    transaction_view.get_all.side_effect = lambda: list(transactions or [])
    account_view = MagicMock()
    account_view.is_online = True
    account_view.get_all.side_effect = lambda: list(ACCOUNTS)
    api_client = MagicMock()
    api_client.list_budgets.return_value = []
    view = PlannedView(
        route="/planned",
        api_client=api_client,
        transaction_view=transaction_view,
        account_view=account_view,
    )
    view.update = MagicMock()
    return view


def _fake_page(view, monkeypatch) -> MagicMock:
    fake_page = MagicMock()
    monkeypatch.setattr(type(view), "page", property(lambda self: fake_page))
    return fake_page


def _open_transactions_dialog(view, tx, monkeypatch) -> ft.AlertDialog:
    fake_page = _fake_page(view, monkeypatch)
    view._open_transaction_dialog(tx=tx)
    return fake_page.show_dialog.call_args.args[0]


def _open_planned_dialog(view, tx, monkeypatch) -> ft.AlertDialog:
    fake_page = _fake_page(view, monkeypatch)
    view._open_transaction_dialog(tx=tx)
    return fake_page.show_dialog.call_args.args[0]


def _tx_dialog_controls(dialog) -> dict:
    controls = dialog.content.content.controls
    return {
        "type_group": controls[0],
        "account_dropdown": controls[1],
        "to_account_dropdown": controls[2],
        "amount_field": controls[3],
        "description_field": controls[4],
        "category_picker": controls[5],
        "date_field": controls[6],
    }


def _planned_dialog_controls(dialog) -> dict:
    controls = dialog.content.content.controls
    return {
        "type_group": controls[0],
        "account_dropdown": controls[1],
        "amount_field": controls[2],
        "description_field": controls[3],
        "category_picker": controls[4],
        "date_field": controls[5],
        "recurrence_switch": controls[6],
        "frequency_dropdown": controls[7],
        "interval_field": controls[8],
    }


def _submit(view, dialog) -> dict:
    save_button = dialog.actions[1]
    asyncio.run(save_button.on_click(None))
    view._transaction_view.update.assert_called_once()
    pk, payload = view._transaction_view.update.call_args.args
    assert pk == 42
    return payload


def _assert_entries_round_trip(payload_entries: list[dict], original_entries: list[dict]) -> None:
    assert [(e["account"], e["amount"]) for e in payload_entries] == [
        (e["account"], e["amount"]) for e in original_entries
    ]
    for entry in payload_entries:
        assert entry["quantity"] == entry["amount"]
        assert entry["unit_price"] == 1


class TestFormState:
    def test_income_single_entry(self) -> None:
        state = form_state([_entry(1, 7.23)])
        assert state.tx_type == "income"
        assert state.amount_text == "7.23"
        assert state.account_id == "1"
        assert state.to_account_id is None

    def test_expense_single_entry(self) -> None:
        state = form_state([_entry(1, -850.0)])
        assert state.tx_type == "expense"
        assert state.amount_text == "850.00"

    def test_tiny_amount_single_entry(self) -> None:
        state = form_state([_entry(1, 1e-12)])
        assert state.tx_type == "income"
        assert state.amount_text == "0.000000000001"
        assert float(state.amount_text) == 1e-12

    def test_negative_tiny_amount_is_expense(self) -> None:
        state = form_state([_entry(1, -1e-12)])
        assert state.tx_type == "expense"
        assert float(state.amount_text) == 1e-12

    def test_transfer_balanced_pair(self) -> None:
        state = form_state([_entry(1, -50.0), _entry(2, 50.0)])
        assert state.tx_type == "transfer"
        assert state.amount_text == "50.00"
        assert state.account_id == "1"
        assert state.to_account_id == "2"

    def test_transfer_order_independent(self) -> None:
        state = form_state([_entry(2, 50.0), _entry(1, -50.0)])
        assert state.tx_type == "transfer"
        assert state.account_id == "1"
        assert state.to_account_id == "2"

    def test_mixed_exchange_is_not_transfer(self) -> None:
        state = form_state([_entry(1, -1.0), _entry(2, 90.0)])
        assert state.tx_type == "income"
        assert float(state.amount_text) == 89.0

    def test_okx_snapshot_multi_entry_matches_card_total(self) -> None:
        entries = [
            {"id": 1, "account": 2, "quantity": 1e-12, "amount": 1e-12, "unit_price": 1},
            {"id": 2, "account": 1, "quantity": 7.23 - 1e-12, "amount": 7.23 - 1e-12, "unit_price": 1},
        ]
        card_total = sum(float(e["amount"]) for e in entries)
        state = form_state(entries)
        assert state.tx_type == "income"
        assert float(state.amount_text) == card_total

    def test_multi_entry_negative_total_is_expense(self) -> None:
        state = form_state([_entry(2, -7.0), _entry(1, -0.23)])
        assert state.tx_type == "expense"
        assert float(state.amount_text) == 7.23

    def test_allow_transfer_false_keeps_sign_type(self) -> None:
        state = form_state([_entry(1, -50.0), _entry(2, 50.0)], allow_transfer=False)
        assert state.tx_type == "income"
        assert state.to_account_id is None

    def test_empty_entries(self) -> None:
        state = form_state([])
        assert state.tx_type == "income"
        assert state.account_id == ""

    def test_is_transfer_same_account_rejected(self) -> None:
        assert not is_transfer([_entry(1, -50.0), _entry(1, 50.0)])

    def test_is_transfer_single_entry_rejected(self) -> None:
        assert not is_transfer([_entry(1, 0.0)])


class TestEditDialogLoad:
    def test_okx_snapshot_amount_matches_card_not_first_entry(self, monkeypatch) -> None:
        entries = [
            {"id": 1, "account": 2, "quantity": 1e-12, "amount": 1e-12, "unit_price": 1},
            {"id": 2, "account": 1, "quantity": 7.23 - 1e-12, "amount": 7.23 - 1e-12, "unit_price": 1},
        ]
        view = _make_transactions_view()
        tx = _tx(entries, description="okx: snapshot 2026-10-09 07:09")
        dialog = _open_transactions_dialog(view, tx, monkeypatch)
        controls = _tx_dialog_controls(dialog)
        card_total = sum(float(e["amount"]) for e in entries)
        assert float(controls["amount_field"].value) == card_total
        assert controls["amount_field"].value != "0.000000000001"

    def test_okx_snapshot_type_is_income(self, monkeypatch) -> None:
        entries = [
            {"id": 1, "account": 2, "quantity": 1e-12, "amount": 1e-12, "unit_price": 1},
            {"id": 2, "account": 1, "quantity": 7.23 - 1e-12, "amount": 7.23 - 1e-12, "unit_price": 1},
        ]
        view = _make_transactions_view()
        dialog = _open_transactions_dialog(view, _tx(entries), monkeypatch)
        assert _tx_dialog_controls(dialog)["type_group"].value == "income"

    def test_expense_type_and_amount(self, monkeypatch) -> None:
        view = _make_transactions_view()
        dialog = _open_transactions_dialog(view, _tx([_entry(2, -126.4)]), monkeypatch)
        controls = _tx_dialog_controls(dialog)
        assert controls["type_group"].value == "expense"
        assert controls["amount_field"].value == "126.40"
        assert controls["account_dropdown"].value == "2"

    def test_transfer_preselects_both_accounts_and_shows_to_field(self, monkeypatch) -> None:
        view = _make_transactions_view()
        dialog = _open_transactions_dialog(view, _tx([_entry(1, -50.0), _entry(2, 50.0)]), monkeypatch)
        controls = _tx_dialog_controls(dialog)
        assert controls["type_group"].value == "transfer"
        assert controls["account_dropdown"].value == "1"
        assert controls["to_account_dropdown"].visible is True
        assert controls["to_account_dropdown"].value == "2"
        assert controls["amount_field"].value == "50.00"

    def test_tiny_single_entry_income(self, monkeypatch) -> None:
        view = _make_transactions_view()
        dialog = _open_transactions_dialog(view, _tx([_entry(1, 1e-12)]), monkeypatch)
        controls = _tx_dialog_controls(dialog)
        assert controls["amount_field"].value == "0.000000000001"
        assert controls["type_group"].value == "income"

    def test_add_dialog_keeps_default_type(self, monkeypatch) -> None:
        view = _make_transactions_view()
        fake_page = _fake_page(view, monkeypatch)
        view._open_transaction_dialog()
        dialog = fake_page.show_dialog.call_args.args[0]
        controls = _tx_dialog_controls(dialog)
        assert controls["type_group"].value == "expense"
        assert controls["to_account_dropdown"].visible is False


class TestSaveRoundTrip:
    def test_roundtrip_income_single_entry_plus_7_23(self, monkeypatch) -> None:
        tx = _tx([_entry(1, 7.23)])
        view = _make_transactions_view()
        dialog = _open_transactions_dialog(view, tx, monkeypatch)
        payload = _submit(view, dialog)
        _assert_entries_round_trip(payload["entries"], tx["entries"])
        assert payload["entries"][0]["amount"] == 7.23
        assert payload["description"] == "Покупка"
        assert payload["category"] == "Еда"
        assert payload["is_planned"] is False
        assert datetime.datetime.fromisoformat(payload["date"]) == datetime.datetime.fromisoformat(tx["date"])

    def test_roundtrip_expense_single_entry(self, monkeypatch) -> None:
        tx = _tx([_entry(2, -850.0)])
        view = _make_transactions_view()
        dialog = _open_transactions_dialog(view, tx, monkeypatch)
        payload = _submit(view, dialog)
        _assert_entries_round_trip(payload["entries"], tx["entries"])
        assert payload["entries"][0]["amount"] == -850.0

    def test_roundtrip_transfer_two_entries(self, monkeypatch) -> None:
        tx = _tx([_entry(1, -50.0), _entry(2, 50.0)], description="Перевод", category="")
        view = _make_transactions_view()
        dialog = _open_transactions_dialog(view, tx, monkeypatch)
        payload = _submit(view, dialog)
        _assert_entries_round_trip(payload["entries"], tx["entries"])
        assert [e["account"] for e in payload["entries"]] == [1, 2]

    def test_roundtrip_tiny_amount_1e_12(self, monkeypatch) -> None:
        tx = _tx([_entry(1, 1e-12)])
        view = _make_transactions_view()
        dialog = _open_transactions_dialog(view, tx, monkeypatch)
        payload = _submit(view, dialog)
        _assert_entries_round_trip(payload["entries"], tx["entries"])
        assert payload["entries"][0]["amount"] == 1e-12

    def test_roundtrip_negative_tiny_amount(self, monkeypatch) -> None:
        tx = _tx([_entry(1, -1e-12)])
        view = _make_transactions_view()
        dialog = _open_transactions_dialog(view, tx, monkeypatch)
        payload = _submit(view, dialog)
        _assert_entries_round_trip(payload["entries"], tx["entries"])
        assert payload["entries"][0]["amount"] == -1e-12

    def test_roundtrip_keeps_time_component(self, monkeypatch) -> None:
        tx = _tx([_entry(1, 12.5)], date="2026-10-09T21:45:30")
        view = _make_transactions_view()
        dialog = _open_transactions_dialog(view, tx, monkeypatch)
        payload = _submit(view, dialog)
        assert payload["date"] == "2026-10-09T21:45:30"

    def test_opening_and_saving_does_not_flip_income_to_expense(self, monkeypatch) -> None:
        tx = _tx([_entry(1, 7.23)], description="okx: snapshot 2026-10-09 07:09", category="")
        view = _make_transactions_view()
        dialog = _open_transactions_dialog(view, tx, monkeypatch)
        controls = _tx_dialog_controls(dialog)
        assert controls["type_group"].value == "income"
        payload = _submit(view, dialog)
        assert payload["entries"][0]["amount"] > 0


class TestPlannedDialogRoundTrip:
    def test_planned_amount_matches_card_total(self, monkeypatch) -> None:
        view = _make_planned_view()
        tx = _tx([_entry(1, -5.0)], is_planned=True, date="2026-10-20")
        dialog = _open_planned_dialog(view, tx, monkeypatch)
        controls = _planned_dialog_controls(dialog)
        assert controls["amount_field"].value == "5.00"
        assert controls["type_group"].value == "expense"

    def test_planned_multi_entry_income_type(self, monkeypatch) -> None:
        entries = [
            {"id": 1, "account": 2, "quantity": 1e-12, "amount": 1e-12, "unit_price": 1},
            {"id": 2, "account": 1, "quantity": 7.23 - 1e-12, "amount": 7.23 - 1e-12, "unit_price": 1},
        ]
        view = _make_planned_view()
        dialog = _open_planned_dialog(view, _tx(entries, is_planned=True), monkeypatch)
        controls = _planned_dialog_controls(dialog)
        card_total = sum(float(e["amount"]) for e in entries)
        assert float(controls["amount_field"].value) == card_total
        assert controls["type_group"].value == "income"

    def test_planned_roundtrip_income(self, monkeypatch) -> None:
        tx = _tx([_entry(1, 7.23)], is_planned=True, date="2026-10-20", description="Зарплата", category="Зарплата")
        view = _make_planned_view()
        dialog = _open_planned_dialog(view, tx, monkeypatch)
        payload = _submit(view, dialog)
        _assert_entries_round_trip(payload["entries"], tx["entries"])
        assert payload["is_planned"] is True
        assert payload["description"] == "Зарплата"
        assert payload["category"] == "Зарплата"
        assert datetime.datetime.fromisoformat(payload["date"]).date() == datetime.date(2026, 10, 20)

    def test_planned_roundtrip_expense(self, monkeypatch) -> None:
        tx = _tx([_entry(2, -126.4)], is_planned=True, date="2026-10-21")
        view = _make_planned_view()
        dialog = _open_planned_dialog(view, tx, monkeypatch)
        payload = _submit(view, dialog)
        _assert_entries_round_trip(payload["entries"], tx["entries"])
        assert payload["entries"][0]["amount"] == -126.4

    def test_planned_roundtrip_recurrence(self, monkeypatch) -> None:
        tx = _tx([_entry(1, -5.0)], is_planned=True, date="2026-10-20", recurrence_rule="monthly every 2")
        view = _make_planned_view()
        dialog = _open_planned_dialog(view, tx, monkeypatch)
        controls = _planned_dialog_controls(dialog)
        assert controls["recurrence_switch"].value is True
        assert controls["frequency_dropdown"].value == "monthly"
        assert controls["interval_field"].value == "2"
        payload = _submit(view, dialog)
        assert payload["recurrence_rule"] == "monthly every 2"

    def test_planned_roundtrip_tiny_amount(self, monkeypatch) -> None:
        tx = _tx([_entry(1, 1e-12)], is_planned=True, date="2026-10-20")
        view = _make_planned_view()
        dialog = _open_planned_dialog(view, tx, monkeypatch)
        payload = _submit(view, dialog)
        _assert_entries_round_trip(payload["entries"], tx["entries"])
        assert payload["entries"][0]["amount"] == 1e-12
