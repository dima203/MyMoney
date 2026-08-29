from core.journal_entry import JournalEntry


class TestJournalEntryCreation:
    def test_create_basic(self):
        entry = JournalEntry(account_id=1, quantity=100, amount=100)
        assert entry.account_id == 1
        assert entry.quantity == 100
        assert entry.amount == 100
        assert entry.unit_price == 1.0

    def test_create_with_unit_price(self):
        entry = JournalEntry(account_id=5, quantity=10, amount=50, unit_price=5.0)
        assert entry.account_id == 5
        assert entry.quantity == 10
        assert entry.amount == 50
        assert entry.unit_price == 5.0

    def test_create_with_string_account_id(self):
        entry = JournalEntry(account_id="acc_abc", quantity=1, amount=100)
        assert entry.account_id == "acc_abc"

    def test_create_with_zero_quantity(self):
        entry = JournalEntry(account_id=1, quantity=0, amount=0)
        assert entry.quantity == 0
        assert entry.amount == 0

    def test_create_with_negative_quantity(self):
        entry = JournalEntry(account_id=1, quantity=-50, amount=-50)
        assert entry.quantity == -50
        assert entry.amount == -50

    def test_create_with_float_values(self):
        entry = JournalEntry(account_id=1, quantity=0.5, amount=150.75, unit_price=301.5)
        assert entry.quantity == 0.5
        assert entry.amount == 150.75
        assert entry.unit_price == 301.5


class TestJournalEntryEquality:
    def test_equal_entries(self):
        e1 = JournalEntry(account_id=1, quantity=10, amount=10)
        e2 = JournalEntry(account_id=1, quantity=10, amount=10)
        assert e1 == e2

    def test_not_equal_different_account(self):
        e1 = JournalEntry(account_id=1, quantity=10, amount=10)
        e2 = JournalEntry(account_id=2, quantity=10, amount=10)
        assert e1 != e2

    def test_not_equal_different_quantity(self):
        e1 = JournalEntry(account_id=1, quantity=10, amount=10)
        e2 = JournalEntry(account_id=1, quantity=20, amount=10)
        assert e1 != e2

    def test_not_equal_different_amount(self):
        e1 = JournalEntry(account_id=1, quantity=10, amount=10)
        e2 = JournalEntry(account_id=1, quantity=10, amount=20)
        assert e1 != e2


class TestJournalEntryToJson:
    def test_to_json_basic(self):
        entry = JournalEntry(account_id=1, quantity=100, amount=100)
        json_data = entry.to_json()
        assert json_data == {"account": 1, "quantity": 100, "amount": 100, "unit_price": 1.0}

    def test_to_json_with_unit_price(self):
        entry = JournalEntry(account_id=2, quantity=50, amount=75, unit_price=1.5)
        json_data = entry.to_json()
        assert json_data == {"account": 2, "quantity": 50, "amount": 75, "unit_price": 1.5}

    def test_to_json_string_account(self):
        entry = JournalEntry(account_id="acc_1", quantity=1, amount=500)
        json_data = entry.to_json()
        assert json_data["account"] == "acc_1"

    def test_to_json_negative_values(self):
        entry = JournalEntry(account_id=1, quantity=-10, amount=-10)
        json_data = entry.to_json()
        assert json_data["quantity"] == -10
        assert json_data["amount"] == -10
