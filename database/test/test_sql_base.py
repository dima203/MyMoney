from pathlib import Path
import os

from database import SQLBase


class TestSQLBase:
    def setup_class(self) -> None:
        self.empty_file_path = Path.cwd() / 'database/test/empty.db'
        self.load_database = SQLBase(str(Path.cwd() / 'database/test/test_database.db'), 'accounts', 'id', 'CHAR(128)',
                                     'value', 'INT', 'currency', 'CHAR(5)')
        self.save_database = SQLBase(str(Path.cwd() / 'database/test/save_database.db'), 'accounts', 'id', 'CHAR(128)',
                                     'value', 'INT', 'currency', 'CHAR(5)')

    def teardown_class(self) -> None:
        os.remove(self.empty_file_path)

    def test_database_load_data(self) -> None:
        data = self.load_database.load()
        assert data['loaded']['value'] == 25
        assert data['loaded']['currency'] == 'BYN'

    def test_database_load_non_exist_file(self) -> None:
        assert not os.path.exists(self.empty_file_path)
        empty_base = SQLBase(str(self.empty_file_path), 'accounts', 'id', 'CHAR(128)',
                             'value', 'INT', 'currency', 'CHAR(5)')
        assert empty_base.load() == {}
        del empty_base
        assert os.path.exists(self.empty_file_path)

    def test_database_save_data(self) -> None:
        data = {
            'test': {
                'value': 50,
                'currency': 'USD'
            }
        }
        self.save_database.save(data)
        accounts = self.save_database.load()
        assert accounts == data
