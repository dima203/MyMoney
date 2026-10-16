import asyncio
import datetime
from collections import defaultdict

import flet as ft
from application.api import ApiError, BackendUnreachableError
from application.components import BaseView
from application.components.category_picker import CategoryPicker
from application.components.navigation_items import NAVIGATION_ITEMS
from application.components.transaction_card import TransactionCard
from application.display import FAB_CLEARANCE, account_display_name, is_read_only_transaction
from application.transaction_form import form_state
from MySpaceShared.components.confirm_dialog import ConfirmDialog
from MySpaceShared.components.connection_status import ConnectionBanner
from MySpaceShared.components.empty_state import EmptyState
from MySpaceShared.components.loading_state import LoadingState

DAY_HEADER_HEIGHT = 36
SCROLL_EPSILON = 0.5


def is_native_amount(value) -> bool:
    if value is None:
        return True
    try:
        return abs(float(value) - 1.0) < 1e-9
    except (TypeError, ValueError):
        return True


def resolve_row_currency(entries: list[dict], account_map: dict) -> str:
    """Валюта строки: общий unit «родных» записей; пусто при смешанных переводах."""
    native_units: set[str] = set()
    all_units: set[str] = set()
    for entry in entries:
        unit = str(account_map.get(entry.get("account"), {}).get("resource") or "").strip()
        if not unit:
            continue
        all_units.add(unit)
        if is_native_amount(entry.get("unit_price")):
            native_units.add(unit)
    if len(native_units) == 1:
        return next(iter(native_units))
    if not native_units and len(all_units) == 1:
        return next(iter(all_units))
    return ""


def day_group_offsets(
    content_height: float,
    card_counts: list[int],
    spacing: int = 8,
    header_height: int = DAY_HEADER_HEIGHT,
    trailer_height: int = FAB_CLEARANCE,
) -> list[float] | None:
    """Y-координаты шапок групп в контенте списка; None, если геометрия непригодна."""
    n_groups = len(card_counts)
    n_cards = sum(card_counts)
    if n_groups == 0 or n_cards == 0:
        return []
    usable = content_height - n_groups * header_height - (n_cards + n_groups) * spacing - trailer_height
    card_height = usable / n_cards
    if card_height <= 0:
        return None
    offsets: list[float] = []
    y = 0.0
    for count in card_counts:
        offsets.append(y)
        y += header_height + spacing + count * (card_height + spacing)
    return offsets


def day_group_index(offsets: list[float], pixels: float) -> int:
    """Индекс верхней видимой группы: самая большая шапка, не ниже точки фиксации."""
    index = 0
    for i, offset in enumerate(offsets):
        if offset <= pixels + SCROLL_EPSILON:
            index = i
        else:
            break
    return index


