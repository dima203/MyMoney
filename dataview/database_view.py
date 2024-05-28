import datetime
from abc import ABC, abstractmethod

from core import Account, Money, Transaction, Resource
from database import DataBase


class BaseView(ABC):
    def __init__(self, database: DataBase, *, reserve_database: DataBase) -> None:
        self._database = database
        self._reserve_database = reserve_database

    @abstractmethod
    def get(self, pk: str | int) -> ...: ...
    @abstractmethod
    def get_all(self) -> dict[str | int, ...]: ...
    @abstractmethod
    def add(self, item: ...) -> None: ...
    @abstractmethod
    def delete(self, pk: str | int) -> None: ...
    @abstractmethod
    def update(self, pk: str | int) -> None: ...
    @abstractmethod
    def load(self) -> None: ...
    @abstractmethod
    def save(self) -> None: ...


class ResourceBaseView(BaseView):
    def __init__(self, database: DataBase, *, reserve_database: DataBase) -> None:
        super().__init__(database, reserve_database=reserve_database)
        self.__resources: dict[int, Resource] = {}

    def get(self, pk: int) -> Resource:
        return self.__resources[pk]

    def get_all(self) -> dict[int, Resource]:
        return self.__resources

    def add(self, item: ...) -> None:
        pass

    def update(self, pk: str | int) -> None:
        pass

    def delete(self, pk: str | int) -> None:
        del self.__resources[pk]
        self._database.delete(pk)
        self._reserve_database.delete(pk)

    def load(self) -> None:
        resources_updates = {}
        for resource_data in self._reserve_database.load():
            resources_updates[resource_data['pk']] = resource_data['last_update']
            self.__resources[resource_data['pk']] = Resource(resource_data['pk'], resource_data['name'])
        for resource_data in self._database.load():
            if resource_data['pk'] in resources_updates:
                if resources_updates[resource_data['pk']] < resource_data['last_update']:
                    self.__resources[resource_data['pk']] = Resource(resource_data['pk'], resource_data['name'])
            else:
                self.__resources[resource_data['pk']] = Resource(resource_data['pk'], resource_data['name'])

    def save(self) -> None:
        for pk, resource in self.__resources.items():
            self._database.update(pk, resource.to_json())
            self._reserve_database.update(pk, resource.to_json())


class AccountBaseView(BaseView):
    def __init__(self, database: DataBase, resource_view: ResourceBaseView, *, reserve_database: DataBase) -> None:
        super().__init__(database, reserve_database=reserve_database)
        self.__accounts: dict[int, Account] = {}
        self.__resource_view = resource_view

    def get(self, pk: int) -> Account | None:
        return self.__accounts.get(pk)

    def get_all(self) -> dict[int, Account]:
        return self.__accounts

    def add(self, item: Account) -> None:
        pk = self._database.add(item.to_json())
        item.pk = pk
        self.__accounts[pk] = item

    def delete(self, pk: int) -> None:
        del self.__accounts[pk]
        self._database.delete(pk)
        self._reserve_database.delete(pk)

    def update(self, pk: int) -> None:
        self._database.update(pk, self.__accounts[pk].to_json())

    def load(self) -> None:
        storages_updates = {}
        for account_data in self._reserve_database.load():
            storages_updates[account_data['pk']] = account_data['last_update']
            self.__accounts[account_data['pk']] = Account(
                account_data['pk'],
                account_data['name'],
                self.__resource_view.get(account_data['resource_type']),
                account_data['resource_count']
            )
        for account_data in self._database.load():
            if account_data['pk'] in storages_updates:
                if storages_updates[account_data['pk']] < account_data['last_update']:
                    self.__accounts[account_data['pk']] = Account(
                        account_data['pk'],
                        account_data['name'],
                        self.__resource_view.get(account_data['resource_type']),
                        account_data['resource_count']
                    )
            else:
                self.__accounts[account_data['pk']] = Account(
                    account_data['pk'],
                    account_data['name'],
                    self.__resource_view.get(account_data['resource_type']),
                    account_data['resource_count']
                )

    def save(self) -> None:
        for pk, storage in self.__accounts.items():
            self._database.update(pk, storage.to_json())
            self._reserve_database.update(pk, storage.to_json())


class TransactionBaseView(BaseView):
    def __init__(self, database: DataBase, account_view: AccountBaseView, *, reserve_database: DataBase) -> None:
        super().__init__(database, reserve_database=reserve_database)
        self.__transactions: dict[int, Transaction] = {}
        self.__account_view = account_view

    def get(self, pk: int) -> Transaction | None:
        return self.__transactions.get(pk)

    def get_all(self) -> dict[int, Transaction]:
        return self.__transactions

    def add(self, item: Transaction) -> None:
        pk = self._database.add(item.to_json())
        self.__transactions[pk] = item

    def delete(self, pk: int) -> None:
        del self.__transactions[pk]
        self._database.delete(pk)
        self._reserve_database.delete(pk)

    def update(self, pk: int) -> None:
        self._database.update(pk, self.__transactions[pk].to_json())

    def load(self) -> None:
        transactions_updates = {}
        for transaction_data in self._reserve_database.load():
            transactions_updates[transaction_data['pk']] = transaction_data['last_update']
            storage = self.__account_view.get(transaction_data['storage_id'])
            time_stamp = datetime.datetime.fromisoformat(transaction_data['time_stamp'])
            self.__transactions[transaction_data['pk']] = Transaction(storage,
                                                                      Money(transaction_data['resource_count'],
                                                                            storage.value.currency),
                                                                      time_stamp)
        for transaction_data in self._database.load():
            if transaction_data['pk'] in transactions_updates:
                if transactions_updates[transaction_data['pk']] < transaction_data['last_update']:
                    storage = self.__account_view.get(transaction_data['storage_id'])
                    time_stamp = datetime.datetime.fromisoformat(transaction_data['time_stamp'])
                    self.__transactions[transaction_data['pk']] = Transaction(storage,
                                                                              Money(transaction_data['resource_count'],
                                                                                    storage.value.currency),
                                                                              time_stamp)
            else:
                storage = self.__account_view.get(transaction_data['storage_id'])
                time_stamp = datetime.datetime.fromisoformat(transaction_data['time_stamp'])
                self.__transactions[transaction_data['pk']] = Transaction(storage,
                                                                          Money(transaction_data['resource_count'],
                                                                                storage.value.currency),
                                                                          time_stamp)

    def save(self) -> None:
        for pk, transaction in self.__transactions.items():
            self._database.update(pk, transaction.to_json())
            self._reserve_database.update(pk, transaction.to_json())

