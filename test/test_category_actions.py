"""Словарь категорий в экранах MyMoney: загрузка, CRUD и автоподстановка (2.53)."""

import asyncio
from unittest.mock import MagicMock

import flet as ft
from application.api import ApiError
from application.components.category_picker import CategoryPicker
from application.view.planned_view import PlannedView
from application.view.transactions_view import TransactionsView

ROWS = [
    {"id": 1, "name": "Еда", "is_archived": False},
    {"id": 2, "name": "Транспорт", "is_archived": False},
    {"id": 3, "name": "Старая", "is_archived": True},
]
TAXI = {"id": 10, "description": "Такси", "category": "Транспорт", "is_planned": False, "entries": []}


def _mocks(rows=None, transactions=None):
    """Заглушки слоёв данных: список, счета и клиент со словарём категорий."""
    transaction_view = MagicMock()
    transaction_view.is_online = True
    transaction_view.get_all.return_value = list(transactions or [])
    account_view = MagicMock()
    account_view.is_online = True
    account_view.get_all.return_value = [{"id": 1, "name": "Основной", "resource": "BYN"}]
    api_client = MagicMock()
    api_client.list_categories.return_value = list(rows or [])
    api_client.list_budgets.return_value = []
    return api_client, transaction_view, account_view


def _view(rows=None, transactions=None):
    api_client, transaction_view, account_view = _mocks(rows, transactions)
    view = TransactionsView(
        route="/transactions",
        api_client=api_client,
        transaction_view=transaction_view,
        account_view=account_view,
    )
    view._category_rows = [dict(row) for row in rows or []]
    view.update = MagicMock()
    return view


def _walk(control):
    yield control
    content = getattr(control, "content", None)
    if content is not None:
        yield from _walk(content)
    for child in getattr(control, "controls", None) or []:
        yield from _walk(child)


def _open_dialog(view, monkeypatch):
    page = MagicMock()
    monkeypatch.setattr(type(view), "page", property(lambda self: page))
    view._open_transaction_dialog()
    return page.show_dialog.call_args.args[0]


class TestLoadCategories:
    def test_loads_rows_from_api(self):
        view = _view(ROWS)

        asyncio.run(view._load_sections())

        assert [row["name"] for row in view._category_rows] == ["Еда", "Транспорт", "Старая"]

    def test_api_failure_keeps_empty_dictionary(self):
        view = _view()
        view.api_client.list_categories.side_effect = ApiError(500, "boom")

        asyncio.run(view._load_sections())

        assert view._category_rows == []

    def test_non_list_response_ignored(self):
        view = _view()
        view.api_client.list_categories.return_value = {"results": ROWS}

        asyncio.run(view._load_sections())

        assert view._category_rows == []


class TestPickerCategories:
    def test_only_active_categories(self):
        view = _view(ROWS)

        assert view._picker_categories() == ["Еда", "Транспорт"]

    def test_unknown_current_value_is_kept(self):
        view = _view(ROWS)

        assert view._picker_categories("Ручная строка") == ["Ручная строка", "Еда", "Транспорт"]

    def test_current_value_not_duplicated(self):
        view = _view(ROWS)

        assert view._picker_categories("еда") == ["Еда", "Транспорт"]

    def test_no_dictionary_returns_none_for_defaults(self):
        view = _view()

        assert view._picker_categories() is None

    def test_all_archived_returns_empty_list(self):
        view = _view([ROWS[2]])

        assert view._picker_categories() == []


