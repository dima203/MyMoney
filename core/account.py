from typing import Self
from weakref import ref, ReferenceType

from .storage import Storage
from .money import Money


class Account(Storage):
    def __init__(self, name: str, currency: str, sources: list[int | str] = None) -> None:
        self.id = name
        self.currency = currency
        self.__saved_value: Money = Money(0, currency)
        self.__sources = sources
        self.__transactions: dict[int | str, ReferenceType] = {}

    def get_balance(self) -> Money:
        result = Money(0, self.currency)
        deleted_transactions = []
        for key, transaction in self.__transactions.items():
            if transaction() is None:
                deleted_transactions.append(key)
            else:
                result += transaction().get_balance()
        for deleted in deleted_transactions:
            del self.__transactions[deleted]
        return result

    def get_sources(self) -> list[int | str]:
        return self.__sources

    def add_source(self, source: Storage) -> None:
        self.__transactions[source.id] = ref(source)

    def __enter__(self) -> Self:
        self.__saved_value = self.value
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
        if exc_type is not None:
            self.value = self.__saved_value
        return True

    def to_json(self) -> dict[str, str | int]:
        return {
            'currency': self.currency,
            'sources': list(filter(lambda key: True if isinstance(key, int) else False, self.__transactions.keys()))
        }
