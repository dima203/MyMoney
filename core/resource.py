class Resource:
    def __init__(
        self,
        pk: str | int,
        name: str,
        *,
        ticker: str = "",
        unit: str = "",
        category: str = "",
        resource_type: str = "custom",
        icon: str = "",
    ) -> None:
        self.pk = pk
        self.name = name
        self.ticker = ticker
        self.unit = unit
        self.category = category
        self.resource_type = resource_type
        self.icon = icon

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Resource):
            return NotImplemented
        return self.pk == other.pk

    def __hash__(self) -> int:
        return hash(self.pk)

    def to_json(self) -> dict[str, str | int]:
        return {
            "id": self.pk,
            "name": self.name,
            "ticker": self.ticker,
            "unit": self.unit,
            "category": self.category,
            "resource_type": self.resource_type,
            "icon": self.icon,
        }
