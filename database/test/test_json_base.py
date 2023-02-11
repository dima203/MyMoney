from pathlib import Path
import json

from database import JSONBase


class TestJSONBase:
    def setup_method(self) -> None:
        self.load_database = JSONBase(str(Path.cwd() / 'database/test/test_data.json'))
        self.save_database = JSONBase(str(Path.cwd() / 'database/test/new_test_data.json'))

    def test_database_load_data(self) -> None:
        data = self.load_database.load()
        assert data['loaded']['value'] == 25
        assert data['loaded']['currency'] == 'BYN'

    def test_database_save_data(self) -> None:
        data = {
            'test': {
                'value': 50,
                'currency': 'USD'
            }
        }
        self.save_database.save(data)
        accounts = json.load((Path.cwd() / 'database/test/new_test_data.json').open())
        assert accounts['test']
        assert accounts['test'] == data['test']
