import flet as ft


class AccountCard(ft.Container):
    def __init__(self, name: str, balance: str, currency_icon: str = "●", on_edit=None, on_delete=None):
        super().__init__()
        self.name = name
        self.balance = balance

        self._name_text = ft.Text(name, size=16, weight=ft.FontWeight.W_500, expand=True)
        self._balance_text = ft.Text(balance, size=16, weight=ft.FontWeight.BOLD)

        menu_button = ft.PopupMenuButton(
            icon=ft.Icons.MORE_VERT,
            icon_size=20,
            # menu_offset=ft.Offset(0, -10),
            items=[
                ft.PopupMenuItem(content="Редактировать", icon=ft.Icons.EDIT, on_click=lambda _: on_edit and on_edit()),
                ft.PopupMenuItem(content="Удалить", icon=ft.Icons.DELETE, on_click=lambda _: on_delete and on_delete()),
            ],
        )

        self.content = ft.Container(
            content=ft.Row(
                [
                    ft.Container(
                        content=ft.Icon(currency_icon, size=24, color=ft.Colors.PRIMARY),
                        width=40,
                        height=40,
                        border_radius=20,
                        bgcolor=ft.Colors.PRIMARY_CONTAINER,
                        alignment=ft.Alignment.CENTER,
                    ),
                    self._name_text,
                    self._balance_text,
                    menu_button,
                ],
                alignment=ft.MainAxisAlignment.START,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            padding=ft.Padding.symmetric(horizontal=16, vertical=12),
            border_radius=8,
            bgcolor=ft.Colors.SURFACE_CONTAINER_LOW,
            ink=True,
        )

    def update_balance(self, balance: str):
        self._balance_text.value = balance
        self.update()
