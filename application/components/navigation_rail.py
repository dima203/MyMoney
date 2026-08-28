import flet as ft

from .navigation_items import NAVIGATION_ITEMS


class NavigationRail(ft.NavigationRail):
    def __init__(self, selected_index=0) -> None:
        super().__init__(
            selected_index=selected_index,
            label_type=ft.NavigationRailLabelType.ALL,
            min_width=80,
            min_extended_width=300,
            group_alignment=-0.9,
            destinations=[
                ft.NavigationRailDestination(
                    icon=item.icon,
                    label=item.label,
                    selected_icon=item.selected_icon,
                )
                for item in NAVIGATION_ITEMS
            ],
            on_change=self._on_nav_change,
        )

    async def _on_nav_change(self, e):
        index = e.control.selected_index
        if len(NAVIGATION_ITEMS) > index:
            self.page.go(NAVIGATION_ITEMS[index].route)
