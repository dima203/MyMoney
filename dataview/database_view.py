import datetime
from abc import ABC, abstractmethod
from typing import Any

from core import Account, Transaction, Resource
from core.journal_entry import JournalEntry
from database import DataBase


class BaseView(ABC):
    def __init__(self, database: DataBase, *, reserve_database: DataBase = None) -> None:
        self._database = database
        self._reserve_database = reserve_database

    @abstractmethod
    def get(self, pk: str | int) -> Any: ...
    @abstractmethod
    def get_all(self) -> dict[str | int, Any]: ...
    @abstractmethod
    def add(self, item: Any) -> None: ...
    @abstractmethod
    def delete(self, pk: str | int) -> None: ...
    @abstractmethod
    def update(self, pk: int | str, data: dict) -> None: ...
    @abstractmethod
    def load(self) -> None: ...
    @abstractmethod
    def save(self) -> None: ...


class ResourceBaseView(BaseView):
    def __init__(self, database: DataBase, *, reserve_database: DataBase = None) -> None:
        super().__init__(database, reserve_database=reserve_database)
        self._resources: dict[int, Resource] = {}
        self._pending_store = None

    def set_pending_store(self, store) -> None:
        self._pending_store = store

    def get(self, pk: int | str) -> Resource | None:
        return self._resources.get(pk)

    def get_all(self) -> dict[int | str, Resource]:
        return self._resources

    def add(self, item: Resource) -> None:
        data = {"name": item.name, "ticker": item.ticker}
        pk = self._database.add(data)
        temp_pk = pk is not None and pk < 0
        item.pk = pk
        if self._reserve_database is not None:
            if temp_pk:
                pk = self._reserve_database.add(item.to_json())
                item.pk = pk
            else:
                self._reserve_database.add(item.to_json())
        self._resources[pk] = item
        if temp_pk and self._pending_store is not None:
            self._pending_store.add("add", "resource", pk, data)

    def update(self, pk: str | int, data: dict) -> None:
        pass

    def delete(self, pk: str | int) -> None:
        del self._resources[pk]
        self._database.delete(pk)
        if self._reserve_database is not None:
            self._reserve_database.delete(pk)

    def load(self) -> None:
        updates = {}
        if self._reserve_database is not None:
            for d in self._reserve_database.load():
                pk = d.get("id", d.get("pk"))
                updates[pk] = d
                self._resources[pk] = Resource(
                    pk,
                    d["name"],
                    ticker=d.get("ticker", ""),
                    unit=d.get("unit", ""),
                    category=d.get("category", ""),
                    resource_type=d.get("resource_type", "custom"),
                    icon=d.get("icon", ""),
                )

        for d in self._database.load():
            pk = d["id"]
            last_update = d.get("created_at", "")
            reserve = updates.get(pk)
            if reserve and reserve.get("created_at", "") >= last_update:
                continue
            self._resources[pk] = Resource(
                pk,
                d["name"],
                ticker=d.get("ticker", ""),
                unit=d.get("unit", ""),
                category=d.get("category", ""),
                resource_type=d.get("resource_type", "custom"),
                icon=d.get("icon", ""),
            )

    def save(self) -> None:
        if self._reserve_database is not None:
            for pk, resource in self._resources.items():
                self._reserve_database.update(pk, resource.to_json())

    def _remap_pk(self, remap: dict[int, int]) -> None:
        for old_pk, new_pk in remap.items():
            if old_pk in self._resources:
                resource = self._resources.pop(old_pk)
                resource.pk = new_pk
                self._resources[new_pk] = resource
                if self._reserve_database is not None:
                    self._reserve_database.delete(old_pk)


