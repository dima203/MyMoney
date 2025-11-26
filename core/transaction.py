import datetime

from .account import Account
from .exchange import Bank
from .money import Money


class Transaction:
    def __init__(self, pk: int, storage: Account, currency: Money, time_stamp: datetime.datetime) -> None:
        self.pk = pk
        self.storage = storage
        self.value = currency
        self.time_stamp = time_stamp

    def execute(self) -> None:
        self.storage.value += self.value

    def cancel(self) -> None:
        self.storage.value -= self.value

    def to_json(self) -> dict[str, str | int]:
        return {
            'pk': self.pk,
            'storage_id': self.storage.pk,
            'resource_count': self.value.value,
            'resource_type': self.value.currency.pk,
            'time_stamp': self.time_stamp.isoformat(),
            'last_update': datetime.datetime.now().isoformat()
        }

    def __del__(self) -> None:
        self.cancel()


class Transfer(Transaction):
    from_account_name = None

    def __init__(self, transaction_id: int, to_account: Account | None, from_account: Account | None,
                 currency: Money, bank: Bank) -> None:
        self.expense = Expense(f'{transaction_id}_exp', from_account, currency, bank)
        if to_account is not None:
            super().__init__(transaction_id, bank.exchange(currency, to_account.value.currency))
        else:
            super().__init__(transaction_id, currency)
        self._type = 'Transfer'
        self.__from = to_account
        self.__bank = bank

    def __del__(self) -> None:
        del self.expense

    def to_json(self) -> dict[str, str | int]:
        return {
            'value': self._value.value,
            'currency': self._value.currency,
            'type': self._type,
            'from': self.__from.name
        }


class Income(Transaction):
    def __init__(self, transaction_id: int, account: Account | None, currency: Money, bank: Bank) -> None:
        if account is not None:
            super().__init__(transaction_id, bank.exchange(currency, account.value.currency))
        else:
            super().__init__(transaction_id, currency)
        self._type = 'Income'
        self.__bank = bank


class Expense(Transaction):
    def __init__(self, transaction_id: int, account: Account | None, currency: Money, bank: Bank) -> None:
        if account is not None:
            super().__init__(transaction_id, -bank.exchange(currency, account.value.currency))
        else:
            super().__init__(transaction_id, -currency)
        self._type = 'Expense'
        self.__bank = bank
