import sqlite3

from .abstract_base import DataBase


class SQLBase(DataBase):
    def __init__(self, path: str) -> None:
        super().__init__(path)
        self.__connection = sqlite3.connect(self._path)
        self.__cursor = self.__connection.cursor()
        self.__cursor.execute('''
CREATE TABLE IF NOT EXISTS accounts (id CHAR(128) PRIMARY KEY,
value INT, currency CHAR(5))
''')
        self.__cursor.execute('''
INSERT INTO accounts (id, value, currency) VALUES (?, ?, ?)
''', ('test', 10, 'BYN'))

    def load(self) -> dict:
        self.__cursor.execute('''SELECT * FROM accounts''')

        result = {}
        for account in self.__cursor.fetchall():
            result[account[0]] = {
                'value': account[1],
                'currency': account[2],
            }
        return result

    def save(self, data: dict) -> None:
        pass


test = SQLBase(':memory:')
test.load()
