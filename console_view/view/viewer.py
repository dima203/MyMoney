from abc import ABC, abstractmethod

from core import Account


class Viewer(ABC):
    @abstractmethod
    def show_accounts(self, accounts: dict[str, Account]) -> None:
        pass

    @abstractmethod
    def show_account(self, name: str, account: Account) -> None:
        pass

    @abstractmethod
    def show_error(self, error_message: str) -> None:
        pass


class ConsoleViewer(Viewer):
    def show_accounts(self, accounts: dict[str, Account]) -> None:
        for name, account in accounts.items():
            print(name, account.value)

    def show_account(self, name: str, account: Account) -> None:
        print(name, account.value)

    def show_error(self, error_message: str) -> None:
        print(error_message)
