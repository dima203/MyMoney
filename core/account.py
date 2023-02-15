from typing import Self
from weakref import ref, ReferenceType

from .storage import Storage
from .money import Money
from .exchange import Bank


class Account(Storage):
    def __init__(self, currency: str) -> None:
        self.currency = currency
        self.__saved_value: Money = Money(0, currency)
        self.__transactions: list[ReferenceType] = []

    def get_balance(self) -> Money:
        result = Money(0, self.currency)
        deleted_transactions = []
        for transaction in self.__transactions:
            if transaction() is None:
                deleted_transactions.append(transaction)
            else:
                result += transaction().get_balance()
        for deleted in deleted_transactions:
            self.__transactions.remove(deleted)
        return result

    def add_source(self, source: Storage):
        self.__transactions.append(ref(source))

    def add(self, value: Money, bank: Bank) -> Money:
        """
        Add value of money to account.

        :param value: amount of money to add
        :type value: Money
        :param bank: bank to exchange value to expected currency
        :type bank: Bank
        :return: amount of added money in expected currency
        :rtype: Money
        """
        self.value += bank.exchange(value, self.value.currency)
        return bank.exchange(value, self.value.currency)

    def remove(self, value: Money, bank: Bank) -> Money:
        if self.value < bank.exchange(value, self.value.currency):
            raise ValueError('Cannot sub bigger value from account')
        self.value -= bank.exchange(value, self.value.currency)
        return bank.exchange(value, self.value.currency)

    def __enter__(self) -> Self:
        self.__saved_value = self.value
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
        if exc_type is not None:
            self.value = self.__saved_value
        return True

    def to_json(self) -> dict[str, str | int]:
        return {
            'value': self.value.value,
            'currency': self.value.currency
        }
