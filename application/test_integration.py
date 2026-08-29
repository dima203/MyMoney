import datetime
from unittest.mock import MagicMock

from core import Account, Resource, Transaction
from core.journal_entry import JournalEntry
from database import JSONBase, PendingStore
from dataview import AccountBaseView, ResourceBaseView, TransactionBaseView

FIXED_DATE = datetime.datetime(2026, 1, 15, 12, 0, tzinfo=datetime.UTC)


class TestAccountTransactionFlow:
    def setup_method(self):
        import tempfile

        self.tmp_dir = tempfile.mkdtemp()
        self.resource_path = f"{self.tmp_dir}/resources.json"
        self.account_path = f"{self.tmp_dir}/accounts.json"
        self.transaction_path = f"{self.tmp_dir}/transactions.json"
        self.pending_path = f"{self.tmp_dir}/pending.json"

        self.resource_db = JSONBase(self.resource_path)
        self.account_db = JSONBase(self.account_path)
        self.transaction_db = JSONBase(self.transaction_path)
        self.pending_store = PendingStore(self.pending_path)

        self.resource_view = ResourceBaseView(self.resource_db, reserve_database=self.resource_db)
        self.account_view = AccountBaseView(self.account_db, self.resource_view, reserve_database=self.account_db)
        self.transaction_view = TransactionBaseView(
            self.transaction_db, self.account_view, reserve_database=self.transaction_db
        )
        self.pending_store = PendingStore(self.pending_path)
        self.resource_view.set_pending_store(self.pending_store)
        self.account_view.set_pending_store(self.pending_store)
        self.transaction_view.set_pending_store(self.pending_store)

    def test_full_lifecycle(self):
        usd = Resource(1, "USD")
        self.resource_view.add(usd)
        assert self.resource_view.get(1) is not None

        account = Account(1, "Main Card", usd, 1000, group="personal", account_type="main")
        self.account_view.add(account)
        assert self.account_view.get(1) is not None
        assert self.account_view.get(1).get_balance().value == 1000

        entry = JournalEntry(account_id=1, quantity=-50, amount=-50)
        tx = Transaction(
            1,
            FIXED_DATE,
            [entry],
            category="food",
            description="Lunch",
        )
        self.transaction_view.add(tx)
        assert self.transaction_view.get(1) is not None

        all_transactions = self.transaction_view.get_all()
        assert len(all_transactions) == 1

    def test_planned_transaction_lifecycle(self):
        usd = Resource(1, "USD")
        self.resource_view.add(usd)

        account = Account(1, "Card", usd, 500)
        self.account_view.add(account)

        entry = JournalEntry(account_id=1, quantity=-100, amount=-100)
        planned_tx = Transaction(
            1,
            FIXED_DATE,
            [entry],
            category="rent",
            description="Monthly rent",
            is_planned=True,
            recurrence_rule="monthly",
        )
        self.transaction_view.add(planned_tx)

        planned = self.transaction_view.get_planned()
        assert len(planned) == 1
        assert 1 in planned

    def test_filter_by_category(self):
        usd = Resource(1, "USD")
        self.resource_view.add(usd)
        account = Account(1, "Card", usd, 500)
        self.account_view.add(account)

        tx1 = Transaction(
            1,
            FIXED_DATE,
            [JournalEntry(account_id=1, quantity=-10, amount=-10)],
            category="food",
        )
        tx2 = Transaction(
            2,
            FIXED_DATE,
            [JournalEntry(account_id=1, quantity=-20, amount=-20)],
            category="transport",
        )
        tx3 = Transaction(
            3,
            FIXED_DATE,
            [JournalEntry(account_id=1, quantity=-30, amount=-30)],
            category="food",
        )
        self.transaction_view.add(tx1)
        self.transaction_view.add(tx2)
        self.transaction_view.add(tx3)

        food = self.transaction_view.get_by_category("food")
        assert len(food) == 2

        transport = self.transaction_view.get_by_category("transport")
        assert len(transport) == 1

    def test_delete_account(self):
        usd = Resource(1, "USD")
        self.resource_view.add(usd)
        account = Account(1, "Temp", usd, 0)
        self.account_view.add(account)
        assert self.account_view.get(1) is not None

        self.account_view.delete(1)
        assert self.account_view.get(1) is None

    def test_delete_transaction(self):
        usd = Resource(1, "USD")
        self.resource_view.add(usd)
        account = Account(1, "Card", usd, 100)
        self.account_view.add(account)

        tx = Transaction(
            1,
            FIXED_DATE,
            [JournalEntry(account_id=1, quantity=-10, amount=-10)],
        )
        self.transaction_view.add(tx)
        assert self.transaction_view.get(1) is not None

        self.transaction_view.delete(1)
        assert self.transaction_view.get(1) is None


