"""Групповые итоги в базовой валюте на экране счетов."""

import asyncio
from unittest.mock import MagicMock

from application.fx_rates import FxRateStore
from application.view.accounts_view import AccountsView
from core.onboarding import OnboardingState

USD_RESOURCE = {"id": 1, "name": "USD", "ticker": "USD", "unit": "USD", "resource_type": "currency"}
BYN_RESOURCE = {"id": 2, "name": "BYN", "ticker": "byn", "unit": "BYN", "resource_type": "currency"}
BTC_RESOURCE = {"id": 3, "name": "Bitcoin", "ticker": "BTC-USDT", "unit": "BTC", "resource_type": "currency"}
USDT_RESOURCE = {"id": 5, "name": "USDT", "ticker": "USDT", "unit": "USDT", "resource_type": "currency"}


def _texts(control) -> list[str]:
    import flet as ft

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
    title = getattr(control, "title", None)
    if title is not None and title is not control:
        found.extend(_texts(title))
    subtitle = getattr(control, "subtitle", None)
    if subtitle is not None:
        found.extend(_texts(subtitle))
    return found


def _acc(resource_id: int, qty, group: str = "Группа", name: str = "Счёт") -> dict:
    return {
        "id": resource_id * 10,
        "name": name,
        "resource_definition": resource_id,
        "group": group,
        "account_type": "main",
        "current_balance_qty": qty,
    }


def _make_view(tmp_path, *, resources, accounts, base_currency="USDT", prices=None, online=True):
    onboarding = OnboardingState(path=tmp_path / "onboarding.json")
    resource_view = MagicMock()
    resource_view.is_online = online
    resource_view.get_all.side_effect = lambda: list(resources)
    account_view = MagicMock()
    account_view.is_online = online
    account_view.get_all.side_effect = lambda: list(accounts)
    api_client = MagicMock()
    api_client.me.return_value = {"username": "u", "base_currency": base_currency}
    api_client.get_prices.return_value = prices if prices is not None else [{"symbol": "USDT", "price": 1.0}]
    view = AccountsView(
        route="/accounts",
        api_client=api_client,
        resource_view=resource_view,
        account_view=account_view,
        onboarding=onboarding,
        fx_store=FxRateStore(tmp_path / "fx.json"),
    )
    view.update = MagicMock()
    return view


class TestGroupTotalConverted:
    def test_single_currency_group_total_in_base(self, tmp_path) -> None:
        accounts = [_acc(1, "100", group="Наличные"), _acc(1, "234.5", group="Наличные")]
        view = _make_view(tmp_path, resources=[USD_RESOURCE], accounts=accounts, base_currency="USD")
        asyncio.run(view._load_data())
        texts = _texts(view._accounts_column)
        assert "Итого: 334.50 USD" in texts

    def test_multi_currency_group_converted_via_usdt(self, tmp_path) -> None:
        prices = [{"symbol": "USDT", "price": 1.0}, {"symbol": "BTC", "price": 50000.0}]
        accounts = [_acc(5, "100", group="Смешанная"), _acc(3, "0.001", group="Смешанная")]
        view = _make_view(
            tmp_path, resources=[USDT_RESOURCE, BTC_RESOURCE], accounts=accounts, base_currency="USDT", prices=prices
        )
        asyncio.run(view._load_data())
        texts = _texts(view._accounts_column)
        assert "Итого: 150.00 USDT" in texts

    def test_base_currency_btc_divides_by_base_price(self, tmp_path) -> None:
        prices = [{"symbol": "USDT", "price": 1.0}, {"symbol": "BTC", "price": 50000.0}]
        accounts = [_acc(5, "100000", group="В биткоине")]
        view = _make_view(tmp_path, resources=[USDT_RESOURCE], accounts=accounts, base_currency="BTC", prices=prices)
        asyncio.run(view._load_data())
        texts = _texts(view._accounts_column)
        assert "Итого: 2.00 BTC" in texts


