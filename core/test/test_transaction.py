import datetime

from core import Bank, Account, Transaction, Money, Resource


class TestTransaction:
    def setup_method(self) -> None:
        self.byn = Resource(0, "BYN")
        self.usd = Resource(1, "USD")
        self.bank = Bank()
        self.bank.add_exchange(self.usd, self.byn, 2.5)
        self.account = Account("", "BYN", self.byn, 10)

    def test_transaction_create(self) -> None:
        Transaction(0, self.account, Money(10, self.byn), datetime.datetime.now())

    def test_transaction_accept(self) -> None:
        _ = Transaction(1, self.account, Money(10, self.byn), datetime.datetime.now())
        _.execute()
        assert self.account.get_balance() == Money(20, self.byn)

    def test_transaction_different_currency_accept(self) -> None:
        _ = Transaction(0, self.account, self.bank.exchange(Money(10, self.usd), self.byn), datetime.datetime.now())
        _.execute()
        assert self.account.get_balance() == Money(35, self.byn)

    def test_transaction_cancel(self) -> None:
        _ = Transaction(1, self.account, -Money(10, self.byn), datetime.datetime.now())
        _.execute()
        assert self.account.get_balance() == Money(0, self.byn)
        del _
        assert self.account.get_balance() == Money(10, self.byn)
