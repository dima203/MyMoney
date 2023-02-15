from core import Account, Money, Transaction, Transfer, Income, Expense, Bank
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

    def load_transactions_to_accounts(self, transactions_base: 'TransactionBaseView') -> None:
        for account in self.__accounts.values():
            for transaction_id in account.get_sources():
                transaction = transactions_base.get_transaction(transaction_id)
                account.add_source(transaction)
                if isinstance(transaction, Transfer):
                    transaction.connect(self.get_account(transaction.from_account_name), account)

    def load_accounts(self) -> None:
        for key, account_data in self.__database.load().items():
            account = Account(key, account_data['currency'], account_data['sources'])
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
        self.__last_id = 0

    def get_transaction(self, transaction_id: int) -> Transaction | None:
        return self.__transactions.get(transaction_id)

    def get_transactions(self) -> dict[int, Transaction]:
        return self.__transactions

    def add_transaction(self, transaction: Transaction) -> None:
        self.__last_id += 1
        self.__transactions[self.__last_id] = transaction
        transaction.id = self.__last_id

    def load_transactions(self) -> None:
        for key, transaction_data in self.__database.load().items():
            key = int(key)
            transaction = None
            if transaction_data['type'] == 'Transfer':
                transaction = Transfer(key, None, None,
                                       Money(transaction_data['value'], transaction_data['currency']),
                                       Bank())
                transaction.from_account_name = transaction_data['from']
            elif transaction_data['type'] == 'Income':
                transaction = Income(key, None, Money(transaction_data['value'], transaction_data['currency']), Bank())
            elif transaction_data['type'] == 'Expense':
                transaction = Expense(key, None, Money(transaction_data['value'], transaction_data['currency']), Bank())
            self.__transactions[key] = transaction
        self.__last_id = max(self.__transactions.keys()) if self.__transactions.keys() else 0

    def save_transactions(self) -> None:
        transaction_dict = {}
        for key, transaction in self.__transactions.items():
            transaction_dict[key] = transaction.to_json()
        self.__database.save(transaction_dict)
