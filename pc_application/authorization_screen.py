from flet import (
    Container,
    TextField,
    Column,
    Row,
    TextButton,
    Text,
    TextStyle,
    MainAxisAlignment,
    ScrollMode,
    Colors,
    View,
)
import requests


class AuthorizationScreen(View):
    def __init__(self, route: str, url: str, success_callback: callable, *args, **kwargs) -> None:
        super().__init__(route, *args, **kwargs)
        self.url = url
        self.success_callback = success_callback

    def build(self) -> Container:
        self.title = Text("Авторизация", style=TextStyle(size=20))
        self.fail_text = Text(style=TextStyle(color=Colors.RED_200))
        self.login_field = TextField(label="Имя пользователя")
        self.password_field = TextField(label="Пароль", password=True, can_reveal_password=True)
        self.submit_button = TextButton("Вход", on_click=lambda _: self._submit())
        self.container = Row(
            [
                Column(
                    [
                        Row([self.title], alignment=MainAxisAlignment.CENTER),
                        self.login_field,
                        self.password_field,
                        Row([self.submit_button], alignment=MainAxisAlignment.CENTER),
                        self.fail_text,
                    ],
                    scroll=ScrollMode.ALWAYS,
                    width=self.page.width * 0.7,
                    alignment=MainAxisAlignment.CENTER,
                )
            ],
            alignment=MainAxisAlignment.CENTER,
        )
        self.controls = [self.container]
        return self

    def _submit(self) -> None:
        self.login_field.error_text = ""
        self.password_field.error_text = ""
        self.fail_text.value = ""
        self.login_field.update()
        self.password_field.update()
        self.fail_text.update()

        if self.url == "api/token/":
            self.success_callback("")
            return

        response = requests.post(
            f"{self.url}", data={"username": self.login_field.value, "password": self.password_field.value}
        ).json()

        if "access" in response:
            token = response["access"]
            self.success_callback(token)
            return
        if "username" in response:
            self.login_field.error_text = "Имя пользователя не может быть пустым"
            self.login_field.update()
        if "password" in response:
            self.password_field.error_text = "Пароль не может быть пустым"
            self.password_field.update()
        if "detail" in response:
            self.fail_text.value = "Неверные данные для входа"
            self.fail_text.update()

        self.update()
