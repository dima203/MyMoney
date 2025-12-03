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
    CrossAxisAlignment,
    ScrollMode,
    Icons,
    View,
)

from datetime import datetime

from dataview import PlannedTransactionBaseView, AccountBaseView
from core import PlannedTransaction, Money
from core.utils import make_function_call


class PlannedTransactionsScreen(View):
    def __init__(
        self, route: str, view: PlannedTransactionBaseView, storage_view: AccountBaseView, *args, **kwargs
    ) -> None:
        super().__init__(route, *args, **kwargs)
        self.__view = view
        self.__storage_view = storage_view

    def did_mount(self):
        self.update()

    def build(self) -> Container:
        self.vertical_alignment = MainAxisAlignment.CENTER
        self.horizontal_alignment = CrossAxisAlignment.CENTER

        self.transaction_list = ListView(spacing=10, width=500)
        self.container = Container(self.transaction_list)
        self.transaction_storage_field = Dropdown(
            label="Счет",
            options=[dropdown.Option(str(pk), storage.name) for pk, storage in self.__storage_view.get_all().items()],
        )
        self.transaction_time_picker = TimePicker(confirm_text="Подтвердить", on_change=self._change_time)
        self.transaction_date_picker = DatePicker(confirm_text="Подтвердить", on_change=self._change_date)
        self.time_button = ElevatedButton(
            text=" ",
            icon=Icons.TIMER,
            on_click=lambda _: self.page.open(self.transaction_time_picker),
        )
        self.date_button = ElevatedButton(
            text=" ", icon=Icons.CALENDAR_MONTH, on_click=lambda _: self.page.open(self.transaction_date_picker)
        )
        self.transaction_value_field = TextField(label="Сумма")
        self.page.overlay.append(self.transaction_time_picker)
        self.page.overlay.append(self.transaction_date_picker)

        self.add_accept_button = TextButton("Подтвердить", on_click=lambda e: self._add_transaction())
        self.update_accept_button = TextButton("Подтвердить")
        self.cancel_button = TextButton("Отмена", on_click=lambda e: self._close_modal())

        self.modal_dialog = AlertDialog(
            modal=True,
            title=Text("Добавление транзакции"),
            content=Container(
                Column(
                    [
                        self.transaction_storage_field,
                        self.transaction_value_field,
                        Row([self.time_button, self.date_button]),
                    ],
                    scroll=ScrollMode.ALWAYS,
                ),
                width=self.page.width * 0.7,
                height=self.page.height * 0.7,
                expand=True,
            ),
            adaptive=True,
        )

        self.controls = [self.transaction_list]
        self.scroll = "always"
        return self

    def update(self) -> None:
        self.transaction_list.controls.clear()
        self.transaction_list.controls.append(
            ListTile(
                title=TextButton("Добавить", Icons.ADD, on_click=lambda e: self._open_add()),
            )
        )
        for pk, transaction in self.__view.get_all().items():
            self.transaction_list.controls.append(
                ListTile(
                    leading=PopupMenuButton(
                        icon=Icons.ADD if transaction.value > 0 else Icons.REMOVE,
                        items=[
                            PopupMenuItem(
                                icon=Icons.CHANGE_CIRCLE,
                                text="update",
                                on_click=make_function_call(self._open_update, pk),
                            ),
                            PopupMenuItem(
                                icon=Icons.REMOVE_CIRCLE,
                                text="delete",
                                on_click=make_function_call(self._delete_transaction, pk),
                            ),
                        ],
                    ),
                    title=Row(
                        [Text(transaction.storage.name), Text(str(abs(transaction.value)))],
                        alignment=MainAxisAlignment.SPACE_BETWEEN,
                    ),
                    subtitle=Text(
                        transaction.planned_time.strftime("%d.%m.%Y %H:%M"), style=TextStyle(size=10, italic=True)
                    ),
                )
            )
        self.transaction_list.update()

    def _delete_transaction(self, pk: int) -> None:
        self.__view.delete(pk)
        self.update()

    def _open_add(self) -> None:
        current_time = datetime.now()
        self.transaction_storage_field.value = ""
        self.transaction_value_field.value = ""
        self.transaction_time_picker.value = current_time.time()
        self.transaction_date_picker.value = current_time.date()

        self.modal_dialog.actions = [self.add_accept_button, self.cancel_button]
        self.page.open(self.modal_dialog)
        self.page.update()
        self._change_time(None)
        self._change_date(None)

    def _close_modal(self):
        self.page.close(self.modal_dialog)
        self.page.update()

    def _add_transaction(self) -> None:
        storage = self.__storage_view.get(int(self.transaction_storage_field.value))
        currency = Money(float(self.transaction_value_field.value), storage.value.currency)

        time_stamp = datetime.combine(self.transaction_date_picker.value.date(), self.transaction_time_picker.value)
        transaction = PlannedTransaction(storage, currency, time_stamp, 0)
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

        self.update_accept_button.on_click = make_function_call(self._update_transaction, pk)
        self.modal_dialog.actions = [self.update_accept_button, self.cancel_button]
        self.page.open(self.modal_dialog)
        self.page.update()
        self._change_time(None)
        self._change_date(None)

    def _update_transaction(self, pk: int) -> None:
        transaction = self.__view.get(pk)
        storage = self.__storage_view.get(int(self.transaction_storage_field.value))
        transaction.storage = storage
        transaction.value = Money(float(self.transaction_value_field.value), storage.value.currency)
        time_stamp = datetime.combine(self.transaction_date_picker.value.date(), self.transaction_time_picker.value)
        transaction.planned_time = time_stamp

        self.page.close(self.modal_dialog)
        self.page.update()
        self.update()

    def _change_time(self, _) -> None:
        self.time_button.text = self.transaction_time_picker.value.strftime("%H:%M")
        self.modal_dialog.update()

    def _change_date(self, _) -> None:
        self.date_button.text = self.transaction_date_picker.value.strftime("%d.%m.%Y")
        self.modal_dialog.update()
