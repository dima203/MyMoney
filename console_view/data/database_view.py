import json
from pathlib import Path


from core import Account, Money


class DataBaseView:
    def __init__(self) -> None:
        self.__accounts: dict[str, Account] = {}

    def get_account(self, name: str) -> Account | None:
        return self.__accounts.get(name)

    def add_account(self, name: str, account: Account) -> None:
        self.__accounts[name] = account

    def load_accounts(self, source: Path) -> None:
        for key, account_data in json.load(source.open()).items():
            account = Account(account_data['currency'])
            account.value = Money(account_data['value'], account_data['currency'])
            self.__accounts[key] = account

    def save_accounts(self, source: Path) -> None:
        accounts_dict = {}
        for key, account in self.__accounts.items():
            accounts_dict[key] = account.to_json()
        json.dump(accounts_dict, source.open("w"), indent=2)