class TestCategoryCrud:
    def test_create_returns_canonical_name(self):
        view = _view()
        view.api_client.create_category.return_value = {"id": 4, "name": "Транспорт"}
        view.api_client.list_categories.return_value = [{"id": 4, "name": "Транспорт"}]

        created = asyncio.run(view._create_category("транспорт"))

        assert created == "Транспорт"
        view.api_client.create_category.assert_called_once_with({"name": "транспорт"})
        assert view._category_rows == [{"id": 4, "name": "Транспорт"}]

    def test_create_failure_shows_error(self):
        view = _view()
        view.api_client.create_category.side_effect = ApiError(500, "boom")

        created = asyncio.run(view._create_category("Транспорт"))

        assert created is None
        assert view._error_text.visible is True
        assert "Не удалось создать категорию" in view._error_text.value

    def test_rename_calls_api_with_id(self):
        view = _view(ROWS)
        view.api_client.update_category.return_value = {"id": 1, "name": "Питание"}
        view.api_client.list_categories.return_value = [{"id": 1, "name": "Питание"}]

        renamed = asyncio.run(view._rename_category("Еда", "Питание"))

        assert renamed == "Питание"
        view.api_client.update_category.assert_called_once_with(1, {"name": "Питание"})

    def test_rename_unknown_category_shows_error(self):
        view = _view(ROWS)

        renamed = asyncio.run(view._rename_category("Нет такой", "Новая"))

        assert renamed is None
        assert "не найдена" in view._error_text.value

    def test_archive_calls_patch(self):
        view = _view(ROWS)
        view.api_client.update_category.return_value = {"id": 2, "name": "Транспорт", "is_archived": True}

        result = asyncio.run(view._archive_category("Транспорт", True))

        assert result["is_archived"] is True
        view.api_client.update_category.assert_called_once_with(2, {"is_archived": True})


class TestDialogWiring:
    def test_dialog_picker_uses_dictionary(self, monkeypatch):
        view = _view(ROWS, [TAXI])
        asyncio.run(view._load_data())

        dialog = _open_dialog(view, monkeypatch)
        pickers = [control for control in _walk(dialog) if isinstance(control, CategoryPicker)]

        assert len(pickers) == 1
        assert pickers[0].categories == ["Еда", "Транспорт"]
        assert pickers[0].rows == ROWS

    def test_dialog_picker_falls_back_to_defaults(self, monkeypatch):
        view = _view()
        asyncio.run(view._load_data())

        dialog = _open_dialog(view, monkeypatch)
        picker = next(control for control in _walk(dialog) if isinstance(control, CategoryPicker))

        assert picker.rows == []
        assert len(picker.categories) > 1

    def test_description_autofills_category(self, monkeypatch):
        view = _view(ROWS, [TAXI])
        asyncio.run(view._load_data())

        dialog = _open_dialog(view, monkeypatch)
        controls = list(_walk(dialog))
        picker = next(control for control in controls if isinstance(control, CategoryPicker))
        description = next(
            control for control in controls if isinstance(control, ft.TextField) and control.label == "Описание"
        )

        description.value = "  такси "
        description.on_change(None)

        assert picker.value == "Транспорт"

    def test_autofill_ignores_categories_when_all_archived(self, monkeypatch):
        view = _view([ROWS[2]], [TAXI])
        asyncio.run(view._load_data())

        dialog = _open_dialog(view, monkeypatch)
        controls = list(_walk(dialog))
        picker = next(control for control in controls if isinstance(control, CategoryPicker))
        description = next(
            control for control in controls if isinstance(control, ft.TextField) and control.label == "Описание"
        )

        description.value = "Такси"
        description.on_change(None)

        assert picker.value == ""

    def test_autofill_does_not_override_selected_category(self, monkeypatch):
        view = _view(ROWS, [TAXI])
        asyncio.run(view._load_data())

        dialog = _open_dialog(view, monkeypatch)
        controls = list(_walk(dialog))
        picker = next(control for control in controls if isinstance(control, CategoryPicker))
        description = next(
            control for control in controls if isinstance(control, ft.TextField) and control.label == "Описание"
        )
        picker.value = "Еда"

        description.value = "Такси"
        description.on_change(None)

        assert picker.value == "Еда"


class TestPlannedViewCategories:
    def _view(self, rows):
        api_client, transaction_view, account_view = _mocks(rows)
        view = PlannedView(
            route="/planned",
            api_client=api_client,
            transaction_view=transaction_view,
            account_view=account_view,
        )
        view.update = MagicMock()
        return view

    def test_planned_dialog_uses_dictionary(self, monkeypatch):
        view = self._view(ROWS)
        asyncio.run(view._load_data())

        dialog = _open_dialog(view, monkeypatch)
        picker = next(control for control in _walk(dialog) if isinstance(control, CategoryPicker))

        assert picker.categories == ["Еда", "Транспорт"]
        assert picker.rows == ROWS
