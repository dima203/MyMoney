"""Отображение счетов и сумм в UI-слое MyMoney (fallback-названия, формат ввода)."""

from decimal import Decimal

from core.analytics import is_snapshot_row

ACCOUNT_TYPE_LABELS: dict[str, str] = {
    "main": "Основной",
    "trading": "Торговый",
    "earn": "Доходный",
}

UNKNOWN_ACCOUNT_NAME = "—"
FAB_CLEARANCE = 88
READ_ONLY_BADGE_LABEL = "Снимок OKX"


def is_read_only_transaction(tx: dict) -> bool:
    """Снимок OKX/импорта: серверный флаг `read_only`, fallback — по префиксу.

    Правило общее с аналитикой (`core.analytics.is_snapshot_row`), чтобы такие
    записи не попадали ни в ленту по умолчанию, ни в расходы.
    """
    return is_snapshot_row(tx)


def account_display_name(account: dict, resource_name: str = "") -> str:
    """Название счёта для строки UI; для безымянных — ресурс и тип счёта."""
    name = str(account.get("name") or "").strip()
    if name:
        return name
    base = resource_name.strip() or str(account.get("resource") or "").strip()
    if not base:
        return UNKNOWN_ACCOUNT_NAME
    type_label = ACCOUNT_TYPE_LABELS.get(str(account.get("account_type") or "").strip().lower())
    if type_label:
        return f"{base} ({type_label.lower()})"
    return base


def format_amount_input(value: float) -> str:
    """Сумма для поля «Сумма»: без экспоненты, минимум 2 знака, точный round-trip."""
    amount = abs(float(value))
    text = format(Decimal(repr(amount)), "f")
    if "." in text:
        _, fraction = text.split(".")
        if len(fraction) < 2:
            text += "0" * (2 - len(fraction))
    else:
        text += ".00"
    return text


__all__ = [
    "ACCOUNT_TYPE_LABELS",
    "FAB_CLEARANCE",
    "READ_ONLY_BADGE_LABEL",
    "UNKNOWN_ACCOUNT_NAME",
    "account_display_name",
    "format_amount_input",
    "is_read_only_transaction",
]
