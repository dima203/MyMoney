from flet import (
    Container,
    Row,
    ListView,
    ListTile,
    PopupMenuButton,
    PopupMenuItem,
    Text,
    TextStyle,
    MainAxisAlignment,
    icons
)

from dataview import TransactionBaseView

from .screen import Screen


class TransactionsScreen(Screen):
    def __init__(self, view: TransactionBaseView) -> None:
        super().__init__()
        self.__view = view

    def build(self) -> Container:
        self.transaction_list = ListView(spacing=10, width=500)
        self.container = Container(self.transaction_list)
        return self.container

    def update(self) -> None:
        self.transaction_list.controls.clear()
        for pk, transaction in self.__view.get_all().items():
            self.transaction_list.controls.append(
                ListTile(
                    leading=PopupMenuButton(
                        icon=icons.ADD if transaction.get_value() > 0 else icons.REMOVE,
                        items=[
                            PopupMenuItem(icon=icons.CHANGE_CIRCLE, text='update'),
                            PopupMenuItem(icon=icons.REMOVE_CIRCLE, text='delete',
                                          on_click=lambda e: self._delete_transaction(pk)),
                        ]
                    ),
                    title=Row([
                        Text(transaction.storage.name),
                        Text(str(abs(transaction.get_value())))
                    ],
                        alignment=MainAxisAlignment.SPACE_BETWEEN
                    ),
                    subtitle=Text(transaction.time_stamp.strftime('%d.%m.%Y %H:%M'),
                                  style=TextStyle(size=10, italic=True)),
                )
            )
        self.transaction_list.update()

    def _delete_transaction(self, pk: int) -> None:
        self.__view.delete(pk)
        self.update()
