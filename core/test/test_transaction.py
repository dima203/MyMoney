import datetime
from unittest.mock import MagicMock

import pytest

from core import Bank, Account, Transaction, Money, Resource
from core.transaction import Income, Expense, Transfer


class TestTransaction:
    def setup_method(self) -> None:
        self.byn = Resource(0, "BYN")
        self.usd = Resource(1, "USD")
        self.bank = Bank()
        self.bank.add_exchange(self.usd, self.byn, 2.5)
        self.account = Account(0, "Test", self.byn, 10)

    def test_transaction_create(self) -> None:
        t = Transaction(0, self.account, Money(10, self.byn), datetime.datetime.now())
        assert t.pk == 0
        assert t.storage == self.account
        assert t.value == Money(10, self.byn)

    def test_transaction_accept(self) -> None:
        t = Transaction(1, self.account, Money(10, self.byn), datetime.datetime.now())
        t.execute()
        assert self.account.get_balance() == Money(20, self.byn)

    def test_transaction_different_currency_accept(self) -> None:
        t = Transaction(0, self.account, self.bank.exchange(Money(10, self.usd), self.byn), datetime.datetime.now())
        t.execute()
        assert self.account.get_balance() == Money(35, self.byn)

    def test_transaction_cancel(self) -> None:
        t = Transaction(1, self.account, -Money(10, self.byn), datetime.datetime.now())
        t.execute()
        assert self.account.get_balance() == Money(0, self.byn)
        del t
        assert self.account.get_balance() == Money(10, self.byn)

    def test_transaction_value_is_copy(self):
        t = Transaction(0, self.account, Money(50, self.byn), datetime.datetime.now())
        v = t.value
        v.value = 999
        assert t.value == Money(50, self.byn)

    def test_transaction_to_json(self):
        ts = datetime.datetime(2025, 6, 15, 12, 0)
        t = Transaction(1, self.account, Money(25, self.byn), ts)
        json_data = t.to_json()
        assert json_data["pk"] == 1
        assert json_data["storage_id"] == 0
        assert json_data["resource_count"] == 25
        assert json_data["resource_type"] == 0
        assert json_data["time_stamp"] == ts.isoformat()
        assert "last_update" in json_data


class TestTransactionSubscribe:
    def setup_method(self):
        self.byn = Resource(0, "BYN")
        self.account = Account(0, "Test", self.byn, 100)

    def test_subscribe_receives_notification(self):
        t = Transaction(0, self.account, Money(10, self.byn), datetime.datetime.now())
        callback = MagicMock()
        t.subscribe(callback)
        t.value = Money(20, self.byn)
        callback.assert_called()

    def test_unsubscribe(self):
        t = Transaction(0, self.account, Money(10, self.byn), datetime.datetime.now())
        callback = MagicMock()
        t.subscribe(callback)
        t.unsubscribe(callback)
        t.value = Money(20, self.byn)
        callback.assert_not_called()


class TestTransactionSetattr:
    def setup_method(self):
        self.byn = Resource(0, "BYN")
        self.account = Account(0, "Test", self.byn, 100)

    def test_changing_value_auto_reverses(self):
        t = Transaction(0, self.account, Money(50, self.byn), datetime.datetime.now())
        t.execute()
        assert self.account.get_balance() == Money(150, self.byn)
        t.value = Money(30, self.byn)
        assert self.account.get_balance() == Money(130, self.byn)

    def test_changing_storage(self):
        account2 = Account(1, "Other", self.byn, 0)
        t = Transaction(0, self.account, Money(50, self.byn), datetime.datetime.now())
        t.execute()
        assert self.account.get_balance() == Money(150, self.byn)
        t.storage = account2
        assert self.account.get_balance() == Money(100, self.byn)
        assert account2.get_balance() == Money(50, self.byn)


class TestIncome:
    def setup_method(self):
        self.byn = Resource(0, "BYN")
        self.usd = Resource(1, "USD")
        self.bank = Bank()
        self.bank.add_exchange(self.usd, self.byn, 2.5)
        self.account = Account(0, "Test", self.byn, 0)

    def test_income_same_currency(self):
        inc = Income(0, self.account, Money(100, self.byn), self.bank)
        inc.execute()
        assert self.account.get_balance() == Money(100, self.byn)

    def test_income_different_currency(self):
        inc = Income(0, self.account, Money(40, self.usd), self.bank)
        inc.execute()
        assert self.account.get_balance() == Money(100, self.byn)

    def test_income_none_account(self):
        inc = Income(0, None, Money(50, self.byn), self.bank)
        assert inc.value == Money(50, self.byn)


class TestExpense:
    def setup_method(self):
        self.byn = Resource(0, "BYN")
        self.usd = Resource(1, "USD")
        self.bank = Bank()
        self.bank.add_exchange(self.usd, self.byn, 2.5)
        self.account = Account(0, "Test", self.byn, 100)

    def test_expense_same_currency(self):
        exp = Expense(0, self.account, Money(30, self.byn), self.bank)
        exp.execute()
        assert self.account.get_balance() == Money(70, self.byn)

    def test_expense_different_currency(self):
        exp = Expense(0, self.account, Money(20, self.usd), self.bank)
        exp.execute()
        assert self.account.get_balance() == Money(50, self.byn)

    def test_expense_none_account(self):
        exp = Expense(0, None, Money(50, self.byn), self.bank)
        assert exp.value == Money(-50, self.byn)


class TestTransfer:
    def setup_method(self):
        self.byn = Resource(0, "BYN")
        self.usd = Resource(1, "USD")
        self.bank = Bank()
        self.bank.add_exchange(self.usd, self.byn, 2.5)
        self.from_account = Account(0, "From", self.byn, 100)
        self.to_account = Account(1, "To", self.byn, 0)

    def test_transfer_same_currency(self):
        tr = Transfer(0, self.to_account, self.from_account, Money(50, self.byn), self.bank)
        tr.execute()
        assert self.from_account.get_balance() == Money(50, self.byn)
        assert self.to_account.get_balance() == Money(50, self.byn)

    def test_transfer_different_currency(self):
        usd_from = Account(2, "USD From", self.usd, 200)
        tr = Transfer(0, self.to_account, usd_from, Money(40, self.usd), self.bank)
        tr.execute()
        assert usd_from.get_balance() == Money(160, self.usd)
        assert self.to_account.get_balance() == Money(100, self.byn)

    def test_transfer_to_none(self):
        tr = Transfer(0, None, self.from_account, Money(30, self.byn), self.bank)
        tr.execute()
        assert self.from_account.get_balance() == Money(70, self.byn)

    def test_transfer_cleans_up_on_delete(self):
        tr = Transfer(0, self.to_account, self.from_account, Money(50, self.byn), self.bank)
        tr.execute()
        assert self.from_account.get_balance() == Money(50, self.byn)
        del tr
        assert self.from_account.get_balance() == Money(100, self.byn)
