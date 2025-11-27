import datetime

from core import Bank, Account, Transaction, Money, Resource


class TestTransaction:
    def setup_method(self) -> None:
        self.bank = Bank()
        self.bank.add_exchange("USD", "BYN", 2.5)
        self.byn = Resource(0, "BYN")
        self.usd = Resource(1, "USD")
        self.account = Account("", "BYN", self.byn, 10)

    def test_transaction_create(self) -> None:
        Transaction(0, self.account, Money(10, self.byn), datetime.datetime.now())

    def test_transaction_accept(self) -> None:
        _ = Transaction(1, self.account, Money.byn(10), datetime.datetime.now())
        assert self.account.get_balance() == Money.byn(20)

    def test_transaction_different_currency_accept(self) -> None:
        _ = Transaction(0, self.account, Money.dollar(10), datetime.datetime.now())
        assert self.account.get_balance() == Money.byn(35)

    def test_transaction_cancel(self) -> None:
        _ = Transaction(1, self.account, -Money.byn(10), datetime.datetime.now())
        assert self.account.get_balance() == Money.byn(0)
        del _
        assert self.account.get_balance() == Money.byn(10)
