from flet import UserControl, Page
from abc import abstractmethod


class Screen(UserControl):
    def did_mount(self) -> None:
        self.update()

    @abstractmethod
    def update(self) -> None: ...
