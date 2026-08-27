import datetime
from abc import ABC, abstractmethod
from typing import Any

from core import Account, Money, Transaction, Resource, PlannedTransaction
from database import DataBase


class BaseView(ABC):
    def __init__(self, database: DataBase, *, reserve_database: DataBase = None) -> None:
        self._database = database
        self._reserve_database = reserve_database

    @abstractmethod
    def get(self, pk: str | int) -> Any: ...
    @abstractmethod
    def get_all(self) -> dict[str | int, ...]: ...
    @abstractmethod
    def add(self, item: Any) -> None: ...
    @abstractmethod
    def delete(self, pk: str | int) -> None: ...
    @abstractmethod
    def update(self, pk: str | int, data: dict) -> None: ...
    @abstractmethod
    def load(self) -> None: ...
    @abstractmethod
    def save(self) -> None: ...


class ResourceBaseView(BaseView):
    def __init__(self, database: DataBase, *, reserve_database: DataBase = None) -> None:
        super().__init__(database, reserve_database=reserve_database)
        self.__resources: dict[int, Resource] = {}

    def get(self, pk: int | str) -> Resource:
        return self.__resources[pk]

    def get_all(self) -> dict[int | str, Resource]:
        return self.__resources

    def add(self, item: Resource) -> None:
        data = {
            "name": item.name,
        }
        pk = self._database.add(data)
        item.pk = pk
        if self._reserve_database is not None:
            if pk is None:
                pk = self._reserve_database.add(item.to_json())
            else:
                self._reserve_database.add(item.to_json())
        item.pk = pk
        self.__resources[pk] = item

    def update(self, pk: str | int, data: dict) -> None:
        pass

    def delete(self, pk: str | int) -> None:
        del self.__resources[pk]
        self._database.delete(pk)
        if self._reserve_database is not None:
            self._reserve_database.delete(pk)

    def load(self) -> None:
        resources_updates = {}
        if self._reserve_database is not None:
            for resource_data in self._reserve_database.load():
                resources_updates[resource_data["pk"]] = resource_data["last_update"]
                self.__resources[resource_data["pk"]] = Resource(resource_data["pk"], resource_data["name"])
        for resource_data in self._database.load():
            pk = resource_data["id"]
            last_update = resource_data.get("created_at", "")
            if pk in resources_updates:
                if resources_updates[pk] < last_update:
                    self.__resources[pk] = Resource(pk, resource_data["name"])
            else:
                self.__resources[pk] = Resource(pk, resource_data["name"])

    def save(self) -> None:
        for pk, resource in self.__resources.items():
            if self._reserve_database is not None:
                self._reserve_database.update(pk, resource.to_json())


class AccountBaseView(BaseView):
    def __init__(
        self, database: DataBase, resource_view: ResourceBaseView, *, reserve_database: DataBase = None
    ) -> None:
        super().__init__(database, reserve_database=reserve_database)
        self.__accounts: dict[int, Account] = {}
        self.__resource_view = resource_view

    def get(self, pk: str | int) -> Account | None:
        return self.__accounts.get(pk)

    def get_all(self) -> dict[str | int, Account]:
        return self.__accounts

    def add(self, item: Account) -> None:
        data = {
            "name": item.name,
            "resource_definition": item.value.currency.pk,
        }
        pk = self._database.add(data)
        item.pk = pk
        if self._reserve_database is not None:
            if pk is None:
                pk = self._reserve_database.add(item.to_json())
            else:
                self._reserve_database.add(item.to_json())
        item.pk = pk
        self.__accounts[pk] = item
        self.__accounts[pk].subscribe(self._on_account_update)

    def delete(self, pk: str | int) -> None:
        del self.__accounts[pk]
        self._database.delete(pk)
        if self._reserve_database is not None:
            self._reserve_database.delete(pk)

    def update(self, pk: int | str, data: dict) -> None:
        self._database.update(pk, data)
        if self._reserve_database is not None:
            self._reserve_database.update(pk, data)

    def load(self) -> None:
        storages_updates = {}
        if self._reserve_database is not None:
            for account_data in self._reserve_database.load():
                storages_updates[account_data["pk"]] = account_data["last_update"]
                self.__accounts[account_data["pk"]] = Account(
                    account_data["pk"],
                    account_data["name"],
                    self.__resource_view.get(account_data["resource_type"]),
                    account_data["resource_count"],
                )
        for account_data in self._database.load():
            pk = account_data["id"]
            name = account_data["name"]
            resource_def_id = account_data["resource_definition"]
            balance = float(account_data.get("current_balance_qty", 0))
            last_update = account_data.get("created_at", "")
            resource = self.__resource_view.get(resource_def_id)

            if resource is None:
                continue

            if pk in storages_updates:
                if storages_updates[pk] < last_update:
                    self.__accounts[pk] = Account(pk, name, resource, balance)
            else:
                self.__accounts[pk] = Account(pk, name, resource, balance)

        for account in self.__accounts.values():
            account.subscribe(self._on_account_update)

    def save(self) -> None:
        for pk, storage in self.__accounts.items():
            if self._reserve_database is not None:
                self._reserve_database.update(pk, storage.to_json())

    def _on_account_update(self, pk: str | int, data: dict) -> None:
        self.update(pk, data)


