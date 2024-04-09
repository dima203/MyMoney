class Money:
    __currency_names = {
        'USD': ('Dollar', '$'),
        'EUR': ('Euro', '€'),
        'RUB': ('Rub', '₽'),
        'BYN': ('Byn', 'BYN')
    }

    def __init__(self, value: float, currency: str) -> None:
        self.value = value
        self.currency = currency

    @staticmethod
    def dollar(value: float) -> 'Money':
        return Money(value, 'USD')

    @staticmethod
    def euro(value: float) -> 'Money':
        return Money(value, 'EUR')

    @staticmethod
    def rub(value: float) -> 'Money':
        return Money(value, 'RUB')

    @staticmethod
    def byn(value: float) -> 'Money':
        return Money(value, 'BYN')

    def __eq__(self, other: 'Money') -> bool:
        if isinstance(other, int | float):
            return self.value == other
        return (self.currency == other.currency) and (self.value == other.value)

    def __gt__(self, other: 'Money') -> bool:
        if isinstance(other, int | float):
            return self.value < other
        if self.currency != other.currency:
            raise TypeError('Cannot compare different currency')
        return self.value < other.value

    def __lt__(self, other: 'Money') -> bool:
        if isinstance(other, int | float):
            return self.value < other
        if self.currency != other.currency:
            raise TypeError('Cannot compare different currency')
        return self.value < other.value

    def __add__(self, other: 'Money') -> 'Money':
        if self.currency != other.currency:
            raise TypeError('Cannot sum two different currency')
        return Money(self.value + other.value, self.currency)

    def __sub__(self, other: 'Money') -> 'Money':
        if self.currency != other.currency:
            raise TypeError('Cannot sub two different currency')
        return Money(self.value - other.value, self.currency)

    def __mul__(self, other: float | int) -> 'Money':
        if not issubclass(type(other), (float, int)):
            raise TypeError(f'Cannot multiply currency on {type(other)}')
        return Money(self.value * other, self.currency)

    def __neg__(self) -> 'Money':
        return Money(-self.value, self.currency)

    def __abs__(self) -> 'Money':
        return self if self > 0 else -self

    def __repr__(self) -> str:
        return f'{self.__currency_names[self.currency][0]}({self.value})'

    def __str__(self) -> str:
        return f'{self.value} {self.__currency_names[self.currency][1]}'
