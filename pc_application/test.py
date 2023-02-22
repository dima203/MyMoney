from kivymd.app import MDApp
from kivymd.uix.screen import MDScreen
from kivymd.uix.widget import MDWidget
from kivymd.uix.label import MDLabel
from kivymd.uix.button import MDRectangleFlatButton


class MyMoneyApp(MDApp):
    def build(self) -> MDWidget:
        self.theme_cls.theme_style = "Dark"
        self.theme_cls.primary_palette = "Cyan"
        return MDScreen(
            MDRectangleFlatButton(
                text='Hello, World!',
                size_hint=(0.1, 0.1),
                pos_hint={'center_x': 0.5, 'center_y': 0.5}
            )
        )


if __name__ == '__main__':
    application = MyMoneyApp()
    application.run()
