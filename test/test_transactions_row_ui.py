"""Регрессии 14.10.2026: валюта снимка OKX (P1), время вместо даты (P1), липкие шапки дней (P2)."""

import asyncio
from datetime import UTC, datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock

import flet as ft
from application.components.transaction_card import TransactionCard
from application.display import FAB_CLEARANCE, is_read_only_transaction
from application.view.transactions_view import (
    DAY_HEADER_HEIGHT,
    TransactionsView,
    day_group_index,
    day_group_offsets,
    resolve_row_currency,
)

BTC_ACCOUNT = {
    "id": 10,
    "name": "",
    "resource_definition": 1,
    "resource": "BTC",
    "group": "",
    "account_type": "trading",
}

SNAPSHOT_ACCOUNTS = [
    BTC_ACCOUNT,
    {"id": 4, "name": "1", "resource_definition": 405, "resource": "USDT", "group": "", "account_type": "main"},
    {"id": 5, "name": "", "resource_definition": 79, "resource": "BTC", "group": "", "account_type": "main"},
    {"id": 14, "name": "", "resource_definition": 26, "resource": "XAMD", "group": "", "account_type": "trading"},
    {"id": 16, "name": "", "resource_definition": 405, "resource": "USDT", "group": "", "account_type": "trading"},
    {"id": 30, "name": "Earn", "resource_definition": 405, "resource": "USDT", "group": "", "account_type": "earn"},
]

SNAPSHOT_ENTRIES = [
    {"account": 4, "quantity": "0.000000000000", "amount": "0.000000000000", "unit_price": "1.000000000000"},
    {"account": 5, "quantity": "0.000000000000", "amount": "0.000000031120", "unit_price": "84084.700000000000"},
    {"account": 14, "quantity": "-0.015055933600", "amount": "-9.249913925832", "unit_price": "614.370000000000"},
    {"account": 16, "quantity": "9.194301370239", "amount": "9.194301370239", "unit_price": "1.000000000000"},
    {"account": 30, "quantity": "0.140000000000", "amount": "0.140000000000", "unit_price": "1.000000000000"},
]


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


class TestSnapshotCurrency:
    def test_resolve_row_currency_prefers_native_units(self) -> None:
        account_map = {a["id"]: a for a in SNAPSHOT_ACCOUNTS}
        assert resolve_row_currency(SNAPSHOT_ENTRIES, account_map) == "USDT"

    def test_snapshot_row_shows_usdt_suffix(self) -> None:
        tx = {
            "id": 12,
            "date": "2026-10-12T00:00:00Z",
            "description": "Снимок OKX",
            "category": "",
            "entries": SNAPSHOT_ENTRIES,
        }
        view = _make_transactions_view(accounts=SNAPSHOT_ACCOUNTS, transactions=[tx])
        asyncio.run(view._load_data())
        assert "+0.08 USDT" in _texts(view._tx_list)

    def test_account_without_resource_key_has_no_suffix(self) -> None:
        entries = [{"account": 9, "amount": 5.0, "unit_price": 1}]
        account_map = {9: {"id": 9, "name": "Кэш", "resource_definition": 5}}
        assert resolve_row_currency(entries, account_map) == ""

    def test_mixed_native_units_have_no_suffix(self) -> None:
        entries = [{"account": 10, "amount": -1.0}, {"account": 11, "amount": 90.0}]
        account_map = {10: BTC_ACCOUNT, 11: {**BTC_ACCOUNT, "id": 11, "resource": "EUR"}}
        assert resolve_row_currency(entries, account_map) == ""

    def test_single_converted_entry_falls_back_to_account_unit(self) -> None:
        entries = [{"account": 10, "amount": 5.0, "unit_price": 84084.7}]
        assert resolve_row_currency(entries, {10: BTC_ACCOUNT}) == "BTC"


