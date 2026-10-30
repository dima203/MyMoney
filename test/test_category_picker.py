"""CategoryPicker: словарь, создание, переименование и архивация (2.53)."""

import asyncio
from unittest.mock import MagicMock

import flet as ft
from application.components.category_picker import DEFAULT_CATEGORIES, CategoryPicker

ROWS = [
    {"id": 1, "name": "Еда", "is_archived": False},
    {"id": 2, "name": "Транспорт", "is_archived": False},
    {"id": 3, "name": "Старая", "is_archived": True},
]


def _picker(**kwargs) -> CategoryPicker:
    picker = CategoryPicker(**kwargs)
    picker.update = MagicMock()
    return picker


class TestOptions:
    def test_defaults_when_categories_none(self):
        picker = _picker()

        assert picker.categories == DEFAULT_CATEGORIES

    def test_custom_categories_override_defaults(self):
        picker = _picker(categories=["Еда", "Транспорт"])

        assert picker.categories == ["Еда", "Транспорт"]

    def test_empty_list_is_kept(self):
        picker = _picker(categories=[])

        assert picker.categories == []

    def test_duplicates_and_blanks_removed_case_insensitively(self):
        picker = _picker(categories=["Еда", " еда ", "", "Транспорт"])

        assert picker.categories == ["Еда", "Транспорт"]

    def test_value_setter_keeps_known_value(self):
        picker = _picker(categories=["Еда"])

        picker.value = "Еда"

        assert picker.value == "Еда"

    def test_value_setter_clears_unknown_value(self):
        picker = _picker(categories=["Еда"])

        picker.value = "Неизвестная"

        assert picker.value == ""

    def test_value_setter_normalizes_case_to_dictionary_spelling(self):
        picker = _picker(categories=["Еда", "Транспорт"])

        picker.value = "еда"

        assert picker.value == "Еда"

    def test_initial_value_normalizes_case(self):
        picker = _picker(categories=["Еда"], value="ЕДА")

        assert picker.value == "Еда"

    def test_add_category_selects_new(self):
        picker = _picker(categories=["Еда"])

        picker.add_category("Транспорт")

        assert picker.categories == ["Еда", "Транспорт"]
        assert picker.value == "Транспорт"

    def test_add_existing_case_insensitive_keeps_spelling(self):
        picker = _picker(categories=["Еда"])

        picker.add_category("еда")

        assert picker.categories == ["Еда"]
        assert picker.value == "Еда"

    def test_remove_category_clears_selection(self):
        picker = _picker(categories=["Еда", "Транспорт"])
        picker.value = "Еда"

        picker.remove_category("еда")

        assert picker.categories == ["Транспорт"]
        assert picker.value == ""

    def test_remove_other_keeps_selection(self):
        picker = _picker(categories=["Еда", "Транспорт"])
        picker.value = "Транспорт"

        picker.remove_category("Еда")

        assert picker.value == "Транспорт"

    def test_rename_category_updates_selection(self):
        picker = _picker(categories=["Еда", "Транспорт"])
        picker.value = "Еда"

        picker.rename_category("Еда", "Питание")

        assert picker.categories == ["Питание", "Транспорт"]
        assert picker.value == "Питание"

    def test_rename_other_keeps_selection(self):
        picker = _picker(categories=["Еда", "Транспорт"])
        picker.value = "Транспорт"

        picker.rename_category("Еда", "Питание")

        assert picker.value == "Транспорт"


class TestInvoke:
    def test_sync_callback(self):
        assert asyncio.run(CategoryPicker._invoke(lambda name: name.upper(), "еда")) == "ЕДА"

    def test_async_callback(self):
        async def create(name):
            return name.strip()

        assert asyncio.run(CategoryPicker._invoke(create, "  Еда ")) == "Еда"

    def test_none_callback(self):
        assert asyncio.run(CategoryPicker._invoke(None)) is None


