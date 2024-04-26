import flet
import requests

from dataview import AccountBaseView, TransactionBaseView, ResourceBaseView
from database import ServerBase

from .storages_screen import StoragesScreen
from .transactions_screen import TransactionsScreen


class Application:
    def __init__(self):
        self.title = 'MyMoney'
        self.theme_color = 'teal'
        base_url = 'http://localhost:8000/'
        self.token = requests.post(
            f'{base_url}api/token/', data={'username': 'admin', 'password': 'admin'}
        ).json()['access']

        self.resource_view = ResourceBaseView(ServerBase(f'{base_url}api/resource_types', token=self.token))
        self.account_view = AccountBaseView(ServerBase(f'{base_url}api/storages', token=self.token), self.resource_view)
        self.transactions_view = TransactionBaseView(ServerBase(f'{base_url}api/transactions', token=self.token), self.account_view)

    def run(self) -> None:
        flet.app(target=self._start, view=flet.FLET_APP_WEB)

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

        self.resource_view.load()
        self.account_view.load()
        self.transactions_view.load()

        self.page.remove(progress_ring)

        storages_screen = StoragesScreen(self.account_view, self.resource_view)
        transactions_screen = TransactionsScreen(self.transactions_view)

        self.screens = (storages_screen, transactions_screen)

        self.page.navigation_bar = flet.NavigationBar(
            destinations=[
                flet.NavigationDestination(icon=flet.icons.WALLET, label='Счета'),
                flet.NavigationDestination(icon=flet.icons.MONEY, label='Транзакции'),
            ],
            on_change=self._navigate
        )
        self.page.add(storages_screen)

    def _navigate(self, e) -> None:
        index = self.page.navigation_bar.selected_index
        self.page.clean()
        self.page.add(self.screens[index])
