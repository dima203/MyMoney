class Money:
    __currency_names = {
        'USD': 'Dollar',
        'EUR': 'Euro',
    }

    def __init__(self, value: float, currency: str):
        self.value = value
        self.currency = currency

    @staticmethod
    def dollar(value: float) -> 'Money':
        return Money(value, 'USD')

    @staticmethod
    def euro(value: float) -> 'Money':
        return Money(value, 'EUR')

    def __eq__(self, other: 'Money') -> bool:
        return (self.currency == other.currency) and (self.value == other.value)

    def __add__(self, other: 'Money') -> 'Money':
        if self.currency != other.currency:
            raise TypeError('Cannot sum two different currency')
        return Money(self.value + other.value, self.currency)

    def __mul__(self, other: float | int) -> 'Money':
        if not issubclass(type(other), (float, int)):
            raise TypeError(f'Cannot multiply currency on {type(other)}')
        return Money(self.value * other, self.currency)

    def __repr__(self) -> str:
        return f'{self.__currency_names[self.currency]}({self.value})'


class Bank:
    def __init__(self):
        self.__exchanges = {}

    def add_exchange(self, currency: str, to: str, rate: float | int) -> None:
        self.__exchanges[(currency, to)] = rate

    def exchange(self, currency: Money, to: str) -> Money:
        if currency.currency == to:
            return currency

        if (currency.currency, to) not in self.__exchanges:
            raise KeyError(f'Exchange from {currency.currency} to {to} is not exist')

        return Money(currency.value * self.__exchanges[(currency.currency, to)], to)
