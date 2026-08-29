import json
from unittest.mock import MagicMock

from database.pending_store import PendingStore


class TestPendingStoreInit:
    def test_init_empty(self, tmp_path):
        store = PendingStore(str(tmp_path / "pending.json"))
        assert store.get_all() == []

    def test_init_loads_existing(self, tmp_path):
        path = tmp_path / "pending.json"
        data = [{"operation": "add", "entity": "account", "temp_pk": -1, "data": {"name": "test"}}]
        path.write_text(json.dumps(data), encoding="utf-8")
        store = PendingStore(str(path))
        assert len(store.get_all()) == 1

    def test_init_corrupted_json(self, tmp_path):
        path = tmp_path / "pending.json"
        path.write_text("not json", encoding="utf-8")
        store = PendingStore(str(path))
        assert store.get_all() == []


class TestPendingStoreAdd:
    def test_add_operation(self, tmp_path):
        store = PendingStore(str(tmp_path / "pending.json"))
        store.add("add", "account", -1, {"name": "Savings"})
        all_ops = store.get_all()
        assert len(all_ops) == 1
        assert all_ops[0]["operation"] == "add"
        assert all_ops[0]["entity"] == "account"
        assert all_ops[0]["temp_pk"] == -1
        assert all_ops[0]["data"]["name"] == "Savings"

    def test_add_multiple_operations(self, tmp_path):
        store = PendingStore(str(tmp_path / "pending.json"))
        store.add("add", "account", -1, {"name": "A"})
        store.add("add", "transaction", -2, {"date": "2026-01-01"})
        assert len(store.get_all()) == 2

    def test_add_persists_to_file(self, tmp_path):
        path = tmp_path / "pending.json"
        store = PendingStore(str(path))
        store.add("add", "resource", -1, {"name": "BTC"})
        loaded = PendingStore(str(path))
        assert len(loaded.get_all()) == 1

    def test_add_various_entities(self, tmp_path):
        store = PendingStore(str(tmp_path / "pending.json"))
        store.add("add", "resource", -1, {"name": "USD"})
        store.add("add", "account", -2, {"name": "Card"})
        store.add("add", "transaction", -3, {"date": "2026-01-01"})
        store.add("delete", "account", -4, {"id": 5})
        store.add("update", "resource", -5, {"id": 1, "name": "Updated"})
        assert len(store.get_all()) == 5


class TestPendingStoreClear:
    def test_clear(self, tmp_path):
        store = PendingStore(str(tmp_path / "pending.json"))
        store.add("add", "account", -1, {"name": "A"})
        store.add("add", "account", -2, {"name": "B"})
        store.clear()
        assert store.get_all() == []

    def test_clear_persists(self, tmp_path):
        path = tmp_path / "pending.json"
        store = PendingStore(str(path))
        store.add("add", "account", -1, {"name": "A"})
        store.clear()
        loaded = PendingStore(str(path))
        assert loaded.get_all() == []


class TestPendingStoreRemoveByTempPk:
    def test_remove_existing(self, tmp_path):
        store = PendingStore(str(tmp_path / "pending.json"))
        store.add("add", "account", -1, {"name": "A"})
        store.add("add", "account", -2, {"name": "B"})
        store.remove_by_temp_pk(-1)
        remaining = store.get_all()
        assert len(remaining) == 1
        assert remaining[0]["temp_pk"] == -2

    def test_remove_nonexistent(self, tmp_path):
        store = PendingStore(str(tmp_path / "pending.json"))
        store.add("add", "account", -1, {"name": "A"})
        store.remove_by_temp_pk(-999)
        assert len(store.get_all()) == 1


class TestPendingStoreSync:
    def test_sync_add_resource(self, tmp_path):
        store = PendingStore(str(tmp_path / "pending.json"))
        store.add("add", "resource", -1, {"name": "BTC"})
        mock_client = MagicMock()
        mock_client.create_resource.return_value = {"id": 10, "name": "BTC"}
        remap = store.sync(mock_client)
        assert remap == {-1: 10}
        assert store.get_all() == []
        mock_client.create_resource.assert_called_once_with({"name": "BTC"})

    def test_sync_add_account(self, tmp_path):
        store = PendingStore(str(tmp_path / "pending.json"))
        store.add("add", "account", -2, {"name": "Savings"})
        mock_client = MagicMock()
        mock_client.create_account.return_value = {"id": 20}
        remap = store.sync(mock_client)
        assert remap == {-2: 20}

    def test_sync_add_transaction(self, tmp_path):
        store = PendingStore(str(tmp_path / "pending.json"))
        store.add("add", "transaction", -3, {"date": "2026-01-01"})
        mock_client = MagicMock()
        mock_client.create_transaction.return_value = {"id": 30}
        remap = store.sync(mock_client)
        assert remap == {-3: 30}

    def test_sync_delete_account(self, tmp_path):
        store = PendingStore(str(tmp_path / "pending.json"))
        store.add("delete", "account", -1, {"id": 5})
        mock_client = MagicMock()
        remap = store.sync(mock_client)
        assert remap == {}
        mock_client.delete_account.assert_called_once_with(5)
        assert store.get_all() == []

    def test_sync_update_account(self, tmp_path):
        store = PendingStore(str(tmp_path / "pending.json"))
        store.add("update", "account", -1, {"id": 5, "name": "Updated"})
        mock_client = MagicMock()
        remap = store.sync(mock_client)
        assert remap == {}
        mock_client.update_account.assert_called_once_with(5, {"name": "Updated"})

    def test_sync_failed_operation_remains(self, tmp_path):
        store = PendingStore(str(tmp_path / "pending.json"))
        store.add("add", "account", -1, {"name": "Failing"})
        mock_client = MagicMock()
        mock_client.create_account.side_effect = Exception("server error")
        remap = store.sync(mock_client)
        assert remap == {}
        assert len(store.get_all()) == 1

    def test_sync_unknown_entity_remains(self, tmp_path):
        store = PendingStore(str(tmp_path / "pending.json"))
        store.add("add", "unknown_entity", -1, {"data": "x"})
        mock_client = MagicMock()
        remap = store.sync(mock_client)
        assert remap == {}
        assert len(store.get_all()) == 1

    def test_sync_empty_store(self, tmp_path):
        store = PendingStore(str(tmp_path / "pending.json"))
        mock_client = MagicMock()
        remap = store.sync(mock_client)
        assert remap == {}

    def test_sync_multiple_operations(self, tmp_path):
        store = PendingStore(str(tmp_path / "pending.json"))
        store.add("add", "account", -1, {"name": "A"})
        store.add("add", "account", -2, {"name": "B"})
        store.add("delete", "resource", -3, {"id": 1})
        mock_client = MagicMock()
        mock_client.create_account.side_effect = [
            {"id": 10, "name": "A"},
            {"id": 11, "name": "B"},
        ]
        remap = store.sync(mock_client)
        assert remap == {-1: 10, -2: 11}
        mock_client.delete_resource.assert_called_once_with(1)
        assert store.get_all() == []
