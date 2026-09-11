import os
import tempfile
from unittest.mock import MagicMock

import pytest

from database.views import AccountView, OfflineView, ResourceView, TransactionView


@pytest.fixture
def tmp_data_dir():
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def mock_rest_client():
    client = MagicMock()
    client.list_resources.return_value = [{"id": 1, "name": "USD", "ticker": "USD"}]
    client.create_resource.return_value = {"id": 2, "name": "EUR", "ticker": "EUR"}
    client.list_accounts.return_value = [
        {"id": 1, "name": "Cash", "resource_definition": 1, "current_balance_qty": 100}
    ]
    client.create_account.return_value = {"id": 2, "name": "Bank", "resource_definition": 1, "current_balance_qty": 500}
    client.update_account.return_value = {"id": 1, "name": "Cash Updated"}
    client.list_transactions.return_value = [
        {"id": 1, "date": "2024-01-01T00:00:00", "entries": [], "is_planned": False}
    ]
    client.create_transaction.return_value = {
        "id": 2,
        "date": "2024-01-02T00:00:00",
        "entries": [],
        "is_planned": False,
    }
    client.update_transaction.return_value = {
        "id": 1,
        "date": "2024-01-01T00:00:00",
        "entries": [],
        "is_planned": False,
    }
    client.me.return_value = {"username": "test", "email": "test@test.com"}
    return client


class TestOfflineViewInit:
    def test_creates_with_methods(self, tmp_data_dir, mock_rest_client):
        view = OfflineView(
            entity_name="resource",
            rest_client=mock_rest_client,
            cache_path=os.path.join(tmp_data_dir, "cache.json"),
            pending_path=os.path.join(tmp_data_dir, "pending.json"),
            methods={"list": mock_rest_client.list_resources},
        )
        assert view.is_online is True

    def test_is_online_default(self, tmp_data_dir, mock_rest_client):
        view = OfflineView(
            entity_name="resource",
            rest_client=mock_rest_client,
            cache_path=os.path.join(tmp_data_dir, "cache.json"),
            pending_path=os.path.join(tmp_data_dir, "pending.json"),
        )
        assert view.is_online is True


class TestResourceView:
    def test_load_online(self, tmp_data_dir, mock_rest_client):
        view = ResourceView(mock_rest_client, tmp_data_dir)
        result = view.get_all()
        assert result == [{"id": 1, "name": "USD", "ticker": "USD"}]
        mock_rest_client.list_resources.assert_called_once()

    def test_load_offline_returns_cache(self, tmp_data_dir, mock_rest_client):
        mock_rest_client.list_resources.side_effect = Exception("offline")
        view = ResourceView(mock_rest_client, tmp_data_dir)
        result = view.get_all()
        assert result == []
        assert view.is_online is False

    def test_add_online(self, tmp_data_dir, mock_rest_client):
        view = ResourceView(mock_rest_client, tmp_data_dir)
        pk = view.add({"name": "EUR", "ticker": "EUR"})
        assert pk == 2
        mock_rest_client.create_resource.assert_called_once_with({"name": "EUR", "ticker": "EUR"})

    def test_add_offline_queues_pending(self, tmp_data_dir, mock_rest_client):
        mock_rest_client.create_resource.side_effect = Exception("offline")
        view = ResourceView(mock_rest_client, tmp_data_dir)
        pk = view.add({"name": "EUR", "ticker": "EUR"})
        assert pk is not None
        assert pk < 0
        pending = view._pending.get_all()
        assert len(pending) == 1
        assert pending[0]["operation"] == "add"
        assert pending[0]["entity"] == "resource"

    def test_get_by_pk(self, tmp_data_dir, mock_rest_client):
        view = ResourceView(mock_rest_client, tmp_data_dir)
        view.get_all()
        item = view.get(1)
        assert item is not None
        assert item["name"] == "USD"

    def test_get_nonexistent_pk(self, tmp_data_dir, mock_rest_client):
        view = ResourceView(mock_rest_client, tmp_data_dir)
        view.get_all()
        item = view.get(999)
        assert item is None


