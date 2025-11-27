from core import Account, Money, Bank, Income, Transfer


class TestAccount:
    def setup_method(self) -> None:
        self.bank = Bank()
        self.bank.add_exchange("USD", "BYN", 2.5)

    def test_get_currency(self) -> None:
        account = Account("", "BYN")
        assert account.get_balance() == Money.byn(0)

    def test_to_json(self) -> None:
        test_account = Account("test", "RUB")
        acc2 = Account("test2", "RUB")
        transaction = Income(0, test_account, Money.rub(100), self.bank)
        assert transaction.to_json() == {"resource_type": "RUB", "resource_count": 100}
        transfer = Transfer(1, test_account, acc2, Money.rub(30), self.bank)
        assert transfer.to_json() == {"type": "Transfer", "currency": "RUB", "value": 30, "from": "test"}

    # TODO: add sum of few accounts
