import asyncio
from collections import defaultdict
from decimal import Decimal

import flet as ft
from application.api import ApiError, BackendUnreachableError, RestClientError
from application.components import BaseView
from application.components.account_group import AccountGroup
from application.components.crypto_summary import CryptoSummary
from application.components.file_save import export_csv
from application.components.navigation_items import NAVIGATION_ITEMS
from application.demo_seed import DemoSeeder
from application.display import FAB_CLEARANCE, account_display_name
from application.view.dialogs import dialog_width, full_width, half_width
from core.app_settings import APP_SETTINGS
from core.csv_export import accounts_csv
from core.group_totals import build_price_map, format_group_total, group_total_in_base
from core.onboarding import OnboardingState

from MySpaceShared.components import AccentIcon, GradientSurface, HeroValue
from MySpaceShared.components.confirm_dialog import ConfirmDialog
from MySpaceShared.components.connection_status import ConnectionBanner
from MySpaceShared.components.empty_state import EmptyState
from MySpaceShared.components.form_kit import apply_field_errors, set_field_error
from MySpaceShared.components.loading_state import LoadingState
from MySpaceShared.core.formatting import format_money
from MySpaceShared.core.tokens import SPACING, accent_gradient

FIELD_LABELS = {
    "name": "Название",
    "resource_definition": "Валюта/ресурс",
    "group": "Группа",
    "account_type": "Тип счёта",
}


def describe_field_errors(errors: dict[str, str]) -> str:
    """Текст общей строки из ошибок полей: «Название: обязательное поле; …»."""
    parts = [f"{FIELD_LABELS.get(field, field)}: {message}" for field, message in errors.items()]
    return "; ".join(parts)


def apply_api_error(
    error_text: ft.Text, exc: ApiError | BackendUnreachableError, fields: dict[str, ft.Control]
) -> None:
    """Ошибки DRF — по полям формы, общий текст — в строку ошибки (2.41/2.42).

    Полевые ошибки подсвечиваются на месте, а строка над кнопкой показывает
    перечень «Название: сообщение» для разобранных полей либо полный читаемый
    текст ошибки (общие ошибки, недоступный сервер, неизвестные поля).
    """
    errors = exc.field_errors if isinstance(exc, ApiError) else {}
    leftovers = apply_field_errors(fields, exc)
    if errors and not leftovers:
        error_text.value = describe_field_errors(errors)
    else:
        error_text.value = str(exc)
    error_text.visible = True


