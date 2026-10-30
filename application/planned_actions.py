"""Действия с плановыми операциями: проведение со сдвигом повторения (2.48)."""

from __future__ import annotations

import asyncio
import datetime

from core.recurrence import next_planned_date


def planned_date(tx: dict) -> datetime.date:
    raw = str(tx.get("date") or "")[:10]
    try:
        return datetime.date.fromisoformat(raw)
    except ValueError:
        return datetime.date.today()


def _planned_time(tx: dict) -> datetime.time:
    try:
        return datetime.datetime.fromisoformat(str(tx.get("date") or "")).time()
    except (ValueError, TypeError):
        return datetime.time(9, 0)


def actual_payload(tx: dict, now: datetime.datetime | None = None) -> dict:
    """Тело фактической операции из плановой (is_planned=False)."""
    moment = now or datetime.datetime.now()
    return {
        "date": moment.isoformat(),
        "entries": tx.get("entries", []),
        "category": tx.get("category", ""),
        "description": tx.get("description", ""),
        "is_planned": False,
        "recurrence_rule": tx.get("recurrence_rule", ""),
    }


async def execute_planned(transaction_view, api_client, tx: dict) -> datetime.date | None:
    """Провести план: создать факт и сдвинуть повтор (или удалить план).

    Возвращает новую дату плана, либо None, если план удалён (разовый/серия кончилась).
    """
    add = transaction_view.add if transaction_view else api_client.create_transaction
    await asyncio.to_thread(add, actual_payload(tx))

    rule = tx.get("recurrence_rule", "")
    next_date = next_planned_date(planned_date(tx), rule) if rule else None
    if next_date is None:
        delete = transaction_view.delete if transaction_view else api_client.delete_transaction
        await asyncio.to_thread(delete, tx["id"])
        return None

    payload = {"date": datetime.datetime.combine(next_date, _planned_time(tx)).isoformat()}
    update = transaction_view.update if transaction_view else api_client.update_transaction
    await asyncio.to_thread(update, tx["id"], payload)
    return next_date


__all__ = ["actual_payload", "execute_planned", "planned_date"]
