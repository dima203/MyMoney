class Money:
    def __init__(self, value: float):
        self.value = value

    def __eq__(self, other: 'Money') -> bool:
        return (type(self) == type(other)) and (self.value == other.value)

    def __add__(self, other: 'Money') -> 'Money':
        if type(self) != type(other):
            raise TypeError('Cannot sum two different currency')
        return type(self)(self.value + other.value)

    def __mul__(self, other: int) -> 'Money':
        return type(self)(self.value * other)

    def __repr__(self) -> str:
        return f'{self.__class__.__name__}({self.value})'


class Dollar(Money):
    def __init__(self, value: float):
        super().__init__(value)


class Euro(Money):
    def __init__(self, value: float):
        super().__init__(value)
