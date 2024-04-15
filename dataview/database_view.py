from core import Account, Money, Transaction, Transfer, Income, Expense, Bank
from database import DataBase


class ResourceBaseView:
    def __init__(self, database: DataBase) -> None:
        self.__resources: dict[str, str] = {}
        self.__database = database

    def get_resource(self, id: str) -> str:
        return self.__resources[id]

    def get_resources(self) -> dict[str, str]:
        return self.__resources

    def load_resources(self) -> None:
        for resource_data in self.__database.load():
            self.__resources[resource_data['pk']] = resource_data['name']


class AccountBaseView:
    def __init__(self, database: DataBase) -> None:
        self.__accounts: dict[int, Account] = {}
        self.__database = database

    def get_account(self, pk: int) -> Account | None:
        return self.__accounts.get(pk)

    def get_accounts(self) -> dict[int, Account]:
        return self.__accounts

    def add_account(self, pk: int, account: Account) -> None:
        self.__accounts[pk] = account

    def delete_account(self, pk: int) -> None:
        del self.__accounts[pk]
        self.__database.delete(pk)

    def load_accounts(self, resource_view: ResourceBaseView) -> None:
        for account_data in self.__database.load():
            account = Account(account_data['name'], resource_view.get_resource(account_data['resource_type']), account_data['resource_count'])
            self.__accounts[account_data['pk']] = account

    def save_accounts(self) -> None:
        accounts_dict = {}
        for key, account in self.__accounts.items():
            accounts_dict[key] = account.to_json()
        self.__database.save(accounts_dict)


class TransactionBaseView:
    def __init__(self, database: DataBase) -> None:
        self.__transactions: dict[int, Transaction] = {}
        self.__database = database
        self.__last_id = 0

    def get_transaction(self, transaction_id: int) -> Transaction | None:
        return self.__transactions.get(transaction_id)

    def get_transactions(self) -> dict[int, Transaction]:
        return self.__transactions

    def add_transaction(self, transaction: Transaction) -> None:
        self.__last_id += 1
        self.__transactions[self.__last_id] = transaction
        transaction.id = self.__last_id

    def load_transactions(self, account_view: AccountBaseView) -> None:
        for transaction_data in self.__database.load():
            storage = account_view.get_account(transaction_data['storage_id'])
            self.__transactions[transaction_data['pk']] = Transaction(storage,
                                                                      Money(transaction_data['resource_count'],
                                                                            storage.value.currency))

    def save_transactions(self) -> None:
        transaction_dict = {}
        for key, transaction in self.__transactions.items():
            transaction_dict[key] = transaction.to_json()
        self.__database.save(transaction_dict)
