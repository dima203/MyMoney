from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

from MySpaceShared.database.json_base import JSONBase
from MySpaceShared.database.pending_store import PendingStore
from MySpaceShared.database.server_base import ServerBase


class OfflineView:
    def __init__(
        self,
        entity_name: str,
        rest_client,
        cache_path: str,
        pending_path: str,
        methods: dict | None = None,
    ) -> None:
        self._entity_name = entity_name
        self._rest_client = rest_client
        self._server = ServerBase(cache_path, rest_client=rest_client, methods=methods or {})
        self._cache = JSONBase(cache_path)
        self._pending = PendingStore(pending_path)
        self._pending_registry: dict[str, callable] = {}

    @property
    def is_online(self) -> bool:
        return self._server.is_online

    def get_all(self) -> list[dict]:
        server_data = self._server.load()
        if server_data:
            self._save_cache(server_data)
            return server_data
        return self._cache.load()

    def get(self, pk: int | str) -> dict | None:
        for item in self.get_all():
            if item.get("id") == pk or item.get("pk") == pk:
                return item
        return None

    def add(self, data: dict) -> int | None:
        pk = self._server.add(data)
        cached = self._cache.load()
        entry = dict(data)
        if pk is not None:
            entry["id"] = pk
        cached.append(entry)
        self._write_cache(cached)
        if pk is not None and pk < 0:
            self._pending.add("add", self._entity_name, pk, data)
        return pk

    def update(self, pk: int | str, data: dict) -> None:
        self._server.update(pk, data)
        if not self._server.is_online:
            real_pk = data.pop("id", data.pop("pk", pk))
            self._pending.add("update", self._entity_name, pk, {"id": real_pk, **data})
        cached = self._cache.load()
        for item in cached:
            if item.get("id") == pk or item.get("pk") == pk:
                item.update(data)
                break
        self._write_cache(cached)

    def delete(self, pk: int | str) -> None:
        self._server.delete(pk)
        if not self._server.is_online:
            self._pending.add("delete", self._entity_name, pk, {"id": pk})
        cached = self._cache.load()
        cached = [item for item in cached if item.get("id") != pk and item.get("pk") != pk]
        self._write_cache(cached)

    def sync_pending(self) -> dict[int, int]:
        return self._pending.sync(self._pending_registry)

    def _save_cache(self, data: list[dict]) -> None:
        self._write_cache(data)

    def _write_cache(self, data: list[dict]) -> None:
        cache_path = Path(self._cache._path)
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp_path = tempfile.mkstemp(dir=cache_path.parent, suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            os.replace(tmp_path, cache_path)
        except Exception:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
            raise


class ResourceView(OfflineView):
    def __init__(self, rest_client, data_dir: str) -> None:
        methods = {
            "list": rest_client.list_resources,
            "create": rest_client.create_resource,
        }
        super().__init__(
            entity_name="resource",
            rest_client=rest_client,
            cache_path=os.path.join(data_dir, "resources.json"),
            pending_path=os.path.join(data_dir, "pending_resources.json"),
            methods=methods,
        )
        self._pending_registry = {
            "create_resource": rest_client.create_resource,
        }


class AccountView(OfflineView):
    def __init__(self, rest_client, data_dir: str) -> None:
        methods = {
            "list": rest_client.list_accounts,
            "create": rest_client.create_account,
            "update": rest_client.update_account,
            "delete": rest_client.delete_account,
        }
        super().__init__(
            entity_name="account",
            rest_client=rest_client,
            cache_path=os.path.join(data_dir, "accounts.json"),
            pending_path=os.path.join(data_dir, "pending_accounts.json"),
            methods=methods,
        )
        self._pending_registry = {
            "create_account": rest_client.create_account,
            "update_account": rest_client.update_account,
            "delete_account": rest_client.delete_account,
        }


class TransactionView(OfflineView):
    def __init__(self, rest_client, data_dir: str) -> None:
        methods = {
            "list": rest_client.list_transactions,
            "create": rest_client.create_transaction,
            "update": rest_client.update_transaction,
            "delete": rest_client.delete_transaction,
        }
        super().__init__(
            entity_name="transaction",
            rest_client=rest_client,
            cache_path=os.path.join(data_dir, "transactions.json"),
            pending_path=os.path.join(data_dir, "pending_transactions.json"),
            methods=methods,
        )
        self._pending_registry = {
            "create_transaction": rest_client.create_transaction,
            "update_transaction": rest_client.update_transaction,
            "delete_transaction": rest_client.delete_transaction,
        }

    def get_planned(self) -> list[dict]:
        all_txs = self.get_all()
        return [tx for tx in all_txs if tx.get("is_planned")]
