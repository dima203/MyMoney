from abc import ABC, abstractmethod

from .storage import Storage
from .account import Account
from .exchange import Bank
from .money import Money


class Transaction(Storage):
    def __init__(self, currency: Money) -> None:
        self._value = currency

    def get_balance(self) -> Money:
        return self._value

    def to_json(self) -> dict[str, str | int]:
        return {
            'value': self._value.value,
            'currency': self._value.currency
        }


class Transfer(Transaction):
    def __init__(self, account: Account, target_account: Account, currency: Money, bank: Bank) -> None:
        super().__init__(currency)
        self.income = Income(target_account, currency, bank)
        self.expense = Expense(account, currency, bank)

    def __del__(self):
        del self.income
        del self.expense


class Income(Transaction):
    def __init__(self, account: Account, currency: Money, bank: Bank) -> None:
        super().__init__(bank.exchange(currency, account.currency))
        account.add_source(self)


class Expense(Transaction):
    def __init__(self, account: Account, currency: Money, bank: Bank) -> None:
        super().__init__(-bank.exchange(currency, account.currency))
        account.add_source(self)
