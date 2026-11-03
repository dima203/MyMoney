"""2.160b: подтверждение перевода карта ↔ OKX в «Операциях»."""

import asyncio
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import flet as ft
import pytest
from application.api import RestClientError
from application.components.transaction_card import TransactionCard
from application.fx_rates import FxRateStore
from application.view.operations_view import (
    TRANSFER_BADGE_HINT,
    TRANSFER_BADGE_MANUAL,
    TRANSFER_EMPTY_HINT,
    TRANSFER_LINK_LABEL,
    TRANSFER_MANUAL_LABEL,
    OperationsView,
)

ACCOUNTS = [
    {"id": 1, "name": "Карта", "resource": "BYN", "account_type": "main"},
    {"id": 2, "name": "OKX", "resource": "USDT", "account_type": "main", "group": "OKX"},
]
OKX_TX = {
    "id": 10,
    "date": "2026-11-03T10:00:00",
    "description": "okx: ввод bill-1",
    "category": "OKX: ввод",
    "is_planned": False,
    "source": "okx",
    "kind": "operation",
    "read_only": True,
    "entries": [{"account": 2, "amount": 100.0, "unit_price": 1}],
}
CARD_TX = {
    "id": 11,
    "date": "2026-11-03T09:00:00",
    "description": "Списание с карты",
    "category": "Перевод",
    "is_planned": False,
    "kind": "operation",
    "entries": [{"account": 1, "amount": -320.0, "unit_price": 1}],
}
SUGGESTION = {
    "okx_transaction": 10,
    "date": "2026-11-03T10:00:00",
    "direction": "deposit",
    "amount_base": "100.00",
    "candidates": [
        {
            "id": 11,
            "date": "2026-11-03T09:00:00",
            "amount": "-100.00",
            "account": 1,
            "account_name": "Карта",
            "diff_percent": "0.00",
        }
    ],
}


@pytest.fixture(autouse=True)
def _no_update(monkeypatch) -> None:
    monkeypatch.setattr(ft.Control, "update", lambda self, *args, **kwargs: None)


def _view(*, transactions=None, suggestions=None, online=True, mode="actual"):
    transaction_view = MagicMock()
    transaction_view.is_online = online
    transaction_view.get_all.return_value = list(transactions or [OKX_TX, CARD_TX])
    account_view = MagicMock()
    account_view.is_online = online
    account_view.get_all.return_value = list(ACCOUNTS)
    api_client = MagicMock()
    api_client.list_budgets.return_value = []
    api_client.me.return_value = {"base_currency": "BYN"}
    api_client.get_prices.return_value = []
    api_client.get_fx_rates.return_value = []
    api_client.list_okx_transfer_suggestions.return_value = suggestions or {"items": [], "unmatched": []}
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


def _walk(control):
    yield control
    for child in getattr(control, "controls", None) or []:
        yield from _walk(child)
    content = getattr(control, "content", None)
    if content is not None:
        yield from _walk(content)


def _texts(control) -> list[str]:
    return [str(item.value) for item in _walk(control) if isinstance(item, ft.Text)]


def _radio_labels(control) -> list[str]:
    return [str(item.label) for item in _walk(control) if isinstance(item, ft.Radio)]


class TestCardActions:
    def test_candidates_give_hint_badge_and_link_action(self):
        view = _view()
        view._transfer_suggestions = {10: SUGGESTION}

        card = view._build_card(OKX_TX)

        assert card._badge == TRANSFER_BADGE_HINT
        menu = next(item for item in _walk(card) if isinstance(item, ft.PopupMenuButton))
        assert [item.content for item in menu.items] == ["Категория", TRANSFER_LINK_LABEL]

    def test_no_candidates_give_manual_badge_and_action(self):
        view = _view()
        view._transfer_suggestions = {10: {**SUGGESTION, "candidates": []}}

        card = view._build_card(OKX_TX)

        assert card._badge == TRANSFER_BADGE_MANUAL
        menu = next(item for item in _walk(card) if isinstance(item, ft.PopupMenuButton))
        assert [item.content for item in menu.items] == ["Категория", TRANSFER_MANUAL_LABEL]

    def test_regular_transaction_has_no_transfer_action(self):
        view = _view()
        view._transfer_suggestions = {10: SUGGESTION}

        card = view._build_card(CARD_TX)

        labels = [item.content for item in _walk(card) if isinstance(item, ft.PopupMenuItem)]
        assert TRANSFER_LINK_LABEL not in labels


