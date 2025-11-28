import datetime
import json
import os
from pathlib import Path

from dataview import ResourceBaseView, AccountBaseView, TransactionBaseView
from core import Account, Money, Transaction
from database import JSONBase, NoneBase


class TestDataBaseView:
    def setup_method(self) -> None:
        self.resources_path = Path.cwd() / "dataview/test/test_resources.json"
        self.data_path = Path.cwd() / "dataview/test/test_accounts.json"
        self.transactions_data_path = Path.cwd() / "dataview/test/test_transactions.json"
        self.accounts_data = json.load(self.data_path.open())
        self.resources_db_view = ResourceBaseView(JSONBase(str(self.resources_path)))
        self.resources_db_view.load()
        self.db_view = AccountBaseView(JSONBase(str(self.data_path)), self.resources_db_view)
        self.db_view.load()
        self.transactions_db_view = TransactionBaseView(JSONBase(str(self.transactions_data_path)), self.db_view)

    def teardown_method(self) -> None:
        json.dump(self.accounts_data, self.data_path.open("w"), indent=2)

    def teardown_class(self) -> None:
        os.remove(str(Path.cwd() / r"dataview/test/saved_data.json"))

    def test_database_view_create(self) -> None:
        AccountBaseView(NoneBase(), self.resources_db_view)

    def test_database_view_get_account(self) -> None:
        account = self.db_view.get(0)
        assert isinstance(account, Account)
        assert account.get_balance() == Money(10, self.resources_db_view.get(0))

    def test_database_view_add_account(self) -> None:
        account = Account(2, "BYN", self.resources_db_view.get(0))
        self.db_view.add(account)
        assert account == self.db_view.get(2)

    def test_database_view_load(self) -> None:
        self.db_view.load()
        assert self.db_view.get(1)

    def test_database_view_save(self) -> None:
        self.db_view.add(Account(2, "USD", self.resources_db_view.get(1)))
        self.db_view.save()
        loaded_db_view = AccountBaseView(JSONBase(str(self.data_path)), self.resources_db_view)
        loaded_db_view.load()
        loaded_accounts = loaded_db_view.get_all()
        current_accounts = self.db_view.get_all()
        for name in current_accounts:
            assert current_accounts[name] == loaded_accounts[name]

    def test_database_view_load_transactions(self) -> None:
        self.transactions_db_view.load()
        assert self.transactions_db_view.get(1)

    def test_database_view_save_transactions(self) -> None:
        save_base = TransactionBaseView(JSONBase(str(Path.cwd() / r"dataview/test/saved_data.json")), self.db_view)
        acc = self.db_view.get(0)
        income = Transaction(0, acc, Money(10, self.resources_db_view.get(0)), datetime.datetime.now())
        income.execute()
        save_base.add(income)
        save_base.save()
        save_base.load()
        assert save_base.get(0)

    def test_accounts_load_transactions(self) -> None:
        self.db_view.load()
        self.transactions_db_view.load()
        assert self.db_view.get(0) == self.transactions_db_view.get(0).storage
