"""Форматирование сумм для карточек MyMoney."""

from __future__ import annotations

UNKNOWN_CURRENCY = "—"


def format_money(amount: float, currency: str) -> str:
    """Сумма с разделителем тысяч: «1 234.50 BYN»."""
    return f"{amount:,.2f} {currency or UNKNOWN_CURRENCY}".replace(",", " ").strip()


__all__ = ["UNKNOWN_CURRENCY", "format_money"]
