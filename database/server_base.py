import requests

from .abstract_base import DataBase


class ServerBase(DataBase):
    def __init__(self, path: str, *, token) -> None:
        super().__init__(path)
        self._path = path

        if not self._path.startswith("http"):
            self.__session = None
            return

        self.__token = token
        self.__session = requests.Session()
        self.__session.headers.update({"Authorization": f"Bearer {self.__token}"})

    def __del__(self) -> None:
        if self.__session is None:
            return

        self.__session.close()

    def load(self) -> list:
        if self.__session is None:
            return []

        data = self.__session.get(self._path)
        return data.json()["results"]

    def add(self, data: dict) -> int | None:
        if self.__session is None:
            return None

        response = self.__session.post(self._path, data=data)
        return response.json()["pk"]

    def update(self, pk: str | int, data: dict) -> None:
        if self.__session is None:
            return

        self.__session.patch(f"{self._path}/{pk}", data=data)

    def delete(self, pk: str | int) -> None:
        if self.__session is None:
            return

        self.__session.delete(f"{self._path}/{pk}")
