from core import Bank, Account, Transfer, Money


class TestTransaction:
    def setup_method(self) -> None:
        self.bank = Bank()
        self.bank.add_exchange('USD', 'BYN', 2.5)

    def test_transaction_create(self) -> None:
        account = Account('BYN')
        target_account = Account('BYN')
        transaction = Transfer(account, target_account, Money.byn(10))

    def test_transaction_accept(self) -> None:
        account = Account('BYN')
        account.add(Money.byn(10), self.bank)
        target_account = Account('BYN')
        transaction = Transfer(account, target_account, Money.byn(10))
        transaction.accept(self.bank)
        assert account.value == Money.byn(0) and target_account.value == Money.byn(10)
