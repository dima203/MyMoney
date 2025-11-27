from datetime import datetime
from typing import Callable

from .storage import Storage
from .money import Money
from .resource import Resource


class Account(Storage):
    def __init__(self, pk: int, name: str, currency: Resource, value: float = 0) -> None:
        self.pk = pk
        self.name = name
        self.__subscribers = []
        self.value: Money = Money(value, currency)
        self.__saved_value: Money = Money(0, currency)

    def subscribe(self, callback: Callable[[int | str, dict], None]) -> None:
        """Subscribe callback function on account value change."""
        self.__subscribers.append(callback)

    def unsubscribe(self, callback: Callable[[int | str, dict], None]) -> None:
        """Unsubscribe callback function on account value change."""
        self.__subscribers.remove(callback)

    def get_balance(self) -> Money:
        return self.value

    def to_json(self) -> dict[str, str | int]:
        return {
            'pk': self.pk,
            'name': self.name,
            'resource_type': self.value.currency.pk,
            'resource_count': self.value.value,
            'last_update': datetime.now().isoformat()
        }

    def __changed(self) -> None:
        if self.__subscribers is None:
            return

        for subscriber in self.__subscribers:
            subscriber(self.pk, self.to_json())

    def __setattr__(self, key, value) -> None:
        if key not in self.__dict__:
            object.__setattr__(self, key, value)
            return

        object.__setattr__(self, key, value)
        self.__changed()

    def __eq__(self, other: 'Account') -> bool:
        return self.value == other.value
