import requests

from .abstract_base import DataBase


class ServerBase(DataBase):
    def __init__(self, path: str, *, token, base_url: str = "", get_refresh_token=None) -> None:
        super().__init__(path)
        self._path = path
        self.__base_url = base_url
        self.__get_refresh_token = get_refresh_token

        if not self._path.startswith("http"):
            self.__session = None
            return

        self.__token = token
        self.__session = requests.Session()
        self.__session.trust_env = False
        self.__session.headers.update({"Authorization": f"Bearer {self.__token}"})

    def __del__(self) -> None:
        if self.__session is None:
            return

        self.__session.close()

    def _refresh_token(self) -> bool:
        if self.__get_refresh_token is None or self.__base_url == "":
            return False

        refresh_token = self.__get_refresh_token()
        if not refresh_token:
            return False

        try:
            response = requests.post(
                f"{self.__base_url}api/v1/auth/token/refresh/",
                json={"refresh": refresh_token},
                proxies={"http": None, "https": None},
            )
            if response.status_code == 200:
                data = response.json()
                self.__token = data["access"]
                self.__session.headers.update({"Authorization": f"Bearer {self.__token}"})
                return True
        except Exception:
            pass

        return False

    def _request(self, method: str, url: str, **kwargs) -> requests.Response:
        response = self.__session.request(method, url, **kwargs)
        if response.status_code == 401 and self._refresh_token():
            response = self.__session.request(method, url, **kwargs)
        return response

    def load(self) -> list:
        if self.__session is None:
            return []

        data = self._request("GET", self._path)
        return data.json()["results"]

    def add(self, data: dict) -> int | None:
        if self.__session is None:
            return None

        response = self._request("POST", self._path, json=data)
        return response.json()["pk"]

    def update(self, pk: str | int, data: dict) -> None:
        if self.__session is None:
            return

        self._request("PATCH", f"{self._path}{pk}", json=data)

    def delete(self, pk: str | int) -> None:
        if self.__session is None:
            return

        self._request("DELETE", f"{self._path}{pk}")
