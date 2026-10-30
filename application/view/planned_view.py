import asyncio
import datetime

import flet as ft
from application.api import ApiError, BackendUnreachableError
from application.components import BaseView
from application.components.cross_app_budget_card import CrossAppBudgetCard
from application.components.navigation_items import NAVIGATION_ITEMS
from application.components.planned_transaction_card import PlannedTransactionCard
from application.components.recurrence_fields import DEFAULT_FREQUENCY, FREQUENCY_OPTIONS, recurrence_rule_text
from application.display import FAB_CLEARANCE, account_currency, account_display_name, is_read_only_transaction
from application.planned_actions import execute_planned
from application.transaction_form import form_state
from application.view.amount_currency import AmountCurrencyMixin
from application.view.category_actions import CategoryActionsMixin
from application.view.dialogs import dialog_width, full_width, half_width
from application.view.planned_sections import (
    build_plan_card,
    filter_cross_app_budgets,
    load_cross_app_budgets,
)
from core.recurrence import RecurrenceRule

from MySpaceShared.components.confirm_dialog import ConfirmDialog
from MySpaceShared.components.connection_status import ConnectionBanner
from MySpaceShared.components.empty_state import EmptyState
from MySpaceShared.components.form_kit import MoneyField, parse_money
from MySpaceShared.components.loading_state import LoadingState
from MySpaceShared.components.section_header import SectionHeader

BUDGETS_SECTION_TITLE = "Запланировано из задач/событий"