class TestAccountView:
    def test_load_online(self, tmp_data_dir, mock_rest_client):
        view = AccountView(mock_rest_client, tmp_data_dir)
        result = view.get_all()
        assert len(result) == 1
        assert result[0]["name"] == "Cash"

    def test_load_offline_returns_cache(self, tmp_data_dir, mock_rest_client):
        mock_rest_client.list_accounts.side_effect = Exception("offline")
        view = AccountView(mock_rest_client, tmp_data_dir)
        result = view.get_all()
        assert result == []
        assert view.is_online is False

    def test_add_online(self, tmp_data_dir, mock_rest_client):
        view = AccountView(mock_rest_client, tmp_data_dir)
        pk = view.add({"name": "Bank", "resource_definition": 1, "current_balance_qty": 500})
        assert pk == 2

    def test_add_offline_queues_pending(self, tmp_data_dir, mock_rest_client):
        mock_rest_client.create_account.side_effect = Exception("offline")
        view = AccountView(mock_rest_client, tmp_data_dir)
        pk = view.add({"name": "Bank", "resource_definition": 1})
        assert pk is not None
        assert pk < 0
        pending = view._pending.get_all()
        assert len(pending) == 1
        assert pending[0]["operation"] == "add"
        assert pending[0]["entity"] == "account"

    def test_update_online(self, tmp_data_dir, mock_rest_client):
        view = AccountView(mock_rest_client, tmp_data_dir)
        view.get_all()
        view.update(1, {"name": "Cash Updated"})
        mock_rest_client.update_account.assert_called_once()

    def test_update_offline_queues_pending(self, tmp_data_dir, mock_rest_client):
        mock_rest_client.update_account.side_effect = Exception("offline")
        view = AccountView(mock_rest_client, tmp_data_dir)
        view.get_all()
        view.update(1, {"name": "Cash Updated"})
        pending = view._pending.get_all()
        assert len(pending) == 1
        assert pending[0]["operation"] == "update"

    def test_delete_online(self, tmp_data_dir, mock_rest_client):
        view = AccountView(mock_rest_client, tmp_data_dir)
        view.get_all()
        view.delete(1)
        mock_rest_client.delete_account.assert_called_once_with(1)

    def test_delete_offline_queues_pending(self, tmp_data_dir, mock_rest_client):
        mock_rest_client.delete_account.side_effect = Exception("offline")
        view = AccountView(mock_rest_client, tmp_data_dir)
        view.get_all()
        view.delete(1)
        pending = view._pending.get_all()
        assert len(pending) == 1
        assert pending[0]["operation"] == "delete"


class TestTransactionView:
    def test_load_online(self, tmp_data_dir, mock_rest_client):
        view = TransactionView(mock_rest_client, tmp_data_dir)
        result = view.get_all()
        assert len(result) == 1

    def test_get_planned(self, tmp_data_dir, mock_rest_client):
        mock_rest_client.list_transactions.return_value = [
            {"id": 1, "date": "2024-01-01T00:00:00", "entries": [], "is_planned": False},
            {"id": 2, "date": "2024-02-01T00:00:00", "entries": [], "is_planned": True},
        ]
        view = TransactionView(mock_rest_client, tmp_data_dir)
        view.get_all()
        planned = view.get_planned()
        assert len(planned) == 1
        assert planned[0]["id"] == 2

    def test_add_offline_queues_pending(self, tmp_data_dir, mock_rest_client):
        mock_rest_client.create_transaction.side_effect = Exception("offline")
        view = TransactionView(mock_rest_client, tmp_data_dir)
        pk = view.add({"date": "2024-01-01T00:00:00", "entries": []})
        assert pk is not None
        assert pk < 0
        pending = view._pending.get_all()
        assert len(pending) == 1
        assert pending[0]["entity"] == "transaction"


class TestSyncPending:
    def test_sync_pending_replays_operations(self, tmp_data_dir, mock_rest_client):
        mock_rest_client.create_resource.side_effect = [Exception("offline"), {"id": 10, "name": "Synced"}]
        view = ResourceView(mock_rest_client, tmp_data_dir)
        pk = view.add({"name": "Synced"})
        assert len(view._pending.get_all()) == 1

        mock_rest_client.create_resource.side_effect = None
        mock_rest_client.create_resource.return_value = {"id": 10, "name": "Synced"}
        remap = view.sync_pending()
        assert len(remap) == 1
        assert remap[pk] == 10
        assert len(view._pending.get_all()) == 0

    def test_sync_pending_keeps_failed(self, tmp_data_dir, mock_rest_client):
        mock_rest_client.create_resource.side_effect = Exception("offline")
        view = ResourceView(mock_rest_client, tmp_data_dir)
        view.add({"name": "Failed"})
        assert len(view._pending.get_all()) == 1

        mock_rest_client.create_resource.side_effect = Exception("still offline")
        view.sync_pending()
        assert len(view._pending.get_all()) == 1
