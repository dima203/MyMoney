import pytest

from core import Money, Resource


class TestMoney:
    def setup_class(self):
        self.usd = Resource("USD", "USD")

    def test_currency_equal(self):
        assert Money(5, self.usd) == Money(5, self.usd)

    def test_currency_little(self):
        assert Money(3, self.usd) < Money(5, self.usd)

    def test_currency_sum(self):
        result = Money(5, self.usd) + Money(7, self.usd)
        assert result == Money(12, self.usd)

    def test_currency_sub(self):
        result = Money(13, self.usd) - Money(7, self.usd)
        assert result == Money(6, self.usd)

    def test_currency_multiply(self):
        result = Money(5, self.usd) * 2
        assert result == Money(10, self.usd)

    def test_currency_float_multiply(self):
        result = Money(1.5, self.usd) * 2
        assert result == Money(3, self.usd)


class TestDifferenceMoney:
    def setup_class(self):
        self.usd = Resource("USD", "USD")
        self.eur = Resource("EUR", "EUR")
        self.byn = Resource("BYN", "BYN")

    def test_currency_not_equal(self) -> None:
        assert Money(5, self.usd) != Money(5, self.eur)

    def test_currency_little(self) -> None:
        with pytest.raises(TypeError):
            _ = Money(3, self.usd) < Money(5, self.byn)

    def test_currency_sum(self) -> None:
        with pytest.raises(TypeError):
            Money(5, self.usd) + Money(7, self.eur)

    def test_currency_sub(self) -> None:
        with pytest.raises(TypeError):
            Money(5, self.usd) - Money(7, self.eur)

    def test_currency_multiply(self) -> None:
        with pytest.raises(TypeError):
            Money(3, self.usd) * Money(5, self.eur)

    def test_repr(self) -> None:
        assert repr(Money(5, self.usd)) == "Dollar(5)"

    def test_str(self) -> None:
        assert str(Money(5, self.usd)) == "5 $"
