from .abstract_base import DataBase


class NoneBase(DataBase):
    def __init__(self) -> None:
        super().__init__("")

    def update(self, pk: str | int, data: dict) -> None:
        pass

    def delete(self, pk: str | int) -> None:
        pass

    def add(self, data: dict) -> int | str:
        return -1

    def load(self) -> list:
        return []
