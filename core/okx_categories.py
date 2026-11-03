"""Массовая разметка OKX-операций (2.57b): отбор неразмеченных и применение категории."""

from __future__ import annotations

from collections.abc import Callable
from datetime import date

from .transaction_filters import ALL_VALUE, in_period, tx_date

SERVICE_CATEGORY_PREFIX = "OKX:"
SERVICE_CATEGORY_LEGACY = "OKX"
# Служебные виды OKX-записей: снимки/открытие/переводы не размечаются категорией.
READ_ONLY_KINDS = frozenset({"snapshot", "opening", "transfer"})
DEFAULT_KIND = "operation"


def is_service_category(category) -> bool:
    """Служебная категория OKX (или пусто) — операция ещё не размечена вручную."""
    text = str(category or "").strip()
    return not text or text == SERVICE_CATEGORY_LEGACY or text.startswith(SERVICE_CATEGORY_PREFIX)


def is_okx_operation(tx) -> bool:
    """OKX-операция, которой можно назначить пользовательскую категорию."""
    if not isinstance(tx, dict):
        return False
    if tx.get("source") != "okx" or tx.get("is_planned"):
        return False
    return str(tx.get("kind") or DEFAULT_KIND) not in READ_ONLY_KINDS


def unlabeled_operations(
    transactions: list[dict],
    *,
    period: str = ALL_VALUE,
    today: date | None = None,
) -> list[dict]:
    """OKX-операции за период без пользовательской категории, новые сверху."""
    current = today or date.today()
    rows = [
        tx
        for tx in transactions
        if is_okx_operation(tx) and is_service_category(tx.get("category")) and in_period(tx_date(tx), period, current)
    ]
    rows.sort(key=lambda tx: (str(tx.get("date") or ""), tx.get("id") or 0), reverse=True)
    return rows


def apply_category(
    rows: list[dict],
    category: str,
    patch: Callable[[int, dict], object],
) -> tuple[int, list[dict]]:
    """Назначить категорию каждой строке через ``patch``; (успешно, неудачные).

    Неудачные строки возвращаются для повтора: повторный вызов с ними не
    создаёт дублей, потому что категория пишется одним PATCH на операцию.
    """
    wanted = str(category or "").strip()
    if not wanted:
        raise ValueError("category is required")
    updated = 0
    failed: list[dict] = []
    for row in rows:
        try:
            patch(row["id"], {"category": wanted})
        except Exception as exc:
            failed.append({"id": row.get("id"), "error": str(exc)})
            continue
        updated += 1
    return updated, failed


__all__ = [
    "DEFAULT_KIND",
    "READ_ONLY_KINDS",
    "SERVICE_CATEGORY_LEGACY",
    "SERVICE_CATEGORY_PREFIX",
    "apply_category",
    "is_okx_operation",
    "is_service_category",
    "unlabeled_operations",
]
