"""2.158: «Накопительный счёт» — галочка в форме, payload и пометка в списке."""

import asyncio
from unittest.mock import AsyncMock, MagicMock

import flet as ft
from application.components.account_card import AccountCard
from application.view.accounts_view import AccountsView
from core.onboarding import OnboardingState

RESOURCES = [{"id": 1, "name": "BYN", "ticker": "BYN", "resource_type": "currency"}]
ACCOUNTS = [
    {
        "id": 1,
        "name": "Копилка",
        "resource_definition": 1,
        "group": "",
        "account_type": "main",
        "current_balance_qty": "100",
        "is_savings": True,
    }
]


def _walk(control):
    yield control
    for child in getattr(control, "controls", None) or []:
        yield from _walk(child)
    content = getattr(control, "content", None)
    if content is not None:
        yield from _walk(content)


def _texts(control) -> list[str]:
    return [str(item.value) for item in _walk(control) if isinstance(item, ft.Text)]


def _view(tmp_path, accounts=None) -> AccountsView:
    resource_view = MagicMock()
    resource_view.is_online = False
    resource_view.get_all.return_value = list(RESOURCES)
    account_view = MagicMock()
    account_view.is_online = False
    account_view.get_all.return_value = list(accounts or [])
    view = AccountsView(
        route="/accounts",
        api_client=MagicMock(),
        resource_view=resource_view,
        account_view=account_view,
        onboarding=OnboardingState(path=tmp_path / "onboarding.json"),
    )
    view.update = MagicMock()
    return view


def _dialog(view, monkeypatch, account=None):
    page = MagicMock()
    monkeypatch.setattr(type(view), "page", property(lambda _self: page), raising=False)
    view._open_account_dialog(account=account)
    return page.show_dialog.call_args.args[0]


def _checkbox(dialog) -> ft.Checkbox:
    return next(control for control in _walk(dialog) if isinstance(control, ft.Checkbox))


class TestAccountDialogSavings:
    def test_new_account_defaults_to_free(self, tmp_path, monkeypatch):
        view = _view(tmp_path)

        dialog = _dialog(view, monkeypatch)

        assert _checkbox(dialog).label == "Накопительный счёт"
        assert _checkbox(dialog).value is False

    def test_edit_prefills_savings(self, tmp_path, monkeypatch):
        view = _view(tmp_path, accounts=ACCOUNTS)

        dialog = _dialog(view, monkeypatch, account=ACCOUNTS[0])

        assert _checkbox(dialog).value is True

    def test_payload_sends_savings_flag(self, tmp_path, monkeypatch):
        view = _view(tmp_path, accounts=ACCOUNTS)
        view._load_data = AsyncMock()
        dialog = _dialog(view, monkeypatch, account=ACCOUNTS[0])

        asyncio.run(dialog.actions[1].on_click(None))

        payload = view._account_view.update.call_args.args[1]
        assert payload["is_savings"] is True

    def test_new_account_can_be_marked_savings(self, tmp_path, monkeypatch):
        view = _view(tmp_path)
        view._load_data = AsyncMock()
        dialog = _dialog(view, monkeypatch)
        controls = list(_walk(dialog))
        name_field = next(control for control in controls if isinstance(control, ft.TextField))
        resource_dropdown = next(control for control in controls if isinstance(control, ft.Dropdown))
        name_field.value = "Копилка"
        resource_dropdown.value = "1"
        _checkbox(dialog).value = True

        asyncio.run(dialog.actions[1].on_click(None))

        payload = view._account_view.add.call_args.args[0]
        assert payload["is_savings"] is True


class TestSavingsListBadge:
    def test_card_shows_savings_badge(self):
        card = AccountCard(name="Копилка", balance="100 BYN", savings=True)

        assert "Накопительный" in _texts(card)

    def test_regular_card_has_no_badge(self):
        card = AccountCard(name="Основной", balance="100 BYN")

        assert "Накопительный" not in _texts(card)

    def test_accounts_view_marks_savings_account(self, tmp_path):
        view = _view(tmp_path, accounts=ACCOUNTS)

        asyncio.run(view._load_data())

        cards = [control for control in _walk(view._accounts_column) if isinstance(control, AccountCard)]
        assert any(card.savings and "Накопительный" in _texts(card) for card in cards)
