from .storage import Storage
from .money import Money
from .resource import Resource


class Account(Storage):
    def __init__(self, name: str, currency: Resource, value: float = 0) -> None:
        self.name = name
        self.value: Money = Money(value, currency)
        self.__saved_value: Money = Money(0, currency)

    def get_balance(self) -> Money:
        return self.value

    def to_json(self) -> dict[str, str | int]:
        return {
            'name': self.name,
            'resource_type': self.value.currency.pk,
            'resource_count': self.value.value,
        }

    def __eq__(self, other: 'Account') -> bool:
        return self.value == other.value
