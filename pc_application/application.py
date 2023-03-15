from kivymd.app import MDApp
from kivymd.uix.widget import MDWidget

from kivy.lang import Builder


class MyMoneyApp(MDApp):
    kv_directory = './kv'

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)

        self.theme_cls.theme_style = "Dark"
        self.theme_cls.primary_palette = "Teal"


# for tests
if __name__ == '__main__':
    application = MyMoneyApp()
    application.run()
