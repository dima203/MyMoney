"""Регрессионные тесты багов 4.4–4.7: названия счетов, валюты строк, формат суммы, FAB."""

import asyncio
from unittest.mock import MagicMock

import flet as ft
import pytest
from application.components.transaction_card import TransactionCard
from application.demo_seed import DEMO_ACCOUNTS
from application.display import FAB_CLEARANCE, account_display_name, format_amount_input
from application.view.accounts_view import AccountsView
from application.view.planned_view import PlannedView
from application.view.transactions_view import TransactionsView
from core.onboarding import OnboardingState

OKX_ACCOUNT = {
    "id": 10,
    "name": "",
    "resource_definition": 1,
    "resource": "BTC",
    "group": "",
    "account_type": "trading",
    "current_balance_qty": 0.08,
}

BTC_RESOURCE = {"id": 1, "name": "Биткоин", "ticker": "BTC-USDT", "resource_type": "currency"}


def _texts(control) -> list[str]:
    found: list[str] = []
    if isinstance(control, ft.Text) and control.value is not None:
        found.append(str(control.value))
    content = getattr(control, "content", None)
    if isinstance(content, str):
        found.append(content)
    elif content is not None:
        found.extend(_texts(content))
    for child in getattr(control, "controls", None) or []:
        found.extend(_texts(child))
    return found


def _make_accounts_view(tmp_path, *, resources=None, accounts=None) -> AccountsView:
    onboarding = OnboardingState(path=tmp_path / "onboarding.json")
    resource_view = MagicMock()
    resource_view.is_online = True
    resource_view.get_all.side_effect = lambda: list(resources or [])
    account_view = MagicMock()
    account_view.is_online = True
    account_view.get_all.side_effect = lambda: list(accounts or [])
    view = AccountsView(
        route="/accounts",
        api_client=MagicMock(),
        resource_view=resource_view,
        account_view=account_view,
        onboarding=onboarding,
    )
    view.update = MagicMock()
    return view


def _make_transactions_view(*, accounts=None, transactions=None) -> TransactionsView:
    transaction_view = MagicMock()
    transaction_view.is_online = True
    transaction_view.get_all.side_effect = lambda: list(transactions or [])
    account_view = MagicMock()
    account_view.is_online = True
    account_view.get_all.side_effect = lambda: list(accounts or [])
    view = TransactionsView(
        route="/transactions",
        api_client=MagicMock(),
        transaction_view=transaction_view,
        account_view=account_view,
    )
    view.update = MagicMock()
    return view


def _make_planned_view(*, accounts=None, transactions=None) -> PlannedView:
    transaction_view = MagicMock()
    transaction_view.is_online = True
    transaction_view.get_all.side_effect = lambda: list(transactions or [])
    account_view = MagicMock()
    account_view.is_online = True
    account_view.get_all.side_effect = lambda: list(accounts or [])
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


class TestAccountDisplayName:
    def test_named_account_is_kept(self) -> None:
        assert account_display_name({"name": "Наличные"}) == "Наличные"

    def test_blank_name_falls_back_to_resource_and_type(self) -> None:
        account = {"name": "  ", "account_type": "trading"}
        assert account_display_name(account, "Биткоин") == "Биткоин (торговый)"

    def test_fallback_uses_account_resource_unit(self) -> None:
        account = {"name": "", "resource": "BTC", "account_type": "main"}
        assert account_display_name(account) == "BTC (основной)"

    def test_missing_type_has_no_suffix(self) -> None:
        assert account_display_name({"name": "", "resource": "USD"}) == "USD"

    def test_unknown_account_is_dash(self) -> None:
        assert account_display_name({}) == "—"

    def test_case_insensitive_type(self) -> None:
        account = {"name": None, "resource": "USDT", "account_type": "EARN"}
        assert account_display_name(account) == "USDT (доходный)"


class TestFormatAmountInput:
    def test_tiny_value_has_no_scientific_notation(self) -> None:
        assert format_amount_input(1e-12) == "0.000000000001"

    def test_three_decimals_kept(self) -> None:
        assert format_amount_input(0.005) == "0.005"

    def test_large_value(self) -> None:
        assert format_amount_input(1234567.89) == "1234567.89"

    def test_zero_gets_two_decimals(self) -> None:
        assert format_amount_input(0) == "0.00"

    def test_single_decimal_padded(self) -> None:
        assert format_amount_input(1.5) == "1.50"

    def test_negative_is_absolute(self) -> None:
        assert format_amount_input(-850.0) == "850.00"

    @pytest.mark.parametrize(
        "value",
        [1e-12, 1e-13, 0.005, 0.0045, 0.1, 1.5, 850.0, 1234567.89, 1e15],
    )
    def test_round_trip_parses_back(self, value: float) -> None:
        text = format_amount_input(value)
        assert "e" not in text.lower()
        assert float(text) == value


