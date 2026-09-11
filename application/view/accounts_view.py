import asyncio
from collections import defaultdict

import flet as ft
from application.api import ApiError, BackendUnreachableError
from application.components import BaseView
from application.components.account_group import AccountGroup
from application.components.crypto_summary import CryptoSummary
from application.components.navigation_items import NAVIGATION_ITEMS
from MySpaceShared.components.connection_status import ConnectionBanner
from MySpaceShared.components.empty_state import EmptyState
from MySpaceShared.components.error_state import ErrorState
from MySpaceShared.components.loading_state import LoadingState


class AccountsView(BaseView):
    def __init__(self, route: str, api_client, resource_view=None, account_view=None, connection_banner=None):
        self.api_client = api_client
        self._resource_view = resource_view
        self._account_view = account_view
        self._connection_banner = connection_banner or ConnectionBanner()
        self._disposed = False
        self._accounts: list[dict] = []
        self._resources: list[dict] = []
        self._resource_map: dict[int, dict] = {}

        self._error_text = ft.Text("", size=13, color=ft.Colors.ERROR, visible=False)
        self._accounts_column = ft.Column(spacing=8, scroll=ft.ScrollMode.AUTO, expand=True)
        self._loading = LoadingState()
        self._loading.visible = True

        content = ft.Column(
            controls=[
                self._connection_banner,
                self._error_text,
                self._loading,
                self._accounts_column,
            ],
            expand=True,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        )

        super().__init__(
            content=content, title="Счета", route=route, selected_index=0, navigation_items=NAVIGATION_ITEMS
        )
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
            self._accounts_column.controls.clear()
            self.update()

            if self._resource_view and self._account_view:
                resources = await asyncio.to_thread(self._resource_view.get_all)
                accounts = await asyncio.to_thread(self._account_view.get_all)
            else:
                resources, accounts = await asyncio.gather(
                    asyncio.to_thread(self.api_client.list_resources),
                    asyncio.to_thread(self.api_client.list_accounts),
                )

            if self._disposed:
                return

            self._resources = resources if isinstance(resources, list) else resources.get("results", [])
            self._accounts = accounts if isinstance(accounts, list) else accounts.get("results", [])
            self._resource_map = {r["id"]: r for r in self._resources}

            self._loading.visible = False
            if self._resource_view and not self._resource_view.is_online:
                self._connection_banner.show()
            else:
                self._connection_banner.hide()
            self._rebuild_ui()
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

    def _rebuild_ui(self):
        self._accounts_column.controls.clear()

        grouped = defaultdict(list)
        crypto_accounts = []

        for acc in self._accounts:
            resource = self._resource_map.get(acc.get("resource_definition"))
            is_crypto = resource and resource.get("resource_type") == "asset"
            balance = float(acc.get("current_balance_qty", 0))
            resource_name = resource["name"] if resource else "—"
            icon = self._get_currency_icon(resource_name)

            account_data = {
                "id": acc["id"],
                "name": acc.get("name", ""),
                "balance": f"{balance:,.2f} {resource_name}",
                "icon": icon,
                "on_edit": lambda a=acc: self._show_edit_dialog(a),
                "on_delete": lambda a=acc: self._show_delete_confirm(a),
            }

            if is_crypto:
                crypto_accounts.append(account_data)
            else:
                group = acc.get("group", "")
                grouped[group].append(account_data)

        for group_name in sorted(grouped.keys()):
            accounts_in_group = grouped[group_name]
            total = sum(
                float(a.get("current_balance_qty", 0))
                for a in self._accounts
                if a.get("group", "") == group_name
                and not (self._resource_map.get(a.get("resource_definition"), {}).get("resource_type") == "asset")
            )
            resource_names = set()
            for a in self._accounts:
                if a.get("group", "") == group_name:
                    r = self._resource_map.get(a.get("resource_definition"))
                    if r and r.get("resource_type") != "asset":
                        resource_names.add(r["name"])
            balance_str = f"{total:,.2f}" if len(resource_names) <= 1 else ""
            if len(resource_names) == 1:
                balance_str += f" {next(iter(resource_names))}"

            group_widget = AccountGroup(
                group_name=group_name,
                total_balance=balance_str,
                accounts=accounts_in_group,
            )
            self._accounts_column.controls.append(group_widget)

        if crypto_accounts:
            crypto_total = sum(
                float(a.get("current_balance_qty", 0))
                for a in self._accounts
                if self._resource_map.get(a.get("resource_definition"), {}).get("resource_type") == "asset"
            )
            crypto_widget = CryptoSummary(
                total_usd=f"${crypto_total:,.2f}",
                accounts=crypto_accounts,
            )
            self._accounts_column.controls.append(crypto_widget)

        if not self._accounts_column.controls:
            self._accounts_column.controls.append(
                EmptyState(
                    icon=ft.Icons.ACCOUNT_BALANCE_WALLET,
                    title="Нет счетов",
                    subtitle="Нажмите + чтобы добавить",
                )
            )

        self.update()

    def _show_add_dialog(self, e):
        self._open_account_dialog()

    def _show_edit_dialog(self, account: dict):
        self._open_account_dialog(account=account)

    def _open_account_dialog(self, account: dict | None = None):
        is_edit = account is not None
        title = "Редактировать счет" if is_edit else "Новый счет"

        name_field = ft.TextField(
            label="Название",
            value=account.get("name", "") if is_edit else "",
            border_radius=8,
            autofocus=True,
        )

        resource_options = [
            ft.dropdown.Option(key=str(r["id"]), text=f"{r['name']} ({r.get('ticker', '')})") for r in self._resources
        ]
        resource_dropdown = ft.Dropdown(
            label="Валюта/Ресурс",
            options=resource_options,
            value=str(account.get("resource_definition", ""))
            if is_edit and account.get("resource_definition")
            else None,
            border_radius=8,
            disabled=is_edit,
        )

        group_field = ft.TextField(
            label="Группа",
            value=account.get("group", "") if is_edit else "",
            border_radius=8,
        )

        account_type_options = [
            ft.dropdown.Option(key="main", text="Основной"),
            ft.dropdown.Option(key="trading", text="Торговый"),
            ft.dropdown.Option(key="earn", text="Доходный"),
        ]
        account_type_dropdown = ft.Dropdown(
            label="Тип счета",
            options=account_type_options,
            value=account.get("account_type", "main") if is_edit else "main",
            border_radius=8,
        )

        error_text = ft.Text("", size=12, color=ft.Colors.ERROR, visible=False)

        async def on_submit(e):
            name = name_field.value.strip() if name_field.value else ""
            resource_id = resource_dropdown.value
            group = group_field.value.strip() if group_field.value else ""
            account_type = account_type_dropdown.value or "main"

            if not name:
                error_text.value = "Введите название"
                error_text.visible = True
                self.update()
                return
            if not resource_id:
                error_text.value = "Выберите валюту"
                error_text.visible = True
                self.update()
                return

            save_button.disabled = True
            save_button.text = "Сохранение..."
            self.page.update()

            try:
                payload = {
                    "name": name,
                    "resource_definition": int(resource_id),
                    "group": group,
                    "account_type": account_type,
                }
                if is_edit:
                    if self._account_view:
                        await asyncio.to_thread(self._account_view.update, account["id"], payload)
                    else:
                        await asyncio.to_thread(self.api_client.update_account, account["id"], payload)
                else:
                    if self._account_view:
                        await asyncio.to_thread(self._account_view.add, payload)
                    else:
                        await asyncio.to_thread(self.api_client.create_account, payload)

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
                    [name_field, resource_dropdown, group_field, account_type_dropdown, error_text],
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

    def _show_delete_confirm(self, account: dict):
        async def on_confirm(e):
            delete_button.disabled = True
            delete_button.text = "Удаление..."
            self.page.update()

            try:
                if self._account_view:
                    await asyncio.to_thread(self._account_view.delete, account["id"])
                else:
                    await asyncio.to_thread(self.api_client.delete_account, account["id"])
                self.page.pop_dialog()
                await self._load_data()
            except (ApiError, BackendUnreachableError) as exc:
                delete_button.disabled = False
                delete_button.text = "Удалить"
                self.page.pop_dialog()
                self._error_text.value = f"Ошибка удаления: {exc}"
                self._error_text.visible = True
                self.update()

        delete_button = ft.Button(
            "Удалить", on_click=on_confirm, bgcolor=ft.Colors.ERROR, color=ft.Colors.ON_ERROR
        )
        dialog = ft.AlertDialog(
            title=ft.Text("Удалить счет?"),
            content=ft.Text(f'Удалить "{account.get("name", "")}"? Это действие необратимо.'),
            actions=[
                ft.TextButton("Отмена", on_click=lambda _: self.page.pop_dialog()),
                delete_button,
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        self.page.show_dialog(dialog)

    @staticmethod
    def _get_currency_icon(resource_name: str) -> str:
        icons = {
            "USD": ft.Icons.ATTACH_MONEY,
            "EUR": ft.Icons.EURO,
            "RUB": ft.Icons.CURRENCY_RUBLE,
            "BYN": ft.Icons.MONEY,
            "BTC": ft.Icons.CURRENCY_BITCOIN,
            "ETH": ft.Icons.CURRENCY_BITCOIN,
            "USDT": ft.Icons.ATTACH_MONEY,
            "USDC": ft.Icons.ATTACH_MONEY,
        }
        return icons.get(resource_name, ft.Icons.CIRCLE)
