import datetime

from core import Bank, Account, Transaction, Resource, Money


class TestTransaction:
    def setup_method(self) -> None:
        self.bank = Bank()
        self.bank.add_exchange('USD', 'BYN', 2.5)
        self.BYN = Resource(0, 'BYN')
        self.account = Account(0, 'test', self.BYN, 0)

    def test_transaction_create(self) -> None:
        Transaction(self.account, Money(10, self.BYN), datetime.datetime.now())
