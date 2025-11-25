import flet
import requests
import socket
from pathlib import Path

from dataview import AccountBaseView, TransactionBaseView, ResourceBaseView
from database import ServerBase, JSONBase

from .storages_view import StoragesView
from .transactions_view import TransactionsView
from .navigation_bar import MainNavigationBar


class Application:
    def __init__(self):
        self.title: str = 'MyMoney'
        self.theme_color: str = 'teal'
        self.server_port: int = 8000
        self.base_url: str = f''
        self.token: str = ''

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
        self.page.dark_theme = flet.Theme(
            color_scheme_seed=self.theme_color
        )

        progress_ring = flet.ProgressRing(width=128, height=128, stroke_width=10)
        self.page.add(progress_ring)

        self.base_url = self.__get_server_url()
        self.token: str = self.__get_token()

        self.resource_view = ResourceBaseView(
            ServerBase(f'{self.base_url}api/resource_types', token=self.token),
            reserve_database=JSONBase(str(Path.cwd() / 'resource.json'))
        )
        self.account_view = AccountBaseView(
            ServerBase(f'{self.base_url}api/storages', token=self.token), self.resource_view,
            reserve_database=JSONBase(str(Path.cwd() / 'storage.json'))
        )
        self.transactions_view = TransactionBaseView(
            ServerBase(f'{self.base_url}api/transactions', token=self.token), self.account_view,
            reserve_database=JSONBase(str(Path.cwd() / 'transaction.json'))
        )

        self.resource_view.load()
        self.account_view.load()
        self.transactions_view.load()

        self.page.remove(progress_ring)

        self.navigation_bar = MainNavigationBar(self.page, on_change=lambda e: self._navigate(e))
        self.storages_screen = StoragesView('/storages', self.account_view, self.resource_view, navigation_bar=self.navigation_bar)
        self.transactions_screen = TransactionsView('/transactions', self.transactions_view, self.account_view, navigation_bar=self.navigation_bar)

        self.page.on_route_change = self._change_route
        self.page.go(self.page.route)

    def _stop(self) -> None:
        self.resource_view.save()
        self.account_view.save()
        self.transactions_view.save()

    def _change_route(self, e) -> None:
        self.page.views.clear()
        self.page.views.append(
            flet.View(
                "/",
                navigation_bar=self.navigation_bar
            )
        )

        if self.page.route == '/storages':
            self.page.views.append(self.storages_screen)

        if self.page.route == '/transactions':
            self.page.views.append(self.transactions_screen)

        self.page.update()

    def _navigate(self, e) -> None:
        match self.page.views[-1].navigation_bar.selected_index:
            case 0:
                self.page.go('/storages')
            case 1:
                self.page.go('/transactions')

    def __get_server_url(self) -> str:
        result = ''
        local_hostname = socket.gethostname()
        ip_addresses = socket.gethostbyname_ex(local_hostname)[2]
        filtered_ips = [ip for ip in ip_addresses]
        for ip in filtered_ips:
            url = f'http://{ip}:{self.server_port}/'
            try:
                _ = requests.get(f'{url}api/ping')
                result = url
                break
            except requests.exceptions.ConnectionError:
                continue

        return result

    def __get_token(self) -> str:
        if self.base_url == '':
            return ''

        return requests.post(
            f'{self.base_url}api/token/', data={'username': 'admin', 'password': 'admin'}
        ).json()['access']