class AccountBaseView(BaseView):
    def __init__(
        self, database: DataBase, resource_view: ResourceBaseView, *, reserve_database: DataBase = None
    ) -> None:
        super().__init__(database, reserve_database=reserve_database)
        self._accounts: dict[int, Account] = {}
        self._resource_view = resource_view
        self._pending_store = None

    def set_pending_store(self, store) -> None:
        self._pending_store = store

    def get(self, pk: str | int) -> Account | None:
        return self._accounts.get(pk)

    def get_all(self) -> dict[str | int, Account]:
        return self._accounts

    def add(self, item: Account) -> None:
        data = {
            "name": item.name,
            "group": item.group,
            "account_type": item.account_type,
            "resource_definition": item.value.currency.pk,
        }
        pk = self._database.add(data)
        temp_pk = pk is not None and pk < 0
        item.pk = pk
        if self._reserve_database is not None:
            if temp_pk:
                pk = self._reserve_database.add(item.to_json())
                item.pk = pk
            else:
                self._reserve_database.add(item.to_json())
        self._accounts[pk] = item
        self._accounts[pk].subscribe(self._on_account_update)
        if temp_pk and self._pending_store is not None:
            self._pending_store.add("add", "account", pk, data)

    def delete(self, pk: str | int) -> None:
        del self._accounts[pk]
        self._database.delete(pk)
        if self._reserve_database is not None:
            self._reserve_database.delete(pk)

    def update(self, pk: int | str, data: dict) -> None:
        self._database.update(pk, data)
        if self._reserve_database is not None:
            self._reserve_database.update(pk, data)

    def load(self) -> None:
        updates = {}
        if self._reserve_database is not None:
            for d in self._reserve_database.load():
                pk = d.get("id", d.get("pk"))
                updates[pk] = d
                resource = self._resource_view.get(d.get("resource_definition", d.get("resource_type")))
                if resource is None:
                    continue
                self._accounts[pk] = Account(
                    pk,
                    d["name"],
                    resource,
                    float(d.get("current_balance_qty", d.get("resource_count", 0))),
                    group=d.get("group", ""),
                    account_type=d.get("account_type", "main"),
                )

        for d in self._database.load():
            pk = d["id"]
            resource_def_id = d["resource_definition"]
            balance = float(d.get("current_balance_qty", 0))
            last_update = d.get("created_at", "")
            resource = self._resource_view.get(resource_def_id)
            if resource is None:
                continue

            reserve = updates.get(pk)
            if reserve and reserve.get("created_at", "") >= last_update:
                continue

            self._accounts[pk] = Account(
                pk,
                d["name"],
                resource,
                balance,
                group=d.get("group", ""),
                account_type=d.get("account_type", "main"),
            )

        for account in self._accounts.values():
            account.subscribe(self._on_account_update)

    def save(self) -> None:
        if self._reserve_database is not None:
            for pk, account in self._accounts.items():
                self._reserve_database.update(pk, account.to_json())

    def _on_account_update(self, pk: str | int, data: dict) -> None:
        self.update(pk, data)

    def reload_from_server(self) -> None:
        if not self._database.is_online:
            return
        self._accounts.clear()
        for d in self._database.load():
            pk = d["id"]
            resource_def_id = d["resource_definition"]
            balance = float(d.get("current_balance_qty", 0))
            resource = self._resource_view.get(resource_def_id)
            if resource is None:
                continue
            self._accounts[pk] = Account(
                pk,
                d["name"],
                resource,
                balance,
                group=d.get("group", ""),
                account_type=d.get("account_type", "main"),
            )
        for account in self._accounts.values():
            account.subscribe(self._on_account_update)
        self.save()

    def _remap_pk(self, remap: dict[int, int]) -> None:
        for old_pk, new_pk in remap.items():
            if old_pk in self._accounts:
                account = self._accounts.pop(old_pk)
                account.pk = new_pk
                self._accounts[new_pk] = account
                account.subscribe(self._on_account_update)
                if self._reserve_database is not None:
                    self._reserve_database.delete(old_pk)


