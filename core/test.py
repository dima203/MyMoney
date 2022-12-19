import pytest

from .main import Money, Bank


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


class TestBankExchange:
    def setup_method(self):
        self.bank = Bank()
        self.bank.add_exchange('USD', 'EUR', 0.9)
        self.bank.add_exchange('EUR', 'USD', 1.1)

    def test_simple_exchange(self):
        result = self.bank.exchange(Money.dollar(5), 'EUR')
        assert result == (Money.euro(5) * 0.9)

    def test_exchange_with_sum(self):
        result = Money.dollar(13) + self.bank.exchange(Money.euro(5), 'USD')
        assert result == Money.dollar(18.5)

    def test_self_exchange(self):
        result = self.bank.exchange(Money.dollar(5), 'USD')
        assert result == Money.dollar(5)

    def test_key_error_exchange(self):
        with pytest.raises(KeyError):
            self.bank.exchange(Money.dollar(5), 'RUB')
