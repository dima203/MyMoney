from typing import Self
from weakref import ref, ReferenceType

from .storage import Storage
from .money import Money


class Account(Storage):
    def __init__(self, name: str, currency: str, sources: list[int | str] = None) -> None:
        self.id = name
        self.currency = currency
        self.__saved_value: Money = Money(0, currency)
        self.__sources = sources if sources is not None else []
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
        if source.id not in self.__sources:
            self.__sources.append(source.id)
        self.__transactions[source.id] = ref(source)

    def to_json(self) -> dict[str, str | int]:
        return {
            'currency': self.currency,
            'sources': list(filter(lambda key: True if isinstance(key, int) else False, self.__transactions.keys()))
        }

    def __eq__(self, other):
        return self.__sources == other.__sources and self.currency == other.currency
