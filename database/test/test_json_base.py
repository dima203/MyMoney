from pathlib import Path
import json
import os

from database import JSONBase


class TestJSONBase:
    def setup_class(self) -> None:
        self.empty_file_path = Path.cwd() / "database/test/empty.json"
        self.load_database = JSONBase(str(Path.cwd() / "database/test/test_data.json"))
        self.save_database = JSONBase(str(Path.cwd() / "database/test/new_test_data.json"))

    def teardown_class(self) -> None:
        os.remove(self.empty_file_path)

    def test_database_load_data(self) -> None:
        data = self.load_database.load()
        data = data[0]
        assert data['resource_count'] == 10
        assert data['resource_type'] == 1

    def test_database_load_non_exist_file(self) -> None:
        assert not os.path.exists(self.empty_file_path)
        empty_base = JSONBase(str(self.empty_file_path))
        assert empty_base.load() == []
        assert os.path.exists(self.empty_file_path)

    def test_database_save_data(self) -> None:
        data = {"pk": 1, "resource_count": 50, "resource_type": 2}
        self.save_database.update(1, data)
        accounts = json.load((Path.cwd() / "database/test/new_test_data.json").open())
        assert accounts[0]
        assert accounts[0] == data
