import pytest

from core import Money, Bank


class TestBankExchange:
    def setup_method(self):
        self.bank = Bank()
        self.bank.add_exchange("USD", "EUR", 0.9)
        self.bank.add_exchange("EUR", "USD", 1.1)

    def test_simple_exchange(self):
        result = self.bank.exchange(Money.dollar(5), "EUR")
        assert result == (Money.euro(5) * 0.9)

    def test_exchange_with_sum(self):
        result = Money.dollar(13) + self.bank.exchange(Money.euro(5), "USD")
        assert result == Money.dollar(18.5)

    def test_self_exchange(self):
        result = self.bank.exchange(Money.dollar(5), "USD")
        assert result == Money.dollar(5)

    def test_key_error_exchange(self):
        with pytest.raises(KeyError):
            self.bank.exchange(Money.dollar(5), "RUB")
