import asyncio
from unittest.mock import MagicMock

import flet as ft
from application.components.transaction_card import TransactionCard
from application.display import FAB_CLEARANCE
from application.view.transactions_view import TransactionsView

from MySpaceShared.components.empty_state import EmptyState

ACCOUNTS = [
    {"id": 1, "name": "Основной", "resource": "BYN", "group": "", "account_type": "main"},
    {"id": 2, "name": "Доллары", "resource": "USD", "group": "", "account_type": "main"},
]


def _tx(tx_id: int, day: str, amount: float, account: int = 1, category: str = "Еда") -> dict:
    return {
        "id": tx_id,
        "date": f"{day}T10:00:00",
        "description": f"Операция {tx_id}",
        "category": category,
        "entries": [{"account": account, "amount": amount, "unit_price": 1}],
    }


def _view(transactions=None) -> TransactionsView:
    transaction_view = MagicMock()
    transaction_view.is_online = True
    transaction_view.get_all.side_effect = lambda: list(transactions or [])
    account_view = MagicMock()
    account_view.is_online = True
    account_view.get_all.side_effect = lambda: list(ACCOUNTS)
    view = TransactionsView(
        route="/transactions",
        api_client=MagicMock(),
        transaction_view=transaction_view,
        account_view=account_view,
    )
    view.update = MagicMock()
    return view


def _cards(view) -> list:
    return [control for control in view._tx_list.controls if isinstance(control, TransactionCard)]


def _texts(control) -> list[str]:
    found: list[str] = []
    if isinstance(control, ft.Text) and control.value is not None:
        found.append(str(control.value))
    content = getattr(control, "content", None)
    if isinstance(content, str):
        found.append(content)
    elif content is not None:
        found.extend(_texts(content))
    for child in getattr(control, "controls", None) or []:
        found.extend(_texts(child))
    return found


def _loaded(transactions) -> TransactionsView:
    view = _view(transactions)
    asyncio.run(view._load_data())
    return view


class TestFilterControls:
    def test_filter_dropdowns_exist(self):
        view = _loaded([_tx(1, "2026-10-01", -10.0)])
        assert view._filter_period.value == "all"
        assert view._filter_account.value == "all"
        assert view._filter_type.value == "all"
        assert view._filter_category.value == "Все"

    def test_period_and_type_options(self):
        view = _view()
        keys = [option.key for option in view._filter_period.options]
        assert keys == ["all", "month", "prev_month", "7d", "30d"]
        type_keys = [option.key for option in view._filter_type.options]
        assert type_keys == ["all", "income", "expense", "transfer"]

    def test_account_options_after_load(self):
        view = _loaded([_tx(1, "2026-10-01", -10.0)])
        texts = [option.text for option in view._filter_account.options]
        assert texts == ["Все счета", "Основной", "Доллары"]
        assert [option.key for option in view._filter_account.options] == ["all", "1", "2"]

    def test_filter_bar_keeps_export_buttons(self):
        view = _view()
        buttons = [control for control in view._filter_bar.controls if isinstance(control, ft.IconButton)]
        assert [button.tooltip for button in buttons] == ["Экспорт CSV", "Импорт CSV"]


class TestFiltersApply:
    def test_filter_by_account(self):
        view = _loaded(
            [
                _tx(1, "2026-10-01", -10.0, account=1),
                _tx(2, "2026-10-02", -20.0, account=2),
            ]
        )
        view._filter_account.value = "2"

        view._apply_filters()

        assert len(_cards(view)) == 1
        assert "Операция 2" in _texts(_cards(view)[0])

    def test_filter_by_type_income(self):
        view = _loaded([_tx(1, "2026-10-01", -10.0), _tx(2, "2026-10-02", 50.0)])
        view._filter_type.value = "income"

        view._apply_filters()

        assert len(_cards(view)) == 1
        assert "Операция 2" in _texts(_cards(view)[0])

    def test_filter_by_period_month(self):
        view = _loaded([_tx(1, "2026-10-01", -10.0), _tx(2, "2020-01-01", -20.0)])
        view._filter_period.value = "month"

        view._apply_filters()

        assert len(_cards(view)) == 1

    def test_combined_filters_empty_state(self):
        view = _loaded([_tx(1, "2026-10-01", -10.0, category="Еда")])
        view._filter_category.value = "Транспорт"

        view._apply_filters()

        empties = [control for control in view._tx_list.controls if isinstance(control, EmptyState)]
        assert empties
        assert "Ничего не найдено" in _texts(empties[0])

    def test_clear_filters_restores_rows(self):
        view = _loaded([_tx(1, "2026-10-01", -10.0), _tx(2, "2026-10-02", -20.0)])
        view._filter_type.value = "income"
        view._apply_filters()
        assert _cards(view) == []

        view._filter_type.value = "all"
        view._apply_filters()

        assert len(_cards(view)) == 2

    def test_fab_spacer_is_last(self):
        view = _loaded([_tx(1, "2026-10-01", -10.0)])
        last = view._tx_list.controls[-1]
        assert isinstance(last, ft.Container)
        assert last.height == FAB_CLEARANCE


def test_export_respects_type_filter(monkeypatch):
    from application.view import transactions_view as module

    saved = {}

    async def fake_export(_page, **kwargs):
        saved["content"] = kwargs["content"]

    monkeypatch.setattr(module, "export_csv", fake_export)
    monkeypatch.setattr(
        type(view := _loaded([_tx(1, "2026-10-01", -10.0), _tx(2, "2026-10-02", 50.0)])),
        "page",
        property(lambda self: MagicMock()),
    )
    view._filter_type.value = "income"
    view._apply_filters()

    asyncio.run(view._export_csv())

    assert "Операция 2" in saved["content"]
    assert "Операция 1" not in saved["content"]
