"""Бюджеты-конверты MyMoney: прогресс лимитов по категориям (слайс 3.2b).

Слой без Flet и API: принимает строки конвертов из `/api/v1/envelopes/`,
транзакции и счета — отдаёт иммутабельные `EnvelopeProgress`.
Лимит месячный: траты считаются за текущий календарный месяц.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from core.analytics import account_currencies, as_float, expense_records

MIN_LIMIT = 0.0


@dataclass(frozen=True)
class EnvelopeProgress:
    """Конверт и его фактические траты за текущий месяц."""

    envelope_id: int | None
    category: str
    limit_amount: float
    currency: str
    spent: float

    @property
    def remaining(self) -> float:
        return round(self.limit_amount - self.spent, 2)

    @property
    def overspent(self) -> float:
        return round(max(self.spent - self.limit_amount, 0.0), 2)

    @property
    def is_over(self) -> bool:
        return self.spent > self.limit_amount

    @property
    def share(self) -> float:
        """Доля израсходованного лимита 0..1 (для ProgressBar)."""
        if self.limit_amount <= 0:
            return 0.0
        return min(max(self.spent / self.limit_amount, 0.0), 1.0)


def envelope_payload(category, limit, currency_id: int | None = None) -> dict:
    """Тело POST/PATCH конверта: категория, положительный лимит, валюта или None."""
    name = str(category or "").strip()
    if not name:
        raise ValueError("Укажите категорию конверта")
    try:
        amount = float(str(limit).replace(",", ".").replace(" ", ""))
    except (TypeError, ValueError):
        raise ValueError("Лимит должен быть числом") from None
    if amount <= MIN_LIMIT:
        raise ValueError("Лимит должен быть больше нуля")
    return {"category": name, "limit_amount": f"{amount:.4f}", "currency": currency_id}


def _spent_index(records, month_start: date, today: date) -> dict[tuple[str, str], float]:
    """Траты месяца по ключу (валюта, категория в casefold)."""
    index: dict[tuple[str, str], float] = {}
    for record in records:
        if month_start <= record.day <= today:
            key = (record.currency, record.category.casefold())
            index[key] = index.get(key, 0.0) + record.amount
    return index


def _progress(envelope: dict, index: dict[tuple[str, str], float], base_currency: str) -> EnvelopeProgress | None:
    """Прогресс одного конверта; `None` — строка без категории (пропускается)."""
    category = str(envelope.get("category") or "").strip()
    if not category:
        return None
    currency = str(envelope.get("currency_ticker") or base_currency or "").strip()
    envelope_id = envelope.get("id", envelope.get("pk"))
    return EnvelopeProgress(
        envelope_id=envelope_id if isinstance(envelope_id, int) else None,
        category=category,
        limit_amount=as_float(envelope.get("limit_amount")),
        currency=currency,
        spent=round(index.get((currency, category.casefold()), 0.0), 2),
    )


def envelope_progress(
    envelopes,
    rows,
    accounts,
    *,
    today: date,
    base_currency: str = "",
) -> list[EnvelopeProgress]:
    """Прогресс каждого конверта: траты месяца по категории и валюте.

    Категория сравнивается без учёта регистра (SQLite и кириллица), валюта —
    по тикеру `currency_ticker` (пусто → базовая валюта). Траты берутся из тех
    же расходных записей, что и аналитика: без плановых, доходов и переводов.
    """
    index = _spent_index(expense_records(rows, account_currencies(accounts)), today.replace(day=1), today)
    items = (_progress(envelope, index, base_currency) for envelope in envelopes or [] if isinstance(envelope, dict))
    return [item for item in items if item is not None]


__all__ = ["EnvelopeProgress", "envelope_payload", "envelope_progress"]
