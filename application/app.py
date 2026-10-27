"""Главный оркестратор MyMoney."""

import asyncio
import logging
import os

import flet as ft
from application.api import (
    ApiError,
    BackendUnreachableError,
    RestClient,
)
from application.components.command_palette import HOTKEY_HINT, HOTKEY_KEY, CommandPalette, as_rows
from application.screens import LoginView
from application.view import SplashView
from core import APP_SETTINGS, build_theme, theme_mode_value
from core.config import SETTINGS
from database.views import AccountView, ResourceView, TransactionView

from MySpaceShared.components.connection_status import ConnectionBanner
from MySpaceShared.components.notifications import NotificationsCenter
from MySpaceShared.components.utils import is_mobile_page

logger = logging.getLogger(__name__)

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")


class MyMoneyApp:
    def __init__(self):
        self.page = None
        self.api_client = RestClient()
        self._resource_view: ResourceView | None = None
        self._account_view: AccountView | None = None
        self._transaction_view: TransactionView | None = None
        self._connection_banner = ConnectionBanner()
        self._palette: CommandPalette | None = None

    def _init_offline_views(self) -> None:
        if self._resource_view is not None:
            return
        os.makedirs(DATA_DIR, exist_ok=True)
        self._resource_view = ResourceView(self.api_client, DATA_DIR)
        self._account_view = AccountView(self.api_client, DATA_DIR)
        self._transaction_view = TransactionView(self.api_client, DATA_DIR)

    def _mount(self, view) -> None:
        """Добавить раздел с действиями «Поиск» и «Уведомления» в шапке."""
        notifications = NotificationsCenter(self.api_client)
        notifications.attach(self.page)
        view.notifications = notifications
        view.app_bar.actions = [
            ft.IconButton(
                ft.Icons.SEARCH,
                tooltip=f"Поиск ({HOTKEY_HINT})",
                on_click=lambda _event: self._open_palette(),
            ),
            notifications.badge,
        ]
        self.page.views.append(view)
        self.page.run_task(notifications.load)

    def _palette_rows(self) -> tuple[list[dict], list[dict]]:
        transactions = self._transaction_view.get_all() if self._transaction_view is not None else []
        accounts = self._account_view.get_all() if self._account_view is not None else []
        return as_rows(transactions), as_rows(accounts)

    def _open_palette(self) -> None:
        """Открыть палитру: только на рабочем маршруте и не поверх уже открытой."""
        if self.page is None or self._palette is not None:
            return
        if getattr(self.page, "route", None) in (None, "", "/login"):
            return
        self._palette = CommandPalette(
            load_rows=self._palette_rows,
            on_navigate=self.page.navigate,
            on_close=self._palette_closed,
        )
        self._palette.show(self.page)

    def _palette_closed(self) -> None:
        self._palette = None

    def _on_keyboard(self, event: ft.KeyboardEvent) -> None:
        if getattr(event, "ctrl", False) and str(getattr(event, "key", "")).lower() == HOTKEY_KEY:
            self._open_palette()

    def _has_stored_token(self) -> bool:
        return self.api_client.token_store.load().is_authenticated

    async def _validate_session(self) -> bool:
        if not self._has_stored_token():
            logger.info("No stored token found")
            return False
        try:
            await asyncio.to_thread(self.api_client.me)
            logger.info("Session validated successfully")
            self._init_offline_views()
            await self._sync_pending()
            return True
        except ApiError:
            logger.warning("Session validation failed: ApiError")
            self.api_client.logout()
            return False
        except BackendUnreachableError:
            logger.warning("Session validation failed: backend unreachable")
            self._init_offline_views()
            self._connection_banner.show()
            return True

    async def _sync_pending(self) -> None:
        if self._resource_view is None:
            return
        try:
            remap_resources = self._resource_view.sync_pending()
            remap_accounts = self._account_view.sync_pending()
            remap_transactions = self._transaction_view.sync_pending()
            if remap_resources or remap_accounts or remap_transactions:
                logger.info(
                    "Synced pending: %d resources, %d accounts, %d transactions",
                    len(remap_resources),
                    len(remap_accounts),
                    len(remap_transactions),
                )
        except Exception:
            logger.exception("Failed to sync pending operations")

    def _update_connection_banner(self) -> None:
        if self._resource_view and not self._resource_view.is_online:
            self._connection_banner.show()
        else:
            self._connection_banner.hide()

    def route_change(self) -> None:
        logger.info("route_change: %s", self.page.route)
        for view in self.page.views:
            if hasattr(view, "dispose"):
                view.dispose()
        self.page.views.clear()

        if self.page.route == "/login":
            self.page.views.append(LoginView(SETTINGS.BACKEND_URL, on_success=self._on_login_success))
            self.page.update()
            return

        if not self._has_stored_token():
            self.page.navigate("/login")
            return

        self._init_offline_views()
        self._update_connection_banner()

        if self.page.route == "/accounts":
            from application.view.accounts_view import AccountsView

            self._mount(
                AccountsView(
                    route="/accounts",
                    api_client=self.api_client,
                    resource_view=self._resource_view,
                    account_view=self._account_view,
                    connection_banner=self._connection_banner,
                )
            )
        elif self.page.route == "/transactions":
            from application.view.transactions_view import TransactionsView

            self._mount(
                TransactionsView(
                    route="/transactions",
                    api_client=self.api_client,
                    transaction_view=self._transaction_view,
                    account_view=self._account_view,
                    connection_banner=self._connection_banner,
                )
            )
        elif self.page.route == "/planned":
            from application.view.planned_view import PlannedView

            self._mount(
                PlannedView(
                    route="/planned",
                    api_client=self.api_client,
                    transaction_view=self._transaction_view,
                    account_view=self._account_view,
                    connection_banner=self._connection_banner,
                )
            )
        elif self.page.route == "/analytics":
            from application.view.analytics_view import AnalyticsView

            self._mount(
                AnalyticsView(
                    route="/analytics",
                    api_client=self.api_client,
                    transaction_view=self._transaction_view,
                    account_view=self._account_view,
                    connection_banner=self._connection_banner,
                )
            )
        elif self.page.route == "/settings":
            from application.view.settings_view import SettingsView

            self._mount(
                SettingsView(
                    route="/settings",
                    api_client=self.api_client,
                    on_logout=self._on_logout,
                )
            )
        else:
            self.page.navigate("/accounts")
            return
        self.page.update()

    def _on_login_success(self, view) -> None:
        logger.info("Login success, loading tokens into RestClient")
        token_data = self.api_client.token_store.load()
        self.api_client._access_token = token_data.access
        self.api_client._refresh_token = token_data.refresh
        logger.info("Tokens loaded, navigating to /accounts")
        self._init_offline_views()
        if self.page is not None:
            self.page.navigate("/accounts")

    def _on_logout(self) -> None:
        self.api_client.logout()
        self.page.views.clear()
        self.page.views.append(LoginView(SETTINGS.BACKEND_URL, on_success=self._on_login_success))
        self.page.update()

    async def view_pop(self, e: ft.ViewPopEvent):
        if e.view is not None:
            if hasattr(e.view, "dispose"):
                e.view.dispose()
            if e.view in self.page.views:
                self.page.views.remove(e.view)
            if self.page.views:
                top_view = self.page.views[-1]
                await self.page.push_route(top_view.route)
            else:
                self.page.navigate("/accounts")

    async def main(self, page: ft.Page) -> None:
        self.page = page
        self.page.title = "MyMoney"
        if not is_mobile_page(page):
            self.page.window.min_width = 500
            self.page.window.min_height = 700
            self.page.window.width = 500
            self.page.window.height = 700

        self.page.theme_mode = theme_mode_value(APP_SETTINGS.theme_mode)
        self.page.theme = build_theme(APP_SETTINGS.accent_color)
        self.page.dark_theme = build_theme(APP_SETTINGS.accent_color, dark=True)

        self.page.on_route_change = self.route_change
        self.page.on_view_pop = self.view_pop
        self.page.on_keyboard_event = self._on_keyboard

        splash = SplashView()
        self.page.views.append(splash)
        self.page.update()

        if await self._validate_session():
            logger.info("Session valid, going to /accounts")
            self.page.views.remove(splash)
            self.page.route = "/accounts"
            self.route_change()
        else:
            logger.info("No valid session, going to /login")
            self.page.views.remove(splash)
            self.page.navigate("/login")

    def run(self):
        ft.run(self.main)