class PlannedView(AmountCurrencyMixin, CategoryActionsMixin, BaseView):
    def __init__(self, route: str, api_client, transaction_view=None, account_view=None, connection_banner=None):
        self.api_client = api_client
        self._transaction_view = transaction_view
        self._account_view = account_view
        self._connection_banner = connection_banner or ConnectionBanner()
        self._disposed = False
        self._transactions: list[dict] = []
        self._budgets: list[dict] = []
        self._category_rows: list[dict] = []
        self._accounts: list[dict] = []
        self._account_map: dict[int, dict] = {}

        self._error_text = ft.Text("", size=13, color=ft.Colors.ERROR, visible=False)
        self._loading = LoadingState()
        self._loading.visible = True
        self._tx_list = ft.Column(spacing=8)
        self._budget_hint = ft.Text(
            "",
            size=12,
            color=ft.Colors.ON_SURFACE_VARIANT,
            visible=False,
        )
        self._budget_items = ft.Column(spacing=8)
        self._budget_section = ft.Column(
            spacing=8,
            visible=False,
            controls=[
                SectionHeader(BUDGETS_SECTION_TITLE),
                self._budget_hint,
                self._budget_items,
            ],
        )
        self._scroll_column = ft.Column(
            controls=[self._tx_list, self._budget_section, ft.Container(height=FAB_CLEARANCE)],
            spacing=16,
            expand=True,
            scroll=ft.ScrollMode.AUTO,
        )

        content = ft.Column(
            controls=[
                self._connection_banner,
                self._error_text,
                self._loading,
                self._scroll_column,
            ],
            expand=True,
        )

        super().__init__(
            content=content, title="Запланированные", route=route, selected_index=1, navigation_items=NAVIGATION_ITEMS
        )
        self.floating_action_button = ft.FloatingActionButton(
            icon=ft.Icons.ADD,
            on_click=self._show_add_dialog,
            bgcolor=ft.Colors.PRIMARY,
            foreground_color=ft.Colors.ON_PRIMARY,
        )

    def did_mount(self):
        super().did_mount()
        self._load_task = asyncio.create_task(self._load_data())

    def dispose(self):
        self._disposed = True

    async def _load_data(self):
        try:
            self._error_text.visible = False
            self._loading.visible = True
            self._tx_list.controls.clear()
            self.update()

            if self._transaction_view and self._account_view:
                all_txs = await asyncio.to_thread(self._transaction_view.get_all)
                accounts = await asyncio.to_thread(self._account_view.get_all)
            else:
                transactions, accounts = await asyncio.gather(
                    asyncio.to_thread(self.api_client.list_transactions),
                    asyncio.to_thread(self.api_client.list_accounts),
                )
                all_txs = transactions if isinstance(transactions, list) else transactions.get("results", [])

            if self._disposed:
                return

            self._transactions = [tx for tx in all_txs if tx.get("is_planned") and not is_read_only_transaction(tx)]
            self._accounts = accounts if isinstance(accounts, list) else accounts.get("results", [])
            self._account_map = {a["id"]: a for a in self._accounts}

            self._loading.visible = False
            if self._transaction_view and not self._transaction_view.is_online:
                self._connection_banner.show()
            else:
                self._connection_banner.hide()
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

        if not self._disposed:
            await self._load_budgets()
            await self._load_categories()

    async def _load_budgets(self) -> None:
        if self._disposed:
            return
        self._budgets, hint = await load_cross_app_budgets(self.api_client, self._transaction_view)
        if self._disposed:
            return
        self._budget_hint.value = hint
        self._render_budget_section()

    def _render_budget_section(self) -> None:
        self._budget_items.controls.clear()
        if self._budgets:
            for item in self._budgets:
                self._budget_items.controls.append(CrossAppBudgetCard(item))
            self._budget_hint.visible = False
            self._budget_section.visible = True
        elif self._budget_hint.value:
            self._budget_hint.visible = True
            self._budget_section.visible = True
        else:
            self._budget_hint.visible = False
            self._budget_section.visible = False
        self.update()

    def _rebuild_list(self):
        self._tx_list.controls.clear()

        if not self._transactions:
            self._tx_list.controls.append(
                EmptyState(
                    icon=ft.Icons.EVENT_NOTE,
                    title="Нет запланированных",
                    subtitle="Нажмите + чтобы добавить",
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
        return build_plan_card(
            tx,
            self._account_map,
            on_execute=self._execute_transaction,
            on_edit=self._show_edit_dialog,
            on_delete=self._show_delete_confirm,
        )

    async def _execute_transaction(self, tx: dict):
        try:
            await execute_planned(self._transaction_view, self.api_client, tx)
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

        account_options = [ft.dropdown.Option(key=str(a["id"]), text=account_display_name(a)) for a in self._accounts]
        account_dropdown = ft.Dropdown(
            label="Счёт", options=account_options, border=ft.OutlineInputBorder(border_radius=8)
        )

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

        amount_field = MoneyField(
            label="Сумма",
            currency="",
            border=ft.OutlineInputBorder(border_radius=8),
        )
        description_field = ft.TextField(label="Описание", border=ft.OutlineInputBorder(border_radius=8))
        account_dropdown.on_change = lambda event: self._sync_amount_currency(amount_field, event.control.value)
        category_picker = self._build_category_picker(tx.get("category", "") if is_edit else "")

        now = datetime.datetime.now()
        if is_edit:
            try:
                now = datetime.datetime.fromisoformat(tx.get("date", now.isoformat()))
            except (ValueError, TypeError):
                now = datetime.datetime.now()

        date_field = ft.TextField(
            label="Плановая дата",
            value=now.strftime("%Y-%m-%d"),
            border=ft.OutlineInputBorder(border_radius=8),
            read_only=True,
            suffix=ft.IconButton(
                icon=ft.Icons.CALENDAR_MONTH,
                icon_size=20,
                on_click=lambda _: self._open_date_picker(date_field),
            ),
        )

        recurrence_switch = ft.Switch(label="Повторяющаяся", value=False)
        frequency_dropdown = ft.Dropdown(
            label="Частота",
            options=FREQUENCY_OPTIONS,
            value=DEFAULT_FREQUENCY.value,
            border=ft.OutlineInputBorder(border_radius=8),
            visible=False,
        )
        interval_field = ft.TextField(
            label="Интервал",
            value="1",
            keyboard_type=ft.KeyboardType.NUMBER,
            border=ft.OutlineInputBorder(border_radius=8),
            visible=False,
            width=100,
        )

        def on_recurrence_toggle(event) -> None:
            visible = bool(event.control.value)
            frequency_dropdown.visible = visible
            interval_field.visible = visible
            dialog.update()

        recurrence_switch.on_change = on_recurrence_toggle

        error_text = ft.Text("", size=12, color=ft.Colors.ERROR, visible=False)

        if is_edit:
            entries = tx.get("entries", [])
            if entries:
                state = form_state(entries, allow_transfer=False)
                amount_field.value = state.amount_text
                account_dropdown.value = state.account_id
                amount_field.set_currency(account_currency(self._accounts, state.account_id))
                type_group.value = state.tx_type
            description_field.value = tx.get("description", "")
            if tx.get("recurrence_rule"):
                recurrence_switch.value = True
                frequency_dropdown.visible = True
                interval_field.visible = True
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
                self.page.update()
                return
            if not account_id_str:
                error_text.value = "Выберите счёт"
                error_text.visible = True
                self.page.update()
                return

            amount = parse_money(amount_str)
            if amount is None:
                error_text.value = "Некорректная сумма"
                error_text.visible = True
                self.page.update()
                return

            quantity = amount if tx_type == "income" else -amount
            entries = [{"account": int(account_id_str), "quantity": quantity, "amount": quantity, "unit_price": 1}]

            date_str = date_field.value or now.strftime("%Y-%m-%d")
            try:
                date_val = datetime.datetime.fromisoformat(date_str)
            except ValueError:
                date_val = now
            if is_edit:
                date_val = date_val.replace(
                    hour=now.hour, minute=now.minute, second=now.second, microsecond=now.microsecond
                )

            recurrence_rule = ""
            if recurrence_switch.value:
                recurrence_rule = recurrence_rule_text(frequency_dropdown.value, interval_field.value)

            payload = {
                "date": date_val.isoformat(),
                "entries": entries,
                "category": category,
                "description": description,
                "is_planned": True,
                "recurrence_rule": recurrence_rule,
            }

            save_button.disabled = True
            save_button.content = "Сохранение..."
            self.page.update()

            try:
                if is_edit:
                    if self._transaction_view:
                        await asyncio.to_thread(self._transaction_view.update, tx["id"], payload)
                    else:
                        await asyncio.to_thread(self.api_client.update_transaction, tx["id"], payload)
                else:
                    if self._transaction_view:
                        await asyncio.to_thread(self._transaction_view.add, payload)
                    else:
                        await asyncio.to_thread(self.api_client.create_transaction, payload)

                self.page.pop_dialog()
                await self._load_data()
            except (ApiError, BackendUnreachableError) as exc:
                save_button.disabled = False
                save_button.content = "Сохранить"
                error_text.value = str(exc)
                error_text.visible = True
                self.page.update()

        save_button = ft.Button("Сохранить", on_click=on_submit)

        dialog = ft.AlertDialog(
            title=ft.Text(title),
            content=ft.Container(
                content=ft.ResponsiveRow(
                    [
                        *full_width(type_group),
                        *half_width(account_dropdown),
                        *half_width(amount_field),
                        *full_width(description_field),
                        *full_width(category_picker),
                        *half_width(date_field),
                        *full_width(recurrence_switch),
                        *half_width(frequency_dropdown),
                        *half_width(interval_field),
                        *full_width(error_text),
                    ],
                    spacing=12,
                    run_spacing=12,
                    columns=12,
                    width=dialog_width(self),
                ),
            ),
            actions=[
                ft.TextButton("Отмена", on_click=lambda _: self.page.pop_dialog()),
                save_button,
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        self._recurrence_dialog = dialog
        self.page.show_dialog(dialog)

    def _open_date_picker(self, date_field):
        picker = ft.DatePicker(
            on_change=lambda e: self._on_date_picked(e, date_field),
        )
        self.page.show_dialog(picker)

    def _on_date_picked(self, e, date_field):
        if e.control.value:
            date_field.value = e.control.value.strftime("%Y-%m-%d")
            date_field.update()

    def _show_delete_confirm(self, tx: dict):
        async def delete(e):
            e.control.disabled = True
            e.control.content = "Удаление..."
            self.page.update()

            try:
                if self._transaction_view:
                    await asyncio.to_thread(self._transaction_view.delete, tx["id"])
                else:
                    await asyncio.to_thread(self.api_client.delete_transaction, tx["id"])
                self.page.pop_dialog()
                await self._load_data()
            except (ApiError, BackendUnreachableError) as exc:
                e.control.disabled = False
                e.control.content = "Удалить"
                self.page.pop_dialog()
                self._error_text.value = f"Ошибка удаления: {exc}"
                self._error_text.visible = True
                self.update()

        desc = tx.get("description", "") or "Без описания"
        ConfirmDialog(
            title="Удалить план?",
            message=f'Удалить "{desc}"?',
            on_confirm=lambda e: asyncio.create_task(delete(e)),
        ).show(self.page)


__all__ = ["PlannedView", "filter_cross_app_budgets"]
