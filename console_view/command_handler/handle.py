import datetime

from dataview import AccountBaseView, TransactionBaseView, ResourceBaseView
from console_view.view import Viewer
from core import Account, Money, Bank, Transaction


class CommandHandler:
    def __init__(
        self,
        resources_view: ResourceBaseView,
        database_view: AccountBaseView,
        transaction_view: TransactionBaseView,
        viewer: Viewer,
        bank: Bank,
    ) -> None:
        self.__resources_view = resources_view
        self.__database_view = database_view
        self.__transaction_view = transaction_view
        self.__viewer = viewer
        self.__bank = bank

    def set_new_bank(self, bank: Bank):
        self.__bank = bank

    def process(self, command: tuple) -> bool:
        match command:
            case "get", "all":
                self.__viewer.show_accounts(self.__database_view.get_all())
            case ("transactions",):
                self.__viewer.show_transactions(self.__transaction_view.get_all())
            case "transactions", *_:
                self.__viewer.show_error('Wrong command syntax "transactions"\ntransactions have syntax:\ntransactions')
            case "get", str(name):
                if self.__database_view.get(name) is None:
                    self.__viewer.show_error(f'Account with name "{name}" is not exist.')
                    return False
                self.__viewer.show_account(name, self.__database_view.get(name))
            case "get", *_:
                self.__viewer.show_error('Wrong command syntax "get"\nget have syntax:\nget <name | all>')
            case "create", str(name), str(currency):
                self.__database_view.add(Account(name, currency, self.__resources_view.get(currency)))
            case "create", *_:
                self.__viewer.show_error('Wrong command syntax "create"\ncreate have syntax:\ncreate <name> <currency>')
            case "add", str(name), str(value), str(currency):
                transaction = Transaction(
                    1,
                    self.__database_view.get(name),
                    Money(float(value), self.__resources_view.get(currency)),
                    datetime.datetime.now(),
                )
                self.__transaction_view.add(transaction)
            case "add", *_:
                self.__viewer.show_error(
                    'Wrong command syntax "add"\nadd have syntax:\nadd <account> <value> <currency>'
                )
            case ("exit",):
                return True
            case _:
                self.__viewer.show_error(f'Command "{command[0]}" is not exist.')
        return False
