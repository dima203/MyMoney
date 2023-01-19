from typing import Self

from .money import Money
from .exchange import Bank


class Account:
    def __init__(self, currency: str) -> None:
        self.value: Money = Money(0, currency)
        self.__saved_value: Money = Money(0, currency)

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
