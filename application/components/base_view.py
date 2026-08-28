import flet as ft

from .navigation_drawer import NavigationDrawer
from .navigation_rail import NavigationRail


class BaseView(ft.View):
    def __init__(
        self,
        content: ft.Control,
        title: str = "",
        route: str = "/",
        selected_index: int = 0,
    ) -> None:
        self.title = title
        self.content = content
        self.selected_index = selected_index
        self.app_bar = ft.AppBar(
            title=ft.Text(self.title),
            bgcolor=ft.Colors.PRIMARY_CONTAINER,
        )
        super().__init__(route=route)

    def did_mount(self):
        self.page.on_resize = self.on_resize
        self._update_layout(self.page.width)

    def on_resize(self, e: ft.PageResizeEvent):
        self._update_layout(e.width)

    def _update_layout(self, width: float):
        content_container = ft.Column(
            expand=True,
            controls=[
                self.app_bar,
                self.content,
            ],
        )

        if width < 800:
            self.app_bar.leading = ft.IconButton(
                icon=ft.Icons.MENU,
                on_click=self._open_drawer,
            )
            self.drawer = NavigationDrawer(self.selected_index)
            self.controls = [content_container]
        else:
            self.app_bar.leading = None
            self.drawer = None
            rail = NavigationRail(self.selected_index)
            self.controls = [
                ft.Row(
                    expand=True,
                    spacing=0,
                    controls=[
                        rail,
                        ft.VerticalDivider(width=1),
                        ft.Container(
                            expand=True,
                            content=content_container,
                            padding=ft.Padding(left=self.padding.left),
                        ),
                    ],
                )
            ]

        self.update()

    def dispose(self) -> None:
        pass

    async def _open_drawer(self, e: ft.Event):
        if self.drawer:
            await self.page.show_drawer()
