import datetime
from typing import Callable


from .account import Account
from .exchange import Bank
from .money import Money


class Transaction:
    def __init__(self, pk: int, storage: Account, currency: Money, time_stamp: datetime.datetime) -> None:
        self.pk = pk
        self.storage = storage
        self.time_stamp = time_stamp
        self.__subscribers = []
        self._value = currency

    @property
    def value(self) -> Money:
        return self._value.copy()

    @value.setter
    def value(self, value: Money) -> None:
        self._value = value

    def subscribe(self, callback: Callable[[int | str, dict], None]) -> None:
        """Subscribe callback function on transaction value change."""
        self.__subscribers.append(callback)

    def unsubscribe(self, callback: Callable[[int | str, dict], None]) -> None:
        """Unsubscribe callback function on transaction value change."""
        self.__subscribers.remove(callback)

    def execute(self) -> None:
        self.storage.value += self._value

    def cancel(self) -> None:
        self.storage.value -= self._value

    def to_json(self) -> dict[str, str | int]:
        return {
            "pk": self.pk,
            "storage_id": self.storage.pk,
            "resource_count": self._value.value,
            "resource_type": self._value.currency.pk,
            "time_stamp": self.time_stamp.isoformat(),
            "last_update": datetime.datetime.now().isoformat(),
        }

    def __changed(self) -> None:
        if self.__subscribers is None:
            return

        for subscriber in self.__subscribers:
            subscriber(self.pk, self.to_json())

    def __setattr__(self, key, value) -> None:
        if key not in self.__dict__:
            object.__setattr__(self, key, value)
            return

        if key in ("_value", "storage"):
            self.cancel()
        object.__setattr__(self, key, value)
        if key in ("_value", "storage"):
            self.execute()
        self.__changed()

    def __del__(self) -> None:
        self.cancel()


class Transfer(Transaction):
    from_account_name = None

    def __init__(
        self, transaction_id: int, to_account: Account | None, from_account: Account | None, currency: Money, bank: Bank
    ) -> None:
        self.expense = Expense(f"{transaction_id}_exp", from_account, currency, bank)
        if to_account is not None:
            super().__init__(transaction_id, bank.exchange(currency, to_account.value.currency))
        else:
            super().__init__(transaction_id, currency)
        self._type = "Transfer"
        self.__from = to_account
        self.__bank = bank

    def __del__(self) -> None:
        del self.expense

    def to_json(self) -> dict[str, str | int]:
        return {
            "value": self._value.value,
            "currency": self._value.currency,
            "type": self._type,
            "from": self.__from.name,
        }


class Income(Transaction):
    def __init__(self, transaction_id: int, account: Account | None, currency: Money, bank: Bank) -> None:
        if account is not None:
            super().__init__(transaction_id, bank.exchange(currency, account.value.currency))
        else:
            super().__init__(transaction_id, currency)
        self._type = "Income"
        self.__bank = bank


class Expense(Transaction):
    def __init__(self, transaction_id: int, account: Account | None, currency: Money, bank: Bank) -> None:
        if account is not None:
            super().__init__(transaction_id, -bank.exchange(currency, account.value.currency))
        else:
            super().__init__(transaction_id, -currency)
        self._type = "Expense"
        self.__bank = bank