class TestAddDialog:
    def _page(self):
        return MagicMock()

    def _open(self, picker, page):
        picker._get_page = lambda: page
        picker._show_add_dialog(None)
        return page.show_dialog.call_args.args[0]

    def test_add_via_async_callback_selects_canonical_name(self):
        async def create(name):
            return "Транспорт"

        picker = _picker(categories=["Еда"], on_create=create)
        page = self._page()
        dialog = self._open(picker, page)
        field = dialog.content.controls[0]
        field.value = "транспорт"
        add_button = dialog.actions[1]

        asyncio.run(add_button.on_click(None))

        assert picker.value == "Транспорт"
        assert "Транспорт" in picker.categories
        page.pop_dialog.assert_called_once()

    def test_add_failure_keeps_dialog_open(self):
        async def create(_name):
            return None

        picker = _picker(categories=["Еда"], on_create=create)
        page = self._page()
        dialog = self._open(picker, page)
        dialog.content.controls[0].value = "Транспорт"
        error = dialog.content.controls[1]

        asyncio.run(dialog.actions[1].on_click(None))

        assert error.visible is True
        assert picker.categories == ["Еда"]
        page.pop_dialog.assert_not_called()

    def test_blank_name_shows_error(self):
        picker = _picker(categories=["Еда"])
        page = self._page()
        dialog = self._open(picker, page)
        dialog.content.controls[0].value = "   "

        asyncio.run(dialog.actions[1].on_click(None))

        assert dialog.content.controls[1].visible is True
        page.pop_dialog.assert_not_called()

    def test_add_without_callback_stays_local(self):
        picker = _picker(categories=["Еда"])
        page = self._page()
        dialog = self._open(picker, page)
        dialog.content.controls[0].value = "Транспорт"

        asyncio.run(dialog.actions[1].on_click(None))

        assert picker.value == "Транспорт"


class TestArchive:
    def test_toggle_archive_removes_category(self):
        archived_calls = []

        def archive(name, flag):
            archived_calls.append((name, flag))
            return {"name": name, "is_archived": flag}

        picker = _picker(categories=["Еда", "Транспорт"], rows=ROWS, on_archive=archive)
        picker.value = "Еда"

        asyncio.run(picker._toggle_archive("Еда", True, lambda: None))

        assert picker.categories == ["Транспорт"]
        assert picker.value == ""
        assert archived_calls == [("Еда", True)]

    def test_restore_returns_category(self):
        def archive(name, flag):
            return {"name": name, "is_archived": flag}

        picker = _picker(categories=["Еда"], rows=ROWS, on_archive=archive)

        asyncio.run(picker._toggle_archive("Старая", False, lambda: None))

        assert "Старая" in picker.categories

    def test_failed_archive_keeps_category(self):
        def archive(_name, _flag):
            return None

        picker = _picker(categories=["Еда"], rows=ROWS, on_archive=archive)

        asyncio.run(picker._toggle_archive("Еда", True, lambda: None))

        assert picker.categories == ["Еда"]


class TestManagerDialog:
    def test_rows_rendered_with_archive_state(self):
        picker = _picker(categories=["Еда", "Транспорт"], rows=ROWS)
        page = MagicMock()
        picker._get_page = lambda: page

        picker._show_manager_dialog(None)

        dialog = page.show_dialog.call_args.args[0]
        texts = [control.controls[0].value for control in dialog.content.controls]
        assert texts == ["Еда", "Транспорт", "Старая"]

    def test_manage_button_only_with_rows(self):
        without_rows = _picker(categories=["Еда"])
        with_rows = _picker(categories=["Еда"], rows=ROWS)

        assert len(without_rows.content.controls) == 2
        assert len(with_rows.content.controls) == 3
        assert isinstance(with_rows.content.controls[2], ft.IconButton)


class TestRunTask:
    def test_without_page_does_nothing(self):
        picker = _picker(categories=["Еда"])
        calls = []

        picker._run_task(calls.append, 1)

        assert calls == []

    def test_with_page_delegates(self):
        picker = _picker(categories=["Еда"])
        page = MagicMock()
        picker._get_page = lambda: page

        picker._run_task(MagicMock(), 1, 2)

        page.run_task.assert_called_once()
