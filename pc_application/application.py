from kivymd.app import MDApp
from kivymd.uix.toolbar import MDTopAppBar
from kivymd.uix.navigationdrawer import MDNavigationDrawer
from kivymd.uix.gridlayout import MDGridLayout
from kivymd.uix.scrollview import MDScrollView
from kivymd.uix.label import MDLabel
from kivymd.uix.card import MDCard, MDCardSwipe
from kivy.properties import StringProperty, DictProperty

import requests

from dataview import AccountBaseView, TransactionBaseView, ResourceBaseView
from database import ServerBase
from core import Transaction, Income, Expense, Transfer


class Menu(MDNavigationDrawer):
    pass


class Navigation(MDTopAppBar):
    pass


class CardSwipe(MDCardSwipe):
    account_id = StringProperty()
    text = StringProperty()


class AccountsView(MDScrollView):
    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.accounts = MDApp.get_running_app().account_view.get_accounts()
        self.accounts_list = MDGridLayout(
            id='accounts_list',
            cols=1,
            size_hint_y=None,
            padding=20,
            spacing=7
        )
        self.accounts_list.bind(minimum_height=self.accounts_list.setter('height'))

        for account in self.accounts.values():
            card = CardSwipe(
                account_id=account.id,
                text=f'{account.id}: {account.get_balance()}',
            )
            self.accounts_list.add_widget(card)

        self.add_widget(self.accounts_list)


class TransactionsView(MDScrollView):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.transactions = MDApp.get_running_app().transactions_view.get_transactions()
        self.transactions_list = MDGridLayout(cols=1, spacing=7, size_hint_y=None, padding=20)
        self.transactions_list.bind(minimum_height=self.transactions_list.setter('height'))

        print(self.transactions)
        for transaction_id, transaction in self.transactions.items():
            match transaction:
                case Transaction() as transaction:
                    label_text = (f'{transaction.storage.id} {'->' if transaction.get_value() < 0 else '<-'}'
                                  f' {abs(transaction.get_value())}')
                case Income() as income:
                    label_text = f'+{income.get_balance()}'
                case Expense() as expense:
                    label_text = f'-{expense.get_balance()}'
                case Transfer() as transfer:
                    label_text = f'{transfer.from_account_name} -> {transfer.get_balance()}'
                case _:
                    label_text = 'error load'

            text = MDLabel(
                text=label_text,
            )
            card = MDCard(
                size_hint_y=None,
                height=50,
                padding=20,
            )
            card.add_widget(text)
            self.transactions_list.add_widget(card)

        self.add_widget(self.transactions_list)


class MyMoneyApp(MDApp):
    kv_directory = './kv'
    error_text_color = StringProperty()
    data = DictProperty()

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)

        self.theme_cls.theme_style = "Dark"
        self.theme_cls.primary_palette = "Teal"
        self.theme_cls.accent_palette = "Red"
        self.theme_cls.accent_hue = '900'
        self.error_text_color = "#FF0000"
        self.token = requests.post('http://127.0.0.1:8000/api/token/', data={'username': 'admin', 'password': 'admin'}).json()['access']

        self.resource_view = ResourceBaseView(ServerBase('http://127.0.0.1:8000/api/resource_types/', token=self.token))
        self.resource_view.load_resources()

        self.account_view = AccountBaseView(ServerBase('http://127.0.0.1:8000/api/storages/', token=self.token))
        self.account_view.load_accounts(self.resource_view)

        self.transactions_view = TransactionBaseView(ServerBase('http://127.0.0.1:8000/api/transactions/', token=self.token))
        self.transactions_view.load_transactions(self.account_view)

        self.data = {
            'Income': [
                'plus',
                'on_press', self.add_income,
            ],
            'Expense': [
                'minus',
                'on_press', self.add_income,
            ]
        }

    def build(self):
        self.root.ids.transactions_layout.add_widget(TransactionsView())

    def menu_call(self):
        self.root.ids.nav_drawer.set_state('open')

    def main_button_press(self):
        self.root.ids.nav_drawer.set_state('close')
        self.root.ids.screen_manager.current = 'main'

    def transactions_button_press(self):
        self.root.ids.nav_drawer.set_state('close')
        self.root.ids.screen_manager.current = 'transactions'

    def delete_card(self, card: CardSwipe):
        print(self.account_view.get_account(card.account_id).get_sources())
        self.root.ids.accounts_list.accounts_list.remove_widget(card)

    def add_income(self, callback):
        print('added')


# for tests
if __name__ == '__main__':
    application = MyMoneyApp()
    application.run()
