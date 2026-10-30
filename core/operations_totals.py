"""Итоги периода для экрана «Операции»: доход/расход в базовой валюте (2.48)."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

from core.group_totals import build_price_map, rate_to_base
from core.transaction_filters import transaction_type


@dataclass(frozen=True)
class PeriodTotals:
    income: Decimal = Decimal(0)
    expense: Decimal = Decimal(0)
    missing_symbols: tuple[str, ...] = ()

    @property
    def net(self) -> Decimal:
        return self.income - self.expense

    @property
    def has_missing(self) -> bool:
        return bool(self.missing_symbols)


def _entry_symbol(entry: dict, account_map: dict[int, dict]) -> str:
    raw_account = entry.get("account")
    try:
        account = account_map.get(int(raw_account)) if raw_account is not None else None
    except (TypeError, ValueError):
        account = None
    if not isinstance(account, dict):
        return ""
    return str(account.get("resource") or account.get("unit") or "").strip().upper()


def _entry_amount(entry: dict) -> Decimal | None:
    try:
        return Decimal(str(entry.get("amount") or 0))
    except (InvalidOperation, ValueError):
        return None


def period_totals(
    rows: list[dict],
    account_map: dict[int, dict],
    base_currency: str,
    price_rows,
) -> PeriodTotals:
    """Суммы доходов и расходов периода, пересчитанные в базовую валюту через USDT-курсы."""
    base = (base_currency or "").strip().upper()
    prices = build_price_map(price_rows)
    income = Decimal(0)
    expense = Decimal(0)
    missing: set[str] = set()
    for tx in rows:
        if transaction_type(tx) == "transfer":
            continue
        for entry in tx.get("entries") or []:
            if not isinstance(entry, dict):
                continue
            amount = _entry_amount(entry)
            if amount is None:
                continue
            symbol = _entry_symbol(entry, account_map)
            rate = rate_to_base(symbol, base, prices)
            if rate is None:
                missing.add(symbol or "—")
                continue
            value = amount * rate
            if value > 0:
                income += value
            elif value < 0:
                expense += -value
    return PeriodTotals(income=income, expense=expense, missing_symbols=tuple(sorted(missing)))


def _amount_text(value: Decimal) -> str:
    """Сумма в формате экосистемы: пробел как разделитель тысяч."""
    return f"{value:,.2f}".replace(",", " ")


def format_period_totals(result: PeriodTotals, base_currency: str) -> str:
    base = (base_currency or "").strip().upper()
    text = f"Доход +{_amount_text(result.income)} · Расход −{_amount_text(result.expense)}"
    if base:
        text += f" {base}"
    if result.has_missing:
        text += f" (курс недоступен: {', '.join(result.missing_symbols)})"
    return text


__all__ = ["PeriodTotals", "format_period_totals", "period_totals"]
