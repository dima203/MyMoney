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


class TestDifferenceMoney:
    def test_currency_not_equal(self) -> None:
        assert Money.dollar(5) != Money.euro(5)

    def test_currency_little(self) -> None:
        with pytest.raises(TypeError):
            Money.dollar(3) < Money.byn(5)

    def test_currency_sum(self) -> None:
        with pytest.raises(TypeError):
            Money.dollar(5) + Money.euro(7)

    def test_currency_sub(self) -> None:
        with pytest.raises(TypeError):
            Money.dollar(5) - Money.euro(7)

    def test_currency_multiply(self) -> None:
        with pytest.raises(TypeError):
            Money.dollar(3) * Money.dollar(5)

    def test_repr(self) -> None:
        assert repr(Money.dollar(5)) == "Dollar(5)"

    def test_str(self) -> None:
        assert str(Money.dollar(5)) == "5 $"
