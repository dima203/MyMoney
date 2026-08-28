import flet as ft


class SplashView(ft.View):
    def __init__(self):
        super().__init__("/splash")
        self.progress_text = ft.Text("Загрузка...", size=16, color=ft.Colors.ON_SURFACE_VARIANT)
        self.progress_ring = ft.ProgressRing(width=48, height=48, stroke_width=4)

        self.controls = [
            ft.Container(
                content=ft.Column(
                    [
                        ft.Container(
                            content=ft.Icon(
                                ft.Icons.ACCOUNT_BALANCE_WALLET,
                                size=72,
                                color=ft.Colors.PRIMARY,
                            ),
                            width=120,
                            height=120,
                            border_radius=60,
                            bgcolor=ft.Colors.PRIMARY_CONTAINER,
                            alignment=ft.Alignment.CENTER,
                        ),
                        ft.Text("MyMoney", size=36, weight=ft.FontWeight.BOLD),
                        ft.Container(height=16),
                        self.progress_ring,
                        ft.Container(height=8),
                        self.progress_text,
                    ],
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    alignment=ft.MainAxisAlignment.CENTER,
                    spacing=4,
                ),
                alignment=ft.Alignment.CENTER,
                expand=True,
            )
        ]

    def update_progress(self, text: str):
        self.progress_text.value = text
        self.update()
