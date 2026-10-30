"""Общие блоки планового экрана: кросс-планы из других приложений и карточка плана (2.48b).

Используются ``PlannedView`` и ``OperationsView``: загрузка планов из задач/событий и
рендер карточки плановой операции у них одинаковые.
"""

from __future__ import annotations

import asyncio
import datetime

from application.api import RestClientError
from application.components.planned_transaction_card import PlannedTransactionCard
from application.display import account_display_name

CROSS_APP_BUDGET_SOURCES = ("task", "calendar")
OFFLINE_PLANS_HINT = "Нет подключения: планы из задач и событий недоступны"
FAILED_PLANS_HINT = "Не удалось загрузить планы из задач и событий"


def filter_cross_app_budgets(items: list[dict]) -> list[dict]:
    """Keep task/calendar budget rows, drop own transactions and duplicates, sort by date."""
    seen: set[tuple] = set()
    result: list[dict] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        if item.get("source_app") not in CROSS_APP_BUDGET_SOURCES:
            continue
        key = (
            item.get("source_app"),
            item.get("source_id"),
            item.get("title"),
            str(item.get("date")),
            str(item.get("amount")),
            item.get("currency"),
        )
        if key in seen:
            continue
        seen.add(key)
        result.append(item)
    result.sort(key=lambda entry: str(entry.get("date") or "9999-12-31"))
    return result


async def load_cross_app_budgets(api_client, transaction_view) -> tuple[list[dict], str]:
    """Планы из задач и событий и подсказка, если они недоступны."""
    if transaction_view is not None and not transaction_view.is_online:
        return [], OFFLINE_PLANS_HINT
    try:
        raw = await asyncio.to_thread(api_client.list_budgets)
    except (RestClientError, AttributeError):
        return [], FAILED_PLANS_HINT
    items = raw.get("results", []) if isinstance(raw, dict) else raw
    return filter_cross_app_budgets(items if isinstance(items, list) else []), ""


def build_plan_card(tx: dict, account_map: dict, *, on_execute, on_edit, on_delete) -> PlannedTransactionCard:
    """Карточка плановой операции; колбэки получают саму операцию."""
    entries = tx.get("entries", [])
    account = account_map.get(entries[0].get("account"), {}) if entries else {}
    return PlannedTransactionCard(
        description=tx.get("description", ""),
        amount=sum(float(entry.get("amount", 0)) for entry in entries),
        account_name=account_display_name(account),
        category=tx.get("category", ""),
        planned_date=_planned_date(tx),
        recurrence_rule=tx.get("recurrence_rule", ""),
        on_execute=lambda: on_execute(tx),
        on_edit=lambda: on_edit(tx),
        on_delete=lambda: on_delete(tx),
    )


def _planned_date(tx: dict) -> datetime.date | None:
    try:
        return datetime.datetime.fromisoformat(str(tx.get("date") or "")).date()
    except (ValueError, TypeError):
        return None


__all__ = [
    "CROSS_APP_BUDGET_SOURCES",
    "FAILED_PLANS_HINT",
    "OFFLINE_PLANS_HINT",
    "build_plan_card",
    "filter_cross_app_budgets",
    "load_cross_app_budgets",
]
