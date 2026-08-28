import asyncio
import datetime

import flet as ft

from application.api import ApiError, BackendUnreachableError
from application.components import BaseView
from application.components.category_picker import CategoryPicker
from application.components.planned_transaction_card import PlannedTransactionCard
from core.recurrence import Frequency, RecurrenceRule


FREQUENCY_OPTIONS = [
    ft.dropdown.Option(key="daily", text="Ежедневно"),
    ft.dropdown.Option(key="weekly", text="Еженедельно"),
    ft.dropdown.Option(key="monthly", text="Ежемесячно"),
    ft.dropdown.Option(key="yearly", text="Ежегодно"),
]


class PlannedView(BaseView):
    def __init__(self, route: str, api_client):
        self.api_client = api_client
        self._disposed = False
        self._transactions: list[dict] = []
        self._accounts: list[dict] = []
        self._account_map: dict[int, dict] = {}

        self._error_text = ft.Text("", size=13, color=ft.Colors.ERROR, visible=False)
        self._loading = ft.ProgressRing(width=40, height=40, visible=True)
        self._tx_list = ft.Column(spacing=8, scroll=ft.ScrollMode.AUTO, expand=True)

        content = ft.Column(
            controls=[
                self._error_text,
                self._loading,
                self._tx_list,
            ],
            expand=True,
        )

        super().__init__(content=content, title="Запланированные", route=route, selected_index=2)
        self.floating_action_button = ft.FloatingActionButton(
            icon=ft.Icons.ADD,
            on_click=self._show_add_dialog,
            bgcolor=ft.Colors.PRIMARY,
            foreground_color=ft.Colors.ON_PRIMARY,
        )

    def did_mount(self):
        super().did_mount()
        asyncio.create_task(self._load_data())

    def dispose(self):
        self._disposed = True

    async def _load_data(self):
        try:
            self._error_text.visible = False
            self._loading.visible = True
            self._tx_list.controls.clear()
            self.update()

            transactions, accounts = await asyncio.gather(
                asyncio.to_thread(self.api_client.list_transactions),
                asyncio.to_thread(self.api_client.list_accounts),
            )
            if self._disposed:
                return

            all_txs = transactions if isinstance(transactions, list) else transactions.get("results", [])
            self._transactions = [tx for tx in all_txs if tx.get("is_planned")]
            self._accounts = accounts if isinstance(accounts, list) else accounts.get("results", [])
            self._account_map = {a["id"]: a for a in self._accounts}

            self._loading.visible = False
            self._rebuild_list()
        except BackendUnreachableError:
            if not self._disposed:
                self._loading.visible = False
                self._error_text.value = "Сервер недоступен"
                self._error_text.visible = True
                self.update()
        except ApiError as exc:
            if not self._disposed:
                self._loading.visible = False
                self._error_text.value = f"Ошибка загрузки: {exc}"
                self._error_text.visible = True
                self.update()

    def _rebuild_list(self):
        self._tx_list.controls.clear()

        if not self._transactions:
            self._tx_list.controls.append(
                ft.Container(
                    content=ft.Column(
                        [
                            ft.Icon(ft.Icons.EVENT_NOTE, size=64, color=ft.Colors.ON_SURFACE_VARIANT),
                            ft.Text("Нет запланированных", size=20, color=ft.Colors.ON_SURFACE_VARIANT),
                            ft.Text("Нажмите + чтобы добавить", size=14, color=ft.Colors.ON_SURFACE_VARIANT),
                        ],
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        alignment=ft.MainAxisAlignment.CENTER,
                        spacing=8,
                    ),
                    alignment=ft.alignment.center,
                    expand=True,
                    padding=40,
                )
            )
            self.update()
            return

        sorted_txs = sorted(
            self._transactions,
            key=lambda tx: tx.get("date", ""),
        )

        for tx in sorted_txs:
            card = self._build_card(tx)
            self._tx_list.controls.append(card)

        self.update()

    def _build_card(self, tx: dict) -> PlannedTransactionCard:
        entries = tx.get("entries", [])
        total = sum(float(e.get("amount", 0)) for e in entries)
        first_entry = entries[0] if entries else {}
        account_id = first_entry.get("account")
        account = self._account_map.get(account_id, {})
        account_name = account.get("name", "—")

        planned_date = None
        date_str = tx.get("date", "")
        try:
            planned_date = datetime.datetime.fromisoformat(date_str).date()
        except (ValueError, TypeError):
            pass

        return PlannedTransactionCard(
            description=tx.get("description", ""),
            amount=total,
            account_name=account_name,
            category=tx.get("category", ""),
            planned_date=planned_date,
            recurrence_rule=tx.get("recurrence_rule", ""),
            on_execute=lambda t=tx: self._execute_transaction(t),
            on_edit=lambda t=tx: self._show_edit_dialog(t),
            on_delete=lambda t=tx: self._show_delete_confirm(t),
        )

    async def _execute_transaction(self, tx: dict):
        try:
            payload = {
                "date": datetime.datetime.now().isoformat(),
                "entries": tx.get("entries", []),
                "category": tx.get("category", ""),
                "description": tx.get("description", ""),
                "is_planned": False,
                "recurrence_rule": tx.get("recurrence_rule", ""),
            }
            await asyncio.to_thread(self.api_client.create_transaction, payload)

            if not tx.get("recurrence_rule"):
                await asyncio.to_thread(self.api_client.delete_transaction, tx["id"])

            await self._load_data()
        except (ApiError, BackendUnreachableError) as exc:
            if not self._disposed:
                self._error_text.value = f"Ошибка: {exc}"
                self._error_text.visible = True
                self.update()

    def _show_add_dialog(self, e):
        self._open_transaction_dialog()

    def _show_edit_dialog(self, tx: dict):
        self._open_transaction_dialog(tx=tx)

    def _open_transaction_dialog(self, tx: dict | None = None):
        is_edit = tx is not None
        title = "Редактировать план" if is_edit else "Новый план"

        account_options = [ft.dropdown.Option(key=str(a["id"]), text=a.get("name", "")) for a in self._accounts]
        account_dropdown = ft.Dropdown(label="Счёт", options=account_options, border_radius=8)

        type_group = ft.RadioGroup(
            content=ft.Row(
                [
                    ft.Radio(value="expense", label="Расход"),
                    ft.Radio(value="income", label="Доход"),
                ],
                spacing=16,
            ),
            value="expense",
        )

        amount_field = ft.TextField(label="Сумма", keyboard_type=ft.KeyboardType.NUMBER, border_radius=8)
        description_field = ft.TextField(label="Описание", border_radius=8)
        category_picker = CategoryPicker(value=tx.get("category", "") if is_edit else "")

        now = datetime.datetime.now()
        if is_edit:
            try:
                now = datetime.datetime.fromisoformat(tx.get("date", now.isoformat()))
            except (ValueError, TypeError):
                now = datetime.datetime.now()

        date_field = ft.TextField(
            label="Плановая дата",
            value=now.strftime("%Y-%m-%d"),
            border_radius=8,
            read_only=True,
            suffix=ft.IconButton(
                icon=ft.Icons.CALENDAR_MONTH,
                icon_size=20,
                on_click=lambda _: self._open_date_picker(date_field),
            ),
        )

        recurrence_switch = ft.Switch(label="Повторяющаяся", value=False, on_change=self._on_recurrence_toggle)
        frequency_dropdown = ft.Dropdown(
            label="Частота",
            options=FREQUENCY_OPTIONS,
            value="monthly",
            border_radius=8,
            visible=False,
        )
        interval_field = ft.TextField(
            label="Интервал",
            value="1",
            keyboard_type=ft.KeyboardType.NUMBER,
            border_radius=8,
            visible=False,
            width=100,
        )

        error_text = ft.Text("", size=12, color=ft.Colors.ERROR, visible=False)

        if is_edit:
            entries = tx.get("entries", [])
            if entries:
                first = entries[0]
                amount_field.value = str(abs(float(first.get("amount", 0))))
                account_dropdown.value = str(first.get("account", ""))
            description_field.value = tx.get("description", "")
            if tx.get("recurrence_rule"):
                recurrence_switch.value = True
                self._show_recurrence_fields(True, frequency_dropdown, interval_field)
                rule = RecurrenceRule.parse(tx["recurrence_rule"])
                if rule:
                    frequency_dropdown.value = rule.frequency.value
                    interval_field.value = str(rule.interval)

        async def on_submit(e):
            amount_str = amount_field.value.strip() if amount_field.value else ""
            account_id_str = account_dropdown.value
            tx_type = type_group.value
            description = description_field.value.strip() if description_field.value else ""
            category = category_picker.value

            if not amount_str:
                error_text.value = "Введите сумму"
                error_text.visible = True
                self.update()
                return
            if not account_id_str:
                error_text.value = "Выберите счёт"
                error_text.visible = True
                self.update()
                return

            try:
                amount = float(amount_str)
            except ValueError:
                error_text.value = "Некорректная сумма"
                error_text.visible = True
                self.update()
                return

            quantity = amount if tx_type == "income" else -amount
            entries = [{"account": int(account_id_str), "quantity": quantity, "amount": quantity, "unit_price": 1}]

            date_str = date_field.value or now.strftime("%Y-%m-%d")
            try:
                date_val = datetime.datetime.fromisoformat(date_str)
            except ValueError:
                date_val = now

            recurrence_rule = ""
            if recurrence_switch.value:
                freq = frequency_dropdown.value
                try:
                    interval = int(interval_field.value)
                except ValueError:
                    interval = 1
                rule = RecurrenceRule(Frequency(freq), interval)
                recurrence_rule = rule.to_string()

            payload = {
                "date": date_val.isoformat(),
                "entries": entries,
                "category": category,
                "description": description,
                "is_planned": True,
                "recurrence_rule": recurrence_rule,
            }

            try:
                if is_edit:
                    await asyncio.to_thread(self.api_client.update_transaction, tx["id"], payload)
                else:
                    await asyncio.to_thread(self.api_client.create_transaction, payload)

                dialog.open = False
                self.update()
                await self._load_data()
            except (ApiError, BackendUnreachableError) as exc:
                error_text.value = str(exc)
                error_text.visible = True
                self.update()

        dialog = ft.AlertDialog(
            title=ft.Text(title),
            content=ft.Container(
                content=ft.Column(
                    [
                        type_group,
                        account_dropdown,
                        amount_field,
                        description_field,
                        category_picker,
                        date_field,
                        recurrence_switch,
                        frequency_dropdown,
                        interval_field,
                        error_text,
                    ],
                    spacing=12,
                    width=350,
                ),
            ),
            actions=[
                ft.TextButton("Отмена", on_click=lambda _: self._close_dialog(dialog)),
                ft.ElevatedButton("Сохранить", on_click=on_submit),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        self.page.overlay.append(dialog)
        dialog.open = True
        self.page.update()

    def _on_recurrence_toggle(self, e):
        dialog = self.page.overlay[-1] if self.page.overlay else None
        if dialog and isinstance(dialog, ft.AlertDialog) and dialog.open:
            content = dialog.content.content
            for control in content.controls:
                if isinstance(control, ft.Dropdown) and control.label == "Частота":
                    control.visible = e.control.value
                if isinstance(control, ft.TextField) and control.label == "Интервал":
                    control.visible = e.control.value
            dialog.update()

    def _show_recurrence_fields(self, visible: bool, freq_dd, interval_tf):
        freq_dd.visible = visible
        interval_tf.visible = visible

    def _open_date_picker(self, date_field):
        picker = ft.DatePicker(
            on_change=lambda e: self._on_date_picked(e, date_field),
        )
        self.page.overlay.append(picker)
        picker.pick_date()
        self.page.update()

    def _on_date_picked(self, e, date_field):
        if e.control.value:
            date_field.value = e.control.value.strftime("%Y-%m-%d")
            date_field.update()

    def _show_delete_confirm(self, tx: dict):
        async def on_confirm(e):
            try:
                await asyncio.to_thread(self.api_client.delete_transaction, tx["id"])
                dialog.open = False
                self.update()
                await self._load_data()
            except (ApiError, BackendUnreachableError) as exc:
                dialog.open = False
                self.update()
                self._error_text.value = f"Ошибка удаления: {exc}"
                self._error_text.visible = True
                self.update()

        desc = tx.get("description", "") or "Без описания"
        dialog = ft.AlertDialog(
            title=ft.Text("Удалить план?"),
            content=ft.Text(f'Удалить "{desc}"?'),
            actions=[
                ft.TextButton("Отмена", on_click=lambda _: self._close_dialog(dialog)),
                ft.ElevatedButton("Удалить", on_click=on_confirm, bgcolor=ft.Colors.ERROR, color=ft.Colors.ON_ERROR),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        self.page.overlay.append(dialog)
        dialog.open = True
        self.page.update()

    def _close_dialog(self, dialog):
        dialog.open = False
        self.page.update()
