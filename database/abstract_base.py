from abc import ABC, abstractmethod
from pathlib import Path


class DataBase(ABC):
    def __init__(self, path: str, *args: str) -> None:
        self._path = Path(path)

    @abstractmethod
    def load(self) -> dict: ...

    @abstractmethod
    def save(self, data: dict) -> None: ...
