import datetime
from unittest.mock import MagicMock

from core import Account, Transaction, Resource
from core.journal_entry import JournalEntry


class TestTransaction:
    def setup_method(self) -> None:
        self.byn = Resource(0, "BYN")
        self.account = Account(0, "Test", self.byn, 10)
        self.date = datetime.datetime(2025, 6, 15, 12, 0)

    def test_transaction_create(self) -> None:
        t = Transaction(0, self.date)
        assert t.pk == 0
        assert t.date == self.date
        assert t.entries == []

    def test_transaction_create_with_entries(self) -> None:
        entry = JournalEntry(account_id=0, quantity=10, amount=10)
        t = Transaction(1, self.date, [entry])
        assert len(t.entries) == 1
        assert t.entries[0].account_id == 0

    def test_transaction_create_with_category(self) -> None:
        t = Transaction(2, self.date, category="food")
        assert t.category == "food"

    def test_transaction_create_with_description(self) -> None:
        t = Transaction(3, self.date, description="Lunch")
        assert t.description == "Lunch"

    def test_transaction_to_json(self) -> None:
        entry = JournalEntry(account_id=0, quantity=25, amount=25)
        t = Transaction(1, self.date, [entry], category="food", description="Lunch")
        json_data = t.to_json()
        assert json_data["id"] == 1
        assert json_data["date"] == self.date.isoformat()
        assert len(json_data["entries"]) == 1
        assert json_data["entries"][0]["account"] == 0
        assert json_data["entries"][0]["quantity"] == 25
        assert json_data["category"] == "food"
        assert json_data["description"] == "Lunch"
        assert json_data["is_planned"] is False

    def test_transaction_to_json_planned(self) -> None:
        t = Transaction(4, self.date, is_planned=True, recurrence_rule="monthly")
        json_data = t.to_json()
        assert json_data["is_planned"] is True
        assert json_data["recurrence_rule"] == "monthly"


class TestTransactionSubscribe:
    def setup_method(self):
        self.date = datetime.datetime.now()

    def test_subscribe_receives_notification(self):
        t = Transaction(0, self.date)
        callback = MagicMock()
        t.subscribe(callback)
        t.category = "new_category"
        callback.assert_called()

    def test_unsubscribe(self):
        t = Transaction(0, self.date)
        callback = MagicMock()
        t.subscribe(callback)
        t.unsubscribe(callback)
        t.category = "new_category"
        callback.assert_not_called()


class TestJournalEntry:
    def test_create(self):
        entry = JournalEntry(account_id=1, quantity=100, amount=100)
        assert entry.account_id == 1
        assert entry.quantity == 100
        assert entry.amount == 100
        assert entry.unit_price == 1.0

    def test_to_json(self):
        entry = JournalEntry(account_id=2, quantity=50, amount=75, unit_price=1.5)
        json_data = entry.to_json()
        assert json_data == {"account": 2, "quantity": 50, "amount": 75, "unit_price": 1.5}
