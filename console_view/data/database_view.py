from core import Account, Money, Transaction
from database import JSONBase


class AccountBaseView:
    def __init__(self, database: JSONBase) -> None:
        self.__accounts: dict[str, Account] = {}
        self.__database = database

    def get_account(self, name: str) -> Account | None:
        return self.__accounts.get(name)

    def get_accounts(self) -> dict[str, Account]:
        return self.__accounts

    def add_account(self, name: str, account: Account) -> None:
        self.__accounts[name] = account

    def load_accounts(self) -> None:
        for key, account_data in self.__database.load().items():
            account = Account(account_data['currency'])
            account.value = Money(account_data['value'], account_data['currency'])
            self.__accounts[key] = account

    def save_accounts(self) -> None:
        accounts_dict = {}
        for key, account in self.__accounts.items():
            accounts_dict[key] = account.to_json()
        self.__database.save(accounts_dict)


class TransactionBaseView:
    def __init__(self, database: JSONBase) -> None:
        self.__transactions: dict[int, Transaction] = {}
        self.__database = database

    def get_transaction(self, transaction_id: int) -> Transaction:
        pass

