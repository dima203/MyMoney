from core import Account, Money, Bank


class TestAccount:
    def setup_method(self) -> None:
        self.bank = Bank()
        self.bank.add_exchange('USD', 'BYN', 2.5)

    def test_get_currency(self) -> None:
        account = Account('BYN')
        assert account.value == Money.byn(0)

    def test_add_currency(self) -> None:
        account = Account('BYN')
        account.add(Money.byn(8), self.bank)
        assert account.value == Money.byn(8)

    def test_add_other_currency(self) -> None:
        account = Account('BYN')
        account.add(Money.dollar(4), self.bank)
        assert account.value == Money.byn(10)
