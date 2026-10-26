"""Форматирование сумм для карточек MyMoney."""

from __future__ import annotations

from MySpaceShared.core.formatting import format_money as _format_money

UNKNOWN_CURRENCY = "—"


def format_money(amount: float, currency: str) -> str:
    """Сумма в едином формате экосистемы: «1 234.50 BYN»."""
    return _format_money(amount, currency or UNKNOWN_CURRENCY)


__all__ = ["UNKNOWN_CURRENCY", "format_money"]
