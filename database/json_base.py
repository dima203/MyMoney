import json
import os
import tempfile

from .abstract_base import DataBase


class JSONBase(DataBase):
    def __init__(self, path: str, *args: str) -> None:
        super().__init__(path, *args)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        if not self._path.exists():
            self._atomic_write([])
        self._last_pk = self._get_last_pk()

    @property
    def is_online(self) -> bool:
        return True

    def load(self) -> list:
        try:
            with self._path.open("r", encoding="utf-8") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return []

    def add(self, data: dict) -> int | str:
        loaded = self.load()
        pk = data.get("id") or data.get("pk")
        if pk is not None:
            self._last_pk = pk if pk > self._last_pk else self._last_pk
        else:
            self._last_pk += 1
            pk = self._last_pk
            data["id"] = pk
        loaded.append(data)
        self._atomic_write(loaded)
        return pk

    def update(self, pk: str | int, data: dict) -> None:
        loaded = self.load()
        data["id"] = pk
        for obj in loaded:
            if obj.get("id") == pk or obj.get("pk") == pk:
                obj.update(data)
                break
        else:
            loaded.append(data)
        self._atomic_write(loaded)

    def delete(self, pk: str | int) -> None:
        data = self.load()
        data = [obj for obj in data if obj.get("id") != pk and obj.get("pk") != pk]
        self._atomic_write(data)

    def _get_last_pk(self) -> int | str:
        loaded = self.load()
        if not loaded:
            return 0
        return max(loaded, key=lambda obj: obj.get("id", obj.get("pk", 0))).get("id", 0)

    def _atomic_write(self, data: list) -> None:
        dir_path = self._path.parent
        fd, tmp_path = tempfile.mkstemp(dir=dir_path, suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            os.replace(tmp_path, self._path)
        except Exception:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
            raise
