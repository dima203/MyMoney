"""Офлайн-старт MyMoney на общем хелпере Shared (2.85)."""

import asyncio
from unittest.mock import AsyncMock, MagicMock

import application.app as app_module
import pytest
from application.app import MyMoneyApp

from MySpaceShared.api.session import SESSION_OFFLINE, SESSION_NO_TOKEN, SESSION_ONLINE


def _app(monkeypatch, state: str) -> MyMoneyApp:
    app = MyMoneyApp()
    app.page = MagicMock()
    app.page.route = "/accounts"
    app._init_offline_views = MagicMock()
    app._sync_pending = AsyncMock()
    monkeypatch.setattr(app_module, "session_state", MagicMock(return_value=state))
    return app


class TestValidateSession:
    def test_online_initializes_views_and_syncs(self, monkeypatch) -> None:
        app = _app(monkeypatch, SESSION_ONLINE)

        assert asyncio.run(app._validate_session()) is True
        app._init_offline_views.assert_called_once()
        app._sync_pending.assert_awaited_once()
        assert app._connection_banner.visible is False

    def test_offline_keeps_working_and_shows_banner(self, monkeypatch) -> None:
        app = _app(monkeypatch, SESSION_OFFLINE)

        assert asyncio.run(app._validate_session()) is True
        app._init_offline_views.assert_called_once()
        app._sync_pending.assert_not_awaited()
        assert app._connection_banner.visible is True

    def test_no_token_goes_to_login(self, monkeypatch) -> None:
        app = _app(monkeypatch, SESSION_NO_TOKEN)

        assert asyncio.run(app._validate_session()) is False
        app._init_offline_views.assert_not_called()

    def test_helper_exception_falls_back_to_login(self, monkeypatch) -> None:
        app = _app(monkeypatch, SESSION_ONLINE)
        monkeypatch.setattr(app_module, "session_state", MagicMock(side_effect=RuntimeError("boom")))

        assert asyncio.run(app._validate_session()) is False


@pytest.mark.parametrize("state", [SESSION_ONLINE, SESSION_OFFLINE])
def test_app_does_not_call_api_directly(monkeypatch, state: str) -> None:
    """Проверка сессии — только через общий хелпер (иначе клиенты разъезжаются)."""
    app = _app(monkeypatch, state)
    app.api_client.me = MagicMock()

    asyncio.run(app._validate_session())

    app.api_client.me.assert_not_called()
