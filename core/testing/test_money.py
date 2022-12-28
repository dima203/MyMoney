import pytest

from core import Money


class TestMoney:
    def test_currency_equal(self):
        assert Money.dollar(5) == Money.dollar(5)

    def test_currency_sum(self):
        result = Money.dollar(5) + Money.dollar(7)
        assert result == Money.dollar(12)

    def test_currency_multiply(self):
        result = Money.dollar(5) * 2
        assert result == Money.dollar(10)

    def test_currency_float_multiply(self):
        result = Money.dollar(1.5) * 2
        assert result == Money.dollar(3)


class TestDifferenceMoney:
    def test_currency_not_equal(self):
        assert Money.dollar(5) != Money.euro(5)

    def test_currency_sum(self):
        result = Money.dollar(5) + Money.dollar(7)
        assert result == Money.dollar(12)

        with pytest.raises(TypeError):
            Money.dollar(5) + Money.euro(7)

    def test_currency_multiply(self):
        result = Money.dollar(5) * 3
        assert result == Money.dollar(15)

        with pytest.raises(TypeError):
            Money.dollar(3) * Money.dollar(5)
