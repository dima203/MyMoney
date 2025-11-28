import datetime
import json
from pathlib import Path

from dataview import ResourceBaseView, AccountBaseView, TransactionBaseView
from core import Account, Money, Resource, Transaction
from database import JSONBase


class TestResourceBaseView:
    def setup_class(self) -> None:
        self.data_path = Path.cwd() / 'dataview/test/test_resources.json'
        self.db = JSONBase(str(self.data_path))
        self.db_view = ResourceBaseView(self.db, reserve_database=self.db)
        self.db_view.load()

    def setup_method(self) -> None:
        self.file_data = json.load(self.data_path.open())

    def teardown_method(self) -> None:
        json.dump(self.file_data, self.data_path.open('w'), indent=2)

    def test_get(self) -> None:
        data = self.db_view.get(1)

    def test_add(self) -> None:
        resource = Resource(2, 'USD')
        self.db_view.add(resource)
        assert resource == self.db_view.get(2)


class TestAccountBaseView:
    def setup_class(self) -> None:
        self.data_path = Path.cwd() / 'dataview/test/test_accounts.json'
        self.resource_path = Path.cwd() / 'dataview/test/test_resources.json'
        self.db = JSONBase(str(self.data_path))
        self.resource_db = JSONBase(str(self.resource_path))
        self.resource_db_view = ResourceBaseView(self.resource_db, reserve_database=self.resource_db)
        self.db_view = AccountBaseView(self.db, self.resource_db_view, reserve_database=self.db)
        self.resource_db_view.load()
        self.db_view.load()

    def setup_method(self) -> None:
        self.file_data = json.load(self.data_path.open())

    def teardown_method(self) -> None:
        json.dump(self.file_data, self.data_path.open('w'), indent=2)

    def test_get(self) -> None:
        data = self.db_view.get(1)

    def test_add(self) -> None:
        account = Account(2, 'test2', Resource(1, 'BYN'), 15)
        self.db_view.add(account)
        assert account == self.db_view.get(2)


class TestTransactionBaseView:
    def setup_class(self) -> None:
        self.data_path = Path.cwd() / 'dataview/test/test_transactions.json'
        self.resource_path = Path.cwd() / 'dataview/test/test_resources.json'
        self.account_path = Path.cwd() / 'dataview/test/test_accounts.json'
        self.resource_db = JSONBase(str(self.resource_path))
        self.account_db = JSONBase(str(self.account_path))
        self.db = JSONBase(str(self.data_path))
        self.resource_db_view = ResourceBaseView(self.resource_db, reserve_database=self.resource_db)
        self.account_db_view = AccountBaseView(self.account_db, self.resource_db_view, reserve_database=self.account_db)
        self.db_view = TransactionBaseView(self.db, self.account_db_view, reserve_database=self.db)
        self.resource_db_view.load()
        self.account_db_view.load()
        self.db_view.load()

    def setup_method(self) -> None:
        self.file_data = json.load(self.data_path.open())

    def teardown_method(self) -> None:
        json.dump(self.file_data, self.data_path.open('w'), indent=2)

    def test_get(self) -> None:
        data = self.db_view.get(1)

    def test_add(self) -> None:
        transaction = Transaction(self.account_db_view.get(1), Money(5, self.resource_db_view.get(1)),
                                  time_stamp=datetime.datetime.now())
        self.db_view.add(transaction)
        assert transaction == self.db_view.get(2)
