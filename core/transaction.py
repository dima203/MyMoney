from .storage import Storage
from .account import Account
from .exchange import Bank
from .money import Money


class Transaction(Storage):
    def __init__(self, transaction_id: int, currency: Money) -> None:
        self.id = transaction_id
        self._value = currency
        self._type = 'None'

    def get_balance(self) -> Money:
        return self._value

    def connect(self) -> None:
        ...

    def to_json(self) -> dict[str, str | int]:
        return {
            'value': self._value.value,
            'currency': self._value.currency,
            'type': self._type
        }


class Transfer(Transaction):
    from_account_name = None

    def __init__(self, transaction_id: int, to_account: Account | None, from_account: Account | None,
                 currency: Money, bank: Bank) -> None:
        self.expense = Expense(f'{transaction_id}_exp', from_account, currency, bank)
        if to_account is not None:
            super().__init__(transaction_id, bank.exchange(currency, to_account.currency))
            to_account.add_source(self)
        else:
            super().__init__(transaction_id, currency)
        self._type = 'Transfer'
        self.__from = to_account
        self.__bank = bank

    def connect(self, from_account: Account, to_account: Account) -> None:
        to_account.add_source(self)
        self.expense.connect(from_account)
        self.__from = from_account
        self._value = self.__bank.exchange(self._value, to_account.currency)

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
            super().__init__(transaction_id, bank.exchange(currency, account.currency))
            account.add_source(self)
        else:
            super().__init__(transaction_id, currency)
        self._type = 'Income'
        self.__bank = bank

    def connect(self, account: Account) -> None:
        account.add_source(self)
        self._value = self.__bank.exchange(self._value, account.currency)


class Expense(Transaction):
    def __init__(self, transaction_id: int, account: Account | None, currency: Money, bank: Bank) -> None:
        if account is not None:
            super().__init__(transaction_id, -bank.exchange(currency, account.currency))
            account.add_source(self)
        else:
            super().__init__(transaction_id, -currency)
        self._type = 'Expense'
        self.__bank = bank

    def connect(self, account: Account) -> None:
        account.add_source(self)
        self._value = self.__bank.exchange(self._value, account.currency)
