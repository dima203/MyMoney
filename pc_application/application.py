import flet
import requests
import socket
from pathlib import Path

from dataview import AccountBaseView, TransactionBaseView, ResourceBaseView, PlannedTransactionBaseView
from database import ServerBase, JSONBase

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

        self.resource_view: ResourceBaseView = None
        self.account_view: AccountBaseView = None
        self.transactions_view: TransactionBaseView = None

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

        self.page.remove(self.progress_ring)

        self.authorization_screen = AuthorizationScreen(f'{self.base_url}api/token/', self._success_authorization)
        self.page.add(self.authorization_screen)

    def _success_authorization(self, token: str) -> None:
        self.page.add(self.progress_ring)
        self.token = token
        self.resource_view = ResourceBaseView(
            ServerBase(f"{self.base_url}api/resource_types", token=self.token),
            reserve_database=JSONBase(str(Path.cwd() / "resource.json")),
        )
        self.account_view = AccountBaseView(
            ServerBase(f"{self.base_url}api/storages", token=self.token),
            self.resource_view,
            reserve_database=JSONBase(str(Path.cwd() / "storage.json")),
        )
        self.transactions_view = TransactionBaseView(
            ServerBase(f"{self.base_url}api/transactions", token=self.token),
            self.account_view,
            reserve_database=JSONBase(str(Path.cwd() / "transaction.json")),
        )
        self.planned_transactions_view = PlannedTransactionBaseView(
            ServerBase(f'{self.base_url}api/planned_transactions', token=self.token), self.account_view,
            reserve_database=JSONBase(str(Path.cwd() / 'planned_transaction.json'))
        )

        self.resource_view.load()
        self.account_view.load()
        self.transactions_view.load()
        self.planned_transactions_view.load()

        self.navigation_bar = MainNavigationBar(self.page, on_change=lambda e: self._navigate(e))
        self.storages_screen = StoragesView(
            "/storages", self.account_view, self.resource_view, navigation_bar=self.navigation_bar
        )
        self.transactions_screen = TransactionsView(
            "/transactions", self.transactions_view, self.account_view, navigation_bar=self.navigation_bar
        )
        self.planned_transactions_screen = PlannedTransactionsScreen(
            "/planned_transactions", self.planned_transactions_view, self.account_view, navigation_bar=self.navigation_bar
        )

        self.page.on_route_change = self._change_route
        self.page.go(self.page.route)

    def _stop(self) -> None:
        self.resource_view.save()
        self.account_view.save()
        self.transactions_view.save()

    def _change_route(self, e) -> None:
        self.page.views.clear()
        self.page.views.append(flet.View("/", navigation_bar=self.navigation_bar))

        if self.page.route == "/storages":
            self.page.views.append(self.storages_screen)

        if self.page.route == "/transactions":
            self.page.views.append(self.transactions_screen)

        self.page.update()

    def _navigate(self, e) -> None:
        match self.page.views[-1].navigation_bar.selected_index:
            case 0:
                self.page.go("/storages")
            case 1:
                self.page.go("/transactions")

    def __get_server_url(self) -> str:
        result = ""
        local_hostname = socket.gethostname()
        ip_addresses = socket.gethostbyname_ex(local_hostname)[2]
        filtered_ips = [ip for ip in ip_addresses]
        for ip in filtered_ips:
            url = f"http://{ip}:{self.server_port}/"
            try:
                _ = requests.get(f"{url}api/ping")
                result = url
                break
            except requests.exceptions.ConnectionError:
                continue

        return result

    def __get_token(self) -> str:
        if self.base_url == "":
            return ""

        return requests.post(f"{self.base_url}api/token/", data={"username": "admin", "password": "admin"}).json()[
            "access"
        ]
