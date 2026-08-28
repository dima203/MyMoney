from unittest.mock import MagicMock

from database import ServerBase


class TestServerBaseInit:
    def test_no_rest_client(self):
        db = ServerBase("/local/path")
        assert db._rest_client is None

    def test_with_rest_client(self):
        mock_client = MagicMock()
        db = ServerBase("http://example.com/api/", rest_client=mock_client)
        assert db._rest_client is mock_client

    def test_is_online_default(self):
        db = ServerBase("/local/path")
        assert db.is_online is True


class TestServerBaseOperations:
    def setup_method(self):
        self.db = ServerBase("/local/path")

    def test_load_no_client(self):
        assert self.db.load() == []

    def test_add_no_client(self):
        assert self.db.add({"name": "test"}) is None

    def test_update_no_client(self):
        self.db.update(1, {"name": "test"})

    def test_delete_no_client(self):
        self.db.delete(1)

    def test_load_with_client(self):
        mock_client = MagicMock()
        mock_client.list_resources.return_value = [{"id": 1, "name": "test"}]
        db = ServerBase("http://example.com/api/resources/", rest_client=mock_client)
        result = db.load()
        assert result == [{"id": 1, "name": "test"}]
        mock_client.list_resources.assert_called_once()

    def test_add_with_client(self):
        mock_client = MagicMock()
        mock_client.create_resource.return_value = {"id": 42, "name": "test"}
        db = ServerBase("http://example.com/api/resources/", rest_client=mock_client)
        pk = db.add({"name": "test"})
        assert pk == 42
        mock_client.create_resource.assert_called_once_with({"name": "test"})

    def test_load_accounts(self):
        mock_client = MagicMock()
        mock_client.list_accounts.return_value = [{"id": 1, "name": "acc"}]
        db = ServerBase("http://example.com/api/accounts/", rest_client=mock_client)
        result = db.load()
        assert result == [{"id": 1, "name": "acc"}]
        mock_client.list_accounts.assert_called_once()

    def test_add_accounts(self):
        mock_client = MagicMock()
        mock_client.create_account.return_value = {"id": 10}
        db = ServerBase("http://example.com/api/accounts/", rest_client=mock_client)
        pk = db.add({"name": "new"})
        assert pk == 10
        mock_client.create_account.assert_called_once_with({"name": "new"})

    def test_update_accounts(self):
        mock_client = MagicMock()
        db = ServerBase("http://example.com/api/accounts/", rest_client=mock_client)
        db.update(1, {"name": "updated"})
        mock_client.update_account.assert_called_once_with(1, {"name": "updated"})

    def test_delete_accounts(self):
        mock_client = MagicMock()
        db = ServerBase("http://example.com/api/accounts/", rest_client=mock_client)
        db.delete(1)
        mock_client.delete_account.assert_called_once_with(1)

    def test_offline_returns_empty(self):
        mock_client = MagicMock()
        mock_client.list_resources.side_effect = Exception("offline")
        db = ServerBase("http://example.com/api/resources/", rest_client=mock_client)
        result = db.load()
        assert result == []
        assert db.is_online is False

    def test_offline_add_returns_temp_pk(self):
        mock_client = MagicMock()
        mock_client.create_resource.side_effect = Exception("offline")
        db = ServerBase("http://example.com/api/resources/", rest_client=mock_client)
        pk = db.add({"name": "test"})
        assert pk == -2
        assert db.is_online is False
        pk2 = db.add({"name": "test2"})
        assert pk2 == -3
