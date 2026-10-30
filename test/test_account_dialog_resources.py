import asyncio
from unittest.mock import MagicMock

import flet as ft
from application.view.accounts_view import AccountsView, resource_option_text, resource_sort_key
from core.onboarding import OnboardingState

RESOURCES = [
    {"id": 3, "name": "Bitcoin", "ticker": "BTC", "resource_type": "asset"},
    {"id": 1, "name": "BYN", "ticker": "BYN", "resource_type": "currency"},
    {"id": 7, "name": "Машина", "ticker": "CAR", "resource_type": "custom", "owner": 1},
    {"id": 5, "name": "USDT", "ticker": "USDT", "resource_type": "currency"},
]


def _make_view(tmp_path) -> AccountsView:
    resource_view = MagicMock()
    resource_view.is_online = False
    resource_view.get_all.side_effect = lambda: list(RESOURCES)
    account_view = MagicMock()
    account_view.is_online = False
    account_view.get_all.side_effect = lambda: []
    api_client = MagicMock()
    api_client.me.return_value = {"username": "u", "base_currency": "USDT"}
    view = AccountsView(
        route="/accounts",
        api_client=api_client,
        resource_view=resource_view,
        account_view=account_view,
        onboarding=OnboardingState(path=tmp_path / "onboarding.json"),
    )
    view.update = MagicMock()
    return view


def _dialog(view, monkeypatch) -> ft.AlertDialog:
    page = MagicMock()
    monkeypatch.setattr(type(view), "page", property(lambda self: page))
    view._open_account_dialog()
    return page.show_dialog.call_args.args[0]


def _resource_dropdown(dialog) -> ft.Dropdown:
    return dialog.content.content.controls[1]


def test_resource_option_text_includes_type():
    assert (
        resource_option_text({"name": "Bitcoin", "ticker": "BTC", "resource_type": "asset"}) == "Bitcoin (BTC) · крипта"
    )
    assert resource_option_text({"name": "BYN", "ticker": "BYN", "resource_type": "currency"}) == "BYN (BYN) · валюта"
    assert resource_option_text({"name": "Машина", "ticker": "", "resource_type": "custom"}) == "Машина · ресурс"


def test_resource_order_fiat_then_own_then_crypto():
    ordered = sorted(RESOURCES, key=resource_sort_key)
    assert [item["name"] for item in ordered] == ["BYN", "USDT", "Машина", "Bitcoin"]


def test_account_dialog_dropdown_is_filterable(tmp_path, monkeypatch):
    view = _make_view(tmp_path)
    asyncio.run(view._load_data())

    dropdown = _resource_dropdown(_dialog(view, monkeypatch))

    assert dropdown.enable_filter is True


def test_account_dialog_options_ordered_and_labelled(tmp_path, monkeypatch):
    view = _make_view(tmp_path)
    asyncio.run(view._load_data())

    dropdown = _resource_dropdown(_dialog(view, monkeypatch))

    assert [option.key for option in dropdown.options] == ["1", "5", "7", "3"]
    assert [option.text for option in dropdown.options] == [
        "BYN (BYN) · валюта",
        "USDT (USDT) · валюта",
        "Машина (CAR) · ресурс",
        "Bitcoin (BTC) · крипта",
    ]


def test_save_button_uses_content_not_text():
    button = ft.Button("Сохранить")
    button.content = "Сохранение..."
    assert button.content == "Сохранение..."
    assert not hasattr(type(button), "text") or getattr(type(button), "text", None) is None
