from console_view import CommandHandler, DataBaseView
from database import JSONBase
from core import Account, Money, Bank

from console_view.view import Viewer


class TestCommandHandle(Viewer):
    def show_accounts(self, accounts: Account) -> None:
        self.show_called += 1

    def show_account(self, name: str, account: Account) -> None:
        self.show_called += 1
        self.showed_name = name

    def show_error(self, error_message: str) -> None:
        self.showed_error = error_message

    def setup_method(self) -> None:
        self.show_called = 0
        self.showed_name = None
        self.showed_error = None
        self.database = DataBaseView(JSONBase(''))
        self.database.add_account('test', Account('BYN'))
        self.handler = CommandHandler(self.database, self, Bank())

    def test_get_all_command_handle(self) -> None:
        self.handler.process(('get', 'all'))
        assert self.show_called == 1

    def test_get_test_command_handle(self) -> None:
        self.handler.process(('get', 'test'))
        assert self.show_called == 1
        assert self.showed_name == 'test'

    def test_get_none_account_command_handle(self) -> None:
        self.handler.process(('get', 'none'))
        assert self.showed_error == 'Account with name "none" is not exist.'

    def test_create_account_command_handle(self) -> None:
        self.handler.process(('create', 'test2', 'BYN'))
        assert self.database.get_account('test2')

    def test_create_command_handle(self) -> None:
        self.handler.process(('create', ))
        assert self.showed_error == 'Wrong command syntax "create"\n' \
                                    'create have syntax:\n' \
                                    'create <name> <currency>'

    def test_add_income_command_handle(self) -> None:
        self.handler.process(('add', 'income', 'test', '10', 'BYN'))
        assert self.database.get_account('test').value == Money.byn(10)

    def test_add_expense_command_handle(self) -> None:
        self.database.get_account('test').add(Money.byn(10), Bank())
        self.handler.process(('add', 'expense', 'test', '10', 'BYN'))
        assert self.database.get_account('test').value == Money.byn(0)

    def test_not_command_handle(self) -> None:
        self.handler.process(('not_command', ))
        assert self.showed_error == 'Command "not_command" is not exist.'