class TestAccountsViewNameFallback:
    def test_nameless_okx_account_shows_fallback(self, tmp_path) -> None:
        view = _make_accounts_view(tmp_path, resources=[BTC_RESOURCE], accounts=[OKX_ACCOUNT])
        asyncio.run(view._load_data())
        texts = _texts(view._accounts_column)
        assert "Биткоин (торговый)" in texts

    def test_named_account_shows_original_name(self, tmp_path) -> None:
        account = {**OKX_ACCOUNT, "name": "Мой счёт"}
        view = _make_accounts_view(tmp_path, resources=[BTC_RESOURCE], accounts=[account])
        asyncio.run(view._load_data())
        texts = _texts(view._accounts_column)
        assert "Мой счёт" in texts
        assert "Биткоин (торговый)" not in texts

    def test_fab_clearance_spacer_is_last(self, tmp_path) -> None:
        view = _make_accounts_view(tmp_path, resources=[BTC_RESOURCE], accounts=[OKX_ACCOUNT])
        asyncio.run(view._load_data())
        last = view._accounts_column.controls[-1]
        assert isinstance(last, ft.Container)
        assert last.height == FAB_CLEARANCE


class TestTransactionsViewRows:
    def _tx(self, amount: float, account_id: int = 10) -> dict:
        return {
            "id": 1,
            "date": "2026-10-12T12:00:00",
            "description": "Покупка",
            "category": "Другое",
            "entries": [{"account": account_id, "amount": amount}],
        }

    def test_row_shows_currency_and_fallback_account_name(self) -> None:
        view = _make_transactions_view(accounts=[OKX_ACCOUNT], transactions=[self._tx(0.08)])
        asyncio.run(view._load_data())
        texts = _texts(view._tx_list)
        assert "+0.08 BTC" in texts
        assert "BTC (торговый)" in texts

    def test_negative_amount_shows_currency(self) -> None:
        view = _make_transactions_view(accounts=[OKX_ACCOUNT], transactions=[self._tx(-126.4)])
        asyncio.run(view._load_data())
        assert "-126.40 BTC" in _texts(view._tx_list)

    def test_unknown_account_shows_dash(self) -> None:
        view = _make_transactions_view(accounts=[OKX_ACCOUNT], transactions=[self._tx(5.0, account_id=999)])
        asyncio.run(view._load_data())
        assert "—" in _texts(view._tx_list)

    def test_transfer_same_currency_shows_unit(self) -> None:
        second_account = {**OKX_ACCOUNT, "id": 11, "resource": "BTC", "account_type": "main", "name": ""}
        transfer = {
            "id": 3,
            "date": "2026-10-12T12:00:00",
            "description": "Перевод",
            "category": "",
            "entries": [
                {"account": 10, "amount": -1.0},
                {"account": 11, "amount": 1.0},
            ],
        }
        view = _make_transactions_view(accounts=[OKX_ACCOUNT, second_account], transactions=[transfer])
        asyncio.run(view._load_data())
        assert "+0.00 BTC" in _texts(view._tx_list)

    def test_mixed_currency_transfer_has_no_suffix(self) -> None:
        eur_account = {**OKX_ACCOUNT, "id": 11, "resource": "EUR", "account_type": "main", "name": ""}
        transfer = {
            "id": 4,
            "date": "2026-10-12T12:00:00",
            "description": "Обмен",
            "category": "",
            "entries": [
                {"account": 10, "amount": -1.0},
                {"account": 11, "amount": 90.0},
            ],
        }
        view = _make_transactions_view(accounts=[OKX_ACCOUNT, eur_account], transactions=[transfer])
        asyncio.run(view._load_data())
        texts = _texts(view._tx_list)
        assert "+89.00" in texts
        assert not any(text.endswith(("BTC", "EUR")) for text in texts if text.startswith("+"))

    def test_fab_clearance_spacer_is_last(self) -> None:
        view = _make_transactions_view(accounts=[OKX_ACCOUNT], transactions=[self._tx(0.08)])
        asyncio.run(view._load_data())
        last = view._tx_list.controls[-1]
        assert isinstance(last, ft.Container)
        assert last.height == FAB_CLEARANCE

    def test_transaction_card_appends_currency(self) -> None:
        card = TransactionCard(description="x", amount=-1.0, account_name="A", currency="USD")
        assert card._amount_text.value == "-1.00 USD"

    def test_transaction_card_without_currency(self) -> None:
        card = TransactionCard(description="x", amount=2.0, account_name="A")
        assert card._amount_text.value == "+2.00"


