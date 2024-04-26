from typing import Self


class Resource:
    def __init__(self, pk: int, name: str) -> None:
        self.pk = pk
        self.name = name

    def __eq__(self, other: Self) -> bool:
        return self.pk == other.pk
