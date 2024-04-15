from abc import ABC, abstractmethod
from pathlib import Path


class DataBase(ABC):
    """Abstract class for database interface"""

    def __init__(self, path: str, *args: str) -> None:
        self._path = Path(path)

    @abstractmethod
    def load(self) -> dict:
        """Load data from database connection"""
        pass

    @abstractmethod
    def save(self, data: dict) -> None:
        """Save data to database connection"""
        pass

    @abstractmethod
    def delete(self, pk: str | int) -> None:
        """Delete record from database"""
        pass
