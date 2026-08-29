import asyncio
import datetime
from collections import defaultdict

import flet as ft

from application.api import ApiError, BackendUnreachableError
from application.components import BaseView
from application.components.navigation_items import NAVIGATION_ITEMS
from application.components.category_picker import CategoryPicker
from application.components.transaction_card import TransactionCard


class TransactionsView(BaseView):
    def __init__(self, route: str, api_client):
        self.api_client = api_client
        self._disposed = False
        self._transactions: list[dict] = []
        self._accounts: list[dict] = []
        self._account_map: dict[int, dict] = {}
        self._categories: list[str] = []

        self._error_text = ft.Text("", size=13, color=ft.Colors.ERROR, visible=False)
        self._loading = ft.ProgressRing(width=40, height=40, visible=True)
        self._tx_list = ft.Column(spacing=8, scroll=ft.ScrollMode.AUTO, expand=True)

        self._filter_category = ft.Dropdown(
            label="Категория",
            options=[ft.dropdown.Option("Все")],
            value="Все",
            border_radius=8,
            width=160,
            on_select=self._apply_filters,
        )
        self._filter_bar = ft.Row(
            controls=[self._filter_category, ft.Container(expand=True)],
            alignment=ft.MainAxisAlignment.START,
        )

        content = ft.Column(
            controls=[
                self._error_text,
                self._loading,
                self._filter_bar,
                self._tx_list,
            ],
            expand=True,
        )

        super().__init__(content=content, title="Транзакции", route=route, selected_index=1, navigation_items=NAVIGATION_ITEMS)
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

            self._transactions = transactions if isinstance(transactions, list) else transactions.get("results", [])
            self._accounts = accounts if isinstance(accounts, list) else accounts.get("results", [])
            self._account_map = {a["id"]: a for a in self._accounts}
            self._collect_categories()

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

    def _collect_categories(self):
        cats = set()
        for tx in self._transactions:
            cat = tx.get("category", "")
            if cat:
                cats.add(cat)
        self._categories = sorted(cats)
        options = [ft.dropdown.Option("Все")] + [ft.dropdown.Option(c) for c in self._categories]
        self._filter_category.options = options

    def _apply_filters(self, e=None):
        self._rebuild_list()

    def _get_filtered_transactions(self) -> list[dict]:
        filtered = self._transactions
        cat_filter = self._filter_category.value
        if cat_filter and cat_filter != "Все":
            filtered = [tx for tx in filtered if tx.get("category") == cat_filter]
        filtered.sort(key=lambda tx: tx.get("date", ""), reverse=True)
        return filtered

    def _rebuild_list(self):
        self._tx_list.controls.clear()
        filtered = self._get_filtered_transactions()

        if not filtered:
            self._tx_list.controls.append(
                ft.Container(
                    content=ft.Column(
                        [
                            ft.Icon(ft.Icons.RECEIPT_LONG, size=64, color=ft.Colors.ON_SURFACE_VARIANT),
                            ft.Text("Нет транзакций", size=20, color=ft.Colors.ON_SURFACE_VARIANT),
                            ft.Text("Нажмите + чтобы добавить", size=14, color=ft.Colors.ON_SURFACE_VARIANT),
                        ],
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        alignment=ft.MainAxisAlignment.CENTER,
                        spacing=8,
                    ),
                    alignment=ft.Alignment.CENTER,
                    expand=True,
                    padding=40,
                )
            )
            self.update()
            return

        grouped = self._group_by_date(filtered)
        for date_label, txs in grouped.items():
            header = ft.Container(
                content=ft.Text(date_label, size=13, weight=ft.FontWeight.W_600, color=ft.Colors.ON_SURFACE_VARIANT),
                padding=ft.Padding.symmetric(horizontal=16, vertical=8),
            )
            self._tx_list.controls.append(header)

            for tx in txs:
                card = self._build_card(tx)
                self._tx_list.controls.append(card)

        self.update()

    def _group_by_date(self, transactions: list[dict]) -> dict[str, list[dict]]:
        groups: dict[str, list[dict]] = defaultdict(list)
        today = datetime.date.today()
        yesterday = today - datetime.timedelta(days=1)

        for tx in transactions:
            date_str = tx.get("date", "")
            try:
                dt = datetime.datetime.fromisoformat(date_str)
                d = dt.date()
            except (ValueError, TypeError):
                d = today

            if d == today:
                label = "Сегодня"
            elif d == yesterday:
                label = "Вчера"
            else:
                label = d.strftime("%d %b %Y")
            groups[label].append(tx)

        return dict(groups)

    def _build_card(self, tx: dict) -> TransactionCard:
        entries = tx.get("entries", [])
        total = sum(float(e.get("amount", 0)) for e in entries)
        first_entry = entries[0] if entries else {}
        account_id = first_entry.get("account")
        account = self._account_map.get(account_id, {})
        account_name = account.get("name", "—")

        try:
            timestamp = datetime.datetime.fromisoformat(tx.get("date", ""))
        except (ValueError, TypeError):
            timestamp = None

        return TransactionCard(
            description=tx.get("description", ""),
            amount=total,
            account_name=account_name,
            category=tx.get("category", ""),
            timestamp=timestamp,
            on_edit=lambda t=tx: self._show_edit_dialog(t),
            on_delete=lambda t=tx: self._show_delete_confirm(t),
        )

    def _show_add_dialog(self, e):
        self._open_transaction_dialog()

    def _show_edit_dialog(self, tx: dict):
        self._open_transaction_dialog(tx=tx)

    def _open_transaction_dialog(self, tx: dict | None = None):
        is_edit = tx is not None
        title = "Редактировать транзакцию" if is_edit else "Новая транзакция"

        type_group = ft.RadioGroup(
            content=ft.Row(
                [
                    ft.Radio(value="expense", label="Расход"),
                    ft.Radio(value="income", label="Доход"),
                    ft.Radio(value="transfer", label="Перевод"),
                ],
                spacing=16,
            ),
            value="expense",
        )

        account_options = [ft.dropdown.Option(key=str(a["id"]), text=a.get("name", "")) for a in self._accounts]
        account_dropdown = ft.Dropdown(label="Счёт", options=account_options, border_radius=8)

        to_account_dropdown = ft.Dropdown(
            label="Счёт получения",
            options=account_options,
            border_radius=8,
            visible=False,
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
            label="Дата",
            value=now.strftime("%Y-%m-%d"),
            border_radius=8,
            read_only=True,
            suffix=ft.IconButton(
                icon=ft.Icons.CALENDAR_MONTH,
                icon_size=20,
                on_click=lambda _: self._open_date_picker(date_field),
            ),
        )

        error_text = ft.Text("", size=12, color=ft.Colors.ERROR, visible=False)

        def on_type_change(e):
            is_transfer = type_group.value == "transfer"
            to_account_dropdown.visible = is_transfer
            to_account_dropdown.update()

        type_group.on_change = on_type_change

        if is_edit:
            entries = tx.get("entries", [])
            if entries:
                first = entries[0]
                amount_field.value = str(abs(float(first.get("amount", 0))))
                account_dropdown.value = str(first.get("account", ""))
            type_group.value = "expense"
            description_field.value = tx.get("description", "")

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

            if tx_type == "expense":
                quantity = -amount
            elif tx_type == "income":
                quantity = amount
            else:
                quantity = -amount

            entries = [{"account": int(account_id_str), "quantity": quantity, "amount": quantity, "unit_price": 1}]

            if tx_type == "transfer":
                to_id = to_account_dropdown.value
                if not to_id:
                    error_text.value = "Выберите счёт получения"
                    error_text.visible = True
                    self.update()
                    return
                entries.append({"account": int(to_id), "quantity": amount, "amount": amount, "unit_price": 1})

            date_str = date_field.value or now.strftime("%Y-%m-%d")
            try:
                date_val = datetime.datetime.fromisoformat(date_str)
            except ValueError:
                date_val = now

            payload = {
                "date": date_val.isoformat(),
                "entries": entries,
                "category": category,
                "description": description,
                "is_planned": False,
            }

            save_button.disabled = True
            save_button.text = "Сохранение..."
            self.page.update()

            try:
                if is_edit:
                    await asyncio.to_thread(self.api_client.update_transaction, tx["id"], payload)
                else:
                    await asyncio.to_thread(self.api_client.create_transaction, payload)

                dialog.open = False
                self.page.update()
                await self._load_data()
            except (ApiError, BackendUnreachableError) as exc:
                save_button.disabled = False
                save_button.text = "Сохранить"
                error_text.value = str(exc)
                error_text.visible = True
                self.page.update()

        save_button = ft.ElevatedButton("Сохранить", on_click=on_submit)

        dialog = ft.AlertDialog(
            title=ft.Text(title),
            content=ft.Container(
                content=ft.Column(
                    [
                        type_group,
                        account_dropdown,
                        to_account_dropdown,
                        amount_field,
                        description_field,
                        category_picker,
                        date_field,
                        error_text,
                    ],
                    spacing=12,
                    width=350,
                ),
            ),
            actions=[
                ft.TextButton("Отмена", on_click=lambda _: self._close_dialog(dialog)),
                save_button,
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        self.page.overlay.append(dialog)
        dialog.open = True
        self.page.update()

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
            delete_button.disabled = True
            delete_button.text = "Удаление..."
            self.page.update()

            try:
                await asyncio.to_thread(self.api_client.delete_transaction, tx["id"])
                dialog.open = False
                self.page.update()
                await self._load_data()
            except (ApiError, BackendUnreachableError) as exc:
                delete_button.disabled = False
                delete_button.text = "Удалить"
                dialog.open = False
                self.page.update()
                self._error_text.value = f"Ошибка удаления: {exc}"
                self._error_text.visible = True
                self.update()

        desc = tx.get("description", "") or "Без описания"
        delete_button = ft.ElevatedButton(
            "Удалить", on_click=on_confirm, bgcolor=ft.Colors.ERROR, color=ft.Colors.ON_ERROR
        )
        dialog = ft.AlertDialog(
            title=ft.Text("Удалить транзакцию?"),
            content=ft.Text(f'Удалить "{desc}"? Это действие необратимо.'),
            actions=[
                ft.TextButton("Отмена", on_click=lambda _: self._close_dialog(dialog)),
                delete_button,
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        self.page.overlay.append(dialog)
        dialog.open = True
        self.page.update()

    def _close_dialog(self, dialog):
        dialog.open = False
        self.page.update()
