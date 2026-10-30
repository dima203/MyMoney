"""Курсы фиатных валют на клиенте: кэш, единая карта курсов и офлайн-фолбэк (2.50)."""

import asyncio
import json
from decimal import Decimal
from typing import ClassVar
from unittest.mock import MagicMock

import pytest
from application.api import BackendUnreachableError
from application.fx_rates import FxRateStore, load_fx_rows
from application.view.accounts_view import AccountsView
from core.group_totals import build_rate_map, rate_to_base
from core.onboarding import OnboardingState
from core.operations_totals import period_totals

FX_ROWS = [
    {"base": "USD", "quote": "BYN", "rate": "0.3125", "source": "nbrb"},
    {"base": "USD", "quote": "EUR", "rate": "1.08", "source": "nbrb"},
    {"base": "USD", "quote": "RUB", "rate": "0.0108", "source": "nbrb"},
]
PRICES = [{"symbol": "USDT", "price": 1.0}, {"symbol": "BTC", "price": 50000.0}]


@pytest.fixture
def fx_path(tmp_path):
    return tmp_path / "fx.json"


@pytest.fixture
def store(fx_path) -> FxRateStore:
    return FxRateStore(fx_path)


class TestFxRateStore:
    def test_round_trip(self, store):
        store.save(FX_ROWS, profile_base="byn")

        assert store.load() == FX_ROWS
        assert store.load_profile_base() == "BYN"

    def test_missing_file_is_empty(self, store):
        assert store.load() == []
        assert store.load_profile_base() is None

    def test_corrupt_file_is_empty(self, fx_path):
        fx_path.write_text("{oops", encoding="utf-8")

        store = FxRateStore(fx_path)

        assert store.load() == []
        assert store.load_profile_base() is None

    def test_profile_base_survives_rates_update(self, store):
        store.save(FX_ROWS, profile_base="BYN")

        store.save(FX_ROWS[:1])

        assert store.load_profile_base() == "BYN"
        assert store.load() == FX_ROWS[:1]

    def test_payload_shape(self, fx_path):
        FxRateStore(fx_path).save(FX_ROWS, profile_base="rub")

        payload = json.loads(fx_path.read_text(encoding="utf-8"))
        assert payload["base"] == "USD"
        assert payload["profile_base"] == "RUB"
        assert payload["rates"] == FX_ROWS


class TestLoadFxRows:
    def test_fresh_rows_are_cached(self, store):
        api_client = MagicMock()
        api_client.get_fx_rates.return_value = FX_ROWS

        rows = load_fx_rows(api_client, store)

        assert rows == FX_ROWS
        assert store.load() == FX_ROWS
        api_client.get_fx_rates.assert_called_once_with("USD")

    def test_network_error_uses_cache(self, store):
        store.save(FX_ROWS)
        api_client = MagicMock()
        api_client.get_fx_rates.side_effect = BackendUnreachableError("down")

        assert load_fx_rows(api_client, store) == FX_ROWS

    def test_empty_server_response_uses_cache(self, store):
        store.save(FX_ROWS)
        api_client = MagicMock()
        api_client.get_fx_rates.return_value = []

        assert load_fx_rows(api_client, store) == FX_ROWS

    def test_non_list_response_uses_cache(self, store):
        store.save(FX_ROWS)
        api_client = MagicMock()
        api_client.get_fx_rates.return_value = {"rates": []}

        assert load_fx_rows(api_client, store) == FX_ROWS


class TestRateMap:
    def test_crypto_and_fiat_share_one_anchor(self):
        rates = build_rate_map(PRICES, FX_ROWS)

        assert rates["BTC"] == Decimal("50000.0")
        assert rates["BYN"] == Decimal("0.3125")
        assert rates["USD"] == Decimal(1)
        assert rates["USDT"] == Decimal(1)

    def test_crypto_to_fiat_chain(self):
        rates = build_rate_map(PRICES, FX_ROWS)

        rate = rate_to_base("BTC", "BYN", rates)

        assert rate == Decimal("50000.0") / Decimal("0.3125")

    def test_fiat_to_crypto_chain(self):
        rates = build_rate_map(PRICES, FX_ROWS)

        assert rate_to_base("EUR", "BTC", rates) == Decimal("1.08") / Decimal("50000.0")

    def test_fiat_to_fiat_without_prices(self):
        rates = build_rate_map([], FX_ROWS)

        assert rate_to_base("BYN", "EUR", rates) == Decimal("0.3125") / Decimal("1.08")

    def test_bad_fx_rows_are_skipped(self):
        rows = [{"quote": "XXX", "rate": "oops"}, {"quote": "", "rate": 1}, "junk", {"quote": "EUR", "rate": 0}]

        rates = build_rate_map([], rows)

        assert "XXX" not in rates
        assert "EUR" not in rates

    def test_symbol_key_supported_as_alias(self):
        rates = build_rate_map([], [{"symbol": "byn", "price": "0.3"}])

        assert rates["BYN"] == Decimal("0.3")


