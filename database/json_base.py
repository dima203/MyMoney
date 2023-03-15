from pathlib import Path
import json

from .abstract_base import DataBase


class JSONBase(DataBase):
    def __init__(self, path: str, *args: str) -> None:
        super().__init__(path, *args)

    def load(self) -> dict:
        try:
            return json.load(self._path.open())
        except FileNotFoundError:
            json.dump({}, self._path.open('w'))
            return json.load(self._path.open())

    def save(self, data: dict) -> None:
        json.dump(data, self._path.open("w"), indent=2)
