"""Тесты JSON-слоя dataview на изолированных копиях фикстур.

Тесты не работают с файлами `dataview/test/*.json` напрямую: каждый из них
получает свежие копии в `tmp_path`, поэтому файлы репозитория не мутируются,
а результат не зависит от порядка прогонов (регрессия `test_account_with_group`,
слайс 3.7 — прежний `teardown_class` мог оставить фикстуры грязными).
"""

import datetime
import shutil
from pathlib import Path

import pytest
from core import Account, Resource, Transaction
from core.journal_entry import JournalEntry
from database import JSONBase

from dataview import AccountBaseView, ResourceBaseView, TransactionBaseView

FIXTURE_DIR = Path(__file__).resolve().parent
FIXTURE_FILES = ("test_accounts.json", "test_resources.json", "test_transactions.json")


def _load_view[V: (ResourceBaseView, AccountBaseView, TransactionBaseView)](
    view_type: type[V], fixture_file: str, data_dir: Path, *dependencies
) -> V:
    """Вьюха поверх свежей копии фикстуры: база же служит reserve-базой."""
    database = JSONBase(str(data_dir / fixture_file))
    view = view_type(database, *dependencies, reserve_database=database)
    view.load()
    return view


@pytest.fixture
def data_dir(tmp_path: Path) -> Path:
    """Копии JSON-фикстур: тесты не трогают файлы репозитория."""
    for name in FIXTURE_FILES:
        shutil.copy(FIXTURE_DIR / name, tmp_path / name)
    return tmp_path


@pytest.fixture
def resource_view(data_dir: Path) -> ResourceBaseView:
    return _load_view(ResourceBaseView, "test_resources.json", data_dir)


@pytest.fixture
def account_view(data_dir: Path, resource_view: ResourceBaseView) -> AccountBaseView:
    return _load_view(AccountBaseView, "test_accounts.json", data_dir, resource_view)


@pytest.fixture
def transaction_view(data_dir: Path, account_view: AccountBaseView) -> TransactionBaseView:
    return _load_view(TransactionBaseView, "test_transactions.json", data_dir, account_view)


class TestResourceBaseView:
    def test_get(self, resource_view) -> None:
        assert resource_view.get(1) is not None

    def test_add(self, resource_view) -> None:
        resource = Resource(2, "USD")
        resource_view.add(resource)
        assert resource == resource_view.get(2)

    def test_get_all(self, resource_view) -> None:
        all_resources = resource_view.get_all()
        assert isinstance(all_resources, dict)
        assert len(all_resources) >= 2

    def test_delete(self, resource_view) -> None:
        resource = Resource(98, "TEMP")
        resource_view.add(resource)
        actual_pk = resource.pk
        resource_view.delete(actual_pk)
        assert actual_pk not in resource_view.get_all()


class TestAccountBaseView:
    def test_get(self, account_view) -> None:
        assert account_view.get(1) is not None

    def test_add(self, account_view) -> None:
        account = Account(2, "test2", Resource(1, "BYN"), 15)
        account_view.add(account)
        assert account == account_view.get(2)

    def test_get_all(self, account_view) -> None:
        all_accounts = account_view.get_all()
        assert isinstance(all_accounts, dict)
        assert len(all_accounts) >= 2

    def test_delete(self, account_view) -> None:
        account = Account(98, "temp_account", Resource(1, "BYN"), 0)
        account_view.add(account)
        actual_pk = account.pk
        account_view.delete(actual_pk)
        assert account_view.get(actual_pk) is None

    def test_get_nonexistent_returns_none(self, account_view) -> None:
        assert account_view.get(9999) is None

    def test_account_with_group(self, account_view) -> None:
        resource = Resource(1, "BYN")
        account = Account(97, "Crypto", resource, 1000, group="investments", account_type="trading")
        account_view.add(account)
        actual_pk = account.pk
        loaded = account_view.get(actual_pk)
        assert loaded.group == "investments"
        assert loaded.account_type == "trading"
        account_view.delete(actual_pk)
        assert account_view.get(actual_pk) is None


class TestTransactionBaseView:
    def test_get(self, transaction_view) -> None:
        assert transaction_view.get(1) is not None

    def test_add(self, transaction_view) -> None:
        entry = JournalEntry(account_id=1, quantity=5, amount=5)
        transaction = Transaction(96, datetime.datetime.now(), [entry])
        transaction_view.add(transaction)
        assert transaction == transaction_view.get(96)

    def test_get_all(self, transaction_view) -> None:
        all_transactions = transaction_view.get_all()
        assert isinstance(all_transactions, dict)
        assert len(all_transactions) >= 1

    def test_delete(self, transaction_view) -> None:
        entry = JournalEntry(account_id=1, quantity=1, amount=1)
        transaction = Transaction(95, datetime.datetime.now(), [entry])
        transaction_view.add(transaction)
        actual_pk = transaction.pk
        transaction_view.delete(actual_pk)
        assert transaction_view.get(actual_pk) is None

    def test_get_planned(self, transaction_view) -> None:
        entry = JournalEntry(account_id=1, quantity=10, amount=10)
        transaction = Transaction(94, datetime.datetime.now(), [entry], is_planned=True, recurrence_rule="monthly")
        transaction_view.add(transaction)
        actual_pk = transaction.pk
        planned = transaction_view.get_planned()
        assert actual_pk in planned
        transaction_view.delete(actual_pk)
        assert actual_pk not in transaction_view.get_planned()
