from abc import ABC, abstractmethod

from .account import Account
from .exchange import Bank
from .money import Money


class Transaction(ABC):
    def __init__(self, account: Account, currency: Money) -> None:
        self._account = account
        self._currency = currency
        self._transaction_bank = Bank()

    @abstractmethod
    def accept(self, bank: Bank) -> None:
        pass

    @abstractmethod
    def cancel(self) -> None:
        pass


class Transfer(Transaction):
    def __init__(self, account: Account, target_account: Account, currency: Money) -> None:
        super().__init__(account, currency)
        self._target_account = target_account

    def accept(self, bank: Bank) -> None:
        with self._target_account as target:
            target.add(self._currency, bank)
            self._account.remove(self._currency, bank)
            self._transaction_bank = bank

    def cancel(self) -> None:
        with self._account as account:
            account.add(self._currency, self._transaction_bank)
            self._target_account.remove(self._currency, self._transaction_bank)


class Income(Transaction):
    def accept(self, bank: Bank) -> None:
        self._account.add(self._currency, bank)
        self._transaction_bank = bank

    def cancel(self) -> None:
        with self._account as account:
            account.remove(self._currency, self._transaction_bank)


class Expense(Transaction):
    def accept(self, bank: Bank) -> None:
        with self._account as account:
            account.remove(self._currency, bank)
            self._transaction_bank = bank

    def cancel(self) -> None:
        self._account.add(self._currency, self._transaction_bank)
