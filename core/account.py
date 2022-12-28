from .money import Money
from .exchange import Bank


class Account:
    def __init__(self, currency: str) -> None:
        self.value = Money(0, currency)

    def add(self, value: Money, bank: Bank) -> None:
        self.value += bank.exchange(value, self.value.currency)
