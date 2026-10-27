"""Тесты палитры команд MyMoney (слайс 1.6)."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import flet as ft
from application.app import MyMoneyApp
from application.components.command_palette import (
    EMPTY_HINT,
    HOTKEY_HINT,
    NO_MATCHES,
    PLACEHOLDER,
    TITLE,
    CommandPalette,
)
from core.search import ACCOUNT_ROUTE, PLANNED_ROUTE, TRANSACTION_ROUTE

ACCOUNTS = [{"id": 1, "name": "Наличные", "resource": "BYN"}]
TRANSACTIONS = [
    {"id": 1, "date": "2026-10-05T10:00:00", "category": "Еда", "description": "Обед в кафе"},
    {"id": 2, "date": "2026-11-01T10:00:00", "category": "Подписки", "description": "Netflix", "is_planned": True},
]


def _palette() -> tuple[CommandPalette, MagicMock, MagicMock]:
    page = MagicMock()
    navigate = MagicMock()
    palette = CommandPalette(load_rows=lambda: (TRANSACTIONS, ACCOUNTS), on_navigate=navigate)
    return palette, page, navigate


def _texts(control) -> list[str]:
    found: list[str] = []
    if isinstance(control, ft.Text):
        found.append(str(control.value))
    for child in getattr(control, "controls", None) or []:
        found.extend(_texts(child))
    content = getattr(control, "content", None)
    if content is not None and not isinstance(content, str):
        found.extend(_texts(content))
    return found


def _tiles(palette: CommandPalette) -> list[ft.ListTile]:
    return [item for item in palette._results.controls if isinstance(item, ft.ListTile)]


def _change(palette: CommandPalette, query: str) -> None:
    """Ввод в поле палитры так, как его присылает Flet."""
    palette._on_change(SimpleNamespace(control=SimpleNamespace(value=query)))


class TestShow:
    def test_shows_dialog_with_empty_hint(self) -> None:
        palette, page, _navigate = _palette()

        palette.show(page)

        page.show_dialog.assert_called_once_with(palette.dialog)
        assert palette.dialog.title.controls[1].value == TITLE
        assert palette._field.autofocus is True
        assert palette._field.hint_text == PLACEHOLDER
        assert EMPTY_HINT in _texts(palette._results)

    def test_loads_rows_once(self) -> None:
        calls: list[int] = []
        palette = CommandPalette(
            load_rows=lambda: (calls.append(1) or TRANSACTIONS, ACCOUNTS),
            on_navigate=MagicMock(),
        )

        palette.show(MagicMock())
        palette._render("обед")

        assert len(calls) == 1


class TestFiltering:
    def test_transaction_tile(self) -> None:
        palette, page, _navigate = _palette()
        palette.show(page)

        _change(palette, "обед")

        tiles = _tiles(palette)
        assert [tile.title.value for tile in tiles] == ["Обед в кафе"]
        assert tiles[0].subtitle.value == "Транзакция · Еда · 2026-10-05"
        page.update.assert_called()

    def test_account_tile_icon(self) -> None:
        palette, page, _navigate = _palette()
        palette.show(page)

        _change(palette, "налич")

        tile = _tiles(palette)[0]
        assert tile.leading.icon == ft.Icons.ACCOUNT_BALANCE_WALLET_OUTLINED

    def test_no_matches_hint(self) -> None:
        palette, page, _navigate = _palette()
        palette.show(page)

        _change(palette, "нет-такого")

        assert _tiles(palette) == []
        assert NO_MATCHES in _texts(palette._results)

    def test_clearing_query_restores_hint(self) -> None:
        palette, page, _navigate = _palette()
        palette.show(page)
        _change(palette, "обед")

        _change(palette, "")

        assert EMPTY_HINT in _texts(palette._results)


class TestChoose:
    def test_choose_navigates_and_closes(self) -> None:
        palette, page, navigate = _palette()
        palette.show(page)

        palette._choose(SimpleNamespace(route=TRANSACTION_ROUTE))

        page.pop_dialog.assert_called_once()
        navigate.assert_called_once_with(TRANSACTION_ROUTE)

    def test_close_notifies_owner(self) -> None:
        closed: list[int] = []
        palette = CommandPalette(
            load_rows=lambda: ([], []),
            on_navigate=MagicMock(),
            on_close=lambda: closed.append(1),
        )
        page = MagicMock()
        palette.show(page)

        palette._close()

        assert closed == [1]
        page.pop_dialog.assert_called_once()
        assert palette._page is None

    def test_planned_hit_navigates_to_planned(self) -> None:
        palette, page, navigate = _palette()
        palette.show(page)

        _change(palette, "netflix")
        tiles = _tiles(palette)
        tiles[0].on_click(None)

        navigate.assert_called_once_with(PLANNED_ROUTE)

    def test_account_hit_navigates_to_accounts(self) -> None:
        palette, page, navigate = _palette()
        palette.show(page)

        _change(palette, "налич")
        _tiles(palette)[0].on_click(None)

        navigate.assert_called_once_with(ACCOUNT_ROUTE)


class TestAppHotkey:
    def _app(self, route: str = "/transactions"):
        app = MyMoneyApp()
        app.page = MagicMock()
        app.page.route = route
        app._palette_rows = lambda: ([], [])
        return app

    def test_ctrl_k_opens_single_palette(self) -> None:
        app = self._app()

        app._on_keyboard(SimpleNamespace(key="K", ctrl=True))
        app._on_keyboard(SimpleNamespace(key="k", ctrl=True))

        assert app.page.show_dialog.call_count == 1
        app._palette._close()
        assert app._palette is None

    def test_hotkey_without_ctrl_is_ignored(self) -> None:
        app = self._app()

        app._on_keyboard(SimpleNamespace(key="K", ctrl=False))

        app.page.show_dialog.assert_not_called()
        assert app._palette is None

    def test_palette_is_not_opened_on_login(self) -> None:
        app = self._app(route="/login")

        app._open_palette()

        app.page.show_dialog.assert_not_called()

    def test_mount_adds_search_action(self) -> None:
        app = self._app()
        view = MagicMock()
        view.app_bar.actions = None

        app._mount(view)

        action = view.app_bar.actions[0]
        assert action.icon == ft.Icons.SEARCH
        assert HOTKEY_HINT in action.tooltip
        app.page.views.append.assert_called_once_with(view)

    def test_mount_adds_notifications_badge_and_loads_it(self) -> None:
        app = self._app()
        app.page.run_task = MagicMock()
        view = MagicMock()

        app._mount(view)

        badge = view.app_bar.actions[1]
        assert badge.tooltip == "Уведомления"
        assert badge.visible is False
        assert view.notifications.badge is badge
        assert app.page.run_task.call_args[0][0] == view.notifications.load

    def test_palette_rows_return_lists(self) -> None:
        app = self._app()
        app._transaction_view = MagicMock()
        app._transaction_view.get_all.return_value = {"1": {"category": "Еда"}}
        app._account_view = MagicMock()
        app._account_view.get_all.return_value = [{"name": "Наличные"}]

        transactions, accounts = MyMoneyApp._palette_rows(app)

        assert transactions == [{"category": "Еда"}]
        assert accounts == [{"name": "Наличные"}]
