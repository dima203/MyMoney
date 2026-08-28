from typing import Self

from .resource import Resource


class Money:
    __currency_names = {
        "USD": "Dollar",
        "EUR": "Euro",
        "RUB": "Ruble",
        "BYN": "Belarusian Ruble",
        "UAH": "Hryvnia",
        "GBP": "Pound",
        "CNY": "Yuan",
        "JPY": "Yen",
        "KZT": "Tenge",
        "PLN": "Zloty",
        "CZK": "Koruna",
        "BRL": "Real",
        "INR": "Rupee",
        "KRW": "Won",
        "BTC": "Bitcoin",
        "ETH": "Ethereum",
        "USDT": "Tether",
        "USDC": "USD Coin",
    }

    __currency_symbols = {
        "USD": "$",
        "EUR": "\u20ac",
        "RUB": "\u20bd",
        "GBP": "\u00a3",
        "JPY": "\u00a5",
        "CNY": "\u00a5",
        "KRW": "\u20a9",
        "PLN": "z\u0142",
        "BRL": "R$",
        "INR": "\u20b9",
        "UAH": "\u20b4",
        "KZT": "\u20b8",
        "CZK": "K\u010d",
    }

    def __init__(self, value: float, currency: Resource) -> None:
        self.value = value
        self.currency = currency

    def copy(self) -> "Money":
        return Money(self.value, self.currency)

    def __eq__(self, other: "Money | int | float") -> bool:
        if isinstance(other, int | float):
            return self.value == other
        if not isinstance(other, Money):
            return NotImplemented
        return (self.currency == other.currency) and (self.value == other.value)

    def __gt__(self, other: Self | int | float) -> bool:
        if isinstance(other, int | float):
            return self.value > other
        if not isinstance(other, Money):
            return NotImplemented
        if self.currency != other.currency:
            raise TypeError("Cannot compare different currency")
        return self.value > other.value

    def __lt__(self, other: Self | int | float) -> bool:
        if isinstance(other, int | float):
            return self.value < other
        if not isinstance(other, Money):
            return NotImplemented
        if self.currency != other.currency:
            raise TypeError("Cannot compare different currency")
        return self.value < other.value

    def __add__(self, other: Self | int | float) -> "Money":
        if isinstance(other, (int, float)):
            return Money(self.value + other, self.currency)
        if not isinstance(other, Money):
            return NotImplemented
        if self.currency != other.currency:
            raise TypeError("Cannot sum two different currency")
        return Money(self.value + other.value, self.currency)

    def __sub__(self, other: Self | int | float) -> "Money":
        if isinstance(other, (int, float)):
            return Money(self.value - other, self.currency)
        if not isinstance(other, Money):
            return NotImplemented
        if self.currency != other.currency:
            raise TypeError("Cannot sub two different currency")
        return Money(self.value - other.value, self.currency)

    def __mul__(self, other: float | int) -> "Money":
        if not isinstance(other, (float, int)):
            return NotImplemented
        return Money(self.value * other, self.currency)

    def __rmul__(self, other: float | int) -> "Money":
        return self.__mul__(other)

    def __neg__(self) -> Self:
        return Money(-self.value, self.currency)

    def __abs__(self) -> Self:
        return self if self > 0 else -self

    def __repr__(self) -> str:
        name = self.__currency_names.get(self.currency.name, self.currency.name)
        return f"Money({self.value}, {name})"

    def __str__(self) -> str:
        symbol = self.__currency_symbols.get(self.currency.name, self.currency.name)
        return f"{self.value} {symbol}"
