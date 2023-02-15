from core import Bank, Account, Transfer, Money, Income, Expense


class TestTransfer:
    def setup_method(self) -> None:
        self.bank = Bank()
        self.bank.add_exchange('USD', 'BYN', 2.5)

    def test_transfer_create(self) -> None:
        account = Account('BYN')
        target_account = Account('BYN')
        Transfer(account, target_account, Money.byn(10), self.bank)

    def test_transfer_accept(self) -> None:
        account = Account('BYN')
        income = Income(account, Money.byn(10), self.bank)
        target_account = Account('BYN')
        transaction = Transfer(account, target_account, Money.byn(10), self.bank)
        assert account.get_balance() == Money.byn(0)
        assert target_account.get_balance() == Money.byn(10)

    def test_transfer_different_currency_accept(self) -> None:
        account = Account('USD')
        income = Income(account, Money.dollar(10), self.bank)
        target_account = Account('BYN')
        transaction = Transfer(account, target_account, Money.dollar(4), self.bank)
        assert account.get_balance() == Money.dollar(6)
        assert target_account.get_balance() == Money.byn(10)

    def test_transfer_cancel(self) -> None:
        account = Account('BYN')
        income = Income(account, Money.byn(10), self.bank)
        target_account = Account('BYN')
        transaction = Transfer(account, target_account, Money.byn(10), self.bank)
        assert account.get_balance() == Money.byn(0)
        assert target_account.get_balance() == Money.byn(10)
        del transaction
        assert account.get_balance() == Money.byn(10)
        assert target_account.get_balance() == Money.byn(0)


class TestIncome:
    def setup_method(self) -> None:
        self.bank = Bank()
        self.bank.add_exchange('USD', 'BYN', 2.5)

    def test_income_create(self) -> None:
        account = Account('BYN')
        Income(account, Money.byn(10), self.bank)

    def test_income_accept(self) -> None:
        account = Account('BYN')
        transaction = Income(account, Money.byn(10), self.bank)
        assert account.get_balance() == Money.byn(10)

    def test_income_different_currency_accept(self) -> None:
        account = Account('BYN')
        transaction = Income(account, Money.dollar(4), self.bank)
        assert account.get_balance() == Money.byn(10)

    def test_income_cancel(self) -> None:
        account = Account('BYN')
        transaction = Income(account, Money.byn(10), self.bank)
        assert account.get_balance() == Money.byn(10)
        del transaction
        assert account.get_balance() == Money.byn(0)

    def test_income_different_currency_cancel(self) -> None:
        account = Account('BYN')
        transaction = Income(account, Money.dollar(4), self.bank)
        assert account.get_balance() == Money.byn(10)
        del transaction
        assert account.get_balance() == Money.byn(0)


class TestExpense:
    def setup_method(self) -> None:
        self.bank = Bank()
        self.bank.add_exchange('USD', 'BYN', 2.5)

    def test_expense_create(self) -> None:
        account = Account('BYN')
        Expense(account, Money.byn(10), Bank())

    def test_expense_accept(self) -> None:
        account = Account('BYN')
        income = Income(account, Money.byn(10), self.bank)
        transaction = Expense(account, Money.byn(10), self.bank)
        assert account.get_balance() == Money.byn(0)

    def test_expense_different_currency_accept(self) -> None:
        account = Account('BYN')
        income = Income(account, Money.byn(10), self.bank)
        transaction = Expense(account, Money.dollar(2), self.bank)
        assert account.get_balance() == Money.byn(5)

    def test_unavailable_expense(self) -> None:
        account = Account('BYN')
        transaction = Expense(account, Money.byn(10), self.bank)
        assert account.get_balance() == -Money.byn(10)

    def test_expense_cancel(self) -> None:
        account = Account('BYN')
        transaction = Expense(account, Money.byn(10), self.bank)
        assert account.get_balance() == Money.byn(-10)
        del transaction
        assert account.get_balance() == Money.byn(0)

    def test_expense_different_currency_cancel(self) -> None:
        account = Account('BYN')
        income = Income(account, Money.byn(10), self.bank)
        transaction = Expense(account, Money.dollar(2), self.bank)
        assert account.get_balance() == Money.byn(5)
        del transaction
        assert account.get_balance() == Money.byn(10)
