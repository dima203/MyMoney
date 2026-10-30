import asyncio
from types import SimpleNamespace
from unittest.mock import MagicMock

import flet as ft
from application.view.dialogs import DIALOG_MAX_WIDTH, dialog_width, full_width, half_width
from application.view.planned_view import PlannedView
from application.view.transactions_view import TransactionsView

ACCOUNTS = [
    {"id": 1, "name": "Основной", "resource": "USDT", "account_type": "main"},
    {"id": 2, "name": "Торговый", "resource": "USDT", "account_type": "trading"},
]


def _view(cls, **kwargs):
    transaction_view = MagicMock()
    transaction_view.is_online = False
    transaction_view.get_all.return_value = []
    account_view = MagicMock()
    account_view.is_online = False
    account_view.get_all.return_value = list(ACCOUNTS)
    api_client = MagicMock()
    api_client.list_budgets.return_value = []
    view = cls(
        route="/transactions",
        api_client=api_client,
        transaction_view=transaction_view,
        account_view=account_view,
        **kwargs,
    )
    view.update = MagicMock()
    return view


def _page(width=None, window_width=None):
    page = MagicMock()
    page.width = width
    page.window.width = window_width
    return page


def _open(view, page, monkeypatch):
    monkeypatch.setattr(type(view), "page", property(lambda self: page))
    view._open_transaction_dialog()
    return page.show_dialog.call_args.args[0]


class TestDialogWidth:
    def test_no_width_falls_back_to_max(self):
        assert dialog_width(SimpleNamespace(width=None)) == DIALOG_MAX_WIDTH

    def test_uses_ninety_percent_of_page(self):
        assert dialog_width(SimpleNamespace(width=400)) == 320

    def test_caps_at_max(self):
        assert dialog_width(SimpleNamespace(width=1920)) == DIALOG_MAX_WIDTH

    def test_uses_window_width_when_page_width_missing(self):
        page = SimpleNamespace(width=None, window=SimpleNamespace(width=800))
        assert dialog_width(page) == 560

    def test_keeps_minimum_for_tiny_windows(self):
        assert dialog_width(SimpleNamespace(width=200)) == 280

    def test_view_without_page_uses_max(self):
        assert dialog_width(SimpleNamespace(page=None)) == DIALOG_MAX_WIDTH


class TestResponsiveFormLayout:
    def test_half_and_full_width_assign_columns(self):
        first, second, third = ft.TextField(), ft.TextField(), ft.TextField()
        assert half_width(first, second) == [first, second]
        assert full_width(third) == [third]
        assert first.col == 6
        assert second.col == 6
        assert third.col == 12

    def test_transaction_dialog_uses_responsive_row(self, monkeypatch):
        view = _view(TransactionsView)
        asyncio.run(view._load_data())
        page = _page(width=800)
        dialog = _open(view, page, monkeypatch)

        content = dialog.content.content
        assert isinstance(content, ft.ResponsiveRow)
        assert content.columns == 12
        assert content.width == 560
        assert content.controls[3].col == 6

    def test_planned_dialog_uses_responsive_row(self, monkeypatch):
        view = _view(PlannedView)
        asyncio.run(view._load_data())
        page = _page(width=None, window_width=600)
        dialog = _open(view, page, monkeypatch)

        content = dialog.content.content
        assert isinstance(content, ft.ResponsiveRow)
        assert content.width == 520
        assert content.controls[0].col == 12


class TestAccountDialogWidth:
    def test_account_dialog_follows_window(self, tmp_path, monkeypatch):
        from application.view.accounts_view import AccountsView
        from core.onboarding import OnboardingState

        resource_view = MagicMock()
        resource_view.is_online = False
        resource_view.get_all.return_value = []
        account_view = MagicMock()
        account_view.is_online = False
        account_view.get_all.return_value = []
        api_client = MagicMock()
        api_client.me.return_value = {"username": "u", "base_currency": "USDT"}
        view = AccountsView(
            route="/accounts",
            api_client=api_client,
            resource_view=resource_view,
            account_view=account_view,
            onboarding=OnboardingState(path=tmp_path / "o.json"),
        )
        view.update = MagicMock()
        asyncio.run(view._load_data())

        page = MagicMock()
        page.width = 400
        monkeypatch.setattr(type(view), "page", property(lambda self: page))
        view._open_account_dialog()

        dialog = page.show_dialog.call_args.args[0]
        assert dialog.content.content.width == 320
        assert isinstance(dialog.content.content, ft.ResponsiveRow)