class TestTransactionsEditDialog:
    def _tx(self, amount: float) -> dict:
        return {
            "id": 1,
            "date": "2026-10-12T12:00:00",
            "description": "Микро",
            "category": "",
            "entries": [{"account": 10, "amount": amount}],
        }

    def _open_dialog(self, view, tx, monkeypatch):
        fake_page = _fake_page(view, monkeypatch)
        view._open_transaction_dialog(tx=tx)
        dialog = fake_page.show_dialog.call_args.args[0]
        return dialog

    def _amount_field(self, dialog) -> ft.TextField:
        return dialog.content.content.controls[3]

    def test_tiny_amount_not_scientific(self, monkeypatch) -> None:
        view = _make_transactions_view(accounts=[OKX_ACCOUNT])
        dialog = self._open_dialog(view, self._tx(1e-12), monkeypatch)
        assert self._amount_field(dialog).value == "0.000000000001"

    def test_regular_amount_round_trip(self, monkeypatch) -> None:
        view = _make_transactions_view(accounts=[OKX_ACCOUNT])
        dialog = self._open_dialog(view, self._tx(1234567.89), monkeypatch)
        field = self._amount_field(dialog)
        assert field.value == "1234567.89"
        assert float(field.value) == 1234567.89

    def test_account_dropdown_uses_fallback_names(self, monkeypatch) -> None:
        view = _make_transactions_view(accounts=[OKX_ACCOUNT])
        asyncio.run(view._load_data())
        dialog = self._open_dialog(view, self._tx(1.0), monkeypatch)
        options = dialog.content.content.controls[1].options
        assert [option.text for option in options] == ["BTC (торговый)"]


class TestDemoSeederNames:
    def test_demo_accounts_all_have_names(self) -> None:
        for spec in DEMO_ACCOUNTS:
            assert spec["name"].strip()


class TestPlannedViewFallbacks:
    def test_nameless_account_shows_fallback(self) -> None:
        planned = {
            "id": 2,
            "date": "2026-10-20",
            "description": "План",
            "category": "",
            "is_planned": True,
            "entries": [{"account": 10, "amount": -5.0}],
        }
        view = _make_planned_view(accounts=[OKX_ACCOUNT], transactions=[planned])
        asyncio.run(view._load_data())
        texts = _texts(view._tx_list)
        assert "BTC (торговый)" in texts

    def test_fab_clearance_spacer_is_last(self) -> None:
        view = _make_planned_view()
        last = view._scroll_column.controls[-1]
        assert isinstance(last, ft.Container)
        assert last.height == FAB_CLEARANCE

    def _open_dialog(self, view, tx, monkeypatch):
        fake_page = _fake_page(view, monkeypatch)
        view._open_transaction_dialog(tx=tx)
        return fake_page.show_dialog.call_args.args[0]

    def test_dialog_amount_not_scientific(self, monkeypatch) -> None:
        view = _make_planned_view(accounts=[OKX_ACCOUNT])
        view._accounts = [OKX_ACCOUNT]
        tx = {
            "id": 3,
            "date": "2026-10-20",
            "description": "План",
            "category": "",
            "is_planned": True,
            "entries": [{"account": 10, "amount": 1e-12}],
        }
        dialog = self._open_dialog(view, tx, monkeypatch)
        assert dialog.content.content.controls[2].value == "0.000000000001"

    def test_dialog_account_dropdown_uses_fallback_names(self, monkeypatch) -> None:
        view = _make_planned_view(accounts=[OKX_ACCOUNT])
        view._accounts = [OKX_ACCOUNT]
        dialog = self._open_dialog(view, None, monkeypatch)
        options = dialog.content.content.controls[1].options
        assert [option.text for option in options] == ["BTC (торговый)"]


class TestPlannedViewReadOnlySnapshots:
    def _tx(self, **overrides) -> dict:
        tx = {
            "id": 7,
            "date": "2026-10-12",
            "description": "okx: snapshot 2026-10-12 07:00",
            "category": "OKX",
            "is_planned": False,
            "entries": [{"account": 10, "amount": 0.5, "unit_price": 1}],
        }
        tx.update(overrides)
        return tx

    def test_snapshot_not_shown_in_planned(self) -> None:
        view = _make_planned_view(accounts=[OKX_ACCOUNT], transactions=[self._tx()])
        asyncio.run(view._load_data())
        assert view._transactions == []

    def test_read_only_planned_row_is_hidden(self) -> None:
        tx = self._tx(is_planned=True, read_only=True)
        view = _make_planned_view(accounts=[OKX_ACCOUNT], transactions=[tx])
        asyncio.run(view._load_data())
        assert view._transactions == []

    def test_editable_planned_row_is_shown(self) -> None:
        tx = self._tx(description="Зарплата", is_planned=True, read_only=False)
        view = _make_planned_view(accounts=[OKX_ACCOUNT], transactions=[tx])
        asyncio.run(view._load_data())
        assert len(view._transactions) == 1
