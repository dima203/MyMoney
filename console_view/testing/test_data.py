from pathlib import Path
import json

from console_view import DataBaseView
from core import Account, Money, Bank


class TestDataBaseView:
    def setup_method(self):
        self.db_view = DataBaseView()
        account = Account('BYN')
        account.add(Money.byn(10), Bank())
        self.db_view.add_account('test', account)

    def test_database_view_create(self) -> None:
        db_view = DataBaseView()

    def test_database_view_get_account(self) -> None:
        account = self.db_view.get_account('test')
        assert isinstance(account, Account)
        assert account.value.currency == 'BYN'
        assert account.value == Money.byn(10)

    def test_database_view_add_account(self) -> None:
        account = Account('BYN')
        self.db_view.add_account('test2', account)
        assert account == self.db_view.get_account('test2')

    def test_database_view_load_accounts(self) -> None:
        self.db_view.load_accounts(Path(r'E:\PyCharmProjects\MyMoney\console_view\testing\test_accounts.json'))
        account = self.db_view.get_account('loaded')
        assert isinstance(account, Account)
        assert account.value.currency == 'BYN'
        assert account.value == Money.byn(25)

    def test_database_view_save_accounts(self) -> None:
        path = Path(r'E:\PyCharmProjects\MyMoney\console_view\testing\new_test_accounts.json')
        self.db_view.save_accounts(path)
        accounts = json.load(path.open())
        assert accounts['test']