class TransactionBaseView(BaseView):
    def __init__(self, database: DataBase, account_view: AccountBaseView, *, reserve_database: DataBase = None) -> None:
        super().__init__(database, reserve_database=reserve_database)
        self.__transactions: dict[int, Transaction] = {}
        self.__account_view = account_view

    def get(self, pk: int) -> Transaction | None:
        return self.__transactions.get(pk)

    def get_all(self) -> dict[int, Transaction]:
        return self.__transactions

    def add(self, item: Transaction) -> None:
        data = {
            "date": item.time_stamp.strftime("%Y-%m-%d"),
            "entries": [
                {
                    "account": item.storage.pk,
                    "quantity": item.value.value,
                    "amount": abs(item.value.value),
                    "unit_price": 1,
                }
            ],
        }
        pk = self._database.add(data)
        item.pk = pk
        if self._reserve_database is not None:
            if pk is None:
                pk = self._reserve_database.add(item.to_json())
            else:
                self._reserve_database.add(item.to_json())
        item.pk = pk
        self.__transactions[pk] = item
        self.__transactions[pk].subscribe(self._on_transaction_update)
        self.__transactions[pk].execute()

    def delete(self, pk: int) -> None:
        self._database.delete(pk)
        if self._reserve_database is not None:
            self._reserve_database.delete(pk)
        del self.__transactions[pk]

    def update(self, pk: int, data: dict) -> None:
        self._database.update(pk, data)
        if self._reserve_database is not None:
            self._reserve_database.update(pk, data)

    def load(self) -> None:
        transactions_updates = {}
        if self._reserve_database is not None:
            for transaction_data in self._reserve_database.load():
                transactions_updates[transaction_data["pk"]] = transaction_data["last_update"]
                storage = self.__account_view.get(transaction_data["storage_id"])
                time_stamp = datetime.datetime.fromisoformat(transaction_data["time_stamp"])
                self.__transactions[transaction_data["pk"]] = Transaction(
                    transaction_data["pk"],
                    storage,
                    Money(transaction_data["resource_count"], storage.value.currency),
                    time_stamp,
                )
        for transaction_data in self._database.load():
            pk = transaction_data["id"]
            date_str = transaction_data.get("date", "")
            time_stamp = datetime.datetime.fromisoformat(date_str) if date_str else datetime.datetime.now()
            last_update = transaction_data.get("created_at", "")
            entries = transaction_data.get("entries", [])

            if not entries:
                continue

            entry = entries[0]
            storage = self.__account_view.get(entry["account"])
            if storage is None:
                continue

            quantity = float(entry.get("quantity", 0))
            amount = float(entry.get("amount", 0))

            if pk in transactions_updates:
                if transactions_updates[pk] < last_update:
                    self.__transactions[pk] = Transaction(
                        pk, storage, Money(amount, storage.value.currency), time_stamp,
                    )
            else:
                self.__transactions[pk] = Transaction(
                    pk, storage, Money(amount, storage.value.currency), time_stamp,
                )

        for transaction in self.__transactions.values():
            transaction.subscribe(self._on_transaction_update)

    def save(self) -> None:
        for pk, transaction in self.__transactions.items():
            if self._reserve_database is not None:
                self._reserve_database.update(pk, transaction.to_json())

    def _on_transaction_update(self, pk: str | int, data: dict) -> None:
        self.update(pk, data)


class PlannedTransactionBaseView(BaseView):
    def __init__(self, database: DataBase, account_view: AccountBaseView, *, reserve_database: DataBase) -> None:
        super().__init__(database, reserve_database=reserve_database)
        self.__transactions: dict[int, PlannedTransaction] = {}
        self.__account_view = account_view

    def get(self, pk: int) -> PlannedTransaction | None:
        return self.__transactions.get(pk)

    def get_all(self) -> dict[int, PlannedTransaction]:
        return self.__transactions

    def add(self, item: PlannedTransaction) -> None:
        pk = self._database.add(item.to_json())
        self.__transactions[pk] = item

    def delete(self, pk: int) -> None:
        del self.__transactions[pk]
        self._database.delete(pk)

    def update(self, pk: str | int, data: dict) -> None:
        self._database.update(pk, self.__transactions[pk].to_json())

    def load(self) -> None:
        for transaction_data in self._database.load():
            source_id = transaction_data.get("source_id", 0)
            title = transaction_data.get("title", "")
            date_str = transaction_data.get("date", "")
            planned_time = datetime.datetime.fromisoformat(date_str) if date_str else datetime.datetime.now()
            amount = float(transaction_data.get("amount", 0))
            currency_ticker = transaction_data.get("currency", "")

            accounts = self.__account_view.get_all()
            storage = None
            for acc in accounts.values():
                if acc.value.currency.name == currency_ticker or acc.name.lower() in title.lower():
                    storage = acc
                    break
            if storage is None and accounts:
                storage = next(iter(accounts.values()))

            if storage is None:
                continue

            self.__transactions[source_id] = PlannedTransaction(
                storage, Money(amount, storage.value.currency), planned_time, 0,
            )

    def save(self) -> None:
        pass
