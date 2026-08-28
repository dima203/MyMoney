import datetime
from typing import Callable

from .journal_entry import JournalEntry


class Transaction:
    def __init__(
        self,
        pk: int | str,
        date: datetime.datetime,
        entries: list[JournalEntry] | None = None,
        *,
        category: str = "",
        description: str = "",
        recurrence_rule: str = "",
        is_planned: bool = False,
    ) -> None:
        self.pk = pk
        self.date = date
        self.entries: list[JournalEntry] = entries or []
        self.category = category
        self.description = description
        self.recurrence_rule = recurrence_rule
        self.is_planned = is_planned
        self.__subscribers: list[Callable] = []

    def subscribe(self, callback: Callable[[int | str, dict], None]) -> None:
        self.__subscribers.append(callback)

    def unsubscribe(self, callback: Callable[[int | str, dict], None]) -> None:
        self.__subscribers.remove(callback)

    def to_json(self) -> dict:
        return {
            "id": self.pk,
            "date": self.date.isoformat(),
            "entries": [e.to_json() for e in self.entries],
            "category": self.category,
            "description": self.description,
            "recurrence_rule": self.recurrence_rule,
            "is_planned": self.is_planned,
        }

    def _notify(self) -> None:
        for subscriber in self.__subscribers:
            subscriber(self.pk, self.to_json())

    def __setattr__(self, key, value) -> None:
        object.__setattr__(self, key, value)
        if (
            key in ("category", "description", "recurrence_rule", "is_planned", "entries")
            and "_Transaction__subscribers" in self.__dict__
        ):
            self._notify()
