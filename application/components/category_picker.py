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
    def __init__(self, value: str = "", categories: list[str] | None = None):
        super().__init__()
        self._categories = categories or DEFAULT_CATEGORIES
        self._on_change = None

        options = [ft.dropdown.Option(cat) for cat in self._categories]
        self._dropdown = ft.Dropdown(
            label="Категория",
            options=options,
            value=value if value in self._categories else None,
            border_radius=8,
            autofocus=False,
            on_select=self._handle_change,
            suffix=ft.IconButton(
                icon=ft.Icons.ADD,
                icon_size=18,
                tooltip="Добавить категорию",
                on_click=self._show_add_dialog,
            ),
        )
        self.content = self._dropdown

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
        self._dropdown.value = val if val in self._categories else None
        self.update()

    def _show_add_dialog(self, e):
        new_category_field = ft.TextField(
            label="Новая категория",
            border_radius=8,
            autofocus=True,
        )

        async def on_add(e):
            name = new_category_field.value.strip() if new_category_field.value else ""
            if name and name not in self._categories:
                self._categories.append(name)
                self._dropdown.options.append(ft.dropdown.Option(name))
                self._dropdown.value = name
                self.update()
                if self._on_change:
                    self._on_change(name)
            dialog.open = False
            self._dropdown.update()

        dialog = ft.AlertDialog(
            title=ft.Text("Новая категория"),
            content=new_category_field,
            actions=[
                ft.TextButton("Отмена", on_click=lambda _: self._close_dialog(dialog)),
                ft.ElevatedButton("Добавить", on_click=on_add),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )

        page = self._get_page()
        if page:
            page.overlay.append(dialog)
            dialog.open = True
            page.update()

    def _close_dialog(self, dialog):
        dialog.open = False
        page = self._get_page()
        if page:
            page.update()

    def _get_page(self):
        try:
            return self.page
        except RuntimeError:
            return None
