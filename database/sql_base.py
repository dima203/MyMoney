import sqlite3

from .abstract_base import DataBase


class SQLBase(DataBase):
    def __init__(self, path: str, *args: str) -> None:
        super().__init__(path, *args)
        self.__fields_names = args
        self.__connection = sqlite3.connect(self._path)
        self.__cursor = self.__connection.cursor()
        fields_sql = ''
        for i in range(3, len(args), 2):
            fields_sql += f'{args[i]} {args[i+1]}, '
        self.__cursor.execute(f'''
            CREATE TABLE IF NOT EXISTS {args[0]} (
                {args[1]} {args[2]} PRIMARY KEY,
                {fields_sql[:-2]}
            )
        ''')

    def load(self) -> dict:
        self.__cursor.execute(f'''SELECT * FROM {self.__fields_names[0]}''')
        result = {}
        for record in self.__cursor.fetchall():
            result[record[0]] = {}
            current_field = 3
            for field in record[1:]:
                result[record[0]][self.__fields_names[current_field]] = field
                current_field += 2
        return result

    def save(self, data: dict) -> None:
        field_sql = ''
        values_sql = ''
        for i in range(1, len(self.__fields_names), 2):
            field_sql += f'{self.__fields_names[i]}, '
            values_sql += '?, '
        for record_id, record in data.items():
            self.__cursor.execute(f'''
                INSERT INTO {self.__fields_names[0]} (
                    {field_sql[:-2]}
                )
                VALUES (
                    {values_sql[:-2]}
                )
            ''', (record_id, *record.values()))
        self.__connection.commit()


test = SQLBase(':memory:', 'accounts', 'id', 'CHAR(128)', 'value', 'INT', 'currency', 'CHAR(5)')
print(test.load())