class TestRowTime:
    def test_naive_datetime_shows_hhmm(self) -> None:
        card = TransactionCard(description="x", amount=-1.0, account_name="A", timestamp=datetime(2027, 3, 15, 14, 35))
        assert "14:35" in _texts(card)

    def test_aware_datetime_shows_hhmm(self) -> None:
        timestamp = datetime(2027, 3, 15, 14, 35, tzinfo=timezone(timedelta(hours=3)))
        card = TransactionCard(description="x", amount=-1.0, account_name="A", timestamp=timestamp)
        assert "14:35" in _texts(card)

    def test_naive_midnight_hides_time(self) -> None:
        card = TransactionCard(description="x", amount=-1.0, account_name="A", timestamp=datetime(2027, 3, 15))
        assert "00:00" not in _texts(card)

    def test_utc_midnight_hides_time(self) -> None:
        card = TransactionCard(
            description="x", amount=-1.0, account_name="A", timestamp=datetime(2027, 3, 15, tzinfo=UTC)
        )
        assert "00:00" not in _texts(card)

    def test_row_replaces_date_with_time(self) -> None:
        tx = {
            "id": 1,
            "date": "2027-03-15T14:35:00",
            "description": "Оплата",
            "category": "",
            "entries": [{"account": 10, "amount": -1.0, "unit_price": 1}],
        }
        view = _make_transactions_view(accounts=[BTC_ACCOUNT], transactions=[tx])
        asyncio.run(view._load_data())
        texts = _texts(view._tx_list)
        assert "14:35" in texts
        assert "15 Mar" not in texts

    def test_date_only_row_shows_no_time(self) -> None:
        tx = {
            "id": 1,
            "date": "2027-03-15",
            "description": "Снимок",
            "category": "",
            "entries": [{"account": 10, "amount": -1.0, "unit_price": 1}],
        }
        view = _make_transactions_view(accounts=[BTC_ACCOUNT], transactions=[tx])
        asyncio.run(view._load_data())
        assert "00:00" not in _texts(view._tx_list)


class TestStickyDayHeaders:
    def test_day_group_offsets_math(self) -> None:
        card_height, spacing = 70.0, 8
        counts = [1, 2]
        content = 2 * DAY_HEADER_HEIGHT + 3 * card_height + (3 + 2) * spacing + FAB_CLEARANCE
        offsets = day_group_offsets(content, counts, spacing=spacing)
        assert offsets == [0.0, DAY_HEADER_HEIGHT + spacing + card_height + spacing]

    def test_day_group_offsets_infeasible_returns_none(self) -> None:
        assert day_group_offsets(DAY_HEADER_HEIGHT, [1]) is None

    def test_day_group_offsets_empty_counts(self) -> None:
        assert day_group_offsets(1000.0, []) == []

    def test_day_group_index_boundaries(self) -> None:
        offsets = [0.0, 110.0]
        assert day_group_index(offsets, 0.0) == 0
        assert day_group_index(offsets, 109.0) == 0
        assert day_group_index(offsets, 110.6) == 1
        assert day_group_index(offsets, 9999.0) == 1

    def test_pinned_header_follows_scroll(self) -> None:
        txs = [
            {
                "id": 1,
                "date": "2027-03-15T14:35:00",
                "description": "A",
                "category": "",
                "entries": [{"account": 10, "amount": -1.0, "unit_price": 1}],
            },
            {
                "id": 2,
                "date": "2027-03-16T14:35:00",
                "description": "B",
                "category": "",
                "entries": [{"account": 10, "amount": -2.0, "unit_price": 1}],
            },
        ]
        view = _make_transactions_view(accounts=[BTC_ACCOUNT], transactions=txs)
        asyncio.run(view._load_data())
        labels = [label for label, _ in view._day_groups]
        assert [count for _, count in view._day_groups] == [1, 1]

        content = 2 * DAY_HEADER_HEIGHT + 2 * 100 + (2 + 2) * 8 + FAB_CLEARANCE
        event = SimpleNamespace(pixels=0.0, max_scroll_extent=content - 300.0, extent_total=content)
        view._on_tx_scroll(event)
        assert view._pinned_header.visible is False

        event.pixels = 1.0
        view._on_tx_scroll(event)
        assert view._pinned_header.visible is True
        assert view._pinned_label.value == labels[0]

        event.pixels = DAY_HEADER_HEIGHT + 8 + 100 + 8 + 0.6
        view._on_tx_scroll(event)
        assert view._pinned_label.value == labels[1]

        event.max_scroll_extent = 0.0
        view._on_tx_scroll(event)
        assert view._pinned_header.visible is False

    def test_rebuild_resets_pinned_header(self) -> None:
        tx = {
            "id": 1,
            "date": "2027-03-15T14:35:00",
            "description": "A",
            "category": "",
            "entries": [{"account": 10, "amount": -1.0, "unit_price": 1}],
        }
        view = _make_transactions_view(accounts=[BTC_ACCOUNT], transactions=[tx])
        asyncio.run(view._load_data())
        event = SimpleNamespace(pixels=50.0, max_scroll_extent=100.0, extent_total=500.0)
        view._on_tx_scroll(event)
        assert view._pinned_header.visible is True
        view._rebuild_list()
        assert view._pinned_header.visible is False
        assert view._pinned_label.value == ""


