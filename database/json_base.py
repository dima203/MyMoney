import json

from .abstract_base import DataBase


class JSONBase(DataBase):
    """Class for connect to JSON file as database"""

    def __init__(self, path: str, *args: str) -> None:
        super().__init__(path, *args)
        try:
            self.__last_pk = self.__get_last_pk()
        except FileNotFoundError:
            json.dump([], self._path.open("w"))
            self.__last_pk = 0

    def add(self, data: dict) -> int | None:
        loaded = json.load(self._path.open())
        new_pk = max(loaded, key=lambda item: item['pk'])['pk'] + 1
        data['pk'] = new_pk
        loaded.append(data)
        json.dump(loaded, self._path.open('w'), indent=2)
        return new_pk

    def load(self) -> list:
        return json.load(self._path.open())

    def update(self, pk: str | int, data: dict) -> None:
        loaded = json.load(self._path.open())
        data["pk"] = pk
        for obj in loaded:
            if obj["pk"] == pk:
                for key in obj:
                    obj[key] = data[key]
                break
        else:
            loaded.append(data)
        json.dump(loaded, self._path.open("w"), indent=2)

    def delete(self, pk: str | int) -> None:
        data: list[dict] = json.load(self._path.open())
        for obj in data:
            if obj["pk"] == pk:
                data.remove(obj)
                break
        json.dump(data, self._path.open("w"), indent=2)

    def add(self, data: dict) -> int | str:
        loaded = json.load(self._path.open())

        if data["pk"] is not None:
            self.__last_pk = data["pk"] if data["pk"] > self.__last_pk else self.__last_pk
        else:
            self.__last_pk += 1
            data["pk"] = self.__last_pk

        loaded.append(data)
        json.dump(loaded, self._path.open("w"), indent=2)
        return self.__last_pk

    def __get_last_pk(self) -> int | str:
        loaded = json.load(self._path.open())
        loaded.append({"pk": 0})
        return max(loaded, key=lambda obj: obj["pk"])["pk"]
