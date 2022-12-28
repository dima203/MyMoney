from .money import Money


class Bank:
    def __init__(self) -> None:
        self.__exchanges = {}

    def add_exchange(self, currency: str, to: str, rate: float | int) -> None:
        self.__exchanges[(currency, to)] = rate

    def exchange(self, currency: Money, to: str) -> Money:
        if currency.currency == to:
            return currency

        if (currency.currency, to) not in self.__exchanges:
            raise KeyError(f'Exchange from {currency.currency} to {to} is not exist')

        return Money(currency.value * self.__exchanges[(currency.currency, to)], to)