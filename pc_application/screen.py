from flet import View
from abc import abstractmethod


class Screen(View):
    def __init__(self, route: str) -> None:
        super().__init__(route)

    # def did_mount(self) -> None:
    #     self.update()

    @abstractmethod
    def update(self) -> None: ...
