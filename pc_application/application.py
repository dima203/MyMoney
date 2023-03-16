from kivymd.app import MDApp
from kivymd.uix.toolbar import MDTopAppBar
from kivymd.uix.navigationdrawer import MDNavigationDrawer
from kivymd.uix.gridlayout import MDGridLayout
from kivymd.uix.scrollview import MDScrollView
from kivymd.uix.label import MDLabel
from pathlib import Path

from dataview import AccountBaseView
from database import JSONBase


class Menu(MDNavigationDrawer):
    pass


class Navigation(MDTopAppBar):
    pass


class AccountsView(MDScrollView):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.accounts = MDApp.get_running_app().account_view.get_accounts()
        self.accounts_list = MDGridLayout(cols=1, spacing=10, size_hint_y=None, padding=20)
        self.accounts_list.bind(minimum_height=self.accounts_list.setter('height'))

        for account_id, account in self.accounts.items():
            self.accounts_list.add_widget(
                MDLabel(
                    text=f'{account_id}: {account.get_balance()}',
                    size_hint_y=None,
                    height=100
                )
            )

        self.add_widget(self.accounts_list)


class MyMoneyApp(MDApp):
    kv_directory = './kv'

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)

        self.theme_cls.theme_style = "Dark"
        self.theme_cls.primary_palette = "Teal"

        self.account_view = AccountBaseView(JSONBase(str(Path.cwd() / 'application_data.json')))
        self.account_view.load_accounts()

    def build(self):
        self.root.ids.main_layout.add_widget(AccountsView())

    def menu_call(self):
        self.root.ids.nav_drawer.set_state('open')

    def main_button_press(self):
        print(1)
        self.root.ids.screen_manager.current = 'main'
        print('1')

    def add_account_button_press(self):
        self.root.ids.screen_manager.current = 'add_account'


# for tests
if __name__ == '__main__':
    application = MyMoneyApp()
    application.run()
