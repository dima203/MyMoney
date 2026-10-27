"""Тесты экрана «Бюджеты» MyMoney (B-13): конверты, цели и шаблоны."""

from __future__ import annotations

import asyncio
import datetime
from typing import ClassVar
from unittest.mock import AsyncMock, MagicMock

import flet as ft
from application.api import BackendUnreachableError
from application.view.budgets_view import (
    ENVELOPES_EMPTY,
    ENVELOPES_OFFLINE,
    GOALS_EMPTY,
    GOALS_OFFLINE,
    TEMPLATES_APPLY,
    TEMPLATES_BUTTON,
    TEMPLATES_DELETE,
    TEMPLATES_EMPTY,
    TEMPLATES_SAVED,
    TEMPLATES_TITLE,
    BudgetsView,
    limit_text,
)
from core.goals import goal_progress

TODAY = datetime.date(2026, 10, 22)
ACCOUNTS = [{"id": 1, "resource": "BYN"}, {"id": 2, "resource": "USD"}]


def _walk(control) -> list:
    found = [control]
    for child in getattr(control, "controls", None) or []:
        found.extend(_walk(child))
    content = getattr(control, "content", None)
    if content is not None and not isinstance(content, str):
        found.extend(_walk(content))
    return found


def _texts(control) -> list[str]:
    return [str(item.value) for item in _walk(control) if isinstance(item, ft.Text)]


def _of_type(control, kind) -> list:
    """Вложенные контролы указанного типа (включая сам control)."""
    return [item for item in _walk(control) if isinstance(item, kind)]


def _entry(account: int, amount: float) -> dict:
    return {"account": account, "amount": amount, "quantity": amount, "unit_price": 1}


def _rows() -> list[dict]:
    return [
        {"date": "2026-10-05T10:00:00", "category": "Еда", "entries": [_entry(1, -100)]},
        {"date": "2026-10-12T10:00:00", "category": "Еда", "entries": [_entry(1, -50)]},
        {"date": "2026-08-01T10:00:00", "category": "Жильё", "entries": [_entry(1, -500)]},
        {"date": "2026-09-20T10:00:00", "category": "Транспорт", "entries": [_entry(1, -30)]},
    ]


def _api(me=None) -> MagicMock:
    api = MagicMock()
    api.me.return_value = {"base_currency": "BYN"} if me is None else me
    api.list_envelopes.return_value = []
    api.list_goals.return_value = []
    return api


def _ready(view: BudgetsView) -> BudgetsView:
    """Фиксирует «сегодня» и отвязывает update от живой Flet-страницы."""
    view._today = lambda: TODAY
    view.update = MagicMock()
    return view


def _view(rows=None, accounts=None, is_online=True, me=None, envelopes=None, goals=None) -> BudgetsView:
    api = _api(me)
    if envelopes is not None:
        api.list_envelopes.return_value = envelopes
    if goals is not None:
        api.list_goals.return_value = goals
    transaction_view = MagicMock()
    transaction_view.is_online = is_online
    transaction_view.get_all.return_value = _rows() if rows is None else rows
    account_view = MagicMock()
    account_view.get_all.return_value = ACCOUNTS if accounts is None else accounts
    return _ready(
        BudgetsView(
            route="/budgets",
            api_client=api,
            transaction_view=transaction_view,
            account_view=account_view,
        )
    )


def _loaded_view(monkeypatch, *, envelopes=None) -> tuple[BudgetsView, MagicMock]:
    """Загруженный экран с подменённым page: диалоги и тосты не требуют живой Flet-страницы."""
    view = _view(envelopes=envelopes)
    asyncio.run(view._load_data())
    page = MagicMock()
    monkeypatch.setattr(type(view), "page", property(lambda _self: page))
    return view, page


def _envelope(**overrides) -> dict:
    row = {"id": 1, "category": "Еда", "limit_amount": "100.0000", "currency_ticker": "BYN", "currency": None}
    row.update(overrides)
    return row


def _goal(**overrides) -> dict:
    row = {
        "id": 1,
        "name": "Отпуск",
        "target_amount": "3000.0000",
        "saved_amount": "1200.0000",
        "currency_ticker": "BYN",
        "currency": None,
        "deadline": "2027-06-01",
    }
    row.update(overrides)
    return row


