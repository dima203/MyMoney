import json
import os
import tempfile
from pathlib import Path


class PendingStore:
    def __init__(self, path: str) -> None:
        self._path = Path(path)
        self._pending: list[dict] = []
        self._load()

    def _load(self) -> None:
        if not self._path.exists():
            self._pending = []
            return
        try:
            self._pending = json.loads(self._path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            self._pending = []

    def _save(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp_path = tempfile.mkstemp(dir=self._path.parent, suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(self._pending, f, indent=2, default=str, ensure_ascii=False)
            os.replace(tmp_path, self._path)
        except Exception:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
            raise

    def add(self, operation: str, entity: str, temp_pk: int, data: dict) -> None:
        self._pending.append(
            {
                "operation": operation,
                "entity": entity,
                "temp_pk": temp_pk,
                "data": data,
            }
        )
        self._save()

    def get_all(self) -> list[dict]:
        return list(self._pending)

    def clear(self) -> None:
        self._pending = []
        self._save()

    def remove_by_temp_pk(self, temp_pk: int) -> None:
        self._pending = [op for op in self._pending if op.get("temp_pk") != temp_pk]
        self._save()

    def sync(self, rest_client) -> dict[int, int]:
        remap: dict[int, int] = {}
        remaining: list[dict] = []

        for op in self._pending:
            entity = op["entity"]
            operation = op["operation"]
            temp_pk = op["temp_pk"]
            data = op["data"]

            try:
                if operation == "add":
                    if entity == "resource":
                        result = rest_client.create_resource(data)
                    elif entity == "account":
                        result = rest_client.create_account(data)
                    elif entity == "transaction":
                        result = rest_client.create_transaction(data)
                    else:
                        remaining.append(op)
                        continue

                    real_pk = result.get("id") if isinstance(result, dict) else None
                    if real_pk is not None:
                        remap[temp_pk] = real_pk
                    else:
                        remaining.append(op)

                elif operation == "update":
                    pk = data.pop("id", data.pop("pk", temp_pk))
                    if entity == "resource":
                        rest_client.update_resource(pk, data)
                    elif entity == "account":
                        rest_client.update_account(pk, data)
                    elif entity == "transaction":
                        rest_client.update_transaction(pk, data)
                    else:
                        remaining.append(op)

                elif operation == "delete":
                    pk = data.get("id", data.get("pk", temp_pk))
                    if entity == "resource":
                        rest_client.delete_resource(pk)
                    elif entity == "account":
                        rest_client.delete_account(pk)
                    elif entity == "transaction":
                        rest_client.delete_transaction(pk)
                    else:
                        remaining.append(op)

            except Exception:
                remaining.append(op)

        self._pending = remaining
        self._save()
        return remap
