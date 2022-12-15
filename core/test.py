import pytest

from core import Money, Dollar, Euro


class TestMoney:
    def test_currency_equal(self):
        assert Money(5) == Money(5)

    def test_currency_sum(self):
        result = Money(5) + Money(7)
        assert result == Money(12)

    def test_currency_multiply(self):
        result = Money(5) * 2
        assert result == Money(10)


class TestDifferenceMoney:
    def test_currency_not_equal(self):
        assert Dollar(5) != Euro(5)

    def test_currency_sum(self):
        result = Dollar(5) + Dollar(7)
        assert result == Dollar(12)

        with pytest.raises(TypeError):
            result = Dollar(5) + Euro(7)

    def test_currency_multiply(self):
        result = Dollar(5) * 3
        assert result == Dollar(15)
