from .account import Account
from .exchange import Bank
from .money import Money


class Transaction:
    def __init__(self, storage: Account, currency: Money) -> None:
        self.storage = storage
        self._value = currency

    def get_value(self) -> Money:
        return self._value

    def to_json(self) -> dict[str, str | int]:
        return {
            'resource_count': self._value.value,
            'resource_type': self._value.currency,
        }


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
            'from': self.__from.id
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
