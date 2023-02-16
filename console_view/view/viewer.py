from abc import ABC, abstractmethod

from core import Account, Transaction


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
        for name, account in accounts.items():
            print(name, account.get_balance())

    def show_account(self, name: str, account: Account) -> None:
        print(name, account.get_balance())

    def show_transactions(self, transactions: dict[int, Transaction]) -> None:
        for transaction_id, transaction in transactions.items():
            print(transaction_id, transaction.get_balance())

    def show_error(self, error_message: str) -> None:
        print(error_message)
