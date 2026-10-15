from decimal import Decimal

from core.group_totals import (
    QUOTE_CURRENCY,
    build_price_map,
    format_group_total,
    group_total_in_base,
    price_symbol_for_resource,
    rate_to_base,
)

RATES = {"BTC": Decimal(50000), "ETH": Decimal(3000), "USDT": Decimal(1)}
GROUP_RESOURCES = {
    1: {"id": 1, "unit": "USDT", "ticker": "USDT", "name": "USDT"},
    2: {"id": 2, "unit": "BYN", "ticker": "byn", "name": "BYN"},
    3: {"id": 3, "unit": "BTC", "ticker": "BTC-USDT", "name": "Bitcoin"},
}
GROUP_PRICES = {"BTC": Decimal(50000), "USDT": Decimal(1)}
FORMAT_RESOURCES = {
    1: {"id": 1, "unit": "USDT", "ticker": "USDT", "name": "USDT"},
    2: {"id": 2, "unit": "BYN", "ticker": "byn", "name": "BYN"},
}
FORMAT_PRICES = {"USDT": Decimal(1)}


class TestPriceSymbolForResource:
    def test_unit_wins(self) -> None:
        assert price_symbol_for_resource({"unit": "btc", "ticker": "BTC-USDT", "name": "Bitcoin"}) == "BTC"

    def test_ticker_suffix_stripped_when_no_unit(self) -> None:
        assert price_symbol_for_resource({"unit": "", "ticker": "ETH-USDT", "name": "Ethereum"}) == "ETH"

    def test_plain_ticker_uppercased(self) -> None:
        assert price_symbol_for_resource({"ticker": "usdt"}) == "USDT"

    def test_name_fallback(self) -> None:
        assert price_symbol_for_resource({"name": "Биткоин"}) == "БИТКОИН"

    def test_empty_resource(self) -> None:
        assert price_symbol_for_resource(None) == ""
        assert price_symbol_for_resource({}) == ""


class TestBuildPriceMap:
    def test_valid_rows(self) -> None:
        rows = [
            {"symbol": "BTC", "price": 50000.0},
            {"symbol": "usdt", "price": 1.0},
        ]
        assert build_price_map(rows) == {"BTC": Decimal("50000.0"), "USDT": Decimal("1.0")}

    def test_decimal_string_price(self) -> None:
        rows = [{"symbol": "ETH", "price": "3000.123456789012"}]
        assert build_price_map(rows) == {"ETH": Decimal("3000.123456789012")}

    def test_invalid_rows_skipped(self) -> None:
        rows = [
            None,
            "x",
            {"symbol": "", "price": 1},
            {"symbol": "BTC"},
            {"symbol": "BTC", "price": "oops"},
            {"symbol": "BTC", "price": 0},
            {"symbol": "BTC", "price": -5},
        ]
        assert build_price_map(rows) == {}

    def test_non_list_input(self) -> None:
        assert build_price_map(None) == {}
        assert build_price_map({"symbol": "BTC"}) == {}


class TestRateToBase:
    def test_same_symbol_is_one(self) -> None:
        assert rate_to_base("BYN", "BYN", RATES) == Decimal(1)

    def test_quote_currency_identity(self) -> None:
        assert rate_to_base(QUOTE_CURRENCY, QUOTE_CURRENCY, RATES) == Decimal(1)

    def test_cross_rate_via_usdt(self) -> None:
        rate = rate_to_base("BTC", "USDT", RATES)
        assert rate == Decimal(50000)

    def test_inverse_cross_rate(self) -> None:
        rate = rate_to_base("USDT", "BTC", RATES)
        assert rate == Decimal(1) / Decimal(50000)

    def test_missing_src_price(self) -> None:
        assert rate_to_base("BYN", "USDT", RATES) is None

    def test_missing_base_price(self) -> None:
        assert rate_to_base("BTC", "BYN", RATES) is None

    def test_empty_inputs(self) -> None:
        assert rate_to_base("", "USDT", RATES) is None
        assert rate_to_base("BTC", "", RATES) is None


