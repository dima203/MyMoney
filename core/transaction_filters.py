"""Фильтры ленты операций MyMoney (2.36): период, счёт, тип, категория."""

from __future__ import annotations

from datetime import date, datetime, timedelta

PERIOD_OPTIONS: tuple[tuple[str, str], ...] = (
    ("all", "Весь период"),
    ("month", "Этот месяц"),
    ("prev_month", "Прошлый месяц"),
    ("7d", "7 дней"),
    ("30d", "30 дней"),
)

TYPE_OPTIONS: tuple[tuple[str, str], ...] = (
    ("all", "Все"),
    ("income", "Доход"),
    ("expense", "Расход"),
    ("transfer", "Перевод"),
)

ALL_CATEGORY = "Все"
ALL_VALUE = "all"


def tx_date(tx: dict) -> date | None:
    raw = str(tx.get("date") or "")[:10]
    try:
        return date.fromisoformat(raw)
    except ValueError:
        return None


def tx_total(tx: dict) -> float:
    total = 0.0
    for entry in tx.get("entries") or []:
        if not isinstance(entry, dict):
            continue
        try:
            total += float(entry.get("amount") or 0)
        except (TypeError, ValueError):
            pass
    return total


def tx_account_ids(tx: dict) -> set[int]:
    ids: set[int] = set()
    for entry in tx.get("entries") or []:
        if not isinstance(entry, dict):
            continue
        account = entry.get("account")
        if isinstance(account, int):
            ids.add(account)
    return ids


def transaction_type(tx: dict) -> str:
    entries = tx.get("entries") or []
    if len(entries) > 1 and len(tx_account_ids(tx)) > 1:
        return "transfer"
    return "income" if tx_total(tx) >= 0 else "expense"


def in_period(day: date | None, period: str, today: date) -> bool:
    if period in ("", ALL_VALUE):
        return True
    if day is None:
        return False
    if period == "month":
        return (day.year, day.month) == (today.year, today.month)
    if period == "prev_month":
        first = today.replace(day=1) - timedelta(days=1)
        return (day.year, day.month) == (first.year, first.month)
    if period == "7d":
        return today - timedelta(days=6) <= day <= today
    if period == "30d":
        return today - timedelta(days=29) <= day <= today
    return True


def filter_transactions(
    rows: list[dict],
    *,
    period: str = "all",
    account_id: int | str | None = None,
    tx_type: str = "all",
    category: str = ALL_CATEGORY,
    today: date | None = None,
) -> list[dict]:
    """Отфильтровать операции: период, счёт, тип и категория (пустые — без фильтра)."""
    current = today or datetime.now().date()
    account = None
    if account_id not in (None, "", ALL_VALUE, ALL_CATEGORY):
        try:
            account = int(account_id)
        except (TypeError, ValueError):
            account = None
    wanted_category = "" if category in ("", ALL_CATEGORY) else str(category)
    result = []
    for tx in rows:
        if not in_period(tx_date(tx), period, current):
            continue
        if account is not None and account not in tx_account_ids(tx):
            continue
        if tx_type not in ("", ALL_VALUE) and transaction_type(tx) != tx_type:
            continue
        if wanted_category and str(tx.get("category") or "") != wanted_category:
            continue
        result.append(tx)
    return result


def has_active_filters(
    *,
    period: str = "all",
    account_id: int | str | None = None,
    tx_type: str = "all",
    category: str = ALL_CATEGORY,
) -> bool:
    account_active = False
    if account_id not in (None, "", ALL_VALUE, ALL_CATEGORY):
        try:
            int(account_id)
            account_active = True
        except (TypeError, ValueError):
            account_active = False
    return (
        period not in ("", ALL_VALUE)
        or account_active
        or tx_type not in ("", ALL_VALUE)
        or category not in ("", ALL_CATEGORY)
    )


__all__ = [
    "ALL_CATEGORY",
    "ALL_VALUE",
    "PERIOD_OPTIONS",
    "TYPE_OPTIONS",
    "filter_transactions",
    "has_active_filters",
    "in_period",
    "transaction_type",
    "tx_account_ids",
    "tx_date",
    "tx_total",
]
