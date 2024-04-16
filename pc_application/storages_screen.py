from flet import Container, Row, ListView, ListTile, PopupMenuButton, PopupMenuItem, Text, MainAxisAlignment, icons

from dataview import AccountBaseView

from .screen import Screen


class StoragesScreen(Screen):
    def __init__(self, view: AccountBaseView) -> None:
        super().__init__()
        self.__view = view

    def build(self) -> Container:
        self.storage_list = ListView(spacing=10, width=500)
        self.container = Container(self.storage_list)
        return self.container

    def update(self) -> None:
        self.storage_list.controls.clear()
        for pk, storage in self.__view.get_all().items():
            self.storage_list.controls.append(
                ListTile(
                    leading=PopupMenuButton(
                        icon=icons.WALLET,
                        items=[
                            PopupMenuItem(icon=icons.CHANGE_CIRCLE, text='update'),
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

    def _delete_storage(self, pk: int) -> None:
        self.__view.delete(pk)
        self.update()
