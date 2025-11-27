from abc import ABC, abstractmethod

from core import Account, Transaction


class Color:
    HEADER = "\033[95m"
    FAIL = "\033[91m"
    DEFAULT = "\033[0m"
    BOLD = "\033[1m"


class Viewer(ABC):
    @abstractmethod
    def show_accounts(self, accounts: dict[str, Account]) -> None:
        pass

    @abstractmethod
    def show_account(self, name: str, account: Account) -> None:
        pass

    @abstractmethod
    def show_transactions(self, transactions: dict[int, Transaction]) -> None:
        pass

    @abstractmethod
    def show_error(self, error_message: str) -> None:
        pass


class ConsoleViewer(Viewer):
    def show_accounts(self, accounts: dict[str, Account]) -> None:
        print(f"+{'-' * 32}+{'-' * 32}+")
        print(
            f"|{Color.HEADER}{Color.BOLD}{'Name': ^32}{Color.DEFAULT}|"
            f"{Color.HEADER}{Color.BOLD}{'Currency': ^32}{Color.DEFAULT}|"
        )
        print(f"+{'-' * 32}+{'-' * 32}+")
        for name, account in accounts.items():
            print(f"|{name: ^32}|{str(account.get_balance()): ^32}|")
            print(f"+{'-' * 32}+{'-' * 32}+")

    def show_account(self, name: str, account: Account) -> None:
        print(name, account.get_balance())

    def show_transactions(self, transactions: dict[int, Transaction]) -> None:
        for transaction_id, transaction in transactions.items():
            print(transaction_id, transaction.get_balance())

    def show_error(self, error_message: str) -> None:
        print(f"{Color.FAIL}CommandError:")
        print(error_message + Color.DEFAULT)
