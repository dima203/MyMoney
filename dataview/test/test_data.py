import json
from pathlib import Path

from dataview import ResourceBaseView, AccountBaseView, TransactionBaseView
from core import Account, Money, Bank, Income
from database import JSONBase


class TestDataBaseView:
    def setup_method(self) -> None:
        self.resources_path = Path.cwd() / "dataview/test/test_resources.json"
        self.data_path = Path.cwd() / "dataview/test/test_accounts.json"
        self.transactions_data_path = Path.cwd() / "dataview/test/test_transactions.json"
        self.accounts_data = json.load(self.data_path.open())
        self.resources_db_view = ResourceBaseView(JSONBase(str(self.resources_path)))
        self.resources_db_view.load_resources()
        self.db_view = AccountBaseView(JSONBase(str(self.data_path)))
        self.db_view.load_accounts(self.resources_db_view)
        self.transactions_db_view = TransactionBaseView(JSONBase(str(self.transactions_data_path)))

    def teardown_method(self) -> None:
        json.dump(self.accounts_data, self.data_path.open("w"), indent=2)

    def test_database_view_create(self) -> None:
        AccountBaseView(JSONBase(""))

    def test_database_view_get_account(self) -> None:
        account = self.db_view.get_account("0")
        assert isinstance(account, Account)
        assert account.get_balance() == Money.byn(10)

    def test_database_view_add_account(self) -> None:
        account = Account("", "BYN")
        self.db_view.add_account("test2", account)
        assert account == self.db_view.get_account("test2")

    def test_database_view_load(self) -> None:
        self.db_view.load_accounts(self.resources_db_view)
        assert self.db_view.get_account("1")

    def test_database_view_save(self) -> None:
        self.db_view.add_account("test2", Account("test2", "USD"))
        self.db_view.save_accounts()
        loaded_db_view = AccountBaseView(JSONBase(str(self.data_path)))
        loaded_db_view.load_accounts(self.resources_db_view)
        loaded_accounts = loaded_db_view.get_accounts()
        current_accounts = self.db_view.get_accounts()
        for name in current_accounts:
            assert current_accounts[name] == loaded_accounts[name]

    def test_database_view_load_transactions(self) -> None:
        self.transactions_db_view.load_transactions(self.db_view)
        assert self.transactions_db_view.get_transaction(1)

    def test_database_view_save_transactions(self) -> None:
        save_base = TransactionBaseView(JSONBase(str(Path.cwd() / r"dataview/test/saved_data.json")))
        acc = Account("test", "BYN")
        income = Income(1, acc, Money.byn(10), Bank())
        save_base.add_transaction(income)
        save_base.save_transactions()
        save_base.load_transactions()
        assert save_base.get_transaction(1)

    def test_accounts_load_transactions(self) -> None:
        self.db_view.load_accounts()
        self.transactions_db_view.load_transactions()
        self.db_view.load_transactions_to_accounts(self.transactions_db_view)
        assert self.db_view.get_account("test")._Account__transactions[
            0
        ]() == self.transactions_db_view.get_transaction(0)