class TestPeriodTotalsWithFx:
    ACCOUNTS: ClassVar[dict] = {1: {"id": 1, "resource": "BYN"}, 2: {"id": 2, "resource": "BTC"}}

    def _tx(self, amount, account=1):
        return {"entries": [{"account": account, "amount": amount}]}

    def test_fiat_same_currency_via_fx(self):
        result = period_totals([self._tx(100.0)], self.ACCOUNTS, "BYN", [], FX_ROWS)

        assert result.income == Decimal(100)

    def test_crypto_income_converted_to_fiat(self):
        result = period_totals([self._tx(0.01, account=2)], self.ACCOUNTS, "BYN", PRICES, FX_ROWS)

        expected = Decimal("0.01") * Decimal("50000.0") / Decimal("0.3125")
        assert round(float(result.income), 6) == round(float(expected), 6)

    def test_missing_fx_reports_symbol(self):
        result = period_totals([self._tx(5.0, account=2)], self.ACCOUNTS, "BYN", [], [])

        assert result.income == 0
        assert "BTC" in result.missing_symbols


class TestAccountsFxContext:
    def _view(self, tmp_path, api_client):
        view = AccountsView(
            route="/accounts",
            api_client=api_client,
            onboarding=OnboardingState(path=tmp_path / "onboarding.json"),
            fx_store=FxRateStore(tmp_path / "fx.json"),
        )
        view.update = MagicMock()
        return view

    def test_context_merges_prices_and_fx(self, tmp_path):
        api_client = MagicMock()
        api_client.me.return_value = {"base_currency": "BYN"}
        api_client.get_prices.return_value = PRICES
        api_client.get_fx_rates.return_value = FX_ROWS
        view = self._view(tmp_path, api_client)

        base, rates = view._fetch_fx_context()

        assert base == "BYN"
        assert rates["BTC"] == Decimal("50000.0")
        assert rates["BYN"] == Decimal("0.3125")
        assert (tmp_path / "fx.json").exists()

    def test_offline_uses_cached_base_and_rates(self, tmp_path):
        store = FxRateStore(tmp_path / "fx.json")
        store.save(FX_ROWS, profile_base="BYN")
        api_client = MagicMock()
        api_client.me.side_effect = BackendUnreachableError("down")
        api_client.get_fx_rates.side_effect = BackendUnreachableError("down")
        view = self._view(tmp_path, api_client)

        base, rates = view._fetch_fx_context()

        assert base == "BYN"
        assert rates["EUR"] == Decimal("1.08")

    def test_no_profile_and_no_cache_returns_none(self, tmp_path):
        api_client = MagicMock()
        api_client.me.return_value = {}
        view = self._view(tmp_path, api_client)

        assert view._fetch_fx_context() == (None, {})

    def test_load_data_offline_uses_cached_fx(self, tmp_path):
        store = FxRateStore(tmp_path / "fx.json")
        store.save(FX_ROWS, profile_base="BYN")
        resource_view = MagicMock()
        resource_view.is_online = False
        resource_view.get_all.return_value = [
            {"id": 1, "name": "Наличные", "resource_definition": 2, "current_balance_qty": "100", "group": ""}
        ]
        account_view = MagicMock()
        account_view.is_online = False
        account_view.get_all.return_value = []
        api_client = MagicMock()
        view = AccountsView(
            route="/accounts",
            api_client=api_client,
            resource_view=resource_view,
            account_view=account_view,
            onboarding=OnboardingState(path=tmp_path / "onboarding.json"),
            fx_store=store,
        )
        view.update = MagicMock()

        asyncio.run(view._load_data())

        assert view._base_currency == "BYN"
        assert view._prices["BYN"] == Decimal("0.3125")
        api_client.me.assert_not_called()
        api_client.get_fx_rates.assert_not_called()

    def test_load_data_offline_without_cache_keeps_legacy_total(self, tmp_path):
        resource_view = MagicMock()
        resource_view.is_online = False
        resource_view.get_all.return_value = []
        account_view = MagicMock()
        account_view.is_online = False
        account_view.get_all.return_value = []
        view = AccountsView(
            route="/accounts",
            api_client=MagicMock(),
            resource_view=resource_view,
            account_view=account_view,
            onboarding=OnboardingState(path=tmp_path / "onboarding.json"),
            fx_store=FxRateStore(tmp_path / "fx.json"),
        )
        view.update = MagicMock()

        asyncio.run(view._load_data())

        assert view._base_currency is None
