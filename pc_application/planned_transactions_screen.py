from flet import (
    Container,
    AlertDialog,
    TextField,
    Dropdown,
    dropdown,
    TimePicker,
    DatePicker,
    Row,
    Column,
    ListView,
    ListTile,
    TextButton,
    ElevatedButton,
    PopupMenuButton,
    PopupMenuItem,
    Text,
    TextStyle,
    MainAxisAlignment,
    ScrollMode,
    icons
)

from datetime import datetime

from dataview import PlannedTransactionBaseView, AccountBaseView
from core import PlannedTransaction, Money
from core.utils import make_function_call

from .screen import Screen


class PlannedTransactionsScreen(Screen):
    def __init__(self, view: PlannedTransactionBaseView, storage_view: AccountBaseView) -> None:
        super().__init__()
        self.__view = view
        self.__storage_view = storage_view

    def build(self) -> Container:
        self.transaction_list = ListView(spacing=10, width=500)
        self.container = Container(self.transaction_list)
        self.transaction_storage_field = Dropdown(
            label='Счет',
            options=[
                dropdown.Option(str(pk), storage.name) for pk, storage in self.__storage_view.get_all().items()
            ]
        )
        self.transaction_time_picker = TimePicker(
            confirm_text='Подтвердить',
            on_change=self._change_time
        )
        self.transaction_date_picker = DatePicker(
            confirm_text='Подтвердить',
            on_change=self._change_date
        )
        self.time_button = ElevatedButton(
            text=' ',
            icon=icons.TIMER,
            on_click=lambda _: self.transaction_time_picker.pick_time()
        )
        self.date_button = ElevatedButton(
            text=' ',
            icon=icons.CALENDAR_MONTH,
            on_click=lambda _: self.transaction_date_picker.pick_date()
        )
        self.transaction_value_field = TextField(label='Сумма')
        self.page.overlay.append(self.transaction_time_picker)
        self.page.overlay.append(self.transaction_date_picker)
        self.modal_dialog: AlertDialog | None = None
        return self.container

    def update(self) -> None:
        self.transaction_list.controls.clear()
        self.transaction_list.controls.append(
            ListTile(
                title=TextButton('Добавить', icons.ADD, on_click=lambda e: self._open_add()),
            )
        )
        for pk, transaction in self.__view.get_all().items():
            self.transaction_list.controls.append(
                ListTile(
                    leading=PopupMenuButton(
                        icon=icons.ADD if transaction.value > 0 else icons.REMOVE,
                        items=[
                            PopupMenuItem(icon=icons.CHANGE_CIRCLE, text='update',
                                          on_click=make_function_call(self._open_update, pk)),
                            PopupMenuItem(icon=icons.REMOVE_CIRCLE, text='delete',
                                          on_click=make_function_call(self._delete_transaction, pk)),
                        ]
                    ),
                    title=Row([
                        Text(transaction.storage.name),
                        Text(str(abs(transaction.value)))
                    ],
                        alignment=MainAxisAlignment.SPACE_BETWEEN
                    ),
                    subtitle=Text(transaction.planned_time.strftime('%d.%m.%Y %H:%M'),
                                  style=TextStyle(size=10, italic=True)),
                )
            )
        self.transaction_list.update()

    def _delete_transaction(self, pk: int) -> None:
        self.__view.delete(pk)
        self.update()

    def _open_add(self) -> None:
        current_time = datetime.now()
        self.transaction_storage_field.value = ''
        self.transaction_value_field.value = ''
        self.transaction_time_picker.value = current_time.time()
        self.transaction_date_picker.value = current_time.date()
        self.modal_dialog = AlertDialog(
            modal=True,
            title=Text("Добавление транзакции"),
            content=Container(
                Column([
                    self.transaction_storage_field,
                    self.transaction_value_field,
                    Row([
                        self.time_button,
                        self.date_button
                    ])
                ],
                    scroll=ScrollMode.ALWAYS,
                ),
                width=self.page.width * 0.7,
                height=self.page.height * 0.7,
                expand=True,
            ),
            actions=[
                TextButton("Подтвердить", on_click=lambda e: self._add_transaction()),
                TextButton("Отмена", on_click=lambda e: self._close_add()),
            ],
            adaptive=True
        )

        self.page.dialog = self.modal_dialog
        self.modal_dialog.open = True
        self.page.update()
        self._change_time(None)
        self._change_date(None)

    def _close_add(self):
        self.modal_dialog.open = False
        self.page.update()

    def _add_transaction(self) -> None:
        storage = self.__storage_view.get(int(self.transaction_storage_field.value))
        currency = Money(
            float(self.transaction_value_field.value),
            storage.value.currency
        )

        time_stamp = datetime.combine(self.transaction_date_picker.value.date(), self.transaction_time_picker.value)
        transaction = PlannedTransaction(
            storage=storage,
            currency=currency,
            planned_time=time_stamp,
            repeatability=0
        )
        self.__view.add(transaction)
        self.modal_dialog.open = False
        self.page.update()
        self.update()

    def _open_update(self, pk: int) -> None:
        transaction = self.__view.get(pk)
        self.transaction_storage_field.value = str(transaction.storage.pk)
        self.transaction_value_field.value = str(transaction.value.value)
        self.transaction_time_picker.value = transaction.planned_time.time()
        self.transaction_date_picker.value = transaction.planned_time

        self.modal_dialog = AlertDialog(
            modal=True,
            title=Text("Изменение транзакции"),
            content=Container(
                Column([
                    self.transaction_storage_field,
                    self.transaction_value_field,
                    Row([
                        self.time_button,
                        self.date_button
                    ])
                ],
                    scroll=ScrollMode.ALWAYS,
                ),
                width=self.page.width * 0.7,
                height=self.page.height * 0.7,
                expand=True,
            ),
            actions=[
                TextButton("Подтвердить", on_click=lambda e: self._update_transaction(pk)),
                TextButton("Отмена", on_click=lambda e: self._close_update()),
            ],
            adaptive=True
        )

        self.page.dialog = self.modal_dialog
        self.modal_dialog.open = True
        self.page.update()
        self._change_time(None)
        self._change_date(None)

    def _close_update(self):
        self.modal_dialog.open = False
        self.page.update()

    def _update_transaction(self, pk: int) -> None:
        transaction = self.__view.get(pk)
        storage = self.__storage_view.get(int(self.transaction_storage_field.value))
        transaction.storage = storage
        transaction.value = Money(
            float(self.transaction_value_field.value),
            storage.value.currency
        )
        time_stamp = datetime.combine(self.transaction_date_picker.value.date(), self.transaction_time_picker.value)
        transaction.planned_time = time_stamp

        self.__view.update(pk)
        self.modal_dialog.open = False
        self.page.update()
        self.update()

    def _change_time(self, _) -> None:
        self.time_button.text = self.transaction_time_picker.value.strftime('%H:%M')
        self.modal_dialog.update()

    def _change_date(self, _) -> None:
        self.date_button.text = self.transaction_date_picker.value.strftime('%d.%m.%Y')
        self.modal_dialog.update()
