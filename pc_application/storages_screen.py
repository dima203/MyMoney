from flet import (
    Page,
    Container,
    AlertDialog,
    TextField,
    Dropdown,
    dropdown,
    Column,
    Row,
    ListView,
    ListTile,
    PopupMenuButton,
    PopupMenuItem,
    TextButton,
    Text,
    MainAxisAlignment,
    ScrollMode,
    icons
)

from dataview import AccountBaseView, ResourceBaseView
from core import Money

from .screen import Screen


class StoragesScreen(Screen):
    def __init__(self, view: AccountBaseView, resource_view: ResourceBaseView) -> None:
        super().__init__()
        self.__view = view
        self.__resource_view = resource_view

    def build(self) -> Container:
        self.storage_list = ListView(spacing=10, width=500)
        self.container = Container(self.storage_list)
        self.storage_name_field = TextField(label='Название')
        self.storage_value_field = TextField(label='Текущий баланс')
        self.storage_currency_field = Dropdown(
            label='Валюта',
            options=[
                dropdown.Option(str(pk), resource.name) for pk, resource in self.__resource_view.get_all().items()
            ]
        )
        self.modal_dialog: AlertDialog | None = None
        return self.container

    def update(self) -> None:
        self.storage_list.controls.clear()
        for pk, storage in self.__view.get_all().items():
            self.storage_list.controls.append(
                ListTile(
                    leading=PopupMenuButton(
                        icon=icons.WALLET,
                        items=[
                            PopupMenuItem(icon=icons.CHANGE_CIRCLE, text='update',
                                          on_click=lambda e: self._open_update(pk)),
                            PopupMenuItem(icon=icons.REMOVE_CIRCLE, text='delete',
                                          on_click=lambda e: self._delete_storage(pk)),
                        ]
                    ),
                    title=Row([
                        Text(storage.name),
                        Text(str(storage.value))
                    ],
                        alignment=MainAxisAlignment.SPACE_BETWEEN
                    ),
                )
            )
        self.storage_list.update()

    def _open_update(self, pk: int) -> None:
        storage = self.__view.get(pk)
        self.storage_name_field.value = storage.name
        self.storage_value_field.value = str(storage.value.value)
        self.storage_currency_field.value = str(storage.value.currency.pk)
        self.modal_dialog = AlertDialog(
            modal=True,
            title=Text("Изменение счета"),
            content=Container(
                Column([
                    self.storage_name_field,
                    self.storage_value_field,
                    self.storage_currency_field
                ],
                    scroll=ScrollMode.ALWAYS,
                ),
                width=self.page.width * 0.7,
                height=self.page.height * 0.7,
                expand=True,
            ),
            actions=[
                TextButton("Подтвердить", on_click=lambda e: self._update_storage(pk)),
                TextButton("Отмена", on_click=lambda e: self._close_update()),
            ],
            adaptive=True
        )

        self.page.dialog = self.modal_dialog
        self.modal_dialog.open = True
        self.page.update()

    def _close_update(self):
        self.modal_dialog.open = False
        self.page.update()

    def _update_storage(self, pk: int) -> None:
        storage = self.__view.get(pk)
        storage.name = self.storage_name_field.value
        storage.value = Money(
            float(self.storage_value_field.value),
            self.__resource_view.get(int(self.storage_currency_field.value))
        )
        self.__view.update(pk)
        self.modal_dialog.open = False
        self.page.update()
        self.update()

    def _delete_storage(self, pk: int) -> None:
        self.__view.delete(pk)
        self.update()