class TransactionsView(BaseView):
    def __init__(self, route: str, api_client, transaction_view=None, account_view=None, connection_banner=None):
        self.api_client = api_client
        self._transaction_view = transaction_view
        self._account_view = account_view
        self._connection_banner = connection_banner or ConnectionBanner()
        self._disposed = False
        self._transactions: list[dict] = []
        self._accounts: list[dict] = []
        self._account_map: dict[int, dict] = {}
        self._categories: list[str] = []
        self._day_groups: list[tuple[str, int]] = []

        self._error_text = ft.Text("", size=13, color=ft.Colors.ERROR, visible=False)
        self._loading = LoadingState()
        self._loading.visible = True
        self._pinned_label = ft.Text("", size=13, weight=ft.FontWeight.W_600, color=ft.Colors.ON_SURFACE_VARIANT)
        self._pinned_header = ft.Container(
            content=self._pinned_label,
            height=DAY_HEADER_HEIGHT,
            left=0,
            right=0,
            top=0,
            padding=ft.Padding.symmetric(horizontal=16),
            alignment=ft.Alignment.CENTER_LEFT,
            bgcolor=ft.Colors.SURFACE,
            visible=False,
            ignore_interactions=True,
        )
        self._tx_list = ft.Column(spacing=8, scroll=ft.ScrollMode.AUTO, expand=True, on_scroll=self._on_tx_scroll)

        self._filter_category = ft.Dropdown(
            label="Категория",
            options=[ft.dropdown.Option("Все")],
            value="Все",
            border=ft.OutlineInputBorder(border_radius=8),
            width=160,
            on_select=self._apply_filters,
        )
        self._filter_bar = ft.Row(
            controls=[self._filter_category, ft.Container(expand=True)],
            alignment=ft.MainAxisAlignment.START,
        )

        content = ft.Column(
            controls=[
                self._connection_banner,
                self._error_text,
                self._loading,
                self._filter_bar,
                ft.Stack(controls=[self._tx_list, self._pinned_header], expand=True),
            ],
            expand=True,
        )

        super().__init__(
            content=content, title="Транзакции", route=route, selected_index=1, navigation_items=NAVIGATION_ITEMS
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
                transactions = await asyncio.to_thread(self._transaction_view.get_all)
                accounts = await asyncio.to_thread(self._account_view.get_all)
            else:
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
        self._day_groups = []
        self._pinned_label.value = ""
        self._pinned_header.visible = False
        filtered = self._get_filtered_transactions()

        if not filtered:
            self._tx_list.controls.append(
                EmptyState(
                    icon=ft.Icons.RECEIPT_LONG,
                    title="Нет транзакций",
                    subtitle="Нажмите + чтобы добавить",
                )
            )
            self.update()
            return

        grouped = self._group_by_date(filtered)
        self._day_groups = [(date_label, len(txs)) for date_label, txs in grouped.items()]
        for date_label, txs in grouped.items():
            header = ft.Container(
                content=ft.Text(date_label, size=13, weight=ft.FontWeight.W_600, color=ft.Colors.ON_SURFACE_VARIANT),
                height=DAY_HEADER_HEIGHT,
                padding=ft.Padding.symmetric(horizontal=16),
                alignment=ft.Alignment.CENTER_LEFT,
            )
            self._tx_list.controls.append(header)

            for tx in txs:
                card = self._build_card(tx)
                self._tx_list.controls.append(card)

        self._tx_list.controls.append(ft.Container(height=FAB_CLEARANCE))
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

    def _resolve_currency(self, entries: list[dict]) -> str:
        return resolve_row_currency(entries, self._account_map)

    def _on_tx_scroll(self, e):
        show = False
        label = ""
        if self._day_groups and e.max_scroll_extent > SCROLL_EPSILON:
            offsets = day_group_offsets(e.extent_total, [count for _, count in self._day_groups])
            if offsets and e.pixels > SCROLL_EPSILON:
                label = self._day_groups[day_group_index(offsets, e.pixels)][0]
                show = True
        if show:
            changed = not self._pinned_header.visible or self._pinned_label.value != label
            self._pinned_label.value = label
            self._pinned_header.visible = True
            if changed:
                self.update()
        elif self._pinned_header.visible:
            self._pinned_header.visible = False
            self.update()

    def _build_card(self, tx: dict) -> TransactionCard:
        entries = tx.get("entries", [])
        total = sum(float(e.get("amount", 0)) for e in entries)
        first_entry = entries[0] if entries else {}
        account_id = first_entry.get("account")
        account = self._account_map.get(account_id, {})
        account_name = account_display_name(account)
        currency = self._resolve_currency(entries)

        try:
            timestamp = datetime.datetime.fromisoformat(tx.get("date", ""))
        except (ValueError, TypeError):
            timestamp = None

        return TransactionCard(
            description=tx.get("description", ""),
            amount=total,
            account_name=account_name,
            currency=currency,
            category=tx.get("category", ""),
            timestamp=timestamp,
            on_edit=lambda t=tx: self._show_edit_dialog(t),
            on_delete=lambda t=tx: self._show_delete_confirm(t),
            read_only=is_read_only_transaction(tx),
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

        account_options = [ft.dropdown.Option(key=str(a["id"]), text=account_display_name(a)) for a in self._accounts]
        account_dropdown = ft.Dropdown(
            label="Счёт", options=account_options, border=ft.OutlineInputBorder(border_radius=8)
        )

        to_account_dropdown = ft.Dropdown(
            label="Счёт получения",
            options=account_options,
            border=ft.OutlineInputBorder(border_radius=8),
            visible=False,
        )

        amount_field = ft.TextField(
            label="Сумма", keyboard_type=ft.KeyboardType.NUMBER, border=ft.OutlineInputBorder(border_radius=8)
        )
        description_field = ft.TextField(label="Описание", border=ft.OutlineInputBorder(border_radius=8))

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
            border=ft.OutlineInputBorder(border_radius=8),
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
                state = form_state(entries)
                amount_field.value = state.amount_text
                account_dropdown.value = state.account_id
                type_group.value = state.tx_type
                if state.to_account_id is not None:
                    to_account_dropdown.visible = True
                    to_account_dropdown.value = state.to_account_id
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
            if is_edit:
                date_val = date_val.replace(
                    hour=now.hour, minute=now.minute, second=now.second, microsecond=now.microsecond
                )

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
                save_button.text = "Сохранить"
                error_text.value = str(exc)
                error_text.visible = True
                self.page.update()

        save_button = ft.Button("Сохранить", on_click=on_submit)

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
                ft.TextButton("Отмена", on_click=lambda _: self.page.pop_dialog()),
                save_button,
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
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
            e.control.text = "Удаление..."
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
                e.control.text = "Удалить"
                self.page.pop_dialog()
                self._error_text.value = f"Ошибка удаления: {exc}"
                self._error_text.visible = True
                self.update()

        desc = tx.get("description", "") or "Без описания"
        ConfirmDialog(
            title="Удалить транзакцию?",
            message=f'Удалить "{desc}"? Это действие необратимо.',
            on_confirm=lambda e: asyncio.create_task(delete(e)),
        ).show(self.page)
