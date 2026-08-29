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
            from auth.google_auth import OAuthCallbackError
            raise OAuthCallbackError(self.error_msg or "OAuth failed")
        return {"access": "acc1", "refresh": "ref1"}


def _view(backend_url="http://testserver"):
    return LoginView(backend_url=backend_url, on_success=MagicMock())


def test_login_view_shows_google_button():
    view = _view()
    assert "Google" in str(view.login_button.content)


def test_authenticate_success():
    view = _view()
    with patch("auth.google_auth.GoogleOAuthFlow") as MockFlow, \
         patch("application.api.token_store.TokenStore") as MockStore:
        MockFlow.return_value = FakeOAuthFlow(success=True)
        ok, message = view.authenticate()
    assert ok is True
    assert message == ""
    MockStore.return_value.save.assert_called_once()


def test_authenticate_saves_tokens():
    view = _view()
    with patch("auth.google_auth.GoogleOAuthFlow") as MockFlow, \
         patch("application.api.token_store.TokenStore") as MockStore:
        MockFlow.return_value = FakeOAuthFlow(success=True)
        view.authenticate()
    saved_data = MockStore.return_value.save.call_args[0][0]
    assert saved_data.access == "acc1"
    assert saved_data.refresh == "ref1"


def test_authenticate_oauth_error():
    view = _view()
    with patch("auth.google_auth.GoogleOAuthFlow") as MockFlow:
        MockFlow.return_value = FakeOAuthFlow(success=False, error_msg="auth denied")
        ok, message = view.authenticate()
    assert ok is False
    assert "auth denied" in message


def test_authenticate_network_error():
    view = _view()
    with patch("auth.google_auth.GoogleOAuthFlow") as MockFlow:
        MockFlow.return_value = FakeOAuthFlow(success=False, error_msg="connection refused")
        ok, message = view.authenticate()
    assert ok is False
    assert "connection refused" in message


def test_submit_success_calls_on_success():
    view = _view()
    with patch("auth.google_auth.GoogleOAuthFlow") as MockFlow, \
         patch("application.api.token_store.TokenStore"):
        MockFlow.return_value = FakeOAuthFlow(success=True)

        async def run():
            await view._submit(None)
        asyncio.run(run())
    view.on_success.assert_called_once_with(view)


def test_submit_error_sets_error_text():
    view = _view()
    with patch("auth.google_auth.GoogleOAuthFlow") as MockFlow:
        MockFlow.return_value = FakeOAuthFlow(success=False, error_msg="oauth failed")

        async def run():
            await view._submit(None)
        asyncio.run(run())
    assert view.error_text.visible is True
    assert "oauth failed" in view.error_text.value
