from __future__ import annotations

import os
import tempfile

import httpx
import pytest
from application.api.rest_client import ApiError, BackendUnreachableError, RestClient
from application.api.token_store import TokenData, TokenStore

BASE = "http://testserver"


def _client(handler, token_store=None) -> tuple[RestClient, TokenStore]:
    store = token_store or TokenStore(os.path.join(tempfile.mkdtemp(), "tokens.json"))
    client = RestClient(base_url=BASE, token_store=store, timeout=2.0)
    client._http = httpx.Client(transport=httpx.MockTransport(handler))
    return client, store


def _ok_json(payload):
    return httpx.Response(200, json=payload)


# ------------------------------------------------------------------ proxy


def test_client_disables_system_proxy_by_default():
    client = RestClient(base_url=BASE, timeout=2.0)
    assert client._http.trust_env is False
    client._http.close()


def test_client_can_enable_system_proxy():
    client = RestClient(base_url=BASE, timeout=2.0, trust_proxy=True)
    assert client._http.trust_env is True
    client._http.close()


# ------------------------------------------------------------------ auth


def test_request_sends_bearer_header(tmp_path):
    def handler(request):
        assert request.headers["Authorization"] == "Bearer test_access"
        return _ok_json({"ok": True})

    client, store = _client(handler, token_store=TokenStore(tmp_path / "tokens.json"))
    store.save(TokenData(access="test_access", refresh="test_refresh", username="user1"))
    data = client.me()
    assert data == {"ok": True}


def test_request_refreshes_on_401(tmp_path):
    calls = {"n": 0}

    def handler(request):
        calls["n"] += 1
        if request.url.path == "/api/v1/auth/token/refresh/":
            return _ok_json({"access": "new_access"})
        if calls["n"] == 1:
            return httpx.Response(401, json={"detail": "expired"})
        assert request.headers["Authorization"] == "Bearer new_access"
        return _ok_json({"ok": True})

    client, store = _client(handler, token_store=TokenStore(tmp_path / "tokens.json"))
    store.save(TokenData(access="old_access", refresh="ref1", username="user1"))
    data = client.me()
    assert data == {"ok": True}
    assert store.load().access == "new_access"
    assert calls["n"] == 3


def test_request_logs_out_when_refresh_fails(tmp_path):
    def handler(request):
        if request.url.path == "/api/v1/auth/token/refresh/":
            return httpx.Response(401, json={"detail": "invalid"})
        return httpx.Response(401, json={"detail": "expired"})

    client, store = _client(handler, token_store=TokenStore(tmp_path / "tokens.json"))
    store.save(TokenData(access="acc1", refresh="ref1", username="user1"))
    with pytest.raises(ApiError):
        client.me()
    assert store.load().access == ""


def test_logout_clears_tokens(tmp_path):
    def handler(request):
        return _ok_json({"ok": True})

    client, store = _client(handler, token_store=TokenStore(tmp_path / "tokens.json"))
    store.save(TokenData(access="acc1", refresh="ref1", username="user1"))
    client.logout()
    assert store.load().access == ""
    assert store.load().refresh == ""


# ------------------------------------------------------------------ domain URLs


def test_domain_methods_hit_correct_urls():
    seen = {}

    def handler(request):
        seen["path"] = request.url.path
        return _ok_json([{"id": 1}])

    client, _ = _client(handler)

    client.list_resources()
    assert seen["path"] == "/api/v1/resources/"

    client.list_accounts()
    assert seen["path"] == "/api/v1/accounts/"

    client.list_transactions()
    assert seen["path"] == "/api/v1/transactions/"

    client.list_planned_transactions()
    assert seen["path"] == "/api/v1/interactions/planned-transactions/"


# ------------------------------------------------------------------ CRUD


def test_create_resource():
    def handler(request):
        assert request.method == "POST"
        assert request.url.path == "/api/v1/resources/"
        return _ok_json({"id": 42, "name": "Bitcoin"})

    client, _ = _client(handler)
    result = client.create_resource({"name": "Bitcoin"})
    assert result["id"] == 42


