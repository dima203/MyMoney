import requests

from .abstract_base import DataBase


class ServerBase(DataBase):
    def __init__(self, path: str, *args: str, **kwargs) -> None:
        super().__init__(path, *args)
        self._path = path
        self.__token = kwargs['token']
        self.__session = requests.Session()
        self.__session.headers.update({'Authorization': f'Bearer {self.__token}'})

    def __del__(self) -> None:
        self.__session.close()

    def load(self) -> dict:
        data = self.__session.get(self._path)
        return data.json()['results']

    def save(self, data: dict) -> None:
        pass

    def delete(self, pk: str | int) -> None:
        self.__session.delete(f'{self._path}/{pk}')