class TestViewShell:
    """2.23: «Бюджеты» — отдельный раздел навигации, аналитика осталась про расходы."""

    def test_title_route_and_nav_index(self) -> None:
        view = _view()

        assert view.title == "Бюджеты"
        assert view.route == "/budgets"
        assert view.selected_index == 3

    def test_loads_without_analytics_charts(self) -> None:
        view = _view()

        asyncio.run(view._load_data())

        assert view._loading.visible is False
        assert not [item for item in _walk(view._body) if isinstance(item, ft.ProgressBar) and item.height == 6]

    def test_navigation_has_budgets_between_plan_and_analytics(self) -> None:
        labels = [item.label for item in view_navigation_items()]

        assert labels == ["Счета", "Транзакции", "План", "Бюджеты", "Аналитика", "Настройки"]


def view_navigation_items():
    from application.components.navigation_items import NAVIGATION_ITEMS

    return NAVIGATION_ITEMS


class TestFormatting:
    def test_limit_text_strips_trailing_zeros(self) -> None:
        assert limit_text("500.0000") == "500"
        assert limit_text("650.50") == "650.5"
        assert limit_text(0) == "0"
        assert limit_text(None) == ""
        assert limit_text("oops") == ""


class TestEnvelopesSection:
    def test_renders_progress_and_overspending(self) -> None:
        view = _view(envelopes=[_envelope()])

        asyncio.run(view._load_data())

        texts = _texts(view._content)
        assert "Конверты месяца" in texts
        assert "150.00 BYN из 100.00 BYN" in texts
        assert "Превышение на 50.00 BYN" in texts
        bars = [item for item in _walk(view._body) if isinstance(item, ft.ProgressBar)]
        assert any(bar.color == ft.Colors.ERROR and bar.value == 1.0 for bar in bars)

    def test_renders_envelope_within_limit(self) -> None:
        view = _view(envelopes=[_envelope(limit_amount="300")])

        asyncio.run(view._load_data())

        texts = _texts(view._content)
        assert "150.00 BYN из 300.00 BYN" in texts
        assert not [text for text in texts if text.startswith("Превышение")]
        bars = [item for item in _walk(view._body) if isinstance(item, ft.ProgressBar)]
        assert any(bar.color == ft.Colors.PRIMARY and bar.value == 0.5 for bar in bars)

    def test_empty_state_has_add_button(self) -> None:
        view = _view()

        asyncio.run(view._load_data())

        texts = _texts(view._content)
        assert ENVELOPES_EMPTY in texts
        buttons = [item for item in _walk(view._body) if isinstance(item, ft.TextButton)]
        assert any(button.content == "Добавить" for button in buttons)

    def test_offline_shows_hint_without_request(self) -> None:
        view = _view(is_online=False)

        asyncio.run(view._load_data())

        assert ENVELOPES_OFFLINE in _texts(view._content)
        view.api_client.list_envelopes.assert_not_called()

    def test_backend_error_keeps_other_sections_alive(self) -> None:
        view = _view()
        view.api_client.list_envelopes.side_effect = BackendUnreachableError("down")

        asyncio.run(view._load_data())

        texts = _texts(view._content)
        assert ENVELOPES_OFFLINE in texts
        assert GOALS_EMPTY in texts
        assert view._error_text.visible is False

    def test_currency_options_map_resource_ids(self) -> None:
        accounts = [
            {"id": 1, "resource": "BYN", "resource_definition": 11},
            {"id": 2, "resource": "USD", "resource_definition": 12},
            {"id": 3, "resource": "BYN", "resource_definition": 11},
            {"id": 4, "resource": "EUR"},
        ]
        view = _view(accounts=accounts)

        asyncio.run(view._load_data())

        assert view._currency_options() == {"BYN": 11, "USD": 12, "EUR": None}

    def test_paginated_envelopes_payload(self) -> None:
        view = _view(envelopes={"results": [_envelope()]})

        asyncio.run(view._load_data())

        assert "150.00 BYN из 100.00 BYN" in _texts(view._content)


class TestEnvelopeDialog:
    def test_edit_dialog_prefilled_and_stretched(self) -> None:
        view = _view()
        view._envelopes = [_envelope(limit_amount="300.0000")]

        dialog = view._envelope_dialog(view._envelopes[0])

        assert dialog.title.value == "Изменить конверт"
        fields = dialog.content.content.controls
        assert [field.value for field in fields[:3]] == ["Еда", "300", "BYN"]
        assert dialog.content.content.horizontal_alignment == ft.CrossAxisAlignment.STRETCH
        assert fields[0].autofocus is True

    def test_new_dialog_defaults(self) -> None:
        view = _view()
        asyncio.run(view._load_data())

        dialog = view._envelope_dialog({})

        assert dialog.title.value == "Новый конверт"
        fields = dialog.content.content.controls
        assert fields[0].value == ""
        assert fields[1].value == ""
        assert fields[2].value == "BYN"
        assert [field.text for field in fields[2].options] == ["BYN", "USD"]
        assert dialog.actions[1].content == "Сохранить"


