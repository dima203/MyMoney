from console_view.data import DataBaseView
from console_view.view import Viewer
from core import Account, Money, Bank, Income, Expense


class CommandHandler:
    def __init__(self, database_view: DataBaseView, viewer: Viewer, bank: Bank) -> None:
        self.__database_view = database_view
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
                self.__database_view.add_account(name, Account(currency))
            case 'create', :
                self.__viewer.show_error(f'Wrong command syntax "create"\n'
                                         f'create have syntax:\n'
                                         f'create <name> <currency>')
            case 'add', *args:
                match args:
                    case 'income', str(account_name), str(value), str(currency):
                        transaction = Income(self.__database_view.get_account(account_name),
                                             Money(int(value), currency))
                        transaction.accept(self.__bank)
                    case 'expense', str(account_name), str(value), str(currency):
                        transaction = Expense(self.__database_view.get_account(account_name),
                                              Money(int(value), currency))
                        transaction.accept(self.__bank)
            case 'exit', :
                return True
            case _:
                self.__viewer.show_error(f'Command "{command[0]}" is not exist.')
        return False
