import datetime

from .account import Account
from .money import Money


class PlannedTransaction:
    def __init__(self, storage: Account, currency: Money, planned_time: datetime.datetime, repeatability) -> None:
        self.storage = storage
        self.value = currency
        self.planned_time = planned_time
        self.repeatability = repeatability

    def to_json(self) -> dict[str, str | int]:
        return {
            "storage_id": self.storage.pk,
            "resource_count": self.value.value,
            "resource_type": self.value.currency.pk,
            "planned_time": self.planned_time.isoformat(),
            "repeatability": self.repeatability,
            "last_update": datetime.datetime.now().isoformat(),
        }