class TestGroupTotalMissingRates:
    def test_missing_rate_marked_not_silent(self, tmp_path) -> None:
        accounts = [_acc(5, "100", group="Наличные"), _acc(2, "50", group="Наличные")]
        view = _make_view(tmp_path, resources=[USDT_RESOURCE, BYN_RESOURCE], accounts=accounts, base_currency="USDT")
        asyncio.run(view._load_data())
        texts = _texts(view._accounts_column)
        assert "Итого: 100.00 USDT (курс недоступен: BYN)" in texts

    def test_fully_missing_rates_show_marker(self, tmp_path) -> None:
        accounts = [_acc(2, "50", group="Наличные")]
        view = _make_view(tmp_path, resources=[BYN_RESOURCE], accounts=accounts, base_currency="USDT")
        asyncio.run(view._load_data())
        texts = _texts(view._accounts_column)
        assert "Итого: курс недоступен" in texts

    def test_usd_is_known_anchor_without_prices(self, tmp_path) -> None:
        accounts = [_acc(1, "100", group="Наличные")]
        view = _make_view(tmp_path, resources=[USD_RESOURCE], accounts=accounts, base_currency="USDT", prices=[])
        asyncio.run(view._load_data())
        texts = _texts(view._accounts_column)
        assert "Итого: 100.00 USDT" in texts


class TestGroupTotalDegradation:
    def test_offline_skips_fx_and_keeps_legacy_total(self, tmp_path) -> None:
        accounts = [_acc(1, "123.45", group="Наличные")]
        view = _make_view(tmp_path, resources=[USD_RESOURCE], accounts=accounts, online=False)
        asyncio.run(view._load_data())
        assert view._base_currency is None
        texts = _texts(view._accounts_column)
        assert "123.45 USD" in texts
        assert not any(t.startswith("Итого:") for t in texts)

    def test_me_failure_keeps_legacy_total(self, tmp_path) -> None:
        from application.api import BackendUnreachableError

        accounts = [_acc(1, "10", group="Наличные")]
        view = _make_view(tmp_path, resources=[USD_RESOURCE], accounts=accounts)
        view.api_client.me.side_effect = BackendUnreachableError("down")
        asyncio.run(view._load_data())
        assert view._base_currency is None
        texts = _texts(view._accounts_column)
        assert "10.00 USD" in texts

    def test_prices_failure_with_base_marks_missing(self, tmp_path) -> None:
        from application.api import BackendUnreachableError

        accounts = [_acc(1, "10", group="Наличные")]
        view = _make_view(tmp_path, resources=[USD_RESOURCE], accounts=accounts, base_currency="USD")
        view.api_client.get_prices.side_effect = BackendUnreachableError("down")
        asyncio.run(view._load_data())
        assert view._base_currency == "USD"
        texts = _texts(view._accounts_column)
        assert "Итого: 10.00 USD" in texts

    def test_prices_failure_other_currency_fully_missing(self, tmp_path) -> None:
        from application.api import BackendUnreachableError

        accounts = [_acc(1, "10", group="Наличные")]
        view = _make_view(tmp_path, resources=[USD_RESOURCE], accounts=accounts, base_currency="BYN")
        view.api_client.get_prices.side_effect = BackendUnreachableError("down")
        asyncio.run(view._load_data())
        assert view._base_currency == "BYN"
        texts = _texts(view._accounts_column)
        assert "Итого: курс недоступен" in texts

    def test_blank_base_currency_falls_back(self, tmp_path) -> None:
        accounts = [_acc(1, "10", group="Наличные")]
        view = _make_view(tmp_path, resources=[USD_RESOURCE], accounts=accounts, base_currency="  ")
        asyncio.run(view._load_data())
        assert view._base_currency is None
        texts = _texts(view._accounts_column)
        assert "10.00 USD" in texts

    def test_non_dict_me_falls_back(self, tmp_path) -> None:
        accounts = [_acc(1, "10", group="Наличные")]
        view = _make_view(tmp_path, resources=[USD_RESOURCE], accounts=accounts)
        view.api_client.me.return_value = ["unexpected"]
        asyncio.run(view._load_data())
        assert view._base_currency is None

    def test_crypto_accounts_still_excluded_from_group_totals(self, tmp_path) -> None:
        crypto = {"id": 4, "name": "BTC2", "ticker": "BTC2-USDT", "unit": "BTC2", "resource_type": "asset"}
        accounts = [_acc(5, "100", group="Наличные"), {**_acc(4, "1", group="Наличные"), "id": 40}]
        view = _make_view(tmp_path, resources=[USDT_RESOURCE, crypto], accounts=accounts, base_currency="USDT")
        asyncio.run(view._load_data())
        texts = _texts(view._accounts_column)
        assert "Итого: 100.00 USDT" in texts
