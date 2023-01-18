from abc import ABC, abstractmethod

from .account import Account
from .exchange import Bank
from .money import Money


class Transaction(ABC):
    def __init__(self, account: Account, currency: Money) -> None:
        self._account = account
        self._currency = currency

    @abstractmethod
    def accept(self, bank: Bank) -> None:
        pass


class Transfer(Transaction):
    def __init__(self, account: Account, target_account: Account, currency: Money) -> None:
        super().__init__(account, currency)
        self._target_account = target_account

    def accept(self, bank: Bank) -> None:
        self._target_account.add(self._currency, bank)
        self._account.remove(self._currency, bank)
