import pytest
from core import Account, Money, Bank, Income


class TestAccount:
    def setup_method(self) -> None:
        self.bank = Bank()
        self.bank.add_exchange('USD', 'BYN', 2.5)

    def test_get_currency(self) -> None:
        account = Account('BYN')
        assert account.get_balance() == Money.byn(0)

    def test_account_sum(self) -> None:
        account = Account('BYN')
        account1 = Account('BYN')
        transaction1 = Income(account1, Money.byn(10), Bank())
        account2 = Account('BYN')
        transaction2 = Income(account2, Money.byn(10), Bank())
        account.add_source(account1)
        account.add_source(account2)
        assert account.get_balance() == Money.byn(20)
        del transaction1
        del transaction2
        assert account.get_balance() == Money.byn(0)
