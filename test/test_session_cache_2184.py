"""2.184: stale-while-revalidate — кэш сессии, мгновенный рендер и баннер устаревания."""

import asyncio
from unittest.mock import MagicMock

import flet as ft
from application.api import BackendUnreachableError
from application.fx_rates import FxRateStore
from application.session_cache import (
    ACCOUNTS,
    CACHE,
    TRANSACTIONS,
    SessionCache,
    endpoint_key,
    invalidate_data,
)
from application.view.accounts_view import AccountsView
from application.view.operations_view import OperationsView
from application.view.stale_cache import STALE_BANNER_TEXT, payload_changed
from core.onboarding import OnboardingState

from MySpaceShared.components.connection_status import ConnectionBanner

USD = {"id": 1, "name": "USD", "ticker": "USD", "unit": "USD", "resource_type": "currency"}
ACCOUNTS_ROWS = [
    {"id": 10, "name": "Наличные", "resource_definition": 1, "group": "Наличные", "current_balance_qty": "10"}
]


def _texts(control) -> list[str]:
    found = []
    value = getattr(control, "value", None)
    if isinstance(value, str) and value:
        found.append(value)
    for child in getattr(control, "controls", None) or []:
        found.extend(_texts(child))
    content = getattr(control, "content", None)
    if content is not None and not isinstance(content, str):
        found.extend(_texts(content))
    return found


class TestSessionCache:
    def test_set_get_and_clear(self):
        cache = SessionCache()

        cache.set("accounts", [1, 2])
        assert cache.get("accounts") == [1, 2]
        assert cache.has("accounts") is True

        cache.clear()
        assert cache.get("accounts") is None

    def test_invalidate_by_prefix(self):
        cache = SessionCache()
        cache.set("transactions", [])
        cache.set("transactions?limit=5", [])
        cache.set("accounts", [])

        removed = cache.invalidate("transactions")

        assert removed == 2
        assert cache.has("accounts") is True
        assert cache.keys() == ["accounts"]

    def test_endpoint_key_sorts_params(self):
        assert endpoint_key("/api/v1/tasks/") == "/api/v1/tasks/"
        assert endpoint_key("/api/v1/tasks/", {"b": 2, "a": 1}) == "/api/v1/tasks/?a=1&b=2"

    def test_invalidate_data_defaults_to_all(self):
        CACHE.set(ACCOUNTS, [])
        CACHE.set(TRANSACTIONS, [])
        CACHE.set("budgets", [])

        invalidate_data()

        assert CACHE.keys() == []

    def test_payload_changed(self):
        assert payload_changed({"a": 1}, {"a": 1}) is False
        assert payload_changed({"a": 1}, {"a": 2}) is True


def _accounts_view(tmp_path, *, accounts=None, base_currency="USD"):
    resource_view = MagicMock()
    resource_view.is_online = True
    resource_view.get_all.side_effect = lambda: [USD]
    account_view = MagicMock()
    account_view.is_online = True
    account_view.get_all.side_effect = lambda: list(accounts if accounts is not None else ACCOUNTS_ROWS)
    api_client = MagicMock()
    api_client.me.return_value = {"base_currency": base_currency}
    api_client.get_prices.return_value = [{"symbol": "USD", "price": 1.0}]
    view = AccountsView(
        route="/accounts",
        api_client=api_client,
        resource_view=resource_view,
        account_view=account_view,
        onboarding=OnboardingState(path=tmp_path / "onboarding.json"),
        fx_store=FxRateStore(tmp_path / "fx.json"),
    )
    view.update = MagicMock()
    return view, resource_view, account_view


