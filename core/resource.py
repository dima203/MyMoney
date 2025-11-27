from datetime import datetime


class Resource:
    def __init__(self, pk: str | int, name: str) -> None:
        self.pk = pk
        self.name = name

    def __eq__(self, other: "Resource") -> bool:
        return self.pk == other.pk

    def to_json(self) -> dict[str, str | int]:
        return {"pk": self.pk, "name": self.name, "last_update": datetime.now().isoformat()}
