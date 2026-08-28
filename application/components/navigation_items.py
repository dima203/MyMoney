from dataclasses import dataclass

import flet as ft


@dataclass
class NavigationItem:
    label: str
    route: str
    icon: ft.IconData
    selected_icon: ft.IconData = None


NAVIGATION_ITEMS = [
    NavigationItem(
        label="Счета",
        route="/accounts",
        icon=ft.Icons.ACCOUNT_BALANCE_WALLET,
        selected_icon=ft.Icons.ACCOUNT_BALANCE_WALLET_OUTLINED,
    ),
    NavigationItem(
        label="Транзакции",
        route="/transactions",
        icon=ft.Icons.RECEIPT_LONG,
        selected_icon=ft.Icons.RECEIPT_LONG_OUTLINED,
    ),
    NavigationItem(
        label="План",
        route="/planned",
        icon=ft.Icons.CALENDAR_MONTH,
        selected_icon=ft.Icons.CALENDAR_MONTH_OUTLINED,
    ),
    NavigationItem(
        label="Настройки",
        route="/settings",
        icon=ft.Icons.SETTINGS,
        selected_icon=ft.Icons.SETTINGS_OUTLINED,
    ),
]
