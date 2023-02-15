from abc import ABC, abstractmethod

from .money import Money


class Storage(ABC):
    id = None

    @abstractmethod
    def get_balance(self) -> Money: ...

    @abstractmethod
    def to_json(self) -> dict[str, str | int]: ...
