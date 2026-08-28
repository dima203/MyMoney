from typing import Callable

from .money import Money
from .resource import Resource


class Account:
    def __init__(
        self,
        pk: int | str,
        name: str,
        currency: Resource,
        value: float = 0,
        *,
        group: str = "",
        account_type: str = "main",
    ) -> None:
        self.pk = pk
        self.name = name
        self.group = group
        self.account_type = account_type
        self.__subscribers: list[Callable] = []
        self.value: Money = Money(value, currency)

    def subscribe(self, callback: Callable[[int | str, dict], None]) -> None:
        self.__subscribers.append(callback)

    def unsubscribe(self, callback: Callable[[int | str, dict], None]) -> None:
        self.__subscribers.remove(callback)

    def get_balance(self) -> Money:
        return self.value

    def to_json(self) -> dict[str, str | int | float]:
        return {
            "id": self.pk,
            "name": self.name,
            "group": self.group,
            "account_type": self.account_type,
            "resource_definition": self.value.currency.pk,
            "current_balance_qty": self.value.value,
        }

    def _notify(self) -> None:
        for subscriber in self.__subscribers:
            subscriber(self.pk, self.to_json())

    def __setattr__(self, key, value) -> None:
        object.__setattr__(self, key, value)
        if key in ("name", "group", "account_type") and "_Account__subscribers" in self.__dict__:
            self._notify()

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Account):
            return NotImplemented
        return self.pk == other.pk

    def __hash__(self) -> int:
        return hash(self.pk)