class TestGoalsSection:
    def test_renders_progress_and_remaining(self) -> None:
        view = _view(goals=[_goal()])

        asyncio.run(view._load_data())

        texts = _texts(view._content)
        assert "Цели накоплений" in texts
        assert "1 200.00 BYN из 3 000.00 BYN" in texts
        assert "Осталось 1 800.00 BYN" in texts
        assert "до 01.06.2027 · 222 дн." in texts
        bars = [item for item in _walk(view._body) if isinstance(item, ft.ProgressBar)]
        assert any(bar.value == 0.4 and bar.color == ft.Colors.PRIMARY for bar in bars)

    def test_reached_goal(self) -> None:
        view = _view(goals=[_goal(saved_amount="3500.0000")])

        asyncio.run(view._load_data())

        texts = _texts(view._content)
        assert "Цель достигнута" in texts
        assert not [text for text in texts if text.startswith("Осталось")]
        bars = [item for item in _walk(view._body) if isinstance(item, ft.ProgressBar)]
        assert any(bar.value == 1.0 and bar.color == ft.Colors.TERTIARY for bar in bars)

    def test_overdue_goal_is_marked(self) -> None:
        view = _view(goals=[_goal(deadline="2026-01-01")])

        asyncio.run(view._load_data())

        assert "до 01.01.2026 · срок истёк" in _texts(view._content)

    def test_no_deadline_has_no_caption(self) -> None:
        view = _view(goals=[_goal(deadline=None)])

        asyncio.run(view._load_data())

        texts = _texts(view._content)
        assert "Осталось 1 800.00 BYN" in texts
        assert not [text for text in texts if text.startswith("до ")]

    def test_empty_state_has_add_button(self) -> None:
        view = _view()

        asyncio.run(view._load_data())

        texts = _texts(view._content)
        assert GOALS_EMPTY in texts
        buttons = [item for item in _walk(view._body) if isinstance(item, ft.TextButton)]
        assert sum(1 for button in buttons if button.content == "Добавить") == 2

    def test_offline_shows_hint_without_request(self) -> None:
        view = _view(is_online=False)

        asyncio.run(view._load_data())

        assert GOALS_OFFLINE in _texts(view._content)
        view.api_client.list_goals.assert_not_called()

    def test_backend_error_keeps_other_sections_alive(self) -> None:
        view = _view()
        view.api_client.list_goals.side_effect = BackendUnreachableError("down")

        asyncio.run(view._load_data())

        texts = _texts(view._content)
        assert GOALS_OFFLINE in texts
        assert ENVELOPES_EMPTY in texts
        assert view._error_text.visible is False

    def test_paginated_goals_payload(self) -> None:
        view = _view(goals={"results": [_goal()]})

        asyncio.run(view._load_data())

        assert "1 200.00 BYN из 3 000.00 BYN" in _texts(view._content)


