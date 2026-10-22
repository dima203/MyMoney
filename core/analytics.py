"""Агрегаты расходов MyMoney: месяцы и категории (слайс 3.2a).

Слой не знает про Flet и API: принимает «сырые» строки транзакций/счетов
(как их отдаёт `TransactionView.get_all()`/`AccountView.get_all()`), отдаёт
иммутабельные dataclass-ы для вью.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime

PERIODS: tuple[tuple[str, str, int], ...] = (
    ("1m", "1М", 1),
    ("3m", "3М", 3),
    ("6m", "6М", 6),
    ("12m", "1Г", 12),
)
PERIOD_MONTHS: dict[str, int] = {key: months for key, _label, months in PERIODS}
DEFAULT_PERIOD = "3m"
UNCATEGORIZED = "Без категории"
TRANSFER_EPSILON = 1e-9
MONTH_LABELS = (
    "янв",
    "фев",
    "мар",
    "апр",
    "май",
    "июн",
    "июл",
    "авг",
    "сен",
    "окт",
    "ноя",
    "дек",
)


@dataclass(frozen=True)
class ExpenseRecord:
    """Одна расходная проводка: день, категория, валюта счёта, модуль суммы."""

    day: date
    category: str
    currency: str
    amount: float


@dataclass(frozen=True)
class MonthTotal:
    year: int
    month: int
    amount: float

    @property
    def label(self) -> str:
        return MONTH_LABELS[self.month - 1]


@dataclass(frozen=True)
class CategoryTotal:
    category: str
    amount: float


@dataclass(frozen=True)
class ExpenseSummary:
    currency: str
    period_months: int
    total: float
    months: tuple[MonthTotal, ...]
    categories: tuple[CategoryTotal, ...]

    @property
    def average_per_month(self) -> float:
        return self.total / self.period_months if self.period_months else 0.0

    @property
    def top_category(self) -> CategoryTotal | None:
        return self.categories[0] if self.categories else None


def parse_day(value) -> date | None:
    """Дата из ISO-строки/date/datetime (aware или naive); мусор → None."""
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str) and value.strip():
        try:
            return datetime.fromisoformat(value.strip()).date()
        except ValueError:
            return None
    return None


def _as_float(value) -> float:
    """Число из значения проводки; мусор/None → 0.0."""
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def expense_total(entries) -> float:
    """Модуль отрицательной суммы проводок; доход/перевод/пусто → 0.

    Перевод (списание + зачисление на ту же сумму) даёт ноль и отсекается
    здесь целиком, а не по отдельной проводке.
    """
    total = 0.0
    for entry in entries or []:
        if isinstance(entry, dict):
            total += _as_float(entry.get("amount"))
    return -total if total < -TRANSFER_EPSILON else 0.0


def account_currencies(accounts) -> dict[int, str]:
    """id счёта → тикер валюты (`resource`, для офлайн-строк — `resource_definition`)."""
    result: dict[int, str] = {}
    for account in accounts or []:
        if not isinstance(account, dict):
            continue
        key = account.get("id", account.get("pk"))
        currency = account.get("resource") or account.get("resource_definition") or ""
        if isinstance(key, int) and isinstance(currency, str) and currency.strip():
            result[key] = currency.strip()
    return result


def expense_records(rows, currencies: dict[int, str]) -> list[ExpenseRecord]:
    """Расходные проводки без плановых транзакций и переводов.

    Перевод (сумма проводок ≈ 0) отбрасывается целиком; категория-пустышка
    становится «Без категории»; счёт без валюты даёт пустой тикер (такая
    запись не попадёт в сводку по валюте).
    """
    records: list[ExpenseRecord] = []
    for tx in rows or []:
        if not isinstance(tx, dict) or tx.get("is_planned"):
            continue
        day = parse_day(tx.get("date"))
        if day is None:
            continue
        entries = tx.get("entries") or []
        if expense_total(entries) <= 0:
            continue
        category = str(tx.get("category") or "").strip() or UNCATEGORIZED
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            amount = _as_float(entry.get("amount"))
            if amount >= -TRANSFER_EPSILON:
                continue
            account_id = entry.get("account")
            currency = currencies.get(account_id, "") if isinstance(account_id, int) else ""
            records.append(ExpenseRecord(day=day, category=category, currency=currency, amount=-amount))
    return records


def preferred_currency(records: list[ExpenseRecord], base_currency: str = "") -> str:
    """Базовая валюта, если в ней есть расходы, иначе валюта с наибольшим объёмом."""
    totals: dict[str, float] = {}
    for record in records:
        totals[record.currency] = totals.get(record.currency, 0.0) + record.amount
    if base_currency and base_currency in totals:
        return base_currency
    if not totals:
        return base_currency
    return max(totals, key=lambda code: totals[code])


def _month_index(value: date) -> int:
    """Сквозной номер месяца (год * 12 + месяц - 1) — для арифметики периодов."""
    return value.year * 12 + value.month - 1


def _month_from_index(index: int) -> tuple[int, int]:
    year, zero_based = divmod(index, 12)
    return year, zero_based + 1


def period_start(today: date, months: int) -> date:
    """Первое число месяца, отстоящего на ``months - 1`` месяцев назад."""
    months = max(int(months), 1)
    year, month = _month_from_index(_month_index(today) - (months - 1))
    return date(year, month, 1)


def month_sequence(today: date, months: int) -> list[tuple[int, int]]:
    """Пары (год, месяц) от начала периода до текущего месяца включительно."""
    start = _month_index(period_start(today, months))
    return [_month_from_index(start + index) for index in range(months)]


def _month_totals(records: list[ExpenseRecord], keys: list[tuple[int, int]]) -> tuple[MonthTotal, ...]:
    amounts: dict[tuple[int, int], float] = dict.fromkeys(keys, 0.0)
    for record in records:
        key = (record.day.year, record.day.month)
        if key in amounts:
            amounts[key] += record.amount
    return tuple(MonthTotal(year, month, round(amount, 2)) for (year, month), amount in amounts.items())


def _category_totals(records: list[ExpenseRecord]) -> tuple[CategoryTotal, ...]:
    amounts: dict[str, float] = {}
    for record in records:
        amounts[record.category] = amounts.get(record.category, 0.0) + record.amount
    return tuple(
        CategoryTotal(category, round(amount, 2))
        for category, amount in sorted(amounts.items(), key=lambda item: (-item[1], item[0]))
    )


def build_summary(
    rows,
    accounts,
    *,
    today: date,
    months: int = PERIOD_MONTHS[DEFAULT_PERIOD],
    base_currency: str = "",
    currency: str | None = None,
) -> ExpenseSummary:
    """Сводка расходов за последние ``months`` месяцев в одной валюте.

    Валюта — явная, иначе базовая (если в ней есть расходы), иначе самая
    объёмная среди расходов. Транзакции с неизвестным счётом не учитываются.
    """
    records = expense_records(rows, account_currencies(accounts))
    chosen = currency or preferred_currency(records, base_currency)
    start = period_start(today, months)
    in_period = [record for record in records if record.currency == chosen and start <= record.day <= today]
    return ExpenseSummary(
        currency=chosen,
        period_months=months,
        total=round(sum(record.amount for record in in_period), 2),
        months=_month_totals(in_period, month_sequence(today, months)),
        categories=_category_totals(in_period),
    )


__all__ = [
    "DEFAULT_PERIOD",
    "PERIODS",
    "PERIOD_MONTHS",
    "UNCATEGORIZED",
    "CategoryTotal",
    "ExpenseRecord",
    "ExpenseSummary",
    "MonthTotal",
    "account_currencies",
    "build_summary",
    "expense_records",
    "expense_total",
    "month_sequence",
    "parse_day",
    "period_start",
    "preferred_currency",
]
