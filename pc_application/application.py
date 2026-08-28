import flet
import requests
import socket
from pathlib import Path

from dataview import AccountBaseView, TransactionBaseView, ResourceBaseView, PlannedTransactionBaseView
from database import ServerBase, JSONBase, PendingStore
from auth import save_tokens, load_tokens, clear_tokens

from .authorization_screen import AuthorizationScreen
from .planned_transactions_screen import PlannedTransactionsScreen
from .storages_view import StoragesView
from .transactions_view import TransactionsView
from .navigation_bar import MainNavigationBar


class Application:
    def __init__(self):
        self.title: str = "MyMoney"
        self.theme_color: str = "teal"
        self.server_port: int = 8000
        self.base_url: str = ""
        self.token: str = ""
        self.refresh_token: str = ""

        self.resource_view: ResourceBaseView = None
        self.account_view: AccountBaseView = None
        self.transactions_view: TransactionBaseView = None
        self.planned_transactions_view: PlannedTransactionBaseView = None

    def run(self) -> None:
        flet.app(target=self._start, view=flet.AppView.FLET_APP)
        self._stop()

    def _start(self, page: flet.Page):
        self.page = page
        self.page.title = self.title
        self.page.vertical_alignment = flet.MainAxisAlignment.CENTER
        self.page.horizontal_alignment = flet.CrossAxisAlignment.CENTER
        self.page.dark_theme = flet.Theme(color_scheme_seed=self.theme_color)

        self.progress_ring = flet.ProgressRing(width=128, height=128, stroke_width=10)
        self.page.add(self.progress_ring)

        self.base_url = self.__get_server_url()
        if not self.base_url:
            self.base_url = f"http://127.0.0.1:{self.server_port}/"

        self.page.remove(self.progress_ring)

        self.navigation_bar = MainNavigationBar(self.page, on_change=lambda e: self._navigate(e))

        self.authorization_screen = AuthorizationScreen(
            "/authorization",
            self.base_url,
            self._success_authorization,
        )

        self.page.on_route_change = self._change_route

        saved = load_tokens()
        if saved and self._verify_token(saved["access"]):
            self.token = saved["access"]
            self.refresh_token = saved.get("refresh", "")
            self._init_views()
            self.page.go("/storages")
        else:
            clear_tokens()
            self.page.go("/authorization")

    def _verify_token(self, token: str) -> bool:
        try:
            resp = requests.get(
                f"{self.base_url}api/v1/resources/",
                headers={"Authorization": f"Bearer {token}"},
                timeout=5,
                proxies={"http": None, "https": None},
            )
            return resp.status_code == 200
        except Exception:
            return False

    def _init_views(self) -> None:
        pending_store = PendingStore(str(Path.cwd() / "pending.json"))

        resource_server = ServerBase(
            f"{self.base_url}api/v1/resources/",
            token=self.token,
            base_url=self.base_url,
            get_refresh_token=lambda: self.refresh_token,
        )
        account_server = ServerBase(
            f"{self.base_url}api/v1/accounts/",
            token=self.token,
            base_url=self.base_url,
            get_refresh_token=lambda: self.refresh_token,
        )
        transaction_server = ServerBase(
            f"{self.base_url}api/v1/transactions/",
            token=self.token,
            base_url=self.base_url,
            get_refresh_token=lambda: self.refresh_token,
        )
        planned_server = ServerBase(
            f"{self.base_url}api/v1/interactions/planned-transactions/",
            token=self.token,
            base_url=self.base_url,
            get_refresh_token=lambda: self.refresh_token,
        )

        self.resource_view = ResourceBaseView(
            resource_server,
            reserve_database=JSONBase(str(Path.cwd() / "resource.json")),
        )
        self.account_view = AccountBaseView(
            account_server,
            self.resource_view,
            reserve_database=JSONBase(str(Path.cwd() / "storage.json")),
        )
        self.transactions_view = TransactionBaseView(
            transaction_server,
            self.account_view,
            reserve_database=JSONBase(str(Path.cwd() / "transaction.json")),
        )
        self.planned_transactions_view = PlannedTransactionBaseView(
            planned_server,
            self.account_view,
            reserve_database=JSONBase(str(Path.cwd() / "planned_transaction.json")),
        )

        self.resource_view.set_pending_store(pending_store)
        self.account_view.set_pending_store(pending_store)
        self.transactions_view.set_pending_store(pending_store)
        self.planned_transactions_view.set_pending_store(pending_store)

        if resource_server.is_online:
            remap = pending_store.sync(
                self.base_url,
                self.token,
                {"Authorization": f"Bearer {self.token}"},
            )
            if remap:
                for view in (self.resource_view, self.account_view, self.transactions_view, self.planned_transactions_view):
                    if hasattr(view, '_remap_pk'):
                        view._remap_pk(remap)

        self.resource_view.load()
        self.account_view.load()
        self.transactions_view.load()
        self.planned_transactions_view.load()

        self.storages_screen = StoragesView(
            "/storages", self.account_view, self.resource_view, navigation_bar=self.navigation_bar
        )
        self.transactions_screen = TransactionsView(
            "/transactions", self.transactions_view, self.account_view, navigation_bar=self.navigation_bar
        )
        self.planned_transactions_screen = PlannedTransactionsScreen(
            "/planned_transactions",
            self.planned_transactions_view,
            self.account_view,
            navigation_bar=self.navigation_bar,
        )

        self.transactions_view._on_data_changed = self.transactions_screen.update

    def _success_authorization(self, token: str, refresh_token: str = "") -> None:
        self.page.add(self.progress_ring)
        self.token = token
        self.refresh_token = refresh_token
        save_tokens(token, refresh_token)
        self._init_views()
        self.page.go("/storages")

    def _stop(self) -> None:
        if self.resource_view is not None:
            self.resource_view.save()
        if self.account_view is not None:
            self.account_view.save()
        if self.transactions_view is not None:
            self.transactions_view.save()
        if self.planned_transactions_view is not None:
            self.planned_transactions_view.save()

    def _change_route(self, e) -> None:
        self.page.views.clear()
        self.page.views.append(flet.View("/", navigation_bar=self.navigation_bar))

        if self.page.route == "/authorization":
            self.page.views.append(self.authorization_screen)

        if self.page.route == "/storages":
            self.page.views.append(self.storages_screen)

        if self.page.route == "/transactions":
            self.page.views.append(self.transactions_screen)

        if self.page.route == "/planned_transactions":
            self.page.views.append(self.planned_transactions_screen)

        self.page.update()

    def _navigate(self, e) -> None:
        match self.page.views[-1].navigation_bar.selected_index:
            case 0:
                self.page.go("/storages")
            case 1:
                self.page.go("/transactions")
            case 2:
                self.page.go("/planned_transactions")

    def __get_server_url(self) -> str:
        result = ""
        local_hostname = socket.gethostname()
        ip_addresses = socket.gethostbyname_ex(local_hostname)[2]
        filtered_ips = [ip for ip in ip_addresses]
        for ip in filtered_ips:
            url = f"http://{ip}:{self.server_port}/"
            try:
                _ = requests.get(f"{url}api/v1/health/", timeout=5, proxies={"http": None, "https": None})
                result = url
                break
            except (requests.exceptions.ConnectionError, requests.exceptions.ReadTimeout):
                continue

        return result
