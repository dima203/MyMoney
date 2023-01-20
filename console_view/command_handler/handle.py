from console_view.data import DataBaseView
from console_view.view import Viewer


class CommandHandler:
    def __init__(self, database_view: DataBaseView, viewer: Viewer) -> None:
        self.__database_view = database_view
        self.__viewer = viewer

    def process(self, command: tuple) -> bool:
        match command:
            case 'get', 'all':
                self.__viewer.show_accounts(self.__database_view.get_accounts())
            case 'get', name:
                if self.__database_view.get_account(name) is None:
                    self.__viewer.show_error(f'Account with name "{name}" is not exist.')
                    return False
                self.__viewer.show_account(name, self.__database_view.get_account(name))
            case 'exit', :
                return True
            case _:
                self.__viewer.show_error(f'Command "{command[0]}" is not exist.')
        return False
