from __future__ import annotations

from .abstract_base import DataBase


class ServerBase(DataBase):
    def __init__(self, path: str, *, rest_client=None) -> None:
        super().__init__(path)
        self._path = path
        self._rest_client = rest_client
        self._is_online = True
        self._temp_pk_counter = -1

    @property
    def is_online(self) -> bool:
        return self._is_online

    def load(self) -> list:
        if self._rest_client is None:
            return []
        try:
            if "resources" in self._path:
                data = self._rest_client.list_resources()
            elif "accounts" in self._path:
                data = self._rest_client.list_accounts()
            elif "transactions" in self._path and "planned" not in self._path:
                data = self._rest_client.list_transactions()
            elif "planned" in self._path:
                data = self._rest_client.list_planned_transactions()
            else:
                data = []
            self._is_online = True
            if isinstance(data, list):
                return data
            return data.get("results", [])
        except Exception:
            self._is_online = False
            return []

    def add(self, data: dict) -> int | None:
        if self._rest_client is None:
            return None
        try:
            if "resources" in self._path:
                result = self._rest_client.create_resource(data)
            elif "accounts" in self._path:
                result = self._rest_client.create_account(data)
            elif "transactions" in self._path and "planned" not in self._path:
                result = self._rest_client.create_transaction(data)
            elif "planned" in self._path:
                result = self._rest_client.list_planned_transactions()
                return None
            else:
                return None
            self._is_online = True
            return result.get("id") if isinstance(result, dict) else None
        except Exception:
            self._is_online = False
            self._temp_pk_counter -= 1
            return self._temp_pk_counter

    def update(self, pk: str | int, data: dict) -> None:
        if self._rest_client is None:
            return
        try:
            if "resources" in self._path:
                self._rest_client.delete_resource(pk)
            elif "accounts" in self._path:
                self._rest_client.update_account(pk, data)
            elif "transactions" in self._path and "planned" not in self._path:
                self._rest_client.update_transaction(pk, data)
            self._is_online = True
        except Exception:
            self._is_online = False

    def delete(self, pk: str | int) -> None:
        if self._rest_client is None:
            return
        try:
            if "resources" in self._path:
                self._rest_client.delete_resource(pk)
            elif "accounts" in self._path:
                self._rest_client.delete_account(pk)
            elif "transactions" in self._path and "planned" not in self._path:
                self._rest_client.delete_transaction(pk)
            self._is_online = True
        except Exception:
            self._is_online = False