def test_create_account():
    def handler(request):
        assert request.method == "POST"
        assert request.url.path == "/api/v1/accounts/"
        return _ok_json({"id": 10, "name": "Savings"})

    client, _ = _client(handler)
    result = client.create_account({"name": "Savings"})
    assert result["id"] == 10


def test_update_account():
    def handler(request):
        assert request.method == "PATCH"
        assert request.url.path == "/api/v1/accounts/5/"
        return _ok_json({"id": 5, "name": "Updated"})

    client, _ = _client(handler)
    result = client.update_account(5, {"name": "Updated"})
    assert result["id"] == 5


def test_delete_account():
    deleted = {}

    def handler(request):
        assert request.method == "DELETE"
        assert request.url.path == "/api/v1/accounts/7/"
        deleted["ok"] = True
        return httpx.Response(204)

    client, _ = _client(handler)
    client.delete_account(7)
    assert deleted["ok"]


def test_create_transaction():
    def handler(request):
        assert request.method == "POST"
        assert request.url.path == "/api/v1/transactions/"
        return _ok_json({"id": 99, "date": "2026-01-01T00:00:00"})

    client, _ = _client(handler)
    result = client.create_transaction({"date": "2026-01-01T00:00:00", "entries": []})
    assert result["id"] == 99


def test_update_transaction():
    def handler(request):
        assert request.method == "PATCH"
        assert request.url.path == "/api/v1/transactions/3/"
        return _ok_json({"id": 3})

    client, _ = _client(handler)
    result = client.update_transaction(3, {"category": "food"})
    assert result["id"] == 3


def test_delete_transaction():
    deleted = {}

    def handler(request):
        assert request.method == "DELETE"
        assert request.url.path == "/api/v1/transactions/4/"
        deleted["ok"] = True
        return httpx.Response(204)

    client, _ = _client(handler)
    client.delete_transaction(4)
    assert deleted["ok"]


# ------------------------------------------------------------------ errors


def test_api_error_raises_with_detail():
    def handler(request):
        return httpx.Response(400, json={"detail": "bad request"})

    client, _ = _client(handler)
    with pytest.raises(ApiError) as exc_info:
        client.list_accounts()
    assert exc_info.value.status_code == 400


def test_api_error_500():
    def handler(request):
        return httpx.Response(500, json={"detail": "server error"})

    client, _ = _client(handler)
    with pytest.raises(ApiError) as exc_info:
        client.list_resources()
    assert exc_info.value.status_code == 500


def test_backend_unreachable_error():
    def handler(request):
        raise httpx.ConnectError("connection refused")

    client, _ = _client(handler)
    with pytest.raises(BackendUnreachableError):
        client.me()


def test_backend_timeout_error():
    def handler(request):
        raise httpx.ReadTimeout("timed out")

    client, _ = _client(handler)
    with pytest.raises(BackendUnreachableError):
        client.list_accounts()


# ------------------------------------------------------------------ response handling


def test_204_returns_none():
    def handler(request):
        return httpx.Response(204)

    client, _ = _client(handler)
    result = client.delete_account(1)
    assert result is None


def test_list_returns_list():
    def handler(request):
        return _ok_json([{"id": 1}, {"id": 2}])

    client, _ = _client(handler)
    result = client.list_resources()
    assert isinstance(result, list)
    assert len(result) == 2


def test_me_returns_dict():
    def handler(request):
        return _ok_json({"username": "alice", "email": "alice@example.com"})

    client, _ = _client(handler)
    result = client.me()
    assert result["username"] == "alice"


# ------------------------------------------------------------------ profile


def test_update_profile():
    def handler(request):
        assert request.method == "PATCH"
        assert request.url.path == "/api/v1/auth/me/"
        return _ok_json({"username": "alice"})

    client, _ = _client(handler)
    result = client.update_profile(username="alice")
    assert result["username"] == "alice"
