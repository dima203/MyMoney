from console_view.data import AccountBaseView, TransactionBaseView
from console_view.view import Viewer
from core import Account, Money, Bank, Income, Expense, Transfer


class CommandHandler:
    def __init__(self, database_view: AccountBaseView, transaction_view: TransactionBaseView,
                 viewer: Viewer, bank: Bank) -> None:
        self.__database_view = database_view
        self.__transaction_view = transaction_view
        self.__viewer = viewer
        self.__bank = bank

    def set_new_bank(self, bank: Bank):
        self.__bank = bank

    def process(self, command: tuple) -> bool:
        match command:
            case 'get', 'all':
                self.__viewer.show_accounts(self.__database_view.get_accounts())
            case 'get', str(name):
                if self.__database_view.get_account(name) is None:
                    self.__viewer.show_error(f'Account with name "{name}" is not exist.')
                    return False
                self.__viewer.show_account(name, self.__database_view.get_account(name))
            case 'create', str(name), str(currency):
                self.__database_view.add_account(name, Account(name, currency))
            case 'create', :
                self.__viewer.show_error(f'Wrong command syntax "create"\n'
                                         f'create have syntax:\n'
                                         f'create <name> <currency>')
            case 'add', *args:
                match args:
                    case 'income', str(account_name), str(value), str(currency):
                        transaction = Income(0, None, Money(int(value), currency), self.__bank)
                        self.__transaction_view.add_transaction(transaction)
                        transaction.connect(self.__database_view.get_account(account_name))
                    case 'expense', str(account_name), str(value), str(currency):
                        transaction = Expense(0, None, Money(int(value), currency), self.__bank)
                        self.__transaction_view.add_transaction(transaction)
                        transaction.connect(self.__database_view.get_account(account_name))
                    case 'transfer', str(from_account), str(to_account), str(value), str(currency):
                        transaction = Transfer(0, None, None, Money(int(value), currency), self.__bank)
                        self.__transaction_view.add_transaction(transaction)
                        transaction.connect(self.__database_view.get_account(from_account),
                                            self.__database_view.get_account(to_account))
            case 'exit', :
                return True
            case _:
                self.__viewer.show_error(f'Command "{command[0]}" is not exist.')
        return False
