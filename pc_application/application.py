import flet
import requests
import socket
from pathlib import Path

from dataview import AccountBaseView, TransactionBaseView, ResourceBaseView, PlannedTransactionBaseView
from database import ServerBase, JSONBase

from .authorization_screen import AuthorizationScreen
from .storages_screen import StoragesScreen
from .transactions_screen import TransactionsScreen
from .planned_transactions_screen import PlannedTransactionsScreen


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
        flet.app(target=self._start, view=flet.FLET_APP_WEB)
        self._stop()

    def _start(self, page: flet.Page):
        self.page = page
        self.page.title = self.title
        self.page.vertical_alignment = flet.MainAxisAlignment.CENTER
        self.page.horizontal_alignment = flet.CrossAxisAlignment.CENTER
        self.page.dark_theme = flet.Theme(
            color_scheme_seed=self.theme_color
        )

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
        self.planned_transactions_view = PlannedTransactionBaseView(
            ServerBase(f'{self.base_url}api/planned_transactions', token=self.token), self.account_view,
            reserve_database=JSONBase(str(Path.cwd() / 'planned_transaction.json'))
        )

        self.resource_view.load()
        self.account_view.load()
        self.transactions_view.load()
        self.planned_transactions_view.load()

        storages_screen = StoragesScreen(self.account_view, self.resource_view)
        transactions_screen = TransactionsScreen(self.transactions_view, self.account_view)
        planned_transactions_screen = PlannedTransactionsScreen(self.planned_transactions_view, self.account_view)
        self.screens = (storages_screen, transactions_screen, planned_transactions_screen)

        self.page.clean()
        self.page.add(self.screens[0])
        self.page.navigation_bar = flet.NavigationBar(
            destinations=[
                flet.NavigationDestination(icon=flet.icons.WALLET, label='Счета'),
                flet.NavigationDestination(icon=flet.icons.MONEY, label='Транзакции'),
                flet.NavigationDestination(icon=flet.icons.ATTACH_MONEY, label='Запланированные транзакции'),
            ],
            on_change=self._navigate
        )
        self.page.update()

    def _stop(self) -> None:
        self.resource_view.save()
        self.account_view.save()
        self.transactions_view.save()

    def _navigate(self, e) -> None:
        index = self.page.navigation_bar.selected_index
        self.page.clean()
        self.page.add(self.screens[index])

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
