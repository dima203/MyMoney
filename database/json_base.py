import json

from .abstract_base import DataBase


class JSONBase(DataBase):
    """Class for connect to JSON file as database"""

    def __init__(self, path: str, *args: str) -> None:
        super().__init__(path, *args)

    def add(self, data: dict) -> int | None:
        loaded = json.load(self._path.open())
        new_pk = max(loaded, key=lambda item: item['pk'])['pk'] + 1
        data['pk'] = new_pk
        loaded.append(data)
        json.dump(loaded, self._path.open('w'), indent=2)
        return new_pk

    def load(self) -> list:
        try:
            return json.load(self._path.open())
        except FileNotFoundError:
            json.dump([], self._path.open('w'))
            return json.load(self._path.open())

    def update(self, pk: str | int, data: dict) -> None:
        loaded = json.load(self._path.open())
        data['pk'] = pk
        for obj in loaded:
            if obj['pk'] == pk:
                for key in obj:
                    obj[key] = data[key]
                break
        else:
            loaded.append(data)
        json.dump(loaded, self._path.open('w'), indent=2)

    def delete(self, pk: str | int) -> None:
        data = json.load(self._path.open())
        for obj in data:
            if obj['pk'] == pk:
                del obj
                break
        json.dump(data, self._path.open('w'), indent=2)
