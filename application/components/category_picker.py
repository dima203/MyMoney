"""Выбор категории из серверного словаря с созданием/переименованием/архивацией (2.53)."""

from __future__ import annotations

import asyncio

import flet as ft

DEFAULT_CATEGORIES = [
    "Еда",
    "Транспорт",
    "Жильё",
    "Развлечения",
    "Здоровье",
    "Образование",
    "Зарплата",
    "Подработка",
    "Подарки",
    "Другое",
]


class CategoryPicker(ft.Container):
    """Dropdown категорий + создание, управление словарём и callback выбора.

    ``categories`` — активные названия; ``None`` — встроенный список (legacy).
    ``rows`` — полный словарь с ``id``/``is_archived``; при передаче появляется
    кнопка управления (переименование и архивация).
    """

    def __init__(
        self,
        value: str = "",
        categories: list[str] | None = None,
        *,
        rows: list[dict] | None = None,
        on_create=None,
        on_rename=None,
        on_archive=None,
    ) -> None:
        super().__init__()
        self._categories = self._normalize(DEFAULT_CATEGORIES if categories is None else categories)
        self._rows = [row for row in rows or [] if isinstance(row, dict)]
        self._on_change = None
        self._on_create = on_create
        self._on_rename = on_rename
        self._on_archive = on_archive

        self._dropdown = ft.Dropdown(
            label="Категория",
            options=[ft.dropdown.Option(cat) for cat in self._categories],
            value=self._match(value),
            border=ft.OutlineInputBorder(border_radius=8),
            autofocus=False,
            on_select=self._handle_change,
            expand=True,
        )
        controls: list[ft.Control] = [
            self._dropdown,
            ft.IconButton(
                icon=ft.Icons.ADD,
                icon_size=18,
                tooltip="Добавить категорию",
                on_click=self._show_add_dialog,
            ),
        ]
        if rows is not None:
            controls.append(
                ft.IconButton(
                    icon=ft.Icons.TUNE,
                    icon_size=18,
                    tooltip="Словарь категорий",
                    on_click=self._show_manager_dialog,
                )
            )
        self.content = ft.Row(controls=controls, vertical_alignment=ft.CrossAxisAlignment.CENTER)

    # ------------------------------------------------------------------ состояние

    @staticmethod
    def _normalize(names) -> list[str]:
        result: list[str] = []
        seen: set[str] = set()
        for raw in names or []:
            name = str(raw or "").strip()
            if not name or name.casefold() in seen:
                continue
            seen.add(name.casefold())
            result.append(name)
        return result

    @property
    def categories(self) -> list[str]:
        return list(self._categories)

    def _sync_options(self) -> None:
        """Перестроить опции dropdown по текущему списку категорий."""
        self._dropdown.options = [ft.dropdown.Option(cat) for cat in self._categories]

    @property
    def rows(self) -> list[dict]:
        return self._rows

    def add_category(self, name: str) -> None:
        """Добавить категорию в список и выбрать её."""
        clean = str(name or "").strip()
        if not clean:
            return
        folded = clean.casefold()
        existing = next((cat for cat in self._categories if cat.casefold() == folded), None)
        canonical = existing or clean
        if existing is None:
            self._categories.append(canonical)
            self._sync_options()
        self._dropdown.value = canonical
        self._safe_update(self._dropdown)
        self.update()

    def remove_category(self, name: str) -> None:
        """Убрать категорию из списка (архивация); выбор сбрасывается, если совпал."""
        folded = str(name or "").strip().casefold()
        self._categories = [cat for cat in self._categories if cat.casefold() != folded]
        self._sync_options()
        if self._dropdown.value and self._dropdown.value.casefold() == folded:
            self._dropdown.value = None
        self._safe_update(self._dropdown)
        self.update()

    def rename_category(self, old: str, new: str) -> None:
        """Заменить название, сохранив выбор и порядок."""
        old_clean = str(old or "").strip()
        new_clean = str(new or "").strip()
        if not old_clean or not new_clean:
            return
        self._categories = [new_clean if cat == old_clean else cat for cat in self._categories]
        self._sync_options()
        if self._dropdown.value == old_clean:
            self._dropdown.value = new_clean
        self._safe_update(self._dropdown)
        self.update()

    def _match(self, value) -> str | None:
        """Каноническое написание значения: точное или без учёта регистра."""
        folded = str(value or "").strip().casefold()
        if not folded:
            return None
        return next((cat for cat in self._categories if cat.casefold() == folded), None)

    def _handle_change(self, e):
        if self._on_change:
            self._on_change(e.control.value)

    def set_on_change(self, callback):
        self._on_change = callback

    @property
    def value(self) -> str:
        return self._dropdown.value or ""

    @value.setter
    def value(self, val: str):
        self._dropdown.value = self._match(val)
        self._safe_update(self._dropdown)

    # ------------------------------------------------------------------ диалоги

    def _show_add_dialog(self, e):
        field = ft.TextField(
            label="Новая категория",
            border=ft.OutlineInputBorder(border_radius=8),
            autofocus=True,
        )
        error = ft.Text("", size=12, color=ft.Colors.ERROR, visible=False)

        async def submit(name: str) -> None:
            if not name:
                self._dialog_error(error, "Введите название")
                return
            if self._on_create is None:
                self.add_category(name)
            else:
                created = await self._invoke(self._on_create, name)
                if not created:
                    self._dialog_error(error, "Не удалось создать категорию")
                    return
                self.add_category(str(created))
            self._close_dialog()
            self._safe_update(self._dropdown)

        self._show_name_dialog("Новая категория", "Добавить", field, error, submit)

    def _show_manager_dialog(self, e):
        page = self._get_page()
        items = ft.Column(spacing=2, scroll=ft.ScrollMode.AUTO, height=320)

        def rebuild() -> None:
            items.controls.clear()
            for row in self._rows:
                items.controls.append(self._manager_row(row, rebuild))
            if not self._rows:
                items.controls.append(
                    ft.Text("Словарь пуст — добавьте категорию через +", size=13, color=ft.Colors.ON_SURFACE_VARIANT)
                )
            self._safe_update(items)

        dialog = ft.AlertDialog(
            title=ft.Text("Словарь категорий"),
            content=items,
            actions=[ft.TextButton("Закрыть", on_click=lambda _: self._close_dialog())],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        rebuild()
        if page:
            page.show_dialog(dialog)

    def _manager_row(self, row: dict, rebuild) -> ft.Control:
        name = str(row.get("name") or "")
        archived = bool(row.get("is_archived"))
        actions = [
            ft.IconButton(
                icon=ft.Icons.EDIT_OUTLINED,
                icon_size=18,
                tooltip="Переименовать",
                on_click=lambda _event, value=name: self._show_rename_dialog(value, rebuild),
            )
        ]
        if self._on_archive is not None:
            actions.append(
                ft.IconButton(
                    icon=ft.Icons.UNARCHIVE if archived else ft.Icons.ARCHIVE_OUTLINED,
                    icon_size=18,
                    tooltip="Вернуть из архива" if archived else "В архив",
                    on_click=lambda _event, value=name, flag=archived: self._run_task(
                        self._toggle_archive, value, not flag, rebuild
                    ),
                )
            )
        return ft.Row(
            controls=[
                ft.Text(name, expand=True, color=ft.Colors.ON_SURFACE_VARIANT if archived else None),
                *actions,
            ],
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )

    def _show_rename_dialog(self, name: str, rebuild) -> None:
        field = ft.TextField(label="Название", value=name, autofocus=True)
        error = ft.Text("", size=12, color=ft.Colors.ERROR, visible=False)

        async def submit(new_name: str) -> None:
            if not new_name or new_name == name:
                self._close_dialog()
                return
            if self._on_rename is None:
                self.rename_category(name, new_name)
            else:
                renamed = await self._invoke(self._on_rename, name, new_name)
                if not renamed:
                    self._dialog_error(error, "Не удалось переименовать")
                    return
                self.rename_category(name, str(renamed))
            self._close_dialog()
            rebuild()

        self._show_name_dialog("Переименовать категорию", "Сохранить", field, error, submit)

    def _show_name_dialog(self, title: str, confirm: str, field: ft.TextField, error: ft.Text, on_submit) -> None:
        """Оболочка диалога ввода названия: поле, строка ошибки и кнопки."""
        page = self._get_page()

        async def submit(_event):
            await on_submit(field.value.strip() if field.value else "")

        dialog = ft.AlertDialog(
            title=ft.Text(title),
            content=ft.Column([field, error], spacing=8, tight=True),
            actions=[
                ft.TextButton("Отмена", on_click=lambda _: self._close_dialog()),
                ft.Button(confirm, on_click=submit),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        if page:
            page.show_dialog(dialog)

    async def _toggle_archive(self, name: str, archived: bool, rebuild) -> None:
        if self._on_archive is not None and not await self._invoke(self._on_archive, name, archived):
            return
        for row in self._rows:
            if str(row.get("name") or "") == name:
                row["is_archived"] = archived
        if archived:
            self.remove_category(name)
        else:
            self.add_category(name)
        rebuild()

    # ------------------------------------------------------------------ утилиты

    def _close_dialog(self) -> None:
        page = self._get_page()
        if page:
            page.pop_dialog()

    def _dialog_error(self, error: ft.Text, message: str) -> None:
        """Показать ошибку валидации внутри открытого диалога."""
        error.value = message
        error.visible = True
        page = self._get_page()
        if page:
            page.update()

    @staticmethod
    async def _invoke(callback, *args):
        if callback is None:
            return None
        result = callback(*args)
        if asyncio.iscoroutine(result):
            result = await result
        return result

    def _run_task(self, handler, *args) -> None:
        page = self._get_page()
        if page is not None:
            page.run_task(handler, *args)

    @staticmethod
    def _safe_update(control) -> None:
        try:
            control.update()
        except RuntimeError:
            pass

    def _get_page(self):
        try:
            return self.page
        except RuntimeError:
            return None


__all__ = ["DEFAULT_CATEGORIES", "CategoryPicker"]
