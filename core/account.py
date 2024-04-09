from weakref import ref, ReferenceType

from .storage import Storage
from .money import Money


class Account(Storage):
    def __init__(self, name: str, currency: str, value: float = None) -> None:
        self.id = name
        self.value: Money = Money(value, currency)
        self.__saved_value: Money = Money(0, currency)
        self.__transactions: dict[int | str, ReferenceType] = {}

    def get_balance(self) -> Money:
        return self.value

    def to_json(self) -> dict[str, str | int]:
        return {
            'resource_type': self.currency,
            'resource_count': list(filter(lambda key: True if isinstance(key, int) else False, self.__transactions.keys()))
        }

    def __eq__(self, other: 'Account') -> bool:
        return self.__value == other.__value and self.currency == other.currency
