"""Тесты секции «Запланировано из задач/ событий» в PlannedView."""

import asyncio
from unittest.mock import MagicMock

import flet as ft
from application.api import ApiError, BackendUnreachableError
from application.components.cross_app_budget_card import CrossAppBudgetCard
from application.view.planned_view import PlannedView, filter_cross_app_budgets


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


def _task_item(**overrides) -> dict:
    item = {
        "source_app": "task",
        "source_id": 1,
        "title": "Gift",
        "amount": "100.0000",
        "currency": "USDT",
        "date": "2026-10-05",
    }
    item.update(overrides)
    return item


def _view(api_client=None, transaction_view=None, is_online=True):
    api = api_client if api_client is not None else MagicMock()
    tv = transaction_view
    if tv is None:
        tv = MagicMock()
        tv.is_online = is_online
        tv.get_all.return_value = []
    view = PlannedView(
        route="/planned",
        api_client=api,
        transaction_view=tv,
        account_view=MagicMock(get_all=MagicMock(return_value=[])),
    )
    view.update = MagicMock()
    return view


class TestFilterCrossAppBudgets:
    def test_keeps_task_and_calendar(self) -> None:
        items = [
            _task_item(),
            {
                "source_app": "calendar",
                "source_id": 2,
                "title": "Cinema",
                "amount": "50.0000",
                "currency": "USDT",
                "date": "2026-10-06",
            },
        ]
        result = filter_cross_app_budgets(items)
        assert [i["source_app"] for i in result] == ["task", "calendar"]

    def test_excludes_own_transactions(self) -> None:
        items = [
            _task_item(),
            {
                "source_app": "transaction",
                "source_id": 9,
                "title": "Rent",
                "amount": "500.0000",
                "currency": "USDT",
                "date": "2026-10-01",
            },
        ]
        result = filter_cross_app_budgets(items)
        assert [i["source_app"] for i in result] == ["task"]

    def test_dedupes_identical_rows(self) -> None:
        items = [_task_item(), _task_item(), _task_item(source_id=2)]
        result = filter_cross_app_budgets(items)
        assert len(result) == 2

    def test_distinct_rows_with_same_title_kept(self) -> None:
        items = [
            _task_item(source_id=1, date="2026-10-05"),
            _task_item(source_id=2, date="2026-10-06"),
        ]
        result = filter_cross_app_budgets(items)
        assert len(result) == 2

    def test_sorts_by_date_ascending_with_missing_last(self) -> None:
        items = [
            _task_item(title="No date", date=None),
            _task_item(title="Later", date="2026-12-01"),
            _task_item(title="Sooner", date="2026-01-01"),
        ]
        result = filter_cross_app_budgets(items)
        assert [i["title"] for i in result] == ["Sooner", "Later", "No date"]

    def test_ignores_non_dict_entries(self) -> None:
        result = filter_cross_app_budgets([None, "x", _task_item()])
        assert len(result) == 1

    def test_unknown_source_ignored(self) -> None:
        result = filter_cross_app_budgets([{"source_app": "crypto", "source_id": 1}])
        assert result == []


