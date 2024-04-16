from abc import ABC, abstractmethod

from core import Account, Money, Transaction, Transfer, Income, Expense, Bank
from database import DataBase


class BaseView(ABC):
    def __init__(self, database: DataBase) -> None:
        self._database = database

    @abstractmethod
    def get(self, pk: str | int) -> ...: ...
    @abstractmethod
    def get_all(self) -> dict[str | int, ...]: ...
    @abstractmethod
    def add(self, pk: str | int, item: ...) -> None: ...
    @abstractmethod
    def delete(self, pk: str | int) -> None: ...
    @abstractmethod
    def load(self) -> None: ...


class ResourceBaseView(BaseView):
    def __init__(self, database: DataBase) -> None:
        super().__init__(database)
        self.__resources: dict[str, str] = {}

    def get(self, pk: str) -> str:
        return self.__resources[pk]

    def get_all(self) -> dict[str, str]:
        return self.__resources

    def add(self, pk: str | int, item: ...) -> None:
        pass

    def delete(self, pk: str | int) -> None:
        pass

    def load(self) -> None:
        for resource_data in self._database.load():
            self.__resources[resource_data['pk']] = resource_data['name']


class AccountBaseView(BaseView):
    def __init__(self, database: DataBase, resource_view: ResourceBaseView) -> None:
        super().__init__(database)
        self.__accounts: dict[int, Account] = {}
        self.__resource_view = resource_view

    def get(self, pk: int) -> Account | None:
        return self.__accounts.get(pk)

    def get_all(self) -> dict[int, Account]:
        return self.__accounts

    def add(self, pk: int, item: Account) -> None:
        self.__accounts[pk] = item

    def delete(self, pk: int) -> None:
        del self.__accounts[pk]
        self._database.delete(pk)

    def load(self) -> None:
        for account_data in self._database.load():
            account = Account(
                account_data['name'],
                self.__resource_view.get(account_data['resource_type']),
                account_data['resource_count']
            )
            self.__accounts[account_data['pk']] = account

    def save_accounts(self) -> None:
        accounts_dict = {}
        for key, account in self.__accounts.items():
            accounts_dict[key] = account.to_json()
        self._database.save(accounts_dict)


class TransactionBaseView(BaseView):
    def __init__(self, database: DataBase, account_view: AccountBaseView) -> None:
        super().__init__(database)
        self.__transactions: dict[int, Transaction] = {}
        self.__account_view = account_view

    def get(self, pk: int) -> Transaction | None:
        return self.__transactions.get(pk)

    def get_all(self) -> dict[int, Transaction]:
        return self.__transactions

    def add(self, pk: int, item: Transaction) -> None:
        self.__transactions[pk] = item

    def delete(self, pk: str | int) -> None:
        del self.__transactions[pk]
        self._database.delete(pk)

    def load(self) -> None:
        for transaction_data in self._database.load():
            storage = self.__account_view.get(transaction_data['storage_id'])
            self.__transactions[transaction_data['pk']] = Transaction(storage,
                                                                      Money(transaction_data['resource_count'],
                                                                            storage.value.currency))

    def save_transactions(self) -> None:
        transaction_dict = {}
        for key, transaction in self.__transactions.items():
            transaction_dict[key] = transaction.to_json()
        self._database.save(transaction_dict)
