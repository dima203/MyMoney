import flet

import requests

from dataview import AccountBaseView, TransactionBaseView, ResourceBaseView
from database import ServerBase
from core import Transaction, Income, Expense, Transfer


class Application:
    def run(self) -> None:
        flet.app(target=main, view=flet.FLET_APP_WEB)


def add_transaction(e) -> None:
    pass


def main(page: flet.Page) -> None:
    page.title = 'MyMoney'
    page.vertical_alignment = flet.MainAxisAlignment.CENTER
    page.horizontal_alignment = flet.CrossAxisAlignment.CENTER
    page.dark_theme = flet.Theme(
        color_scheme_seed='teal'
    )

    progress_ring = flet.ProgressRing(width=128, height=128, stroke_width=10)
    page.add(progress_ring)

    base_url = 'http://localhost:8000/'
    token = requests.post(f'{base_url}api/token/', data={'username': 'admin', 'password': 'admin'}).json()['access']

    resource_view = ResourceBaseView(ServerBase(f'{base_url}api/resource_types', token=token))
    resource_view.load_resources()

    account_view = AccountBaseView(ServerBase(f'{base_url}api/storages', token=token))
    account_view.load_accounts(resource_view)

    transactions_view = TransactionBaseView(ServerBase(f'{base_url}api/transactions', token=token))
    transactions_view.load_transactions(account_view)

    page.remove(progress_ring)

    def load_storages() -> None:
        storage_list.controls.clear()
        for pk, storage in account_view.get_accounts().items():
            storage_list.controls.append(flet.ListTile(
                    leading=flet.PopupMenuButton(
                        icon=flet.icons.WALLET,
                        items=[
                            flet.PopupMenuItem(icon=flet.icons.CHANGE_CIRCLE, text='update'),
                            flet.PopupMenuItem(icon=flet.icons.REMOVE_CIRCLE, text='delete',
                                               on_click=lambda e: delete_storage(pk)),
                        ]
                    ),
                    title=flet.Row([
                        flet.Text(storage.name),
                        flet.Text(str(storage.value))
                    ],
                        alignment=flet.MainAxisAlignment.SPACE_BETWEEN
                    ),
                )
            )
        storage_list.update()

    def load_transactions() -> None:
        transaction_list.controls.clear()
        for pk, transaction in transactions_view.get_transactions().items():
            transaction_list.controls.append(flet.ListTile(
                    leading=flet.PopupMenuButton(
                        icon=flet.icons.ADD if transaction.get_value() > 0 else flet.icons.REMOVE,
                        items=[
                            flet.PopupMenuItem(icon=flet.icons.CHANGE_CIRCLE, text='update'),
                            flet.PopupMenuItem(icon=flet.icons.REMOVE_CIRCLE, text='delete',
                                               on_click=lambda e: delete_transaction(pk)),
                        ]
                    ),
                    title=flet.Row([
                        flet.Text(transaction.storage.name),
                        flet.Text(str(abs(transaction.get_value())))
                    ],
                        alignment=flet.MainAxisAlignment.SPACE_BETWEEN
                    ),
                )
            )
        storage_list.update()

    def delete_storage(pk: int) -> None:
        account_view.delete_account(pk)
        load_storages()

    def delete_transaction(pk: int) -> None:
        # transactions_view.delete_transaction(pk)
        load_transactions()

    storage_list = flet.ListView(spacing=10, width=500)
    storages_screen = flet.Container(storage_list)

    transaction_list = flet.ListView(spacing=10, width=500)
    transactions_screen = flet.Container(transaction_list)

    screens = ((storages_screen, load_storages), (transactions_screen, load_transactions))

    def navigate(e):
        index = page.navigation_bar.selected_index
        page.clean()
        page.add(screens[index][0])
        screens[index][1]()
        print(index)

    page.navigation_bar = flet.NavigationBar(
        destinations=[
            flet.NavigationDestination(icon=flet.icons.WALLET, label='Счета'),
            flet.NavigationDestination(icon=flet.icons.MONEY, label='Транзакции'),
        ],
        on_change=navigate
    )

    page.add(storages_screen)
