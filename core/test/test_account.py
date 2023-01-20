import pytest
from core import Account, Money, Bank


class TestAccount:
    def setup_method(self) -> None:
        self.bank = Bank()
        self.bank.add_exchange('USD', 'BYN', 2.5)

    def test_get_currency(self) -> None:
        account = Account('BYN')
        assert account.value == Money.byn(0)

    def test_add_currency(self) -> None:
        account = Account('BYN')
        account.add(Money.byn(8), self.bank)
        assert account.value == Money.byn(8)

    def test_add_other_currency(self) -> None:
        account = Account('BYN')
        account.add(Money.dollar(4), self.bank)
        assert account.value == Money.byn(10)

    def test_remove_currency(self) -> None:
        account = Account('BYN')
        account.add(Money.byn(10), self.bank)
        account.remove(Money.byn(7), self.bank)
        assert account.value == Money.byn(3)

    def test_remove_other_currency(self) -> None:
        account = Account('BYN')
        account.add(Money.byn(10), self.bank)
        account.remove(Money.dollar(2), self.bank)
        assert account.value == Money.byn(5)

    def test_remove_bigger_currency(self) -> None:
        account = Account('BYN')
        account.add(Money.byn(10), self.bank)
        with pytest.raises(ValueError):
            account.remove(Money.byn(15), self.bank)
