"""Тесты LoginView с Google OAuth."""

import asyncio
from unittest.mock import MagicMock, patch

from application.screens import LoginView


class FakeOAuthFlow:
    def __init__(self, success=True, error_msg=None):
        self.success = success
        self.error_msg = error_msg

    def start(self):
        if not self.success:
            from MySpaceShared.auth.google_auth import OAuthCallbackError
            raise OAuthCallbackError(self.error_msg or "OAuth failed")
        return {"access": "acc1", "refresh": "ref1"}


def _view(backend_url="http://testserver"):
    return LoginView(backend_url=backend_url, on_success=MagicMock())


def test_login_view_shows_google_button():
    view = _view()
    assert "Google" in str(view.login_button.content)


def _mock_config_response():
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"client_id": "test-client-id"}
    mock_resp.raise_for_status = MagicMock()
    return mock_resp


def test_authenticate_success():
    view = _view()
    with patch("MySpaceShared.auth.google_auth.GoogleOAuthFlow") as MockFlow, \
         patch("MySpaceShared.api.token_store.TokenStore") as MockStore, \
         patch("httpx.Client") as MockClient:
        MockFlow.return_value = FakeOAuthFlow(success=True)
        MockClient.return_value.__enter__ = lambda s: s
        MockClient.return_value.__exit__ = MagicMock(return_value=False)
        MockClient.return_value.get.return_value = _mock_config_response()
        ok, message = view.authenticate()
    assert ok is True
    assert message == ""
    MockStore.return_value.save.assert_called_once()


def test_authenticate_saves_tokens():
    view = _view()
    with patch("MySpaceShared.auth.google_auth.GoogleOAuthFlow") as MockFlow, \
         patch("MySpaceShared.api.token_store.TokenStore") as MockStore, \
         patch("httpx.Client") as MockClient:
        MockFlow.return_value = FakeOAuthFlow(success=True)
        MockClient.return_value.__enter__ = lambda s: s
        MockClient.return_value.__exit__ = MagicMock(return_value=False)
        MockClient.return_value.get.return_value = _mock_config_response()
        view.authenticate()
    saved_data = MockStore.return_value.save.call_args[0][0]
    assert saved_data.access == "acc1"
    assert saved_data.refresh == "ref1"


def test_authenticate_oauth_error():
    view = _view()
    with patch("MySpaceShared.auth.google_auth.GoogleOAuthFlow") as MockFlow, \
         patch("httpx.Client") as MockClient:
        MockFlow.return_value = FakeOAuthFlow(success=False, error_msg="auth denied")
        MockClient.return_value.__enter__ = lambda s: s
        MockClient.return_value.__exit__ = MagicMock(return_value=False)
        MockClient.return_value.get.return_value = _mock_config_response()
        ok, message = view.authenticate()
    assert ok is False
    assert "auth denied" in message


def test_authenticate_network_error():
    view = _view()
    with patch("MySpaceShared.auth.google_auth.GoogleOAuthFlow") as MockFlow, \
         patch("httpx.Client") as MockClient:
        MockFlow.return_value = FakeOAuthFlow(success=False, error_msg="connection refused")
        MockClient.return_value.__enter__ = lambda s: s
        MockClient.return_value.__exit__ = MagicMock(return_value=False)
        MockClient.return_value.get.return_value = _mock_config_response()
        ok, message = view.authenticate()
    assert ok is False
    assert "connection refused" in message


def test_submit_success_calls_on_success():
    view = _view()
    with patch("MySpaceShared.auth.google_auth.GoogleOAuthFlow") as MockFlow, \
         patch("MySpaceShared.api.token_store.TokenStore"), \
         patch("httpx.Client") as MockClient:
        MockFlow.return_value = FakeOAuthFlow(success=True)
        MockClient.return_value.__enter__ = lambda s: s
        MockClient.return_value.__exit__ = MagicMock(return_value=False)
        MockClient.return_value.get.return_value = _mock_config_response()

        async def run():
            await view._submit(None)
        asyncio.run(run())
    view.on_success.assert_called_once_with(view)


def test_submit_error_sets_error_text():
    view = _view()
    with patch("MySpaceShared.auth.google_auth.GoogleOAuthFlow") as MockFlow, \
         patch("httpx.Client") as MockClient:
        MockFlow.return_value = FakeOAuthFlow(success=False, error_msg="oauth failed")
        MockClient.return_value.__enter__ = lambda s: s
        MockClient.return_value.__exit__ = MagicMock(return_value=False)
        MockClient.return_value.get.return_value = _mock_config_response()

        async def run():
            await view._submit(None)
        asyncio.run(run())
    assert view.error_text.visible is True
    assert "oauth failed" in view.error_text.value
