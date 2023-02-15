from abc import ABC, abstractmethod

from .storage import Storage
from .account import Account
from .exchange import Bank
from .money import Money


class Transaction(Storage):
    def __init__(self, currency: Money) -> None:
        self._value = currency
        self._transaction_bank = Bank()

    def get_balance(self) -> Money:
        return self._value

    def to_json(self) -> dict[str, str | int]:
        return {
            'value': self._value.value,
            'currency': self._value.currency
        }


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