class TestAccountsStaleWhileRevalidate:
    def test_cold_start_shows_spinner(self, tmp_path):
        view, resources, _accounts = _accounts_view(tmp_path)
        observed = {}

        def probe():
            observed["loading"] = view._loading.visible
            observed["rendered"] = bool(view._accounts_column.controls)
            return [USD]

        resources.get_all.side_effect = probe

        assert CACHE.has(ACCOUNTS) is False
        asyncio.run(view._load_data())

        assert observed == {"loading": True, "rendered": False}
        assert view._loading.visible is False
        assert CACHE.has(ACCOUNTS)

    def test_second_open_paints_from_cache_without_spinner(self, tmp_path):
        first, _resources, _accounts = _accounts_view(tmp_path)
        asyncio.run(first._load_data())
        assert first._loading.visible is False

        second, _resources2, account_view = _accounts_view(tmp_path)
        observed = {}

        def probe():
            observed["loading"] = second._loading.visible
            observed["rendered"] = bool(second._accounts_column.controls)
            return list(ACCOUNTS_ROWS)

        account_view.get_all.side_effect = probe

        asyncio.run(second._load_data())

        assert observed == {"loading": False, "rendered": True}
        assert second._loading.visible is False
        assert "10.00 USD" in " ".join(_texts(second._accounts_column))
        assert account_view.get_all.call_count == 1  # одно фоновое обновление

    def test_network_error_with_cache_shows_stale_banner(self, tmp_path):
        view, _resources, _accounts = _accounts_view(tmp_path)
        asyncio.run(view._load_data())

        second, resources2, _acc2 = _accounts_view(tmp_path)
        resources2.get_all.side_effect = BackendUnreachableError("down")

        asyncio.run(second._load_data())

        assert second._stale_banner.visible is True
        assert STALE_BANNER_TEXT in " ".join(_texts(second._stale_banner))
        assert second._error_text.visible is False
        assert "10.00 USD" in " ".join(_texts(second._accounts_column))

    def test_network_error_without_cache_shows_error(self, tmp_path):
        view, resources, _accounts = _accounts_view(tmp_path)
        resources.get_all.side_effect = BackendUnreachableError("down")

        asyncio.run(view._load_data())

        assert view._stale_banner.visible is False
        assert view._error_text.visible is True

    def test_cache_survives_view_list_and_invalidates_after_write(self, tmp_path):
        view, _resources, _accounts = _accounts_view(tmp_path)
        asyncio.run(view._load_data())
        assert CACHE.has(ACCOUNTS)

        invalidate_data(ACCOUNTS, TRANSACTIONS)

        assert CACHE.has(ACCOUNTS) is False


class TestTransactionsCache:
    def _view(self, transactions, *, online=True):
        return self._view_at(MagicMock(), transactions, online=online)

    def _view_at(self, path, transactions, *, online=True):
        transaction_view = MagicMock()
        transaction_view.is_online = online
        transaction_view.get_all.side_effect = lambda: list(transactions)
        account_view = MagicMock()
        account_view.is_online = online
        account_view.get_all.side_effect = lambda: [
            {"id": 1, "name": "Наличные", "resource_definition": 1, "account_type": "main"}
        ]
        api_client = MagicMock()
        api_client.list_categories.return_value = []
        api_client.list_budgets.return_value = []
        api_client.me.return_value = {"base_currency": "USD"}
        api_client.get_prices.return_value = []
        api_client.get_fx_rates.return_value = []
        view = OperationsView(
            route="/operations",
            api_client=api_client,
            transaction_view=transaction_view,
            account_view=account_view,
            connection_banner=ConnectionBanner(visible=False),
            fx_store=FxRateStore(path / "fx.json"),
        )
        view.update = MagicMock()
        return view

    def test_second_open_paints_cached_transactions(self, tmp_path):
        tx = {
            "id": 1,
            "date": "2026-11-01T10:00:00",
            "description": "Кофе",
            "category": "Продукты",
            "is_planned": False,
            "entries": [{"account": 1, "amount": -3.0, "unit_price": 1}],
        }
        first = self._view_at(tmp_path, [tx])
        asyncio.run(first._load_data())
        assert CACHE.has(TRANSACTIONS)

        second = self._view_at(tmp_path, [tx])
        asyncio.run(second._load_data())

        assert second._loading.visible is False
        assert "Кофе" in " ".join(_texts(second._tx_list))


class TestLogoutClearsCache:
    def test_cache_is_cleared_for_next_session(self):
        CACHE.set(ACCOUNTS, [{"id": 1}])
        CACHE.set(TRANSACTIONS, [{"id": 1}])

        # выход из аккаунта очищает кэш (та же операция, что в MyMoneyApp._on_logout)
        CACHE.clear()

        assert CACHE.keys() == []


def test_stale_banner_has_retry_button():
    from application.view.stale_cache import RETRY_LABEL, build_stale_banner

    banner = build_stale_banner(lambda: None)
    texts = [control.content for control in banner.content.controls if isinstance(control, ft.TextButton)]

    assert texts == [RETRY_LABEL]
    assert banner.visible is False
