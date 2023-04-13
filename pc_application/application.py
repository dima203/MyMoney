from kivymd.app import MDApp
from kivymd.uix.toolbar import MDTopAppBar
from kivymd.uix.navigationdrawer import MDNavigationDrawer
from kivymd.uix.gridlayout import MDGridLayout
from kivymd.uix.list import MDList
from kivymd.uix.scrollview import MDScrollView
from kivymd.uix.label import MDLabel
from kivymd.uix.card import MDCard, MDCardSwipe, MDCardSwipeFrontBox, MDCardSwipeLayerBox
from kivy.properties import StringProperty
from pathlib import Path
from dataview import AccountBaseView, TransactionBaseView
from database import JSONBase
from core import Income, Expense, Transfer


class Menu(MDNavigationDrawer):
    pass


class Navigation(MDTopAppBar):
    pass


class CardSwipe(MDCardSwipe):
    account_id = StringProperty()
    text = StringProperty()


class AccountsView(MDScrollView):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.accounts = MDApp.get_running_app().account_view.get_accounts()

        for account_id, account in self.accounts.items():
            card = CardSwipe(
                account_id=account_id,
                text=f'{account_id}: {account.get_balance()}',
                size_hint_y=None,
                height=50,
            )
            self.ids.accounts_list.add_widget(card)


class TransactionsView(MDScrollView):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.transactions = MDApp.get_running_app().transactions_view.get_transactions()
        self.transactions_list = MDGridLayout(cols=1, spacing=7, size_hint_y=None, padding=20)
        self.transactions_list.bind(minimum_height=self.transactions_list.setter('height'))

        for transaction_id, transaction in self.transactions.items():
            match transaction:
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

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)

        self.theme_cls.theme_style = "Dark"
        self.theme_cls.primary_palette = "Teal"

        self.account_view = AccountBaseView(JSONBase(str(Path.cwd() / 'application_data.json')))
        self.account_view.load_accounts()

        self.transactions_view = TransactionBaseView(JSONBase(str(Path.cwd() / 'application_transaction_data.json')))
        self.transactions_view.load_transactions()

        self.account_view.load_transactions_to_accounts(self.transactions_view)

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
        self.root.ids.accounts_list.remove_widget(card)


# for tests
if __name__ == '__main__':
    application = MyMoneyApp()
    application.run()
