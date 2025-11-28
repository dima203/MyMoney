from pathlib import Path
import json
import os

from database import JSONBase


class TestJSONBase:
    def setup_class(self) -> None:
        self.empty_file_path = Path.cwd() / 'database/test/empty.json'
        self.load_database = JSONBase(str(Path.cwd() / 'database/test/test_data.json'))
        self.save_database = JSONBase(str(Path.cwd() / 'database/test/new_test_data.json'))

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
        data = {
            'pk': 1,
            'name': 'test',
            'resource_count': 10,
            'resource_type': 2,
            'last_update': "2024-06-03T17:30:57.156636"
        }
        self.save_database.update(1, data)
        accounts = json.load((Path.cwd() / 'database/test/new_test_data.json').open())
        account = accounts[0]
        assert account
        assert account == data
