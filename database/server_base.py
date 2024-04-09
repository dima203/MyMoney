import requests

from .abstract_base import DataBase


class ServerBase(DataBase):
    def __init__(self, path: str, *args: str, **kwargs) -> None:
        super().__init__(path, *args)
        self._path = path
        self.__token = kwargs['token']

    def load(self) -> dict:
        data = requests.get(self._path, headers={'Authorization': f'Bearer {self.__token}'})
        return data.json()['results']

    def save(self, data: dict) -> None:
        pass
