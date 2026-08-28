import flet as ft

from .navigation_items import NAVIGATION_ITEMS


class NavigationDrawer(ft.NavigationDrawer):
    def __init__(self, selected_index=0):
        super().__init__(
            controls=[
                ft.Container(height=12),
                *[
                    ft.NavigationDrawerDestination(
                        icon=item.icon,
                        label=item.label,
                        selected_icon=item.selected_icon,
                    )
                    for item in NAVIGATION_ITEMS
                ],
            ],
            on_change=self.on_drawer_change,
            selected_index=selected_index,
            width=300,
        )

    async def on_drawer_change(self, e):
        index = e.control.selected_index
        if len(NAVIGATION_ITEMS) > index:
            self.page.go(NAVIGATION_ITEMS[index].route)
