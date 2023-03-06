from console_view import CommandHandler
from dataview import AccountBaseView, TransactionBaseView
from database import JSONBase
from core import Account, Money, Bank, Transaction

from console_view.view import Viewer


class TestCommandHandle(Viewer):
    def show_accounts(self, accounts: Account) -> None:
        self.show_accounts_called += 1

    def show_account(self, name: str, account: Account) -> None:
        self.show_accounts_called += 1
        self.showed_name = name

    def show_transactions(self, transactions: dict[int, Transaction]) -> None:
        self.show_transactions_called += 1

    def show_error(self, error_message: str) -> None:
        self.showed_error = error_message

    def setup_method(self) -> None:
        self.show_accounts_called = 0
        self.show_transactions_called = 0
        self.showed_name = None
        self.showed_error = None
        self.database = AccountBaseView(JSONBase(''))
        self.database2 = TransactionBaseView(JSONBase(''))
        self.database.add_account('test', Account('test', 'BYN'))
        self.database.add_account('test2', Account('test2', 'BYN'))
        self.handler = CommandHandler(self.database, self.database2, self, Bank())

    def test_get_all_command_handle(self) -> None:
        self.handler.process(('get', 'all'))
        assert self.show_accounts_called == 1

    def test_get_test_command_handle(self) -> None:
        self.handler.process(('get', 'test'))
        assert self.show_accounts_called == 1
        assert self.showed_name == 'test'

    def test_get_none_account_command_handle(self) -> None:
        self.handler.process(('get', 'none'))
        assert self.showed_error == 'Account with name "none" is not exist.'

    def test_get_command_false_handle(self) -> None:
        self.handler.process(('get', ))
        assert self.showed_error == 'Wrong command syntax "get"\n' \
                                    'get have syntax:\n' \
                                    'get <name | all>'

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
        assert self.database.get_account('test').get_balance() == Money.byn(10)

    def test_add_expense_command_handle(self) -> None:
        acc = self.database.get_account('test')
        self.handler.process(('add', 'income', 'test', '10', 'BYN'))
        self.handler.process(('add', 'expense', 'test', '10', 'BYN'))
        assert self.database.get_account('test').get_balance() == Money.byn(0)

    def test_add_transfer_command_handle(self) -> None:
        acc = self.database.get_account('test')
        acc2 = self.database.get_account('test2')
        self.handler.process(('add', 'income', 'test', '10', 'BYN'))
        self.handler.process(('add', 'transfer', 'test', 'test2', '10', 'BYN'))
        assert self.database.get_account('test').get_balance() == Money.byn(0)
        assert self.database.get_account('test2').get_balance() == Money.byn(10)

    def test_add_command_false_handle(self) -> None:
        self.handler.process(('add', ))
        assert self.showed_error == 'Wrong command syntax "add"\n' \
                                    'add have syntax:\n' \
                                    'add <type> <account> [account2](for transfer) <value> <currency>'

    def test_transactions_command_handle(self) -> None:
        self.handler.process(('transactions', ))
        assert self.show_transactions_called == 1

    def test_transactions_command_false_handle(self) -> None:
        self.handler.process(('transactions', ''))
        assert self.showed_error == 'Wrong command syntax "transactions"\n' \
                                    'transactions have syntax:\n' \
                                    'transactions'

    def test_not_command_handle(self) -> None:
        self.handler.process(('not_command', ))
        assert self.showed_error == 'Command "not_command" is not exist.'

    def test_exit_command_handle(self) -> None:
        assert self.handler.process(('exit', ))