class TestSuggestionsLoading:
    def test_online_loads_map(self):
        view = _view(suggestions={"items": [SUGGESTION], "unmatched": []})

        asyncio.run(view._load_data())

        assert set(view._transfer_suggestions) == {10}
        cards = [control for control in _walk(view._tx_list) if isinstance(control, TransactionCard)]
        assert any(card._badge == TRANSFER_BADGE_HINT for card in cards)

    def test_offline_does_not_request_suggestions(self):
        view = _view(online=False)

        asyncio.run(view._load_data())

        assert view._transfer_suggestions == {}
        view.api_client.list_okx_transfer_suggestions.assert_not_called()


class TestTransferDialog:
    def _page(self, monkeypatch, view):
        page = MagicMock()
        monkeypatch.setattr(type(view), "page", property(lambda _self: page), raising=False)
        return page

    def test_dialog_lists_candidates_and_links(self, monkeypatch):
        view = _view()
        page = self._page(monkeypatch, view)
        view._load_data = AsyncMock()
        scheduled: list = []
        monkeypatch.setattr(
            "application.view.operations_view.asyncio.create_task",
            lambda coro: scheduled.append(coro) or MagicMock(),
        )

        view._show_transfer_dialog(OKX_TX, SUGGESTION)
        dialog = page.show_dialog.call_args.args[0]
        labels = _radio_labels(dialog)
        assert any("Карта" in label and "0.00 %" in label for label in labels)
        dialog.actions[1].on_click(None)
        asyncio.run(scheduled[0])

        view.api_client.link_okx_transfer.assert_called_once_with(10, 11)
        page.pop_dialog.assert_called_once()
        view._load_data.assert_awaited_once()

    def test_dialog_empty_candidates_shows_hint_and_manual_window(self, monkeypatch):
        view = _view()
        page = self._page(monkeypatch, view)
        asyncio.run(view._load_data())

        view._show_transfer_dialog(OKX_TX, {**SUGGESTION, "candidates": []})

        dialog = page.show_dialog.call_args.args[0]
        assert TRANSFER_EMPTY_HINT in _texts(dialog)
        radios = [control for control in _walk(dialog) if isinstance(control, ft.Radio)]
        assert [radio.value for radio in radios] == ["11"]

    def test_manual_window_ignores_okx_planned_and_old_rows(self):
        old = {**CARD_TX, "id": 21, "date": "2026-10-01T09:00:00"}
        okx_row = {**OKX_TX, "id": 22}
        planned = {**CARD_TX, "id": 23, "is_planned": True}
        view = _view(transactions=[OKX_TX, CARD_TX, old, okx_row, planned])
        asyncio.run(view._load_data())

        rows = view._manual_operations(OKX_TX)

        assert [row["id"] for row in rows] == [11]

    def test_offline_dialog_toasts_and_does_not_open(self, monkeypatch):
        view = _view(online=False)
        page = self._page(monkeypatch, view)
        toasts: list[str] = []
        monkeypatch.setattr("application.view.operations_view.show_toast", lambda page, text: toasts.append(text))

        view._show_transfer_dialog(OKX_TX, SUGGESTION)

        assert toasts == ["Нужен сервер"]
        page.show_dialog.assert_not_called()

    def test_link_error_is_shown_and_dialog_stays(self, monkeypatch):
        view = _view()
        page = self._page(monkeypatch, view)
        view._show_error = MagicMock()
        scheduled: list = []
        monkeypatch.setattr(
            "application.view.operations_view.asyncio.create_task",
            lambda coro: scheduled.append(coro) or MagicMock(),
        )
        view.api_client.link_okx_transfer.side_effect = RestClientError("boom")

        view._show_transfer_dialog(OKX_TX, SUGGESTION)
        page.show_dialog.call_args.args[0].actions[1].on_click(None)
        asyncio.run(scheduled[0])

        view._show_error.assert_called_once()
        page.pop_dialog.assert_not_called()
