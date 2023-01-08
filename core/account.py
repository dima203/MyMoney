from .money import Money
from .exchange import Bank


class Account:
    def __init__(self, currency: str) -> None:
        self.value = Money(0, currency)

    def add(self, value: Money, bank: Bank) -> Money:
        self.value += bank.exchange(value, self.value.currency)
        return bank.exchange(value, self.value.currency)

    def remove(self, value: Money, bank: Bank) -> Money:
        if self.value < bank.exchange(value, self.value.currency):
            print(self.value, bank.exchange(value, self.value.currency))
            raise ValueError('Cannot sub bigger value from account')
        self.value -= bank.exchange(value, self.value.currency)
        return bank.exchange(value, self.value.currency)