def build_empty_state(show_welcome: bool, on_seed, on_start_fresh) -> ft.Control:
    seed_button = ft.Button("Заполнить примерами", on_click=on_seed)
    if show_welcome:
        return ft.Container(
            content=ft.Column(
                controls=[
                    AccentIcon(ft.Icons.WAVING_HAND, size=72),
                    ft.Text(
                        "Добро пожаловать в MyMoney!",
                        size=22,
                        weight=ft.FontWeight.BOLD,
                        text_align=ft.TextAlign.CENTER,
                    ),
                    ft.Text(
                        "Счета, операции и бюджеты в одном месте. "
                        "Начните с примеров или добавьте первый счёт кнопкой +.",
                        size=14,
                        color=ft.Colors.ON_SURFACE_VARIANT,
                        text_align=ft.TextAlign.CENTER,
                    ),
                    ft.Row(
                        controls=[seed_button, ft.TextButton("Начать с нуля", on_click=on_start_fresh)],
                        alignment=ft.MainAxisAlignment.CENTER,
                        wrap=True,
                    ),
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=SPACING["md"],
            ),
            alignment=ft.Alignment.CENTER,
            padding=ft.Padding.only(top=48, bottom=24),
        )
    return ft.Container(
        content=ft.Column(
            controls=[
                EmptyState(
                    icon=ft.Icons.ACCOUNT_BALANCE_WALLET,
                    title="Нет счетов",
                    subtitle="Нажмите + чтобы добавить",
                ),
                ft.Row(controls=[seed_button], alignment=ft.MainAxisAlignment.CENTER),
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=12,
        ),
        height=360,
    )


RESOURCE_KIND_LABELS = {"currency": "валюта", "asset": "крипта", "custom": "ресурс"}
RESOURCE_KIND_ORDER = {"currency": 0, "asset": 2}


def resource_option_text(resource: dict) -> str:
    """Подпись опции ресурса: «Название (TICKER) · тип»."""
    name = str(resource.get("name") or "").strip()
    ticker = str(resource.get("ticker") or "").strip()
    label = f"{name} ({ticker})" if ticker else name
    kind = RESOURCE_KIND_LABELS.get(str(resource.get("resource_type") or ""), "ресурс")
    return f"{label} · {kind}"


def resource_sort_key(resource: dict) -> tuple[int, str]:
    """Порядок: фиатные валюты → свои ресурсы → крипта → прочее."""
    kind = str(resource.get("resource_type") or "")
    if kind == "currency":
        rank = 0
    elif resource.get("owner"):
        rank = 1
    else:
        rank = RESOURCE_KIND_ORDER.get(kind, 3)
    return rank, str(resource.get("name") or "").casefold()


class AccountsView(BaseView):
    def __init__(
        self,
        route: str,
        api_client,
        resource_view=None,
        account_view=None,
        connection_banner=None,
        onboarding: OnboardingState | None = None,
        seeder_factory=None,
    ):
        self.api_client = api_client
        self._resource_view = resource_view
        self._account_view = account_view
        self._connection_banner = connection_banner or ConnectionBanner()
        self._disposed = False
        self._accounts: list[dict] = []
        self._resources: list[dict] = []
        self._resource_map: dict[int, dict] = {}
        self._base_currency: str | None = None
        self._prices: dict[str, Decimal] = {}
        self._onboarding = onboarding if onboarding is not None else OnboardingState()
        self._seeder_factory = seeder_factory
        self._seeding = False
        self._seed_busy = False

        self._error_text = ft.Text("", size=13, color=ft.Colors.ERROR, visible=False)
        self._seed_status = ft.Text("", size=13, color=ft.Colors.ON_SURFACE_VARIANT, visible=False)
        self._accounts_column = ft.Column(spacing=SPACING["md"], scroll=ft.ScrollMode.AUTO, expand=True)
        self._loading = LoadingState()
        self._loading.visible = True

        content = ft.Column(
            controls=[
                self._connection_banner,
                self._error_text,
                self._seed_status,
                self._loading,
                ft.Row(
                    controls=[
                        ft.Container(expand=True),
                        ft.IconButton(
                            ft.Icons.DOWNLOAD_OUTLINED,
                            tooltip="Экспорт CSV",
                            on_click=self._export_csv,
                        ),
                    ],
                ),
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
        self._load_task = asyncio.create_task(self._load_data())

    def dispose(self):
        self._disposed = True

    async def _load_data(self):
        try:
            self._error_text.visible = False
            self._seed_busy = False
            self._seed_status.visible = False
            self._loading.visible = True
            self._accounts_column.controls.clear()
            self.update()

            if self._resource_view and self._account_view:
                resources = await asyncio.to_thread(self._resource_view.get_all)
                accounts = await asyncio.to_thread(self._account_view.get_all)
                online = bool(self._resource_view.is_online)
            else:
                resources, accounts = await asyncio.gather(
                    asyncio.to_thread(self.api_client.list_resources),
                    asyncio.to_thread(self.api_client.list_accounts),
                )
                online = True

            if self._disposed:
                return

            self._resources = resources if isinstance(resources, list) else resources.get("results", [])
            self._accounts = accounts if isinstance(accounts, list) else accounts.get("results", [])
            self._resource_map = {r["id"]: r for r in self._resources}

            if online:
                self._base_currency, self._prices = await asyncio.to_thread(self._fetch_fx_context)
            else:
                self._base_currency, self._prices = None, {}

            self._loading.visible = False
            if self._resource_view and not self._resource_view.is_online:
                self._connection_banner.show()
            else:
                self._connection_banner.hide()
            self._rebuild_ui()
        except BackendUnreachableError:
            if not self._disposed:
                self._loading.visible = False
                self._show_error("Сервер недоступен")
        except ApiError as exc:
            if not self._disposed:
                self._loading.visible = False
                self._show_error(f"Ошибка загрузки: {exc}")

    def _fetch_fx_context(self) -> tuple[str | None, dict[str, Decimal]]:
        try:
            profile = self.api_client.me()
        except RestClientError:
            return None, {}
        base = profile.get("base_currency") if isinstance(profile, dict) else None
        if not isinstance(base, str) or not base.strip():
            return None, {}
        try:
            prices_rows = self.api_client.get_prices()
        except RestClientError:
            return base.strip().upper(), {}
        return base.strip().upper(), build_price_map(prices_rows)

    def _rebuild_ui(self):
        self._accounts_column.controls.clear()

        grouped = defaultdict(list)
        grouped_raw = defaultdict(list)
        crypto_accounts = []

        for acc in self._accounts:
            resource = self._resource_map.get(acc.get("resource_definition"))
            is_crypto = resource and resource.get("resource_type") == "asset"
            balance = float(acc.get("current_balance_qty", 0))
            resource_name = resource["name"] if resource else "—"
            icon = self._get_currency_icon(resource_name)

            account_data = {
                "id": acc["id"],
                "name": account_display_name(acc, resource["name"] if resource else ""),
                "balance": format_money(balance, resource_name),
                "icon": icon,
                "on_edit": lambda a=acc: self._show_edit_dialog(a),
                "on_delete": lambda a=acc: self._show_delete_confirm(a),
            }

            if is_crypto:
                crypto_accounts.append(account_data)
            else:
                group = acc.get("group", "")
                grouped[group].append(account_data)
                grouped_raw[group].append(acc)

        hero = self._build_summary_hero(grouped_raw)
        if hero is not None:
            self._accounts_column.controls.append(hero)

        for group_name in sorted(grouped.keys()):
            balance_str = self._group_balance_text(grouped_raw[group_name])
            group_widget = AccountGroup(
                group_name=group_name,
                total_balance=balance_str,
                accounts=grouped[group_name],
            )
            self._accounts_column.controls.append(group_widget)

        if crypto_accounts:
            crypto_total = sum(
                float(a.get("current_balance_qty", 0))
                for a in self._accounts
                if self._resource_map.get(a.get("resource_definition"), {}).get("resource_type") == "asset"
            )
            crypto_widget = CryptoSummary(
                total_usd=format_money(crypto_total, prefix="$"),
                accounts=crypto_accounts,
            )
            self._accounts_column.controls.append(crypto_widget)

        if not self._accounts_column.controls:
            self._accounts_column.controls.append(
                build_empty_state(
                    not self._onboarding.welcome_seen,
                    self._on_seed_demo,
                    self._on_start_fresh,
                )
            )
        else:
            self._accounts_column.controls.append(ft.Container(height=FAB_CLEARANCE))

        self.update()

    def _group_balance_text(self, group_accounts: list[dict]) -> str:
        if self._base_currency:
            result = group_total_in_base(
                group_accounts,
                self._resource_map,
                self._base_currency,
                self._prices,
            )
            return format_group_total(result, self._base_currency)

        total = sum(float(a.get("current_balance_qty", 0)) for a in group_accounts)
        resource_names = set()
        for a in group_accounts:
            r = self._resource_map.get(a.get("resource_definition"))
            if r:
                resource_names.add(r["name"])
        balance_str = format_money(total) if len(resource_names) <= 1 else ""
        if len(resource_names) == 1:
            balance_str += f" {next(iter(resource_names))}"
        return balance_str

    def _build_summary_hero(self, grouped_raw: dict) -> ft.Control | None:
        accounts = [acc for raws in grouped_raw.values() for acc in raws]
        if not accounts or not self._base_currency:
            return None
        result = group_total_in_base(
            accounts,
            self._resource_map,
            self._base_currency,
            self._prices,
        )
        if result.converted == 0:
            return None

        value = format_money(result.total, self._base_currency)
        delta = f"курс недоступен: {', '.join(result.missing_symbols)}" if result.has_missing else None
        hero_value = HeroValue(
            value,
            label="Всего на счетах",
            delta=delta,
            delta_color=ft.Colors.with_opacity(0.85, ft.Colors.WHITE),
            value_size=32,
        )
        hero_value.value_text.color = ft.Colors.WHITE
        hero_value.label_text.color = ft.Colors.with_opacity(0.85, ft.Colors.WHITE)

        content = ft.Row(
            [
                AccentIcon(ft.Icons.ACCOUNT_BALANCE_WALLET, size=44, color=ft.Colors.WHITE),
                hero_value,
            ],
            spacing=SPACING["lg"],
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )
        return GradientSurface(
            content,
            gradient=accent_gradient(APP_SETTINGS.accent_color),
            padding=ft.Padding.symmetric(horizontal=20, vertical=16),
        )

    def _show_error(self, message: str) -> None:
        self._error_text.value = message
        self._error_text.visible = True
        self.update()

    async def _export_csv(self, _event=None) -> None:
        """Сохранить счета и балансы в CSV-файл."""
        await export_csv(
            self.page,
            kind="accounts",
            content=accounts_csv(self._accounts),
            on_error=self._show_error,
        )

    def _make_seeder(self) -> DemoSeeder:
        if self._seeder_factory is not None:
            return self._seeder_factory()
        return DemoSeeder(
            resource_view=self._resource_view,
            account_view=self._account_view,
            api_client=self.api_client,
        )

    def _set_seed_status(self, message: str, is_error: bool) -> None:
        self._seed_status.value = message
        self._seed_status.color = ft.Colors.ERROR if is_error else ft.Colors.ON_SURFACE_VARIANT
        self._seed_status.visible = bool(message)

    def _on_start_fresh(self, e):
        self._onboarding.mark_welcome_seen()
        self._rebuild_ui()

    async def _on_seed_demo(self, e=None):
        if self._seeding:
            return
        self._seeding = True
        self._seed_busy = True
        self._set_seed_status("Заполнение примеров...", is_error=False)
        self._rebuild_ui()
        try:
            result = await asyncio.to_thread(self._make_seeder().seed)
            if self._disposed:
                return
            self._seed_busy = False
            if result.status == "created":
                self._onboarding.mark_welcome_seen()
            await self._load_data()
            if result.status != "created":
                self._set_seed_status(
                    result.message,
                    is_error=result.status in ("partial", "error", "offline"),
                )
                self.update()
        except Exception as exc:
            if not self._disposed:
                self._seed_busy = False
                await self._load_data()
                self._set_seed_status(f"Ошибка заполнения: {exc}", is_error=True)
                self.update()
        finally:
            self._seeding = False

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
            border=ft.OutlineInputBorder(border_radius=8),
            autofocus=True,
        )

        resource_options = [
            ft.dropdown.Option(key=str(resource["id"]), text=resource_option_text(resource))
            for resource in sorted(self._resources, key=resource_sort_key)
        ]
        resource_dropdown = ft.Dropdown(
            label="Валюта/Ресурс",
            options=resource_options,
            value=str(account.get("resource_definition", ""))
            if is_edit and account.get("resource_definition")
            else None,
            border=ft.OutlineInputBorder(border_radius=8),
            enable_filter=True,
            disabled=is_edit,
        )

        group_field = ft.TextField(
            label="Группа",
            value=account.get("group", "") if is_edit else "",
            border=ft.OutlineInputBorder(border_radius=8),
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
            border=ft.OutlineInputBorder(border_radius=8),
        )

        error_text = ft.Text("", size=12, color=ft.Colors.ERROR, visible=False)
        form_fields = {
            "name": name_field,
            "resource_definition": resource_dropdown,
            "group": group_field,
            "account_type": account_type_dropdown,
        }

        def clear_field_errors() -> None:
            apply_field_errors(form_fields, {})

        def show_validation_error(field: ft.Control, message: str) -> None:
            set_field_error(field, message)
            error_text.value = message
            error_text.visible = True
            self.update()

        async def on_submit(e):
            clear_field_errors()
            name = name_field.value.strip() if name_field.value else ""
            resource_id = resource_dropdown.value
            group = group_field.value.strip() if group_field.value else ""
            account_type = account_type_dropdown.value or "main"

            if not name:
                show_validation_error(name_field, "Введите название")
                return
            if not resource_id:
                show_validation_error(resource_dropdown, "Выберите валюту")
                return

            save_button.disabled = True
            save_button.content = "Сохранение..."
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
                save_button.content = "Сохранить"
                apply_api_error(error_text, exc, form_fields)
                self.page.update()

        save_button = ft.Button("Сохранить", on_click=on_submit)

        dialog = ft.AlertDialog(
            title=ft.Text(title),
            content=ft.Container(
                content=ft.ResponsiveRow(
                    [
                        *full_width(name_field, resource_dropdown),
                        *half_width(group_field, account_type_dropdown),
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
        self.page.show_dialog(dialog)

    def _show_delete_confirm(self, account: dict):
        async def delete(e):
            e.control.disabled = True
            e.control.content = "Удаление..."
            self.page.update()

            try:
                if self._account_view:
                    await asyncio.to_thread(self._account_view.delete, account["id"])
                else:
                    await asyncio.to_thread(self.api_client.delete_account, account["id"])
                self.page.pop_dialog()
                await self._load_data()
            except (ApiError, BackendUnreachableError) as exc:
                e.control.disabled = False
                e.control.content = "Удалить"
                self.page.pop_dialog()
                self._show_error(f"Ошибка удаления: {exc}")

        ConfirmDialog(
            title="Удалить счет?",
            message=f'Удалить "{account_display_name(account)}"? Это действие необратимо.',
            on_confirm=lambda e: asyncio.create_task(delete(e)),
        ).show(self.page)

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