def _find_controls(control, cls) -> list:
    found: list = []
    if isinstance(control, cls):
        found.append(control)
    content = getattr(control, "content", None)
    if content is not None and not isinstance(content, str):
        found.extend(_find_controls(content, cls))
    for child in getattr(control, "controls", None) or []:
        found.extend(_find_controls(child, cls))
    return found


def _cards(view) -> list[TransactionCard]:
    return [c for c in view._tx_list.controls if isinstance(c, TransactionCard)]


def _row_tx(**overrides) -> dict:
    tx = {
        "id": 1,
        "date": "2027-03-15T14:35:00",
        "description": "Покупка",
        "category": "",
        "entries": [{"account": 10, "amount": -1.0, "unit_price": 1}],
    }
    tx.update(overrides)
    return tx


class TestReadOnlyDetection:
    def test_server_flag_true_is_read_only(self) -> None:
        assert is_read_only_transaction({"description": "Покупка", "read_only": True}) is True

    def test_server_flag_false_wins_over_prefix(self) -> None:
        tx = {"description": "okx: snapshot 2026-10-09 07:09", "read_only": False}
        assert is_read_only_transaction(tx) is False

    def test_missing_flag_falls_back_to_okx_prefix(self) -> None:
        assert is_read_only_transaction({"description": "okx: snapshot 2026-10-09 07:09"}) is True

    def test_missing_flag_falls_back_to_legacy_prefix(self) -> None:
        assert is_read_only_transaction({"description": "import: snapshot 2026-08-02 12:00"}) is True

    def test_regular_transaction_is_editable(self) -> None:
        assert is_read_only_transaction({"description": "Покупка"}) is False


class TestReadOnlyCard:
    def test_read_only_card_hides_menu_and_shows_badge(self) -> None:
        card = TransactionCard(
            description="okx: snapshot 2026-10-09 07:09",
            amount=1.0,
            account_name="A",
            on_edit=lambda: None,
            on_delete=lambda: None,
            read_only=True,
        )
        assert not _find_controls(card, ft.PopupMenuButton)
        assert "Снимок OKX" in _texts(card)

    def test_editable_card_keeps_menu_and_has_no_badge(self) -> None:
        card = TransactionCard(
            description="Покупка", amount=-1.0, account_name="A", on_edit=lambda: None, on_delete=lambda: None
        )
        assert len(_find_controls(card, ft.PopupMenuButton)) == 1
        assert "Снимок OKX" not in _texts(card)


class TestReadOnlyRows:
    def _load(self, tx: dict, *, show_snapshots: bool = True) -> TransactionsView:
        view = _make_transactions_view(accounts=[BTC_ACCOUNT], transactions=[tx])
        view._show_snapshots.value = show_snapshots
        asyncio.run(view._load_data())
        return view

    def test_row_with_server_flag_is_read_only(self) -> None:
        view = self._load(_row_tx(description="Покупка", read_only=True))
        cards = _cards(view)
        assert len(cards) == 1
        assert not _find_controls(cards[0], ft.PopupMenuButton)
        assert "Снимок OKX" in _texts(view._tx_list)

    def test_row_with_prefix_fallback_is_read_only(self) -> None:
        view = self._load(_row_tx(description="okx: snapshot 2026-10-09 07:09"))
        cards = _cards(view)
        assert len(cards) == 1
        assert not _find_controls(cards[0], ft.PopupMenuButton)
        assert "Снимок OKX" in _texts(view._tx_list)

    def test_snapshots_hidden_by_default(self) -> None:
        """2.12: технические записи не засоряют ленту, пока не включён тумблер."""
        view = self._load(_row_tx(description="okx: snapshot 2026-10-09 07:09"), show_snapshots=False)
        assert _cards(view) == []
        assert "Нет транзакций" in _texts(view._tx_list)
        assert view._show_snapshots.value is False

    def test_regular_row_keeps_menu_and_no_badge(self) -> None:
        view = self._load(_row_tx(), show_snapshots=False)
        cards = _cards(view)
        assert len(cards) == 1
        assert len(_find_controls(cards[0], ft.PopupMenuButton)) == 1
        assert "Снимок OKX" not in _texts(view._tx_list)