class TestOfflineSync:
    def setup_method(self):
        import tempfile

        self.tmp_dir = tempfile.mkdtemp()
        self.pending_path = f"{self.tmp_dir}/pending.json"
        self.pending_store = PendingStore(self.pending_path)

    def test_offline_add_pending(self):
        self.pending_store.add("add", "account", -1, {"name": "Offline Account"})
        assert len(self.pending_store.get_all()) == 1

    def test_sync_remaps_pks(self):
        self.pending_store.add("add", "account", -1, {"name": "A"})
        self.pending_store.add("add", "account", -2, {"name": "B"})

        mock_client = MagicMock()
        mock_client.create_account.side_effect = [
            {"id": 10, "name": "A"},
            {"id": 11, "name": "B"},
        ]
        remap = self.pending_store.sync(mock_client)
        assert remap == {-1: 10, -2: 11}

    def test_failed_sync_keeps_operations(self):
        self.pending_store.add("add", "account", -1, {"name": "Fail"})
        mock_client = MagicMock()
        mock_client.create_account.side_effect = Exception("offline")

        self.pending_store.sync(mock_client)
        assert len(self.pending_store.get_all()) == 1


class TestResourceViewRemapPk:
    def setup_method(self):
        import tempfile

        self.tmp_dir = tempfile.mkdtemp()
        self.db = JSONBase(f"{self.tmp_dir}/resources.json")
        self.view = ResourceBaseView(self.db, reserve_database=self.db)

    def test_remap_pk(self):
        r = Resource(1, "Temp")
        self.view.add(r)
        assert self.view.get(1) is not None

        self.view._remap_pk({1: 100})
        assert self.view.get(1) is None
        assert self.view.get(100) is not None
        assert self.view.get(100).pk == 100


class TestAccountViewRemapPk:
    def setup_method(self):
        import tempfile

        self.tmp_dir = tempfile.mkdtemp()
        self.resource_db = JSONBase(f"{self.tmp_dir}/resources.json")
        self.account_db = JSONBase(f"{self.tmp_dir}/accounts.json")
        self.resource_view = ResourceBaseView(self.resource_db, reserve_database=self.resource_db)
        self.account_view = AccountBaseView(self.account_db, self.resource_view, reserve_database=self.account_db)

    def test_remap_pk(self):
        r = Resource(1, "USD")
        self.resource_view.add(r)
        acc = Account(1, "Temp", r, 0)
        self.account_view.add(acc)
        assert self.account_view.get(1) is not None

        self.account_view._remap_pk({1: 50})
        assert self.account_view.get(1) is None
        assert self.account_view.get(50) is not None


class TestTransactionViewRemapPk:
    def setup_method(self):
        import tempfile

        self.tmp_dir = tempfile.mkdtemp()
        self.resource_db = JSONBase(f"{self.tmp_dir}/resources.json")
        self.account_db = JSONBase(f"{self.tmp_dir}/accounts.json")
        self.transaction_db = JSONBase(f"{self.tmp_dir}/transactions.json")
        self.resource_view = ResourceBaseView(self.resource_db, reserve_database=self.resource_db)
        self.account_view = AccountBaseView(self.account_db, self.resource_view, reserve_database=self.account_db)
        self.tx_view = TransactionBaseView(self.transaction_db, self.account_view, reserve_database=self.transaction_db)

    def test_remap_pk(self):
        r = Resource(1, "USD")
        self.resource_view.add(r)
        acc = Account(1, "Card", r, 100)
        self.account_view.add(acc)

        tx = Transaction(
            -1,
            FIXED_DATE,
            [JournalEntry(account_id=1, quantity=-10, amount=-10)],
        )
        self.tx_view.add(tx)
        assert self.tx_view.get(-1) is not None

        self.tx_view._remap_pk({-1: 75})
        assert self.tx_view.get(-1) is None
        assert self.tx_view.get(75) is not None
