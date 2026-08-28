import datetime
import json
from pathlib import Path

from dataview import ResourceBaseView, AccountBaseView, TransactionBaseView
from core import Account, Transaction, Resource
from core.journal_entry import JournalEntry
from database import JSONBase


class TestResourceBaseView:
    def setup_class(self) -> None:
        self.data_path = Path.cwd() / "dataview/test/test_resources.json"
        self.file_data = json.load(self.data_path.open())
        self.db = JSONBase(str(self.data_path))
        self.db_view = ResourceBaseView(self.db, reserve_database=self.db)
        self.db_view.load()

    def teardown_class(self) -> None:
        json.dump(self.file_data, self.data_path.open("w"), indent=2)

    def test_get(self) -> None:
        _ = self.db_view.get(1)

    def test_add(self) -> None:
        resource = Resource(2, "USD")
        self.db_view.add(resource)
        assert resource == self.db_view.get(2)

    def test_get_all(self):
        all_resources = self.db_view.get_all()
        assert isinstance(all_resources, dict)
        assert len(all_resources) >= 2

    def test_delete(self):
        r = Resource(98, "TEMP")
        self.db_view.add(r)
        actual_pk = r.pk
        self.db_view.delete(actual_pk)
        all_resources = self.db_view.get_all()
        assert actual_pk not in all_resources


class TestAccountBaseView:
    def setup_class(self) -> None:
        self.data_path = Path.cwd() / "dataview/test/test_accounts.json"
        self.resource_path = Path.cwd() / "dataview/test/test_resources.json"
        self.file_data = json.load(self.data_path.open())
        self.db = JSONBase(str(self.data_path))
        self.resource_db = JSONBase(str(self.resource_path))
        self.resource_db_view = ResourceBaseView(self.resource_db, reserve_database=self.resource_db)
        self.db_view = AccountBaseView(self.db, self.resource_db_view, reserve_database=self.db)
        self.resource_db_view.load()
        self.db_view.load()

    def teardown_class(self) -> None:
        json.dump(self.file_data, self.data_path.open("w"), indent=2)

    def test_get(self) -> None:
        _ = self.db_view.get(1)

    def test_add(self) -> None:
        account = Account(2, "test2", Resource(1, "BYN"), 15)
        self.db_view.add(account)
        assert account == self.db_view.get(2)

    def test_get_all(self):
        all_accounts = self.db_view.get_all()
        assert isinstance(all_accounts, dict)
        assert len(all_accounts) >= 2

    def test_delete(self):
        account = Account(98, "temp_account", Resource(1, "BYN"), 0)
        self.db_view.add(account)
        actual_pk = account.pk
        self.db_view.delete(actual_pk)
        assert self.db_view.get(actual_pk) is None

    def test_get_nonexistent_returns_none(self):
        assert self.db_view.get(9999) is None

    def test_account_with_group(self):
        resource = Resource(1, "BYN")
        account = Account(97, "Crypto", resource, 1000, group="investments", account_type="trading")
        self.db_view.add(account)
        actual_pk = account.pk
        loaded = self.db_view.get(actual_pk)
        assert loaded.group == "investments"
        assert loaded.account_type == "trading"
        self.db_view.delete(actual_pk)


class TestTransactionBaseView:
    def setup_class(self) -> None:
        self.data_path = Path.cwd() / "dataview/test/test_transactions.json"
        self.resource_path = Path.cwd() / "dataview/test/test_resources.json"
        self.account_path = Path.cwd() / "dataview/test/test_accounts.json"
        self.file_data = json.load(self.data_path.open())
        self.account_file_data = json.load(self.account_path.open())
        self.resources_file_data = json.load(self.resource_path.open())
        self.resource_db = JSONBase(str(self.resource_path))
        self.account_db = JSONBase(str(self.account_path))
        self.db = JSONBase(str(self.data_path))
        self.resource_db_view = ResourceBaseView(self.resource_db, reserve_database=self.resource_db)
        self.account_db_view = AccountBaseView(self.account_db, self.resource_db_view, reserve_database=self.account_db)
        self.db_view = TransactionBaseView(self.db, self.account_db_view, reserve_database=self.db)
        self.resource_db_view.load()
        self.account_db_view.load()
        self.db_view.load()

    def teardown_class(self) -> None:
        json.dump(self.file_data, self.data_path.open("w"), indent=2)
        json.dump(self.account_file_data, self.account_path.open("w"), indent=2)
        json.dump(self.resources_file_data, self.resource_path.open("w"), indent=2)

    def test_get(self) -> None:
        _ = self.db_view.get(1)

    def test_add(self) -> None:
        entry = JournalEntry(account_id=1, quantity=5, amount=5)
        transaction = Transaction(
            96,
            datetime.datetime.now(),
            [entry],
        )
        self.db_view.add(transaction)
        assert transaction == self.db_view.get(96)

    def test_get_all(self):
        all_transactions = self.db_view.get_all()
        assert isinstance(all_transactions, dict)
        assert len(all_transactions) >= 1

    def test_delete(self):
        entry = JournalEntry(account_id=1, quantity=1, amount=1)
        t = Transaction(95, datetime.datetime.now(), [entry])
        self.db_view.add(t)
        actual_pk = t.pk
        self.db_view.delete(actual_pk)
        assert self.db_view.get(actual_pk) is None

    def test_get_planned(self):
        entry = JournalEntry(account_id=1, quantity=10, amount=10)
        t = Transaction(94, datetime.datetime.now(), [entry], is_planned=True, recurrence_rule="monthly")
        self.db_view.add(t)
        actual_pk = t.pk
        planned = self.db_view.get_planned()
        assert actual_pk in planned
        self.db_view.delete(actual_pk)