class TestBudgetsSectionSuccess:
    def test_renders_only_task_and_calendar_cards(self) -> None:
        api = MagicMock()
        api.list_budgets.return_value = [
            _task_item(),
            {
                "source_app": "calendar",
                "source_id": 2,
                "title": "Cinema",
                "amount": "50.0000",
                "currency": "USDT",
                "date": "2026-10-06",
            },
            {
                "source_app": "transaction",
                "source_id": 3,
                "title": "Rent",
                "amount": "500.0000",
                "currency": "USDT",
                "date": "2026-10-01",
            },
        ]
        view = _view(api_client=api)
        asyncio.run(view._load_budgets())

        assert len(view._budgets) == 2
        assert view._budget_section.visible is True
        assert view._budget_hint.visible is False
        assert len(view._budget_items.controls) == 2
        assert all(isinstance(card, CrossAppBudgetCard) for card in view._budget_items.controls)

        texts = _texts(view._budget_items)
        assert "Gift" in texts
        assert "Cinema" in texts
        assert "Rent" not in texts

    def test_card_shows_badge_amount_and_date(self) -> None:
        api = MagicMock()
        api.list_budgets.return_value = [_task_item()]
        view = _view(api_client=api)
        asyncio.run(view._load_budgets())

        texts = _texts(view._budget_items)
        assert "Задача" in texts
        assert "100.00 USDT" in texts
        assert "05.10.2026" in texts

    def test_calendar_badge_label(self) -> None:
        api = MagicMock()
        api.list_budgets.return_value = [
            {
                "source_app": "calendar",
                "source_id": 2,
                "title": "Cinema",
                "amount": "50.0000",
                "currency": "USDT",
                "date": "2026-10-06",
            }
        ]
        view = _view(api_client=api)
        asyncio.run(view._load_budgets())
        assert "Событие" in _texts(view._budget_items)

    def test_accepts_dict_results_payload(self) -> None:
        api = MagicMock()
        api.list_budgets.return_value = {"results": [_task_item()]}
        view = _view(api_client=api)
        asyncio.run(view._load_budgets())
        assert len(view._budget_items.controls) == 1

    def test_empty_response_hides_section(self) -> None:
        api = MagicMock()
        api.list_budgets.return_value = []
        view = _view(api_client=api)
        asyncio.run(view._load_budgets())
        assert view._budget_section.visible is False
        assert view._budget_hint.visible is False
        assert view._budget_items.controls == []

    def test_unexpected_payload_hides_section(self) -> None:
        api = MagicMock()
        api.list_budgets.return_value = MagicMock()
        view = _view(api_client=api)
        asyncio.run(view._load_budgets())
        assert view._budget_section.visible is False


class TestBudgetsSectionOffline:
    def test_offline_skips_request_and_shows_hint(self) -> None:
        api = MagicMock()
        view = _view(api_client=api, is_online=False)
        asyncio.run(view._load_budgets())

        api.list_budgets.assert_not_called()
        assert view._budgets == []
        assert view._budget_items.controls == []
        assert view._budget_section.visible is True
        assert view._budget_hint.visible is True
        assert "Нет подключения" in view._budget_hint.value

    def test_offline_does_not_raise_and_keeps_main_state(self) -> None:
        view = _view(is_online=False)
        asyncio.run(view._load_data())
        assert view._loading.visible is False
        assert view._budget_hint.visible is True
        assert view._error_text.visible is False


class TestBudgetsSectionErrors:
    def test_backend_unreachable_shows_muted_hint(self) -> None:
        api = MagicMock()
        api.list_budgets.side_effect = BackendUnreachableError("connection refused")
        view = _view(api_client=api)
        asyncio.run(view._load_budgets())

        assert view._budgets == []
        assert view._budget_items.controls == []
        assert view._budget_section.visible is True
        assert view._budget_hint.visible is True
        assert "Не удалось загрузить" in view._budget_hint.value

    def test_api_error_shows_muted_hint(self) -> None:
        api = MagicMock()
        api.list_budgets.side_effect = ApiError(500, "server error")
        view = _view(api_client=api)
        asyncio.run(view._load_budgets())

        assert view._budget_section.visible is True
        assert view._budget_hint.visible is True
        assert view._budget_items.controls == []

    def test_error_does_not_break_main_view(self) -> None:
        api = MagicMock()
        api.list_budgets.side_effect = BackendUnreachableError("down")
        view = _view(api_client=api)
        asyncio.run(view._load_data())

        assert view._loading.visible is False
        assert view._error_text.visible is False
        assert view._budget_hint.visible is True


class TestBudgetsSectionRefresh:
    def test_reload_replaces_previous_cards(self) -> None:
        api = MagicMock()
        api.list_budgets.return_value = [_task_item()]
        view = _view(api_client=api)
        asyncio.run(view._load_budgets())
        assert len(view._budget_items.controls) == 1

        api.list_budgets.side_effect = BackendUnreachableError("down")
        api.list_budgets.return_value = None
        asyncio.run(view._load_budgets())
        assert view._budget_items.controls == []
        assert view._budget_hint.visible is True