class TestGroupTotalInBase:
    def _acc(self, resource_id: int, qty) -> dict:
        return {"resource_definition": resource_id, "current_balance_qty": qty}

    def test_single_currency_group(self) -> None:
        accounts = [self._acc(1, "100.5"), self._acc(1, "2.5")]
        result = group_total_in_base(accounts, GROUP_RESOURCES, "USDT", GROUP_PRICES)
        assert result.total == Decimal("103.0")
        assert result.converted == 2
        assert result.missing_symbols == ()
        assert result.has_missing is False
        assert result.is_fully_missing is False

    def test_multi_currency_group_converted(self) -> None:
        accounts = [self._acc(1, "100"), self._acc(3, "0.001")]
        result = group_total_in_base(accounts, GROUP_RESOURCES, "USDT", GROUP_PRICES)
        assert result.total == Decimal(150)
        assert result.converted == 2

    def test_missing_rate_marks_symbol(self) -> None:
        accounts = [self._acc(1, "100"), self._acc(2, "50")]
        result = group_total_in_base(accounts, GROUP_RESOURCES, "USDT", GROUP_PRICES)
        assert result.total == Decimal(100)
        assert result.converted == 1
        assert result.missing_symbols == ("BYN",)
        assert result.has_missing is True
        assert result.is_fully_missing is False

    def test_fully_missing_rates(self) -> None:
        accounts = [self._acc(2, "50")]
        result = group_total_in_base(accounts, GROUP_RESOURCES, "EUR", GROUP_PRICES)
        assert result.total == Decimal(0)
        assert result.converted == 0
        assert result.missing_symbols == ("BYN",)
        assert result.is_fully_missing is True

    def test_decimal_string_balance(self) -> None:
        accounts = [self._acc(3, "0.000000031120")]
        result = group_total_in_base(accounts, GROUP_RESOURCES, "USDT", GROUP_PRICES)
        assert result.total == Decimal("0.000000031120") * Decimal(50000)

    def test_float_balance(self) -> None:
        accounts = [self._acc(1, 100.5)]
        result = group_total_in_base(accounts, GROUP_RESOURCES, "USDT", GROUP_PRICES)
        assert result.total == Decimal("100.5")

    def test_invalid_balance_treated_as_zero(self) -> None:
        accounts = [self._acc(1, "not-a-number")]
        result = group_total_in_base(accounts, GROUP_RESOURCES, "USDT", GROUP_PRICES)
        assert result.total == Decimal(0)
        assert result.converted == 1

    def test_unknown_resource_is_missing(self) -> None:
        accounts = [self._acc(99, "10")]
        result = group_total_in_base(accounts, GROUP_RESOURCES, "USDT", GROUP_PRICES)
        assert result.missing_symbols == ("—",)
        assert result.is_fully_missing is True

    def test_negative_balance_converted(self) -> None:
        accounts = [self._acc(1, "-20")]
        result = group_total_in_base(accounts, GROUP_RESOURCES, "USDT", GROUP_PRICES)
        assert result.total == Decimal(-20)

    def test_empty_accounts(self) -> None:
        result = group_total_in_base([], GROUP_RESOURCES, "USDT", GROUP_PRICES)
        assert result.total == Decimal(0)
        assert result.converted == 0
        assert result.missing_symbols == ()


class TestFormatGroupTotal:
    def test_full_conversion(self) -> None:
        accounts = [{"resource_definition": 1, "current_balance_qty": "1234.5"}]
        result = group_total_in_base(accounts, FORMAT_RESOURCES, "USDT", FORMAT_PRICES)
        assert format_group_total(result, "USDT") == "Итого: 1,234.50 USDT"

    def test_fully_missing(self) -> None:
        accounts = [{"resource_definition": 2, "current_balance_qty": "50"}]
        result = group_total_in_base(accounts, FORMAT_RESOURCES, "USDT", FORMAT_PRICES)
        assert format_group_total(result, "USDT") == "Итого: курс недоступен"

    def test_partial_marks_missing(self) -> None:
        accounts = [
            {"resource_definition": 1, "current_balance_qty": "100"},
            {"resource_definition": 2, "current_balance_qty": "50"},
        ]
        result = group_total_in_base(accounts, FORMAT_RESOURCES, "USDT", FORMAT_PRICES)
        assert format_group_total(result, "USDT") == "Итого: 100.00 USDT (курс недоступен: BYN)"

    def test_negative_total(self) -> None:
        accounts = [{"resource_definition": 1, "current_balance_qty": "-20.5"}]
        result = group_total_in_base(accounts, FORMAT_RESOURCES, "USDT", FORMAT_PRICES)
        assert format_group_total(result, "USDT") == "Итого: -20.50 USDT"
