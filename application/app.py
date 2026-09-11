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
from application.screens import LoginView
from application.view import SplashView
from core import APP_SETTINGS, build_theme, theme_mode_value
from core.config import SETTINGS
from database.views import AccountView, ResourceView, TransactionView
from MySpaceShared.components.connection_status import ConnectionBanner

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

    def _init_offline_views(self) -> None:
        if self._resource_view is not None:
            return
        os.makedirs(DATA_DIR, exist_ok=True)
        self._resource_view = ResourceView(self.api_client, DATA_DIR)
        self._account_view = AccountView(self.api_client, DATA_DIR)
        self._transaction_view = TransactionView(self.api_client, DATA_DIR)

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
            self.page.go("/login")
            return

        self._init_offline_views()
        self._update_connection_banner()

        if self.page.route == "/accounts":
            from application.view.accounts_view import AccountsView

            self.page.views.append(
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

            self.page.views.append(
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

            self.page.views.append(
                PlannedView(
                    route="/planned",
                    api_client=self.api_client,
                    transaction_view=self._transaction_view,
                    account_view=self._account_view,
                    connection_banner=self._connection_banner,
                )
            )
        elif self.page.route == "/settings":
            from application.view.settings_view import SettingsView

            self.page.views.append(
                SettingsView(
                    route="/settings",
                    api_client=self.api_client,
                    on_logout=self._on_logout,
                )
            )
        else:
            self.page.go("/accounts")
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
            self.page.go("/accounts")

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
                self.page.go("/accounts")

    async def main(self, page: ft.Page) -> None:
        self.page = page
        self.page.title = "MyMoney"
        self.page.window.min_width = 500
        self.page.window.min_height = 700
        self.page.window.width = 500
        self.page.window.height = 700

        self.page.theme_mode = theme_mode_value(APP_SETTINGS.theme_mode)
        self.page.theme = build_theme(APP_SETTINGS.accent_color)
        self.page.dark_theme = build_theme(APP_SETTINGS.accent_color)

        self.page.on_route_change = self.route_change
        self.page.on_view_pop = self.view_pop

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
            self.page.go("/login")

    def run(self):
        ft.app(target=self.main)
