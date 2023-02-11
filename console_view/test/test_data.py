from pathlib import Path

from console_view import DataBaseView
from core import Account, Money, Bank
from database import JSONBase


class TestDataBaseView:
    def setup_method(self) -> None:
        self.db_view = DataBaseView(JSONBase(str(Path.cwd() / 'console_view/test/test_accounts.json')))
        self.account = Account('BYN')
        self.account.add(Money.byn(10), Bank())
        self.db_view.add_account('test', self.account)

    def test_database_view_create(self) -> None:
        db_view = DataBaseView(JSONBase(''))

    def test_database_view_get_account(self) -> None:
        account = self.db_view.get_account('test')
        assert isinstance(account, Account)
        assert account.value.currency == 'BYN'
        assert account.value == Money.byn(10)

    def test_database_view_get_accounts(self) -> None:
        assert self.db_view.get_accounts() == {'test': self.account}

    def test_database_view_add_account(self) -> None:
        account = Account('BYN')
        self.db_view.add_account('test2', account)
        assert account == self.db_view.get_account('test2')

    def test_database_view_load(self) -> None:
        self.db_view.load_accounts()
        assert self.db_view.get_account('loaded')
