import pytest

from core import Money


class TestMoney:
    def test_currency_equal(self):
        assert Money.dollar(5) == Money.dollar(5)

    def test_currency_little(self):
        assert Money.dollar(3) < Money.dollar(5)

    def test_currency_sum(self):
        result = Money.dollar(5) + Money.dollar(7)
        assert result == Money.dollar(12)

    def test_currency_sub(self):
        result = Money.dollar(13) - Money.dollar(7)
        assert result == Money.dollar(6)

    def test_currency_multiply(self):
        result = Money.dollar(5) * 2
        assert result == Money.dollar(10)

    def test_currency_float_multiply(self):
        result = Money.dollar(1.5) * 2
        assert result == Money.dollar(3)
