import json
import os
from pathlib import Path

import pytest

from database import JSONBase


class TestJSONBaseLoad:
    def setup_class(self) -> None:
        self.load_database = JSONBase(str(Path.cwd() / "database/test/test_data.json"))

    def test_database_load_data(self) -> None:
        data = self.load_database.load()
        data = data[0]
        assert data["resource_count"] == 10
        assert data["resource_type"] == 1

    def test_database_load_non_exist_file(self, tmp_path) -> None:
        path = tmp_path / "new.json"
        assert not path.exists()
        base = JSONBase(str(path))
        assert base.load() == []
        assert path.exists()


class TestJSONBaseAdd:
    def setup_method(self) -> None:
        self.path = Path.cwd() / "database/test/test_add_data.json"
        self.db = JSONBase(str(self.path))

    def teardown_method(self) -> None:
        if self.path.exists():
            os.remove(self.path)

    def test_add_first_record(self):
        pk = self.db.add({"pk": None, "name": "test", "value": 10})
        assert pk == 1
        data = self.db.load()
        assert len(data) == 1
        assert data[0]["pk"] == 1

    def test_add_multiple_records(self):
        self.db.add({"pk": None, "name": "first"})
        pk2 = self.db.add({"pk": None, "name": "second"})
        assert pk2 == 2
        data = self.db.load()
        assert len(data) == 2

    def test_add_with_explicit_pk(self):
        pk = self.db.add({"pk": 100, "name": "explicit"})
        assert pk == 100
        data = self.db.load()
        assert data[0]["pk"] == 100


class TestJSONBaseUpdate:
    def setup_method(self) -> None:
        self.path = Path.cwd() / "database/test/test_update_data.json"
        self.db = JSONBase(str(self.path))
        self.db.add({"pk": 1, "name": "original", "value": 10})

    def teardown_method(self) -> None:
        if self.path.exists():
            os.remove(self.path)

    def test_update_existing_record(self):
        self.db.update(1, {"pk": 1, "name": "updated", "value": 20})
        data = self.db.load()
        assert data[0]["name"] == "updated"
        assert data[0]["value"] == 20

    def test_update_nonexistent_record_appends(self):
        self.db.update(99, {"pk": 99, "name": "new"})
        data = self.db.load()
        assert len(data) == 2
        assert data[1]["pk"] == 99


class TestJSONBaseDelete:
    def setup_method(self) -> None:
        self.path = Path.cwd() / "database/test/test_delete_data.json"
        self.db = JSONBase(str(self.path))
        self.db.add({"pk": 1, "name": "first"})
        self.db.add({"pk": 2, "name": "second"})

    def teardown_method(self) -> None:
        if self.path.exists():
            os.remove(self.path)

    def test_delete_existing(self):
        self.db.delete(1)
        data = self.db.load()
        assert len(data) == 1
        assert data[0]["pk"] == 2

    def test_delete_nonexistent(self):
        self.db.delete(999)
        data = self.db.load()
        assert len(data) == 2
