from unittest.mock import MagicMock, patch

import pytest

from database import ServerBase


class TestServerBaseInit:
    def test_non_http_path_no_session(self):
        db = ServerBase("/local/path", token="")
        assert db._ServerBase__session is None

    def test_http_path_creates_session(self):
        db = ServerBase("http://example.com/api/", token="test_token")
        assert db._ServerBase__session is not None

    def test_session_has_auth_header(self):
        db = ServerBase("http://example.com/api/", token="my_token")
        assert db._ServerBase__session.headers["Authorization"] == "Bearer my_token"


class TestServerBaseOperations:
    def setup_method(self):
        self.db = ServerBase("/local/path", token="")

    def test_load_no_session(self):
        assert self.db.load() == []

    def test_add_no_session(self):
        assert self.db.add({"pk": 1}) is None

    def test_update_no_session(self):
        self.db.update(1, {"pk": 1})

    def test_delete_no_session(self):
        self.db.delete(1)

    @patch("database.server_base.requests.Session")
    def test_load_with_session(self, mock_session_cls):
        mock_session = MagicMock()
        mock_session_cls.return_value = mock_session
        mock_session.request.return_value.json.return_value = {"results": [{"pk": 1, "name": "test"}]}

        db = ServerBase("http://example.com/api/", token="tok")
        result = db.load()

        assert result == [{"pk": 1, "name": "test"}]
        mock_session.request.assert_called_once_with("GET", "http://example.com/api/")

    @patch("database.server_base.requests.Session")
    def test_add_with_session(self, mock_session_cls):
        mock_session = MagicMock()
        mock_session_cls.return_value = mock_session
        mock_session.request.return_value.json.return_value = {"pk": 42}

        db = ServerBase("http://example.com/api/", token="tok")
        pk = db.add({"name": "test"})

        assert pk == 42
        mock_session.request.assert_called_once_with("POST", "http://example.com/api/", json={"name": "test"})

    @patch("database.server_base.requests.Session")
    def test_update_with_session(self, mock_session_cls):
        mock_session = MagicMock()
        mock_session_cls.return_value = mock_session
        mock_session.request.return_value.status_code = 200

        db = ServerBase("http://example.com/api/", token="tok")
        db.update(1, {"name": "updated"})

        mock_session.request.assert_called_once_with("PATCH", "http://example.com/api/1", json={"name": "updated"})

    @patch("database.server_base.requests.Session")
    def test_delete_with_session(self, mock_session_cls):
        mock_session = MagicMock()
        mock_session_cls.return_value = mock_session
        mock_session.request.return_value.status_code = 204

        db = ServerBase("http://example.com/api/", token="tok")
        db.delete(1)

        mock_session.request.assert_called_once_with("DELETE", "http://example.com/api/1")

    @patch("database.server_base.requests.post")
    @patch("database.server_base.requests.Session")
    def test_token_refresh_on_401(self, mock_session_cls, mock_requests_post):
        mock_session = MagicMock()
        mock_session_cls.return_value = mock_session

        unauthorized_response = MagicMock()
        unauthorized_response.status_code = 401

        ok_response = MagicMock()
        ok_response.status_code = 200
        ok_response.json.return_value = {"results": [{"pk": 1}]}

        mock_session.request.side_effect = [unauthorized_response, ok_response]

        mock_refresh_resp = MagicMock()
        mock_refresh_resp.status_code = 200
        mock_refresh_resp.json.return_value = {"access": "new_token"}
        mock_requests_post.return_value = mock_refresh_resp

        db = ServerBase(
            "http://example.com/api/",
            token="old_token",
            base_url="http://example.com/",
            get_refresh_token=lambda: "refresh_tok",
        )

        result = db.load()

        assert result == [{"pk": 1}]
        assert mock_session.request.call_count == 2
        mock_requests_post.assert_called_once_with(
            "http://example.com/api/v1/auth/token/refresh/",
            json={"refresh": "refresh_tok"},
            proxies={"http": None, "https": None},
        )
