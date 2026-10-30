from decimal import Decimal

from core.operations_totals import format_period_totals, period_totals

ACCOUNTS = {
    1: {"id": 1, "resource": "BYN"},
    2: {"id": 2, "resource": "EUR"},
    3: {"id": 3, "resource": "XXX"},
}
PRICES = [
    {"symbol": "USDT", "price": 1.0},
    {"symbol": "BYN", "price": 0.33},
    {"symbol": "EUR", "price": 1.08},
]


def _tx(amount: float, account: int = 1) -> dict:
    return {"entries": [{"account": account, "amount": amount}]}


class TestPeriodTotals:
    def test_same_currency(self):
        result = period_totals([_tx(100.0), _tx(-40.0)], ACCOUNTS, "BYN", PRICES)
        assert result.income == Decimal(100)
        assert result.expense == Decimal(40)
        assert result.net == Decimal(60)
        assert result.missing_symbols == ()

    def test_converts_via_usdt_cross(self):
        result = period_totals([_tx(100.0, account=2)], ACCOUNTS, "BYN", PRICES)
        assert round(float(result.income), 2) == round(100 * 1.08 / 0.33, 2)

    def test_missing_rate_is_reported(self):
        result = period_totals([_tx(5.0, account=3)], ACCOUNTS, "BYN", PRICES)
        assert result.income == Decimal(0)
        assert result.missing_symbols == ("XXX",)

    def test_unknown_account_counts_as_missing(self):
        result = period_totals([_tx(5.0, account=99)], ACCOUNTS, "BYN", PRICES)
        assert result.missing_symbols == ("—",)

    def test_bad_entries_ignored(self):
        rows = [{"entries": [{"account": 1, "amount": "мусор"}, None]}]
        result = period_totals(rows, ACCOUNTS, "BYN", PRICES)
        assert result.income == 0
        assert result.expense == 0

    def test_format_text(self):
        result = period_totals([_tx(100.0), _tx(-25.0)], ACCOUNTS, "BYN", PRICES)
        text = format_period_totals(result, "BYN")
        assert "Доход +100.00" in text
        assert "Расход −25.00" in text
        assert "BYN" in text

    def test_format_missing_note(self):
        result = period_totals([_tx(5.0, account=3)], ACCOUNTS, "BYN", PRICES)
        assert "курс недоступен: XXX" in format_period_totals(result, "BYN")

    def test_transfer_is_not_income_or_expense(self):
        transfer = {
            "entries": [
                {"account": 1, "amount": -500.0},
                {"account": 2, "amount": 500.0},
            ]
        }
        result = period_totals([transfer], ACCOUNTS, "BYN", PRICES)
        assert result.income == 0
        assert result.expense == 0

    def test_thousands_use_space_separator(self):
        result = period_totals([_tx(1234.5)], ACCOUNTS, "BYN", PRICES)
        assert "+1 234.50" in format_period_totals(result, "BYN")
