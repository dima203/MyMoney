import pytest

from core import Money, Bank, Resource


class TestBankExchange:
    def setup_class(self):
        self.usd = Resource("USD", "USD")
        self.eur = Resource("EUR", "EUR")
        self.rub = Resource("RUB", "RUB")
        self.bank = Bank()
        self.bank.add_exchange(self.usd, self.eur, 0.9)
        self.bank.add_exchange(self.eur, self.usd, 1.1)

    def test_simple_exchange(self):
        result = self.bank.exchange(Money(5, self.usd), self.eur)
        assert result == (Money(5, self.eur) * 0.9)

    def test_exchange_with_sum(self):
        result = Money(13, self.usd) + self.bank.exchange(Money(5, self.eur), self.usd)
        assert result == Money(18.5, self.usd)

    def test_self_exchange(self):
        result = self.bank.exchange(Money(5, self.usd), self.usd)
        assert result == Money(5, self.usd)

    def test_key_error_exchange(self):
        with pytest.raises(KeyError):
            self.bank.exchange(Money(5, self.usd), self.rub)