class TransactionBaseView(BaseView):
    def __init__(self, database: DataBase, account_view: AccountBaseView, *, reserve_database: DataBase = None) -> None:
        super().__init__(database, reserve_database=reserve_database)
        self._transactions: dict[int, Transaction] = {}
        self._account_view = account_view
        self._on_data_changed: callable = None
        self._pending_store = None

    def set_pending_store(self, store) -> None:
        self._pending_store = store

    def get(self, pk: int) -> Transaction | None:
        return self._transactions.get(pk)

    def get_all(self) -> dict[int, Transaction]:
        return self._transactions

    def add(self, item: Transaction) -> None:
        data = {
            "id": item.pk,
            "date": item.date.isoformat(),
            "entries": [e.to_json() for e in item.entries],
            "category": item.category,
            "description": item.description,
            "recurrence_rule": item.recurrence_rule,
            "is_planned": item.is_planned,
        }
        pk = self._database.add(data)
        temp_pk = pk is not None and pk < 0
        item.pk = pk
        if self._reserve_database is not None:
            if temp_pk:
                pk = self._reserve_database.add(item.to_json())
                item.pk = pk
            else:
                self._reserve_database.add(item.to_json())
        self._transactions[pk] = item
        self._transactions[pk].subscribe(self._on_transaction_update)
        if temp_pk and self._pending_store is not None:
            self._pending_store.add("add", "transaction", pk, data)
        self._account_view.reload_from_server()
        if self._on_data_changed:
            self._on_data_changed()

    def delete(self, pk: int) -> None:
        self._database.delete(pk)
        if self._reserve_database is not None:
            self._reserve_database.delete(pk)
        del self._transactions[pk]
        self._account_view.reload_from_server()
        if self._on_data_changed:
            self._on_data_changed()

    def update(self, pk: int, data: dict) -> None:
        self._database.update(pk, data)
        if self._reserve_database is not None:
            self._reserve_database.update(pk, data)
        self._account_view.reload_from_server()
        if self._on_data_changed:
            self._on_data_changed()

    def load(self) -> None:
        updates = {}
        if self._reserve_database is not None:
            for d in self._reserve_database.load():
                pk = d.get("id", d.get("pk"))
                updates[pk] = d
                entries = _parse_entries(d.get("entries", []))
                date_str = d.get("date", d.get("time_stamp", ""))
                time_stamp = datetime.datetime.fromisoformat(date_str) if date_str else datetime.datetime.now()
                self._transactions[pk] = Transaction(
                    pk,
                    time_stamp,
                    entries,
                    category=d.get("category", ""),
                    description=d.get("description", ""),
                    recurrence_rule=d.get("recurrence_rule", ""),
                    is_planned=d.get("is_planned", False),
                )

        for d in self._database.load():
            pk = d["id"]
            date_str = d.get("date", "")
            time_stamp = datetime.datetime.fromisoformat(date_str) if date_str else datetime.datetime.now()
            last_update = d.get("created_at", "")
            entries = _parse_entries(d.get("entries", []))

            reserve = updates.get(pk)
            if reserve and reserve.get("created_at", "") >= last_update:
                continue

            self._transactions[pk] = Transaction(
                pk,
                time_stamp,
                entries,
                category=d.get("category", ""),
                description=d.get("description", ""),
                recurrence_rule=d.get("recurrence_rule", ""),
                is_planned=d.get("is_planned", False),
            )

        for tx in self._transactions.values():
            tx.subscribe(self._on_transaction_update)

    def save(self) -> None:
        if self._reserve_database is not None:
            for pk, tx in self._transactions.items():
                self._reserve_database.update(pk, tx.to_json())

    def _on_transaction_update(self, pk: str | int, data: dict) -> None:
        self.update(pk, data)

    def _remap_pk(self, remap: dict[int, int]) -> None:
        for old_pk, new_pk in remap.items():
            if old_pk in self._transactions:
                tx = self._transactions.pop(old_pk)
                tx.pk = new_pk
                self._transactions[new_pk] = tx
                tx.subscribe(self._on_transaction_update)
                if self._reserve_database is not None:
                    self._reserve_database.delete(old_pk)

    def get_planned(self) -> dict[int, Transaction]:
        return {pk: tx for pk, tx in self._transactions.items() if tx.is_planned}

    def get_by_category(self, category: str) -> dict[int, Transaction]:
        return {pk: tx for pk, tx in self._transactions.items() if tx.category == category}


def _parse_entries(entries_data: list[dict]) -> list[JournalEntry]:
    entries = []
    for e in entries_data:
        entries.append(
            JournalEntry(
                account_id=e.get("account", e.get("account_id", 0)),
                quantity=float(e.get("quantity", 0)),
                amount=float(e.get("amount", 0)),
                unit_price=float(e.get("unit_price", 1)),
            )
        )
    return entries
