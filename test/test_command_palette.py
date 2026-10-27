"""Палитра Ctrl+K в MyMoney (слайс 1.6 → 2.26, общий компонент MySpaceShared)."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

from application.app import MyMoneyApp

from MySpaceShared.components.command_palette import (
    HOTKEY_HINT,
    PaletteController,
)


class TestAppHotkey:
    def _app(self, route: str = "/transactions") -> MyMoneyApp:
        app = MyMoneyApp()
        app.page = MagicMock()
        app.page.route = route
        return app

    def test_app_uses_shared_palette_controller(self) -> None:
        app = self._app()

        assert isinstance(app.palette, PaletteController)

    def test_ctrl_k_opens_single_palette(self) -> None:
        app = self._app()

        app._on_keyboard(SimpleNamespace(key="K", ctrl=True))
        app._on_keyboard(SimpleNamespace(key="k", ctrl=True))

        assert app.page.show_dialog.call_count == 1
        app.page.run_task.assert_called_once()

    def test_hotkey_without_ctrl_is_ignored(self) -> None:
        app = self._app()

        app._on_keyboard(SimpleNamespace(key="K", ctrl=False))

        app.page.show_dialog.assert_not_called()
        assert app.palette.palette is None

    def test_hotkey_on_login_route_is_ignored(self) -> None:
        app = self._app(route="/login")

        app._on_keyboard(SimpleNamespace(key="k", ctrl=True))

        app.page.show_dialog.assert_not_called()

    def test_mount_adds_search_action_with_hotkey_hint(self) -> None:
        app = self._app()
        view = MagicMock()

        app._mount(view)

        action = view.app_bar.actions[0]
        assert action.icon is not None
        assert HOTKEY_HINT in action.tooltip
