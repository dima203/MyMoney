"""Deep links MyMoney: /accounts/<id>, подсветка и неизвестный счёт (2.114a)."""

import asyncio
from unittest.mock import MagicMock, patch

from application.app import MyMoneyApp
from application.components.account_card import AccountCard
from application.fx_rates import FxRateStore
from application.view.accounts_view import AccountsView
from core.onboarding import OnboardingState

ACCOUNTS = [
    {
        "id": 1,
        "name": "Наличные",
        "resource_definition": 1,
        "current_balance_qty": "100",
        "group": "",
        "account_type": "main",
    }
]
RESOURCES = [{"id": 1, "name": "BYN", "ticker": "BYN", "resource_type": "currency"}]


def _walk(control):
    yield control
    for child in getattr(control, "controls", None) or []:
        yield from _walk(child)
    content = getattr(control, "content", None)
    if content is not None:
        yield from _walk(content)


def _view(tmp_path, account_id):
    resource_view = MagicMock()
    resource_view.is_online = False
    resource_view.get_all.return_value = list(RESOURCES)
    account_view = MagicMock()
    account_view.is_online = False
    account_view.get_all.return_value = list(ACCOUNTS)
    view = AccountsView(
        route="/accounts",
        api_client=MagicMock(),
        resource_view=resource_view,
        account_view=account_view,
        onboarding=OnboardingState(path=tmp_path / "onboarding.json"),
        fx_store=FxRateStore(tmp_path / "fx.json"),
        initial_account_id=account_id,
    )
    view.update = MagicMock()
    return view


class TestRouteParsing:
    def test_account_id(self):
        assert MyMoneyApp._account_id_from_route("/accounts/5") == 5

    def test_plain_accounts(self):
        assert MyMoneyApp._account_id_from_route("/accounts") is None

    def test_non_numeric_marked_unknown(self):
        assert MyMoneyApp._account_id_from_route("/accounts/abc") == -1

    def test_other_route(self):
        assert MyMoneyApp._account_id_from_route("/operations") is None


class TestAccountsHighlight:
    def test_known_account_is_highlighted(self, tmp_path):
        view = _view(tmp_path, 1)

        asyncio.run(view._load_data())

        cards = [control for control in _walk(view._accounts_column) if isinstance(control, AccountCard)]
        assert any(card.highlighted for card in cards)

    def test_unknown_account_toasts_and_clears(self, tmp_path):
        view = _view(tmp_path, 99)

        with (
            patch("application.components.file_save.show_toast") as toast,
            patch.object(type(view), "page", new_callable=lambda: property(lambda self: MagicMock())),
        ):
            asyncio.run(view._load_data())

        assert view._highlight_account_id is None
        toast.assert_called_once()

    def test_no_initial_id_keeps_cards_normal(self, tmp_path):
        view = _view(tmp_path, None)

        asyncio.run(view._load_data())

        cards = [control for control in _walk(view._accounts_column) if isinstance(control, AccountCard)]
        assert not any(card.highlighted for card in cards)
