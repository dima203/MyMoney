from flet import NavigationBar, NavigationBarDestination, Icons, Page


class MainNavigationBar(NavigationBar):
    def __init__(self, page: Page, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.page = page

    def build(self):
        self.destinations = [
            NavigationBarDestination(icon=Icons.WALLET, label="Счета"),
            NavigationBarDestination(icon=Icons.MONEY, label="Транзакции"),
            NavigationBarDestination(icon=Icons.MONEY, label="Запланированные Транзакции"),
        ]
        return self

    def _navigate(self, e) -> None:
        print(self.page)
        match self.selected_index:
            case 0:
                self.page.go("/storages")
            case 1:
                self.page.go("/transactions")
            case 2:
                self.page.go("/planned_transactions")
