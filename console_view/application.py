from pathlib import Path

from console_view import CommandHandler, ConsoleInput, ConsoleViewer
from dataview import AccountBaseView, TransactionBaseView
from core import Bank
from database import JSONBase


class Application:
    def __init__(self):
        self.database = JSONBase(str(Path.cwd() / r"application_data.json"))
        self.transaction_database = JSONBase(str(Path.cwd() / r"application_transaction_data.json"))
        self.database_view = AccountBaseView(self.database)
        self.transactions_view = TransactionBaseView(self.transaction_database)
        self.viewer = ConsoleViewer()
        self.input = ConsoleInput()
        self.bank = Bank()
        self.command_handler = CommandHandler(self.database_view, self.transactions_view, self.viewer, self.bank)

    def run(self) -> None:
        self.database_view.load_accounts()
        self.transactions_view.load_transactions()
        self.database_view.load_transactions_to_accounts(self.transactions_view)
        self.__app_cycle()

    def stop(self) -> None:
        self.database_view.save_accounts()
        self.transactions_view.save_transactions()

    def __app_cycle(self) -> None:
        while True:
            command = self.input.get_input()
            command = tuple(command.split(" "))
            if self.command_handler.process(command):
                self.stop()
                break