class TestTemplates:
    MINE: ClassVar[list[dict]] = [
        {"id": 1, "name": "Мой", "items": [{"category": "Еда"}], "is_public": False, "currency_ticker": "BYN"},
    ]
    PUBLIC: ClassVar[list[dict]] = [
        {"id": 2, "name": "Публичный", "items": [{"category": "Еда"}, {"category": "Кафе"}], "is_public": True},
    ]

    def test_templates_button_in_section(self) -> None:
        view = _view()

        asyncio.run(view._load_data())

        assert TEMPLATES_BUTTON in [button.content for button in _of_type(view._body, ft.TextButton)]

    def test_dialog_lists_mine_and_public(self) -> None:
        view = _view()

        dialog = view._templates_dialog(self.MINE, self.PUBLIC)

        texts = _texts(dialog)
        assert dialog.title.value == TEMPLATES_TITLE
        assert "Мой" in texts
        assert "Публичный" in texts
        assert "2 категорий · публичный" in texts
        assert [button.content for button in _of_type(dialog, ft.TextButton)].count(TEMPLATES_APPLY) == 2

    def test_own_tile_has_delete_public_does_not(self) -> None:
        view = _view()

        dialog = view._templates_dialog(self.MINE, self.PUBLIC)

        delete_buttons = [button for button in _of_type(dialog, ft.IconButton) if button.tooltip == TEMPLATES_DELETE]
        assert len(delete_buttons) == 1

    def test_empty_state(self) -> None:
        view = _view()

        dialog = view._templates_dialog([], [])

        assert TEMPLATES_EMPTY in _texts(dialog)

    def test_save_template_uses_current_envelopes(self, monkeypatch) -> None:
        view, page = _loaded_view(monkeypatch, envelopes=[_envelope()])
        toast = MagicMock()
        monkeypatch.setattr("application.view.budgets_view.show_toast", toast)

        dialog = view._templates_dialog([], [])
        name_field, public_switch = dialog.content.content.controls[:2]
        name_field.value = "Базовый"
        public_switch.value = True

        asyncio.run(_of_type(dialog, ft.Button)[0].on_click(None))

        view.api_client.create_budget_template.assert_called_once()
        payload = view.api_client.create_budget_template.call_args.args[0]
        assert payload["name"] == "Базовый"
        assert payload["items"] == [{"category": "Еда", "limit_amount": "100.0000"}]
        assert payload["is_public"] is True
        page.pop_dialog.assert_called_once()
        toast.assert_called_once_with(page, TEMPLATES_SAVED)

    def test_save_without_envelopes_shows_error(self, monkeypatch) -> None:
        view, page = _loaded_view(monkeypatch)

        dialog = view._templates_dialog([], [])
        dialog.content.content.controls[0].value = "Пустой"

        asyncio.run(_of_type(dialog, ft.Button)[0].on_click(None))

        error_text = dialog.content.content.controls[2]
        assert error_text.visible is True
        assert "Нет конвертов" in error_text.value
        view.api_client.create_budget_template.assert_not_called()
        assert page.update.called

    def test_apply_template_reports_counts(self, monkeypatch) -> None:
        view, page = _loaded_view(monkeypatch)
        toast = MagicMock()
        monkeypatch.setattr("application.view.budgets_view.show_toast", toast)
        reload_mock = AsyncMock()
        monkeypatch.setattr(view, "_reload_envelopes", reload_mock)
        view.api_client.apply_budget_template.return_value = {"created": 2, "skipped": 1}

        asyncio.run(view._apply_template(2))

        view.api_client.apply_budget_template.assert_called_once_with(2)
        page.pop_dialog.assert_called_once()
        assert "Создано конвертов: 2, пропущено: 1" in toast.call_args.args[1]
        reload_mock.assert_awaited_once()

    def test_delete_template_reopens_dialog(self, monkeypatch) -> None:
        view, page = _loaded_view(monkeypatch)
        reopened = AsyncMock()
        monkeypatch.setattr(view, "_open_templates", reopened)

        asyncio.run(view._delete_template(1))

        view.api_client.delete_budget_template.assert_called_once_with(1)
        page.pop_dialog.assert_called_once()
        reopened.assert_awaited_once()


class TestGoalDialogs:
    def test_edit_dialog_prefilled(self) -> None:
        view = _view()
        asyncio.run(view._load_data())
        goal = _goal()

        dialog = view._goal_dialog(goal)

        assert dialog.title.value == "Изменить цель"
        fields = dialog.content.content.controls
        assert [field.value for field in fields[:5]] == ["Отпуск", "3000", "1200", "2027-06-01", "BYN"]
        assert dialog.content.content.horizontal_alignment == ft.CrossAxisAlignment.STRETCH
        assert fields[0].autofocus is True

    def test_new_dialog_defaults(self) -> None:
        view = _view()
        asyncio.run(view._load_data())

        dialog = view._goal_dialog({})

        assert dialog.title.value == "Новая цель"
        fields = dialog.content.content.controls
        assert [field.value for field in fields[:4]] == ["", "", "", ""]
        assert fields[4].value == "BYN"
        assert dialog.actions[1].content == "Сохранить"

    def test_contribution_dialog(self) -> None:
        view = _view()
        goal = _goal()

        dialog = view._contribution_dialog(goal)

        assert dialog.title.value == "Пополнить «Отпуск»"
        fields = dialog.content.content.controls
        assert fields[0].label == "Сумма пополнения"
        assert fields[0].autofocus is True
        assert dialog.actions[1].content == "Пополнить"

    def test_goal_card_actions(self) -> None:
        view = _view()
        progress = goal_progress([_goal()])[0]

        card = view._goal_card(progress, None)

        buttons = [item for item in _walk(card) if isinstance(item, ft.IconButton)]
        assert [button.tooltip for button in buttons] == [
            "Пополнить цель",
            "Изменить цель",
            "Удалить цель",
        ]
