import datetime
import json
from pathlib import Path

import pytest

from dataview import ResourceBaseView, AccountBaseView, TransactionBaseView, PlannedTransactionBaseView
from core import Account, Money, Transaction, Resource, PlannedTransaction
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
        r = Resource(99, "TEMP")
        self.db_view.add(r)
        self.db_view.delete(99)
        all_resources = self.db_view.get_all()
        assert 99 not in all_resources


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
        account = Account(99, "temp_account", Resource(1, "BYN"), 0)
        self.db_view.add(account)
        self.db_view.delete(99)
        assert self.db_view.get(99) is None

    def test_get_nonexistent_returns_none(self):
        assert self.db_view.get(9999) is None


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
        transaction = Transaction(
            2,
            self.account_db_view.get(1),
            Money(5, self.resource_db_view.get(1)),
            time_stamp=datetime.datetime.now(),
        )
        self.db_view.add(transaction)
        assert transaction == self.db_view.get(2)

    def test_get_all(self):
        all_transactions = self.db_view.get_all()
        assert isinstance(all_transactions, dict)
        assert len(all_transactions) >= 1

    def test_delete(self):
        t = Transaction(
            99,
            self.account_db_view.get(1),
            Money(1, self.resource_db_view.get(1)),
            time_stamp=datetime.datetime.now(),
        )
        self.db_view.add(t)
        self.db_view.delete(99)
        assert self.db_view.get(99) is None


class TestPlannedTransactionBaseView:
    def setup_class(self) -> None:
        self.data_path = Path.cwd() / "dataview/test/test_planned_transactions.json"
        self.resource_path = Path.cwd() / "dataview/test/test_resources.json"
        self.account_path = Path.cwd() / "dataview/test/test_accounts.json"
        self.file_data = []
        if self.data_path.exists():
            self.file_data = json.load(self.data_path.open())

        self.resource_db = JSONBase(str(self.resource_path))
        self.account_db = JSONBase(str(self.account_path))
        self.db = JSONBase(str(self.data_path))
        self.resource_db_view = ResourceBaseView(self.resource_db, reserve_database=self.resource_db)
        self.account_db_view = AccountBaseView(self.account_db, self.resource_db_view, reserve_database=self.account_db)
        self.db_view = PlannedTransactionBaseView(self.db, self.account_db_view, reserve_database=self.db)
        self.resource_db_view.load()
        self.account_db_view.load()
        self.db_view.load()

    def teardown_class(self) -> None:
        json.dump(self.file_data, self.data_path.open("w"), indent=2)

    def test_get_nonexistent(self):
        assert self.db_view.get(999) is None

    def test_add(self):
        account = self.account_db_view.get(1)
        if account is None:
            return
        pt = PlannedTransaction(
            account,
            Money(100, account.value.currency),
            datetime.datetime(2025, 12, 1),
            "monthly",
        )
        self.db_view.add(pt)
        all_pts = self.db_view.get_all()
        assert len(all_pts) >= 1

    def test_get_all(self):
        all_pts = self.db_view.get_all()
        assert isinstance(all_pts, dict)

    def test_delete(self):
        account = self.account_db_view.get(1)
        if account is None:
            return
        pt = PlannedTransaction(
            account,
            Money(50, account.value.currency),
            datetime.datetime(2025, 6, 1),
            None,
        )
        self.db_view.add(pt)
        keys = list(self.db_view.get_all().keys())
        last_key = keys[-1]
        self.db_view.delete(last_key)
        assert self.db_view.get(last_key) is None
