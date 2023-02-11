from . import CommandHandler, DataBaseView, ConsoleInput, ConsoleViewer
from core import Bank

from database import JSONBase


class Application:
    def __init__(self):
        self.database = JSONBase(r'E:\PyCharmProjects\MyMoney\application_data.json')
        self.database_view = DataBaseView(self.database)
        self.viewer = ConsoleViewer()
        self.input = ConsoleInput()
        self.bank = Bank()
        self.command_handler = CommandHandler(self.database_view, self.viewer, self.bank)

    def run(self) -> None:
        self.database_view.load_accounts()
        self.__app_cycle()

    def stop(self) -> None:
        self.database_view.save_accounts()

    def __app_cycle(self) -> None:
        while True:
            command = self.input.get_input()
            command = tuple(command.split(' '))
            if self.command_handler.process(command):
                self.stop()
                break
