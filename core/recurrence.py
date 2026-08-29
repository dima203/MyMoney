import datetime
from enum import Enum


class Frequency(Enum):
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    YEARLY = "yearly"


class RecurrenceRule:
    def __init__(self, frequency: Frequency, interval: int = 1, until: datetime.date | None = None) -> None:
        if interval < 1:
            raise ValueError("Interval must be >= 1")
        self.frequency = frequency
        self.interval = interval
        self.until = until

    @classmethod
    def parse(cls, rule_str: str) -> "RecurrenceRule | None":
        if not rule_str:
            return None
        parts = rule_str.lower().strip().split()
        if not parts:
            return None

        freq_map = {
            "daily": Frequency.DAILY,
            "weekly": Frequency.WEEKLY,
            "monthly": Frequency.MONTHLY,
            "yearly": Frequency.YEARLY,
        }
        freq = freq_map.get(parts[0])
        if freq is None:
            return None

        interval = 1
        until = None
        i = 1
        while i < len(parts):
            if parts[i] == "every" and i + 1 < len(parts):
                try:
                    interval = int(parts[i + 1])
                except ValueError:
                    pass
                i += 2
            elif parts[i] == "until" and i + 1 < len(parts):
                try:
                    until = datetime.date.fromisoformat(parts[i + 1])
                except ValueError:
                    pass
                i += 2
            else:
                i += 1

        return cls(freq, interval, until)

    def next_date(self, from_date: datetime.date) -> datetime.date:
        if self.frequency == Frequency.DAILY:
            return from_date + datetime.timedelta(days=self.interval)
        if self.frequency == Frequency.WEEKLY:
            return from_date + datetime.timedelta(weeks=self.interval)
        if self.frequency == Frequency.MONTHLY:
            month = from_date.month + self.interval
            year = from_date.year + (month - 1) // 12
            month = (month - 1) % 12 + 1
            day = min(from_date.day, _days_in_month(year, month))
            return datetime.date(year, month, day)
        if self.frequency == Frequency.YEARLY:
            new_year = from_date.year + self.interval
            try:
                return from_date.replace(year=new_year)
            except ValueError:
                return datetime.date(new_year, from_date.month, 28)
        raise ValueError(f"Unknown frequency: {self.frequency}")

    def generate_dates(self, start: datetime.date, count: int = 10) -> list[datetime.date]:
        dates = []
        current = start
        for _ in range(count):
            current = self.next_date(current)
            if self.until and current > self.until:
                break
            dates.append(current)
        return dates

    def to_string(self) -> str:
        parts = [self.frequency.value]
        if self.interval > 1:
            parts.extend(["every", str(self.interval)])
        if self.until:
            parts.extend(["until", self.until.isoformat()])
        return " ".join(parts)

    def __str__(self) -> str:
        return self.to_string()

    def __repr__(self) -> str:
        return f"RecurrenceRule({self.to_string()!r})"


def _days_in_month(year: int, month: int) -> int:
    if month == 12:
        return 31
    return (datetime.date(year, month + 1, 1) - datetime.date(year, month, 1)).days
